"""
SAATHI AI -- Intent Classifier Training
========================================
Fine-tunes DistilBERT (distilbert-base-uncased) for 7-class intent classification.

Training strategy:
  Phase 1: 2 epochs -- freeze encoder, train classification head only
  Phase 2: up to 4 epochs -- unfreeze all, full fine-tuning with class weights
             early stop: patience=3 on val macro_f1

Class weights (from spec 03_INTENT_CLASSIFIER.md):
  seek_support=1.5, book_appointment=1.2, crisis_emergency=3.0,
  information_request=1.0, feedback_complaint=1.0, general_chat=1.0,
  assessment_request=2.0

Qualification gates:
  - Test accuracy     >= 88%
  - Test macro F1     >= 0.85
  - crisis_emergency recall >= 95%

Run:
    python "Intent classifier model/scripts/train_intent_distilbert.py"
"""

import json
import logging
import math
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score, classification_report, f1_score, confusion_matrix
)
from torch.optim import AdamW
from torch.optim.lr_scheduler import LinearLR, SequentialLR
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).resolve().parent
BASE_DIR    = SCRIPT_DIR.parent
SPLITS_DIR  = BASE_DIR / "data" / "splits"
MODEL_DIR   = BASE_DIR / "models" / "best_model"
RESULTS_DIR = BASE_DIR / "results"
LOGS_DIR    = BASE_DIR / "logs"
for d in [MODEL_DIR, RESULTS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Logging ──────────────────────────────────────────────────────────────────
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOGS_DIR / f"training_{ts}.log"

fmt = "%(asctime)s [%(levelname)s] %(message)s"
datefmt = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(
    level=logging.INFO,
    format=fmt,
    datefmt=datefmt,
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────
MODEL_NAME   = "distilbert-base-uncased"
MAX_LEN      = 128
BATCH_SIZE   = 16          # CPU-friendly
P1_EPOCHS    = 2
P1_LR        = 1e-3
P2_EPOCHS    = 4
P2_LR        = 3e-5
WARMUP_RATIO = 0.1
PATIENCE     = 3
SEED         = 42

# Class order must match label encoding
INTENT_CLASSES = [
    "seek_support",
    "book_appointment",
    "crisis_emergency",
    "information_request",
    "feedback_complaint",
    "general_chat",
    "assessment_request",
]
LABEL2ID = {c: i for i, c in enumerate(INTENT_CLASSES)}
ID2LABEL = {i: c for i, c in enumerate(INTENT_CLASSES)}

# Class weights per spec: crisis=3.0, assessment=2.0, seek_support=1.5, book=1.2, rest=1.0
CLASS_WEIGHTS = torch.tensor([1.5, 1.2, 3.0, 1.0, 1.0, 1.0, 2.0], dtype=torch.float32)

torch.manual_seed(SEED)
np.random.seed(SEED)


# ─── Dataset ──────────────────────────────────────────────────────────────────
class IntentDataset(Dataset):
    def __init__(self, df, tokenizer):
        self.texts  = df["utterance"].tolist()
        self.labels = df["label"].tolist()
        self.tok    = tokenizer

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        enc = self.tok(
            self.texts[idx],
            max_length=MAX_LEN,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        )
        return {
            "input_ids":      enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels":         torch.tensor(self.labels[idx], dtype=torch.long),
        }


# ─── Training helpers ─────────────────────────────────────────────────────────
def run_epoch(model, loader, optimizer=None, scheduler=None,
              loss_fn=None, device="cpu", train=True):
    model.train(train)
    total_loss, all_preds, all_labels = 0.0, [], []

    for batch in loader:
        input_ids      = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels         = batch["labels"].to(device)

        with torch.set_grad_enabled(train):
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits  = outputs.logits
            loss    = loss_fn(logits, labels)

        if train:
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            if scheduler:
                scheduler.step()

        total_loss += loss.item() * len(labels)
        preds = torch.argmax(logits, dim=-1).cpu().numpy()
        all_preds.extend(preds)
        all_labels.extend(labels.cpu().numpy())

    n = len(all_labels)
    avg_loss = total_loss / n
    acc      = accuracy_score(all_labels, all_preds)
    macro_f1 = f1_score(all_labels, all_preds, average="macro", zero_division=0)
    return avg_loss, acc, macro_f1, all_labels, all_preds


def freeze_encoder(model):
    for name, param in model.named_parameters():
        if "classifier" not in name and "pre_classifier" not in name:
            param.requires_grad = False


def unfreeze_all(model):
    for param in model.parameters():
        param.requires_grad = True


def trainable_count(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()

    log.info("=" * 60)
    log.info("SAATHI AI -- Intent Classifier Training")
    log.info("=" * 60)
    log.info(f"Model      : {MODEL_NAME}")
    log.info(f"Classes    : {INTENT_CLASSES}")
    log.info(f"P1 epochs  : {P1_EPOCHS}  lr={P1_LR}")
    log.info(f"P2 epochs  : {P2_EPOCHS}  lr={P2_LR}")
    log.info(f"Batch size : {BATCH_SIZE} | Max length: {MAX_LEN}")
    log.info(f"Early stop : patience={PATIENCE} on val macro_f1")
    log.info(f"Seed       : {SEED}")
    log.info(f"Log        : {log_file}")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # ── Load data ────────────────────────────────────────────────────────────
    log.info("\nLoading data splits...")
    for split in ["train", "val", "test"]:
        if not (SPLITS_DIR / f"{split}.csv").exists():
            log.error(f"Missing {split}.csv -- run prepare_data_splits.py first")
            sys.exit(1)

    train_df = pd.read_csv(SPLITS_DIR / "train.csv")
    val_df   = pd.read_csv(SPLITS_DIR / "val.csv")
    test_df  = pd.read_csv(SPLITS_DIR / "test.csv")

    for df in [train_df, val_df, test_df]:
        df["label"] = df["primary_intent"].map(LABEL2ID)

    log.info(f"  Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}")

    # ── Device ───────────────────────────────────────────────────────────────
    log.info(f"\nDevice     : {device}")

    # ── Class weights ────────────────────────────────────────────────────────
    log.info("\nClass weights (from spec):")
    for i, (intent, w) in enumerate(zip(INTENT_CLASSES, CLASS_WEIGHTS.tolist())):
        log.info(f"  {intent:<22}: {w:.4f}")

    # ── Tokenizer + Model ────────────────────────────────────────────────────
    log.info(f"\nLoading tokenizer: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    log.info(f"Loading model: {MODEL_NAME} (num_labels={len(INTENT_CLASSES)})")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=len(INTENT_CLASSES),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )
    model.to(device)
    log.info(f"Total parameters: {sum(p.numel() for p in model.parameters()):,}")

    # ── DataLoaders ──────────────────────────────────────────────────────────
    train_ds = IntentDataset(train_df, tokenizer)
    val_ds   = IntentDataset(val_df,   tokenizer)
    test_ds  = IntentDataset(test_df,  tokenizer)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE * 2)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE * 2)

    history = {"phase1": [], "phase2": []}

    # ── PHASE 1: Classifier head only ────────────────────────────────────────
    log.info("\n" + "=" * 60)
    log.info("PHASE 1: Train classifier head only (encoder frozen)")
    log.info("=" * 60)

    freeze_encoder(model)
    log.info(f"Trainable params (Phase 1): {trainable_count(model):,}")

    # Phase 1 uses uniform loss (head warmup)
    p1_loss_fn = nn.CrossEntropyLoss()
    p1_optimizer = AdamW(
        filter(lambda p: p.requires_grad, model.parameters()), lr=P1_LR
    )

    for epoch in range(1, P1_EPOCHS + 1):
        ep_t0 = time.time()
        tr_loss, tr_acc, tr_f1, _, _ = run_epoch(
            model, train_loader, p1_optimizer, loss_fn=p1_loss_fn, device=device
        )
        val_loss, val_acc, val_f1, _, _ = run_epoch(
            model, val_loader, loss_fn=p1_loss_fn, device=device, train=False
        )
        elapsed = int(time.time() - ep_t0)
        log.info(
            f"P1 Epoch {epoch}/{P1_EPOCHS} | "
            f"TrLoss={tr_loss:.4f} TrAcc={tr_acc:.4f} TrF1={tr_f1:.4f} | "
            f"ValLoss={val_loss:.4f} ValAcc={val_acc:.4f} ValF1={val_f1:.4f} | "
            f"{elapsed}s"
        )
        history["phase1"].append({
            "epoch": epoch, "tr_loss": tr_loss, "tr_acc": tr_acc, "tr_f1": tr_f1,
            "val_loss": val_loss, "val_acc": val_acc, "val_f1": val_f1,
        })

    # ── PHASE 2: Full fine-tuning ─────────────────────────────────────────────
    log.info("\n" + "=" * 60)
    log.info("PHASE 2: Full fine-tuning (all layers unfrozen)")
    log.info("=" * 60)

    unfreeze_all(model)
    log.info(f"Trainable params (Phase 2): {trainable_count(model):,}")

    total_steps  = math.ceil(len(train_loader) * P2_EPOCHS)
    warmup_steps = int(total_steps * WARMUP_RATIO)
    log.info(f"Total P2 steps: {total_steps} | Warmup steps: {warmup_steps}")

    p2_loss_fn  = nn.CrossEntropyLoss(weight=CLASS_WEIGHTS.to(device))
    p2_optimizer = AdamW(model.parameters(), lr=P2_LR, weight_decay=0.01)

    warmup_sched = LinearLR(p2_optimizer, start_factor=0.1, end_factor=1.0,
                             total_iters=warmup_steps)
    decay_sched  = LinearLR(p2_optimizer, start_factor=1.0, end_factor=0.0,
                             total_iters=total_steps - warmup_steps)
    scheduler = SequentialLR(p2_optimizer,
                              schedulers=[warmup_sched, decay_sched],
                              milestones=[warmup_steps])

    best_val_f1    = 0.0
    patience_count = 0
    best_epoch     = 0

    for epoch in range(1, P2_EPOCHS + 1):
        ep_t0 = time.time()
        tr_loss, tr_acc, tr_f1, _, _ = run_epoch(
            model, train_loader, p2_optimizer, scheduler,
            loss_fn=p2_loss_fn, device=device
        )
        val_loss, val_acc, val_f1, _, _ = run_epoch(
            model, val_loader, loss_fn=p2_loss_fn, device=device, train=False
        )
        elapsed = int(time.time() - ep_t0)

        improved = val_f1 > best_val_f1
        flag     = " -- NEW BEST -- checkpoint saved" if improved else ""
        log.info(
            f"P2 Epoch {epoch}/{P2_EPOCHS} | "
            f"TrLoss={tr_loss:.4f} TrAcc={tr_acc:.4f} TrF1={tr_f1:.4f} | "
            f"ValLoss={val_loss:.4f} ValAcc={val_acc:.4f} ValF1={val_f1:.4f} | "
            f"{elapsed}s{flag}"
        )
        history["phase2"].append({
            "epoch": epoch, "tr_loss": tr_loss, "tr_acc": tr_acc, "tr_f1": tr_f1,
            "val_loss": val_loss, "val_acc": val_acc, "val_f1": val_f1, "best": improved,
        })

        if improved:
            best_val_f1    = val_f1
            patience_count = 0
            best_epoch     = epoch
            model.save_pretrained(MODEL_DIR)
            tokenizer.save_pretrained(MODEL_DIR)
            with open(MODEL_DIR / "checkpoint_meta.json", "w") as f:
                json.dump({"best_epoch": f"P2 Epoch {epoch}", "val_macro_f1": val_f1,
                           "val_acc": val_acc, "model": MODEL_NAME}, f, indent=2)
        else:
            patience_count += 1
            if patience_count >= PATIENCE:
                log.info(f"Early stopping triggered (patience={PATIENCE})")
                break

    # ── Save training history ─────────────────────────────────────────────────
    history_path = RESULTS_DIR / "training_history.json"
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)
    log.info(f"\nTraining history saved: {history_path}")

    # ── Test Evaluation ───────────────────────────────────────────────────────
    log.info("\n" + "=" * 60)
    log.info(f"TEST EVALUATION (best checkpoint: P2 Epoch {best_epoch})")
    log.info("=" * 60)

    log.info("Reloading best checkpoint from disk...")
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
    model.to(device)

    eval_loss_fn = nn.CrossEntropyLoss(weight=CLASS_WEIGHTS.to(device))
    _, test_acc, test_macro_f1, all_labels, all_preds = run_epoch(
        model, test_loader, loss_fn=eval_loss_fn, device=device, train=False
    )

    log.info(f"\nTest Accuracy    : {test_acc:.4f} ({test_acc * 100:.2f}%)")

    weighted_f1 = f1_score(all_labels, all_preds, average="weighted", zero_division=0)
    log.info(f"Test Weighted F1 : {weighted_f1:.4f}")
    log.info(f"Test Macro F1    : {test_macro_f1:.4f}")

    report = classification_report(
        all_labels, all_preds,
        target_names=INTENT_CLASSES,
        output_dict=True,
        zero_division=0,
    )
    report_txt = classification_report(
        all_labels, all_preds,
        target_names=INTENT_CLASSES,
        zero_division=0,
    )

    log.info("\nPer-class F1 scores (test set):")
    per_class_f1 = {}
    for intent in INTENT_CLASSES:
        f1 = report[intent]["f1-score"]
        per_class_f1[intent] = f1
        log.info(f"  {intent:<22}: {f1:.4f}")

    log.info(f"\nFull Classification Report:\n{report_txt}")

    # ── Crisis emergency recall check ────────────────────────────────────────
    crisis_idx    = LABEL2ID["crisis_emergency"]
    crisis_recall = report["crisis_emergency"]["recall"]

    # ── Confusion matrix ─────────────────────────────────────────────────────
    cm = confusion_matrix(all_labels, all_preds)

    # ── Qualification gates ───────────────────────────────────────────────────
    gate1 = test_acc    >= 0.88
    gate2 = test_macro_f1 >= 0.85
    gate3 = crisis_recall >= 0.95

    log.info("QUALIFICATION GATES:")
    log.info(f"  Accuracy >= 88%              : {'PASS' if gate1 else 'FAIL'} ({test_acc * 100:.2f}%)")
    log.info(f"  Macro F1 >= 0.85             : {'PASS' if gate2 else 'FAIL'} ({test_macro_f1:.4f})")
    log.info(f"  crisis_emergency recall >= 95%: {'PASS' if gate3 else 'FAIL'} ({crisis_recall:.4f})")
    overall = gate1 and gate2 and gate3
    log.info(f"  OVERALL APPROVED             : {'YES' if overall else 'NO -- review needed'}")

    # ── Save results ──────────────────────────────────────────────────────────
    eval_data = {
        "test_accuracy":      round(test_acc, 4),
        "test_weighted_f1":   round(weighted_f1, 4),
        "test_macro_f1":      round(test_macro_f1, 4),
        "per_class_f1":       {k: round(v, 4) for k, v in per_class_f1.items()},
        "per_class_report":   {k: {m: round(v, 4) for m, v in vs.items()}
                                for k, vs in report.items() if k in INTENT_CLASSES},
        "confusion_matrix":   cm.tolist(),
        "qualification_gates": {
            "accuracy_ge_88pct":             gate1,
            "macro_f1_ge_0_85":              gate2,
            "crisis_emergency_recall_ge_95pct": gate3,
            "overall_approved":              overall,
        },
        "best_epoch":         f"P2 Epoch {best_epoch}",
        "best_val_macro_f1":  round(best_val_f1, 4),
        "model":              MODEL_NAME,
        "num_labels":         len(INTENT_CLASSES),
    }

    with open(RESULTS_DIR / "test_evaluation.json", "w") as f:
        json.dump(eval_data, f, indent=2)

    summary_lines = [
        "SAATHI AI -- Intent Classifier -- Test Evaluation Summary",
        "=" * 55,
        f"Test Accuracy    : {test_acc * 100:.2f}%",
        f"Test Macro F1    : {test_macro_f1:.4f}",
        f"Test Weighted F1 : {weighted_f1:.4f}",
        "",
        "Per-class F1:",
    ]
    for intent in INTENT_CLASSES:
        summary_lines.append(f"  {intent:<22}: {per_class_f1[intent]:.4f}")
    summary_lines += [
        "",
        "Qualification Gates:",
        f"  Accuracy >= 88%              : {'PASS' if gate1 else 'FAIL'} ({test_acc * 100:.2f}%)",
        f"  Macro F1 >= 0.85             : {'PASS' if gate2 else 'FAIL'} ({test_macro_f1:.4f})",
        f"  crisis_emergency recall >= 95%: {'PASS' if gate3 else 'FAIL'} ({crisis_recall:.4f})",
        f"  OVERALL APPROVED             : {'YES' if overall else 'NO'}",
    ]
    with open(RESULTS_DIR / "test_evaluation.txt", "w") as f:
        f.write("\n".join(summary_lines))

    elapsed_total = (time.time() - t0) / 60
    log.info(f"\nResults saved: {RESULTS_DIR / 'test_evaluation.json'}")
    log.info(f"Summary saved: {RESULTS_DIR / 'test_evaluation.txt'}")
    log.info(f"Best model  : {MODEL_DIR}")
    log.info(f"Total time  : {elapsed_total:.1f} minutes")
    log.info("\nTraining complete.")


if __name__ == "__main__":
    main()
