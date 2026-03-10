"""
SAATHI AI -- Phase 3 Crisis Detection Model Training
=====================================================
DistilBERT 6-class classifier for lower-risk crisis spectrum.
Trained on Phase 3 dataset: 1,500 C-SSRS-aligned examples.

Classes:
  0 -> safe                     (no crisis indicators)
  1 -> passive_ideation         (passive death wish, no plan)
  2 -> mild_distress            (significant distress, no ideation)
  3 -> moderate_concern         (active ideation, no method)
  4 -> elevated_monitoring      (ideation with some method consideration)
  5 -> pre_crisis_intervention  (imminent risk, specific plan forming)

Safety Gate design:
  - Classes 4 and 5 = HIGH-RISK: target ? 98% recall
  - Class weights:  [0.5, 0.7, 0.85, 1.0, 3.5, 12.0]
  - Safety threshold: if P(class4 or class5) > 0.15 -> force high-risk
  - Early stopping monitors high-risk recall, not loss

Run:
    python scripts/train_phase3_distilbert.py

Output:
    models/best_model/          (best high-risk-recall checkpoint)
    results/training_metrics.json
    results/test_evaluation.json
    logs/training.log
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
)
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

# -- Paths ---------------------------------------------------------------------
BASE_DIR    = Path(__file__).resolve().parent.parent
DATA_DIR    = BASE_DIR / "data" / "splits"
MODEL_DIR   = BASE_DIR / "models" / "best_model"
RESULTS_DIR = BASE_DIR / "results"
LOG_DIR     = BASE_DIR / "logs"

for d in [MODEL_DIR, RESULTS_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# -- Logging -------------------------------------------------------------------
log_path = LOG_DIR / f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# -- Hyperparameters -----------------------------------------------------------
BASE_MODEL    = "distilbert-base-uncased"
NUM_LABELS    = 6
MAX_LENGTH    = 128
BATCH_SIZE    = 16
NUM_EPOCHS    = 25
LEARNING_RATE = 3e-5
WARMUP_RATIO  = 0.1
RANDOM_SEED   = 42

# Class weights from guide (imbalance ratio 20:1, Class 5 gets 12?)
CLASS_WEIGHTS  = torch.tensor([0.5, 0.7, 0.85, 1.0, 3.5, 12.0], dtype=torch.float)

# Safety gate
HIGH_RISK_CLASSES  = [4, 5]
SAFETY_THRESHOLD   = 0.15    # P(class4 or class5) > this -> force high-risk
HIGH_RISK_RECALL_TARGET = 0.98

# Early stopping
ES_PATIENCE = 3              # epochs without high-risk recall improvement

CLASS_NAMES = [
    "safe",
    "passive_ideation",
    "mild_distress",
    "moderate_concern",
    "elevated_monitoring",
    "pre_crisis_intervention",
]

# -- Reproducibility -----------------------------------------------------------
torch.manual_seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


# -- Dataset -------------------------------------------------------------------

class Phase3Dataset(Dataset):
    """Loads Phase 3 crisis CSV and tokenizes utterances on the fly."""

    def __init__(self, csv_path: Path, tokenizer, max_length: int = 128):
        self.rows = []
        self.tokenizer = tokenizer
        self.max_length = max_length

        with open(csv_path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                self.rows.append({
                    "text":  row["utterance"].strip(),
                    "label": int(row["crisis_label"]),
                })

        label_counts = {}
        for r in self.rows:
            label_counts[r["label"]] = label_counts.get(r["label"], 0) + 1
        logger.info(f"Loaded {len(self.rows)} rows from {csv_path.name}: {dict(sorted(label_counts.items()))}")

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        item  = self.rows[idx]
        enc   = self.tokenizer(
            item["text"],
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids":      enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "label":          torch.tensor(item["label"], dtype=torch.long),
        }


# -- Metrics -------------------------------------------------------------------

def compute_metrics(labels: list, preds: list) -> dict:
    """Compute overall + per-class + high-risk metrics."""
    labels = np.array(labels)
    preds  = np.array(preds)

    acc     = float((labels == preds).mean())
    w_f1    = float(f1_score(labels, preds, average="weighted", zero_division=0))
    mac_f1  = float(f1_score(labels, preds, average="macro",    zero_division=0))

    # Per-class recall for high-risk classes
    hr_true = np.isin(labels, HIGH_RISK_CLASSES).astype(int)
    hr_pred = np.isin(preds,  HIGH_RISK_CLASSES).astype(int)
    tp = int(((hr_true == 1) & (hr_pred == 1)).sum())
    fn = int(((hr_true == 1) & (hr_pred == 0)).sum())
    hr_recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    report = classification_report(
        labels, preds,
        target_names=CLASS_NAMES,
        zero_division=0,
        output_dict=True,
    )
    cm = confusion_matrix(labels, preds).tolist()

    return {
        "accuracy":        round(acc,     4),
        "weighted_f1":     round(w_f1,    4),
        "macro_f1":        round(mac_f1,  4),
        "high_risk_recall": round(hr_recall, 4),
        "false_negatives_high_risk": fn,
        "per_class":       report,
        "confusion_matrix": cm,
    }


def safety_gate_predict(logits: torch.Tensor) -> torch.Tensor:
    """
    Apply safety threshold: if max P(class 4 or 5) > SAFETY_THRESHOLD
    -> force prediction to whichever high-risk class has higher probability.
    Operates on a batch of logits [B, 6].
    """
    probs = torch.softmax(logits, dim=1)       # [B, 6]
    hr_probs = probs[:, HIGH_RISK_CLASSES]     # [B, 2]
    hr_max, hr_argmax = hr_probs.max(dim=1)    # [B]

    normal_preds = probs.argmax(dim=1)         # [B]
    forced_preds = torch.tensor(
        [HIGH_RISK_CLASSES[i] for i in hr_argmax.tolist()],
        dtype=torch.long,
        device=logits.device,
    )
    mask = hr_max > SAFETY_THRESHOLD
    return torch.where(mask, forced_preds, normal_preds)


# -- Training ------------------------------------------------------------------

def train_epoch(model, loader, optimizer, scheduler, device, loss_fn) -> dict:
    model.train()
    total_loss = 0.0
    all_labels, all_preds = [], []

    for batch in loader:
        input_ids  = batch["input_ids"].to(device)
        attn_mask  = batch["attention_mask"].to(device)
        labels     = batch["label"].to(device)

        optimizer.zero_grad()
        outputs = model(input_ids=input_ids, attention_mask=attn_mask)
        loss    = loss_fn(outputs.logits, labels)
        loss.backward()

        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()

        total_loss += loss.item()
        preds = safety_gate_predict(outputs.logits)
        all_labels.extend(labels.cpu().tolist())
        all_preds.extend(preds.cpu().tolist())

    metrics = compute_metrics(all_labels, all_preds)
    metrics["loss"] = round(total_loss / len(loader), 4)
    return metrics


@torch.no_grad()
def evaluate(model, loader, device, loss_fn) -> dict:
    model.eval()
    total_loss = 0.0
    all_labels, all_preds = [], []

    for batch in loader:
        input_ids  = batch["input_ids"].to(device)
        attn_mask  = batch["attention_mask"].to(device)
        labels     = batch["label"].to(device)

        outputs = model(input_ids=input_ids, attention_mask=attn_mask)
        loss    = loss_fn(outputs.logits, labels)
        total_loss += loss.item()

        preds = safety_gate_predict(outputs.logits)
        all_labels.extend(labels.cpu().tolist())
        all_preds.extend(preds.cpu().tolist())

    metrics = compute_metrics(all_labels, all_preds)
    metrics["loss"] = round(total_loss / len(loader), 4)
    return metrics


# -- Main ----------------------------------------------------------------------

def main():
    start_time = time.time()
    logger.info("=" * 70)
    logger.info("SAATHI AI -- Phase 3 Crisis Detection Training")
    logger.info(f"Model        : {BASE_MODEL}")
    logger.info(f"Num classes  : {NUM_LABELS}")
    logger.info(f"Epochs       : {NUM_EPOCHS}")
    logger.info(f"Batch size   : {BATCH_SIZE}")
    logger.info(f"Learning rate: {LEARNING_RATE}")
    logger.info(f"Class weights: {CLASS_WEIGHTS.tolist()}")
    logger.info(f"Safety thresh: {SAFETY_THRESHOLD}")
    logger.info(f"HR target    : {HIGH_RISK_RECALL_TARGET}")
    logger.info("=" * 70)

    device = torch.device("cpu")
    logger.info(f"Device: {device} (CPU inference -- no GPU detected)")

    # -- Load tokenizer & model ------------------------------------------------
    logger.info(f"Loading tokenizer: {BASE_MODEL} ...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    logger.info(f"Loading model architecture: {BASE_MODEL} ...")
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=NUM_LABELS,
        ignore_mismatched_sizes=True,
    )
    model.to(device)

    total_params = sum(p.numel() for p in model.parameters())
    trainable    = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Model parameters: {total_params:,} total, {trainable:,} trainable")

    # -- Datasets & Loaders ----------------------------------------------------
    logger.info("Loading datasets ...")
    train_ds = Phase3Dataset(DATA_DIR / "train.csv", tokenizer, MAX_LENGTH)
    val_ds   = Phase3Dataset(DATA_DIR / "val.csv",   tokenizer, MAX_LENGTH)
    test_ds  = Phase3Dataset(DATA_DIR / "test.csv",  tokenizer, MAX_LENGTH)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False)

    logger.info(f"Train batches: {len(train_loader)} | Val batches: {len(val_loader)} | Test batches: {len(test_loader)}")

    # -- Loss, optimizer, scheduler --------------------------------------------
    loss_fn   = nn.CrossEntropyLoss(weight=CLASS_WEIGHTS.to(device))
    optimizer = AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)

    total_steps   = len(train_loader) * NUM_EPOCHS
    warmup_steps  = int(total_steps * WARMUP_RATIO)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )
    logger.info(f"Total steps: {total_steps} | Warmup steps: {warmup_steps}")

    # -- Training loop ---------------------------------------------------------
    best_hr_recall = 0.0
    patience_counter = 0
    history = []

    for epoch in range(1, NUM_EPOCHS + 1):
        epoch_start = time.time()
        logger.info(f"\n{'-'*60}")
        logger.info(f"Epoch {epoch}/{NUM_EPOCHS}")

        train_m = train_epoch(model, train_loader, optimizer, scheduler, device, loss_fn)
        val_m   = evaluate(model, val_loader, device, loss_fn)

        epoch_secs = time.time() - epoch_start

        logger.info(
            f"  Train -> loss:{train_m['loss']:.4f} "
            f"acc:{train_m['accuracy']:.4f} "
            f"w_f1:{train_m['weighted_f1']:.4f} "
            f"hr_recall:{train_m['high_risk_recall']:.4f} "
            f"hr_fn:{train_m['false_negatives_high_risk']}"
        )
        logger.info(
            f"  Val   -> loss:{val_m['loss']:.4f} "
            f"acc:{val_m['accuracy']:.4f} "
            f"w_f1:{val_m['weighted_f1']:.4f} "
            f"hr_recall:{val_m['high_risk_recall']:.4f} "
            f"hr_fn:{val_m['false_negatives_high_risk']}"
        )
        logger.info(f"  Time  : {epoch_secs:.1f}s")

        epoch_record = {
            "epoch": epoch,
            "train": {k: v for k, v in train_m.items() if k not in ("per_class", "confusion_matrix")},
            "val":   {k: v for k, v in val_m.items()   if k not in ("per_class", "confusion_matrix")},
            "epoch_seconds": round(epoch_secs, 1),
        }
        history.append(epoch_record)

        # -- SafetyGate Early Stopping: save on val high-risk recall improvement --
        val_hr = val_m["high_risk_recall"]
        if val_hr > best_hr_recall:
            best_hr_recall = val_hr
            patience_counter = 0
            logger.info(f"  *** New best high-risk recall: {best_hr_recall:.4f} -- saving checkpoint ***")
            model.save_pretrained(str(MODEL_DIR))
            tokenizer.save_pretrained(str(MODEL_DIR))

            # Save checkpoint metadata
            ckpt_meta = {
                "epoch": epoch,
                "val_high_risk_recall": val_hr,
                "val_accuracy":   val_m["accuracy"],
                "val_weighted_f1": val_m["weighted_f1"],
                "val_false_negatives_high_risk": val_m["false_negatives_high_risk"],
                "saved_at": datetime.now().isoformat(),
            }
            with open(MODEL_DIR / "checkpoint_meta.json", "w") as f:
                json.dump(ckpt_meta, f, indent=2)
        else:
            patience_counter += 1
            logger.info(f"  No improvement ({patience_counter}/{ES_PATIENCE})")

        if patience_counter >= ES_PATIENCE:
            logger.info(f"\nEarly stopping triggered at epoch {epoch} (patience={ES_PATIENCE}).")
            logger.info(f"Best val high-risk recall: {best_hr_recall:.4f}")
            break

        # -- Progress checkpoint -------------------------------------------------
        if epoch % 5 == 0:
            with open(RESULTS_DIR / "training_history_partial.json", "w") as f:
                json.dump(history, f, indent=2)

    # -- Save full training history ---------------------------------------------
    with open(RESULTS_DIR / "training_history.json", "w") as f:
        json.dump(history, f, indent=2)
    logger.info(f"\nTraining history saved: {RESULTS_DIR / 'training_history.json'}")

    # -- Final test evaluation on best checkpoint -------------------------------
    logger.info("\n" + "=" * 70)
    logger.info("FINAL TEST EVALUATION (best checkpoint)")
    logger.info("=" * 70)

    best_model = AutoModelForSequenceClassification.from_pretrained(
        str(MODEL_DIR), num_labels=NUM_LABELS
    ).to(device)
    best_tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))

    best_test_ds     = Phase3Dataset(DATA_DIR / "test.csv", best_tokenizer, MAX_LENGTH)
    best_test_loader = DataLoader(best_test_ds, batch_size=BATCH_SIZE, shuffle=False)

    test_m = evaluate(best_model, best_test_loader, device, loss_fn)

    logger.info(f"Test Accuracy        : {test_m['accuracy']:.4f}")
    logger.info(f"Test Weighted F1     : {test_m['weighted_f1']:.4f}")
    logger.info(f"Test Macro F1        : {test_m['macro_f1']:.4f}")
    logger.info(f"Test High-Risk Recall: {test_m['high_risk_recall']:.4f}")
    logger.info(f"Test HR False Negatives: {test_m['false_negatives_high_risk']}")

    # Safety gate verdict
    hr_pass     = test_m["high_risk_recall"] >= HIGH_RISK_RECALL_TARGET
    wf1_pass    = test_m["weighted_f1"] >= 0.75
    fn_pass     = test_m["false_negatives_high_risk"] == 0

    logger.info("\n" + "-" * 60)
    logger.info("SAFETY GATE REQUIREMENTS:")
    logger.info(f"  High-risk recall >= {HIGH_RISK_RECALL_TARGET} : {'PASS' if hr_pass else 'FAIL'} ({test_m['high_risk_recall']:.4f})")
    logger.info(f"  Weighted F1 >= 0.75              : {'PASS' if wf1_pass else 'FAIL'} ({test_m['weighted_f1']:.4f})")
    logger.info(f"  Zero false negatives (HR)        : {'PASS' if fn_pass else 'FAIL'} ({test_m['false_negatives_high_risk']} FN)")
    overall_pass = hr_pass and fn_pass
    logger.info(f"\n  OVERALL: {'PASS APPROVED for gated deployment' if overall_pass else 'FAIL REQUIRES re-training'}")

    # Per-class detail
    logger.info("\nPer-class report:")
    for cls, stats in test_m["per_class"].items():
        if isinstance(stats, dict):
            logger.info(
                f"  {cls:<30} precision:{stats.get('precision', 0):.2f}  "
                f"recall:{stats.get('recall', 0):.2f}  "
                f"f1:{stats.get('f1-score', 0):.2f}  "
                f"support:{int(stats.get('support', 0))}"
            )

    # Save test results
    total_secs = time.time() - start_time
    test_results = {
        "model":            BASE_MODEL,
        "phase":            "Phase 3 -- Lower-Risk 6-Class",
        "trained_at":       datetime.now().isoformat(),
        "training_seconds": round(total_secs),
        "best_val_hr_recall": best_hr_recall,
        "test_metrics":     test_m,
        "safety_requirements": {
            "high_risk_recall_pass": hr_pass,
            "weighted_f1_pass":      wf1_pass,
            "zero_fn_pass":          fn_pass,
            "overall_approved":      overall_pass,
        },
        "config": {
            "num_labels":      NUM_LABELS,
            "max_length":      MAX_LENGTH,
            "batch_size":      BATCH_SIZE,
            "num_epochs":      NUM_EPOCHS,
            "learning_rate":   LEARNING_RATE,
            "class_weights":   CLASS_WEIGHTS.tolist(),
            "safety_threshold": SAFETY_THRESHOLD,
            "high_risk_classes": HIGH_RISK_CLASSES,
            "random_seed":     RANDOM_SEED,
        },
    }
    result_path = RESULTS_DIR / "test_evaluation.json"
    with open(result_path, "w") as f:
        json.dump(test_results, f, indent=2)
    logger.info(f"\nTest evaluation saved: {result_path}")

    # Human-readable summary
    summary_lines = [
        "PHASE 3 CRISIS DETECTION MODEL -- TEST EVALUATION SUMMARY",
        "=========================================================",
        "",
        f"Model     : {BASE_MODEL} fine-tuned (6-class)",
        f"Phase     : Phase 3 -- Lower-Risk Crisis Spectrum",
        f"Test set  : {len(test_ds)} samples",
        f"Trained   : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Duration  : {round(total_secs/3600, 1)} hours",
        "",
        "RESULTS",
        "-------",
        f"Accuracy        : {test_m['accuracy']:.4f} ({test_m['accuracy']*100:.1f}%)",
        f"Weighted F1     : {test_m['weighted_f1']:.4f}",
        f"Macro F1        : {test_m['macro_f1']:.4f}",
        f"HR Recall       : {test_m['high_risk_recall']:.4f} (classes 4+5)",
        f"HR False Neg.   : {test_m['false_negatives_high_risk']}",
        "",
        "SAFETY GATE STATUS",
        "------------------",
        f"HR Recall >= {HIGH_RISK_RECALL_TARGET} : {'PASS' if hr_pass else 'FAIL'}",
        f"Weighted F1 >= 0.75 : {'PASS' if wf1_pass else 'FAIL'}",
        f"Zero FN (HR)        : {'PASS' if fn_pass else 'FAIL'}",
        f"APPROVED            : {'YES' if overall_pass else 'NO'}",
        "",
        "Model saved: models/best_model/",
    ]
    summary_path = RESULTS_DIR / "test_evaluation.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))
    logger.info(f"Summary saved: {summary_path}")

    logger.info(f"\nTotal training time: {round(total_secs/3600, 2)} hours")
    logger.info("Training complete.")


if __name__ == "__main__":
    main()
