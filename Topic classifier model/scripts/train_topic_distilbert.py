"""
SAATHI AI -- Topic Classifier Training (Multi-Label)
=====================================================
Fine-tunes DistilBERT for 5-class multi-label topic classification.

Key differences from Emotion/Intent classifiers:
  - BCEWithLogitsLoss (not CrossEntropyLoss)
  - Sigmoid activation per class (not softmax)
  - Per-class threshold optimization on validation set
  - Metrics: F1_samples, F1_macro, F1_micro (multi-label specific)

Training strategy: 2-phase
  Phase 1: 2 epochs -- freeze encoder, train head only
  Phase 2: up to 4 epochs -- full fine-tuning, early stop on val F1_samples

Qualification gates:
  - F1_samples >= 0.82
  - F1_macro   >= 0.80
  - Per-class F1 >= 0.75 for all 5 classes

Run:
    python "Topic classifier model/scripts/train_topic_distilbert.py"
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
    f1_score, classification_report
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
ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOGS_DIR / f"training_{ts}.log"
fmt      = "%(asctime)s [%(levelname)s] %(message)s"
datefmt  = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(
    level=logging.INFO, format=fmt, datefmt=datefmt,
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────
MODEL_NAME   = "distilbert-base-uncased"
MAX_LEN      = 128
BATCH_SIZE   = 16
P1_EPOCHS    = 2
P1_LR        = 1e-3
P2_EPOCHS    = 4
P2_LR        = 3e-5
WARMUP_RATIO = 0.1
PATIENCE     = 3
THRESHOLD    = 0.50      # default classification threshold
SEED         = 42

TOPICS = [
    "workplace_stress",
    "relationship_issues",
    "academic_stress",
    "health_concerns",
    "financial_stress",
]
NUM_LABELS = len(TOPICS)

torch.manual_seed(SEED)
np.random.seed(SEED)


# ─── Dataset (multi-label) ────────────────────────────────────────────────────
class TopicDataset(Dataset):
    def __init__(self, df, tokenizer):
        self.texts = df["utterance"].tolist()
        self.tok   = tokenizer
        # Build binary label matrix
        self.labels = np.zeros((len(df), NUM_LABELS), dtype=np.float32)
        for i, row in enumerate(df["topics"]):
            for t in json.loads(row):
                if t in TOPICS:
                    self.labels[i, TOPICS.index(t)] = 1.0

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
            "labels":         torch.tensor(self.labels[idx], dtype=torch.float32),
        }


# ─── Helpers ──────────────────────────────────────────────────────────────────
def sigmoid_np(x):
    return 1.0 / (1.0 + np.exp(-x))


def run_epoch(model, loader, optimizer=None, scheduler=None,
              loss_fn=None, device="cpu", train=True):
    model.train(train)
    total_loss  = 0.0
    all_logits  = []
    all_labels  = []

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
        all_logits.append(logits.detach().cpu().numpy())
        all_labels.append(labels.detach().cpu().numpy())

    n          = sum(len(l) for l in all_labels)
    avg_loss   = total_loss / n
    logits_arr = np.vstack(all_logits)
    labels_arr = np.vstack(all_labels)
    probs_arr  = sigmoid_np(logits_arr)
    preds_arr  = (probs_arr >= THRESHOLD).astype(int)

    f1_samp = f1_score(labels_arr, preds_arr, average="samples",  zero_division=0)
    f1_mac  = f1_score(labels_arr, preds_arr, average="macro",    zero_division=0)
    f1_mic  = f1_score(labels_arr, preds_arr, average="micro",    zero_division=0)
    return avg_loss, f1_samp, f1_mac, f1_mic, logits_arr, labels_arr


def optimize_thresholds(logits, labels):
    """Find per-class threshold maximising per-class F1 on validation set."""
    probs  = sigmoid_np(logits)
    thresholds = {}
    for i, topic in enumerate(TOPICS):
        best_f1, best_t = 0.0, 0.50
        for t in np.arange(0.25, 0.80, 0.05):
            preds = (probs[:, i] >= t).astype(int)
            f1    = f1_score(labels[:, i], preds, zero_division=0)
            if f1 > best_f1:
                best_f1, best_t = f1, t
        thresholds[topic] = round(float(best_t), 2)
        log.info(f"  {topic:<24}: optimal threshold={best_t:.2f}  F1={best_f1:.4f}")
    return thresholds


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
    log.info("SAATHI AI -- Topic Classifier Training (Multi-Label)")
    log.info("=" * 60)
    log.info(f"Model      : {MODEL_NAME}")
    log.info(f"Topics     : {TOPICS}")
    log.info(f"P1 epochs  : {P1_EPOCHS}  lr={P1_LR}")
    log.info(f"P2 epochs  : {P2_EPOCHS}  lr={P2_LR}")
    log.info(f"Batch size : {BATCH_SIZE} | Max length: {MAX_LEN}")
    log.info(f"Loss       : BCEWithLogitsLoss (multi-label)")
    log.info(f"Early stop : patience={PATIENCE} on val F1_samples")
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
    log.info(f"  Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}")
    log.info(f"  Device: {device}")

    # ── Tokenizer + Model ────────────────────────────────────────────────────
    log.info(f"\nLoading tokenizer: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    log.info(f"Loading model: {MODEL_NAME} (num_labels={NUM_LABELS}, multi_label)")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_LABELS,
        problem_type="multi_label_classification",
        id2label={i: t for i, t in enumerate(TOPICS)},
        label2id={t: i for i, t in enumerate(TOPICS)},
    )
    model.to(device)
    log.info(f"Total parameters: {sum(p.numel() for p in model.parameters()):,}")

    # ── DataLoaders ──────────────────────────────────────────────────────────
    train_ds = TopicDataset(train_df, tokenizer)
    val_ds   = TopicDataset(val_df,   tokenizer)
    test_ds  = TopicDataset(test_df,  tokenizer)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE * 2)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE * 2)

    loss_fn = nn.BCEWithLogitsLoss()
    history = {"phase1": [], "phase2": []}

    # ── PHASE 1: Head warmup ──────────────────────────────────────────────────
    log.info("\n" + "=" * 60)
    log.info("PHASE 1: Train classifier head only (encoder frozen)")
    log.info("=" * 60)

    freeze_encoder(model)
    log.info(f"Trainable params (Phase 1): {trainable_count(model):,}")

    p1_opt = AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=P1_LR)

    for epoch in range(1, P1_EPOCHS + 1):
        ep_t0 = time.time()
        tr_loss, tr_f1s, tr_f1m, tr_f1i, _, _ = run_epoch(
            model, train_loader, p1_opt, loss_fn=loss_fn, device=device
        )
        val_loss, val_f1s, val_f1m, val_f1i, _, _ = run_epoch(
            model, val_loader, loss_fn=loss_fn, device=device, train=False
        )
        elapsed = int(time.time() - ep_t0)
        log.info(
            f"P1 Epoch {epoch}/{P1_EPOCHS} | "
            f"TrLoss={tr_loss:.4f} TrF1s={tr_f1s:.4f} TrF1m={tr_f1m:.4f} | "
            f"ValLoss={val_loss:.4f} ValF1s={val_f1s:.4f} ValF1m={val_f1m:.4f} | {elapsed}s"
        )
        history["phase1"].append({
            "epoch": epoch, "tr_loss": tr_loss, "tr_f1_samples": tr_f1s, "tr_f1_macro": tr_f1m,
            "val_loss": val_loss, "val_f1_samples": val_f1s, "val_f1_macro": val_f1m,
        })

    # ── PHASE 2: Full fine-tuning ─────────────────────────────────────────────
    log.info("\n" + "=" * 60)
    log.info("PHASE 2: Full fine-tuning (all layers unfrozen)")
    log.info("=" * 60)

    unfreeze_all(model)
    log.info(f"Trainable params (Phase 2): {trainable_count(model):,}")

    total_steps  = math.ceil(len(train_loader) * P2_EPOCHS)
    warmup_steps = int(total_steps * WARMUP_RATIO)
    log.info(f"Total P2 steps: {total_steps} | Warmup: {warmup_steps}")

    p2_opt   = AdamW(model.parameters(), lr=P2_LR, weight_decay=0.01)
    warm_sch = LinearLR(p2_opt, start_factor=0.1, end_factor=1.0, total_iters=warmup_steps)
    deca_sch = LinearLR(p2_opt, start_factor=1.0, end_factor=0.0, total_iters=total_steps - warmup_steps)
    scheduler = SequentialLR(p2_opt, schedulers=[warm_sch, deca_sch], milestones=[warmup_steps])

    best_val_f1s   = 0.0
    best_val_logits = None
    best_val_labels = None
    patience_count = 0
    best_epoch     = 0

    for epoch in range(1, P2_EPOCHS + 1):
        ep_t0 = time.time()
        tr_loss, tr_f1s, tr_f1m, tr_f1i, _, _ = run_epoch(
            model, train_loader, p2_opt, scheduler, loss_fn=loss_fn, device=device
        )
        val_loss, val_f1s, val_f1m, val_f1i, val_logits, val_labels = run_epoch(
            model, val_loader, loss_fn=loss_fn, device=device, train=False
        )
        elapsed = int(time.time() - ep_t0)

        improved = val_f1s > best_val_f1s
        flag     = " -- NEW BEST -- checkpoint saved" if improved else ""
        log.info(
            f"P2 Epoch {epoch}/{P2_EPOCHS} | "
            f"TrLoss={tr_loss:.4f} TrF1s={tr_f1s:.4f} TrF1m={tr_f1m:.4f} | "
            f"ValLoss={val_loss:.4f} ValF1s={val_f1s:.4f} ValF1m={val_f1m:.4f} | "
            f"{elapsed}s{flag}"
        )
        history["phase2"].append({
            "epoch": epoch, "tr_loss": tr_loss, "tr_f1_samples": tr_f1s, "tr_f1_macro": tr_f1m,
            "val_loss": val_loss, "val_f1_samples": val_f1s, "val_f1_macro": val_f1m, "best": improved,
        })

        if improved:
            best_val_f1s    = val_f1s
            best_val_logits = val_logits
            best_val_labels = val_labels
            patience_count  = 0
            best_epoch      = epoch
            model.save_pretrained(MODEL_DIR)
            tokenizer.save_pretrained(MODEL_DIR)
        else:
            patience_count += 1
            if patience_count >= PATIENCE:
                log.info(f"Early stopping triggered (patience={PATIENCE})")
                break

    # ── Threshold optimization on validation set ──────────────────────────────
    log.info("\nOptimizing per-class classification thresholds on validation set...")
    thresholds = optimize_thresholds(best_val_logits, best_val_labels)
    with open(MODEL_DIR / "thresholds.json", "w") as f:
        json.dump(thresholds, f, indent=2)
    log.info(f"Thresholds saved: {MODEL_DIR / 'thresholds.json'}")

    # ── Save training history ─────────────────────────────────────────────────
    with open(RESULTS_DIR / "training_history.json", "w") as f:
        json.dump(history, f, indent=2)
    log.info(f"\nTraining history saved.")

    # ── Test Evaluation ───────────────────────────────────────────────────────
    log.info("\n" + "=" * 60)
    log.info(f"TEST EVALUATION (best checkpoint: P2 Epoch {best_epoch})")
    log.info("=" * 60)

    log.info("Reloading best checkpoint from disk...")
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
    model.to(device)

    _, _, _, _, test_logits, test_labels = run_epoch(
        model, test_loader, loss_fn=loss_fn, device=device, train=False
    )

    test_probs = sigmoid_np(test_logits)

    # Apply optimized thresholds
    test_preds_opt = np.zeros_like(test_probs, dtype=int)
    for i, topic in enumerate(TOPICS):
        t = thresholds.get(topic, 0.50)
        test_preds_opt[:, i] = (test_probs[:, i] >= t).astype(int)

    # Also compute with default 0.50 threshold
    test_preds_def = (test_probs >= 0.50).astype(int)

    f1_samp_opt = f1_score(test_labels, test_preds_opt, average="samples",  zero_division=0)
    f1_mac_opt  = f1_score(test_labels, test_preds_opt, average="macro",    zero_division=0)
    f1_mic_opt  = f1_score(test_labels, test_preds_opt, average="micro",    zero_division=0)
    f1_samp_def = f1_score(test_labels, test_preds_def, average="samples",  zero_division=0)
    f1_mac_def  = f1_score(test_labels, test_preds_def, average="macro",    zero_division=0)

    log.info(f"\nWith optimized thresholds:")
    log.info(f"  F1 (samples) : {f1_samp_opt:.4f}")
    log.info(f"  F1 (macro)   : {f1_mac_opt:.4f}")
    log.info(f"  F1 (micro)   : {f1_mic_opt:.4f}")
    log.info(f"\nWith default threshold (0.50):")
    log.info(f"  F1 (samples) : {f1_samp_def:.4f}")
    log.info(f"  F1 (macro)   : {f1_mac_def:.4f}")

    log.info("\nPer-class F1 (optimized thresholds):")
    per_class_f1 = {}
    for i, topic in enumerate(TOPICS):
        f1 = f1_score(test_labels[:, i], test_preds_opt[:, i], zero_division=0)
        per_class_f1[topic] = float(f1)
        log.info(f"  {topic:<24}: {f1:.4f}  (threshold={thresholds[topic]:.2f})")

    # Per-class detailed report
    report = {}
    for i, topic in enumerate(TOPICS):
        tp = int(np.sum((test_preds_opt[:, i] == 1) & (test_labels[:, i] == 1)))
        fp = int(np.sum((test_preds_opt[:, i] == 1) & (test_labels[:, i] == 0)))
        fn = int(np.sum((test_preds_opt[:, i] == 0) & (test_labels[:, i] == 1)))
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        report[topic] = {"precision": round(prec, 4), "recall": round(rec, 4),
                         "f1": round(f1, 4), "support": int(test_labels[:, i].sum())}

    # Multi-label accuracy (exact match)
    exact_match = float(np.mean(np.all(test_preds_opt == test_labels, axis=1)))
    log.info(f"\nExact match (all labels correct): {exact_match:.4f} ({exact_match*100:.2f}%)")

    # ── Qualification gates ───────────────────────────────────────────────────
    gate1 = f1_samp_opt >= 0.82
    gate2 = f1_mac_opt  >= 0.80
    gate3 = all(v >= 0.75 for v in per_class_f1.values())
    overall = gate1 and gate2 and gate3

    log.info("\nQUALIFICATION GATES:")
    log.info(f"  F1_samples >= 0.82       : {'PASS' if gate1 else 'FAIL'} ({f1_samp_opt:.4f})")
    log.info(f"  F1_macro   >= 0.80       : {'PASS' if gate2 else 'FAIL'} ({f1_mac_opt:.4f})")
    log.info(f"  All per-class F1 >= 0.75 : {'PASS' if gate3 else 'FAIL'}")
    for topic, f1 in per_class_f1.items():
        log.info(f"    {topic:<24}: {f1:.4f} {'OK' if f1 >= 0.75 else 'BELOW'}")
    log.info(f"  OVERALL APPROVED         : {'YES' if overall else 'NO -- review needed'}")

    # ── Save results ──────────────────────────────────────────────────────────
    eval_data = {
        "f1_samples_optimized": round(f1_samp_opt, 4),
        "f1_macro_optimized":   round(f1_mac_opt,  4),
        "f1_micro_optimized":   round(f1_mic_opt,  4),
        "f1_samples_default":   round(f1_samp_def, 4),
        "f1_macro_default":     round(f1_mac_def,  4),
        "exact_match":          round(exact_match, 4),
        "per_class_report":     report,
        "per_class_f1":         {k: round(v, 4) for k, v in per_class_f1.items()},
        "thresholds_applied":   thresholds,
        "qualification_gates": {
            "f1_samples_ge_0_82":     gate1,
            "f1_macro_ge_0_80":       gate2,
            "all_per_class_f1_ge_75": gate3,
            "overall_approved":       overall,
        },
        "best_epoch":   f"P2 Epoch {best_epoch}",
        "best_val_f1_samples": round(best_val_f1s, 4),
        "model":        MODEL_NAME,
        "num_labels":   NUM_LABELS,
    }
    with open(RESULTS_DIR / "test_evaluation.json", "w") as f:
        json.dump(eval_data, f, indent=2)

    summary = [
        "SAATHI AI -- Topic Classifier -- Test Evaluation Summary",
        "=" * 55,
        f"F1 Samples (optimized thresholds): {f1_samp_opt:.4f}",
        f"F1 Macro   (optimized thresholds): {f1_mac_opt:.4f}",
        f"F1 Micro   (optimized thresholds): {f1_mic_opt:.4f}",
        f"Exact Match Accuracy             : {exact_match*100:.2f}%",
        "",
        "Per-class F1 (optimized thresholds):",
    ]
    for topic in TOPICS:
        summary.append(f"  {topic:<24}: {per_class_f1[topic]:.4f}  (thresh={thresholds[topic]:.2f})")
    summary += [
        "",
        "Qualification Gates:",
        f"  F1_samples >= 0.82       : {'PASS' if gate1 else 'FAIL'} ({f1_samp_opt:.4f})",
        f"  F1_macro   >= 0.80       : {'PASS' if gate2 else 'FAIL'} ({f1_mac_opt:.4f})",
        f"  All per-class F1 >= 0.75 : {'PASS' if gate3 else 'FAIL'}",
        f"  OVERALL APPROVED         : {'YES' if overall else 'NO'}",
    ]
    with open(RESULTS_DIR / "test_evaluation.txt", "w") as f:
        f.write("\n".join(summary))

    # Save checkpoint meta
    with open(MODEL_DIR / "checkpoint_meta.json", "w") as f:
        json.dump({"best_epoch": f"P2 Epoch {best_epoch}",
                   "val_f1_samples": round(best_val_f1s, 4),
                   "model": MODEL_NAME, "problem_type": "multi_label"}, f, indent=2)

    elapsed_total = (time.time() - t0) / 60
    log.info(f"\nResults saved: {RESULTS_DIR / 'test_evaluation.json'}")
    log.info(f"Best model  : {MODEL_DIR}")
    log.info(f"Total time  : {elapsed_total:.1f} minutes")
    log.info("\nTraining complete.")


if __name__ == "__main__":
    main()
