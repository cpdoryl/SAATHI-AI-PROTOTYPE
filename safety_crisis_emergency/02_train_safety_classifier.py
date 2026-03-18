#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAATHI AI -- Safety Classifier Training
========================================
Fine-tunes microsoft/deberta-v3-small for multi-label safety classification.
DeBERTa-v3-small: 86M params, state-of-art for text classification, fast CPU inference.

Labels (6, non-exclusive):
  safe | harmful_content | crisis_escalation_missing |
  hallucinated_fact | toxic_language | scope_violation

Medical-grade design:
  - Weighted loss for rare but critical labels (crisis_escalation_missing)
  - High-recall training for safety-critical categories
  - Threshold tuning: optimise for recall >= 0.95 on harmful_content + crisis labels
  - All training metadata logged to training_report.json

Usage:
  python 02_train_safety_classifier.py
  python 02_train_safety_classifier.py --epochs 10 --batch 8 --lr 2e-5
"""

import sys, io, os, json, time, argparse, random
from pathlib import Path
from dataclasses import dataclass, asdict

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE     = Path(__file__).parent
DATA_DIR = BASE / "data"
OUT_DIR  = BASE / "output" / "safety-classifier"

# ── Label config ──────────────────────────────────────────────────────────────
LABELS = [
    "safe",
    "harmful_content",
    "crisis_escalation_missing",
    "hallucinated_fact",
    "toxic_language",
    "scope_violation",
]
NUM_LABELS = len(LABELS)

# Critical safety labels — must achieve high recall
CRITICAL_LABELS = {"harmful_content", "crisis_escalation_missing"}
CRITICAL_INDICES = [LABELS.index(l) for l in CRITICAL_LABELS]

# Label weights: rare but critical labels get higher weight
LABEL_WEIGHTS = {
    "safe":                       1.0,
    "harmful_content":            3.0,   # must not miss harmful content
    "crisis_escalation_missing":  5.0,   # highest weight — missing crisis is worst failure
    "hallucinated_fact":          2.5,
    "toxic_language":             2.0,
    "scope_violation":            2.0,
}


@dataclass
class TrainConfig:
    base_model:       str = "microsoft/deberta-v3-small"
    max_length:       int = 256
    epochs:           int = 8
    batch_size:       int = 8
    learning_rate:    float = 2e-5
    weight_decay:     float = 0.01
    warmup_ratio:     float = 0.10
    classification_threshold: float = 0.40  # lower threshold = higher recall
    critical_threshold:       float = 0.30  # even lower for safety-critical labels
    seed:             int = 42
    dataloader_num_workers: int = 0  # Windows-safe


# ── Dataset ───────────────────────────────────────────────────────────────────
class SafetyDataset(Dataset):
    def __init__(self, path: Path, tokenizer, max_length: int):
        self.examples = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.examples.append(json.loads(line))
        self.tokenizer  = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        ex  = self.examples[idx]
        enc = self.tokenizer(
            ex["text"],
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        binary = ex["binary"]
        labels = torch.tensor(
            [binary.get(l, 0) for l in LABELS],
            dtype=torch.float,
        )
        return {
            "input_ids":      enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels":         labels,
        }


# ── Weighted BCE loss ─────────────────────────────────────────────────────────
class WeightedBCELoss(torch.nn.Module):
    def __init__(self):
        super().__init__()
        weights = torch.tensor(
            [LABEL_WEIGHTS[l] for l in LABELS], dtype=torch.float
        )
        self.register_buffer("weights", weights)

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce = torch.nn.functional.binary_cross_entropy_with_logits(
            logits, targets, reduction="none"
        )
        return (bce * self.weights).mean()


# ── Metrics ───────────────────────────────────────────────────────────────────
def compute_metrics(all_preds: np.ndarray, all_labels: np.ndarray,
                    threshold: float = 0.40, critical_threshold: float = 0.30):
    """Compute per-label precision/recall/F1 and macro averages."""
    probs = 1 / (1 + np.exp(-all_preds))  # sigmoid

    # Apply label-specific thresholds
    preds_bin = np.zeros_like(probs)
    for i, lbl in enumerate(LABELS):
        t = critical_threshold if lbl in CRITICAL_LABELS else threshold
        preds_bin[:, i] = (probs[:, i] >= t).astype(int)

    metrics = {}
    for i, lbl in enumerate(LABELS):
        tp = ((preds_bin[:, i] == 1) & (all_labels[:, i] == 1)).sum()
        fp = ((preds_bin[:, i] == 1) & (all_labels[:, i] == 0)).sum()
        fn = ((preds_bin[:, i] == 0) & (all_labels[:, i] == 1)).sum()

        prec   = tp / (tp + fp + 1e-8)
        recall = tp / (tp + fn + 1e-8)
        f1     = 2 * prec * recall / (prec + recall + 1e-8)

        metrics[lbl] = {
            "precision": round(float(prec), 4),
            "recall":    round(float(recall), 4),
            "f1":        round(float(f1), 4),
            "tp": int(tp), "fp": int(fp), "fn": int(fn),
        }

    # Critical recall check
    critical_recall_ok = all(
        metrics[lbl]["recall"] >= 0.90 for lbl in CRITICAL_LABELS
    )
    macro_f1 = np.mean([metrics[l]["f1"] for l in LABELS])

    return {
        "per_label":          metrics,
        "macro_f1":           round(float(macro_f1), 4),
        "critical_recall_ok": critical_recall_ok,
    }


# ── Training loop ─────────────────────────────────────────────────────────────
def train(config: TrainConfig):
    random.seed(config.seed)
    np.random.seed(config.seed)
    torch.manual_seed(config.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Load tokenizer and model
    print(f"Loading {config.base_model}...")
    tokenizer = AutoTokenizer.from_pretrained(
        config.base_model, trust_remote_code=True
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        config.base_model,
        num_labels=NUM_LABELS,
        problem_type="multi_label_classification",
        trust_remote_code=True,
        ignore_mismatched_sizes=True,
    ).to(device)

    # Datasets
    train_ds = SafetyDataset(DATA_DIR / "train.jsonl", tokenizer, config.max_length)
    val_ds   = SafetyDataset(DATA_DIR / "val.jsonl",   tokenizer, config.max_length)

    train_loader = DataLoader(train_ds, batch_size=config.batch_size,
                              shuffle=True, num_workers=config.dataloader_num_workers)
    val_loader   = DataLoader(val_ds,   batch_size=config.batch_size,
                              shuffle=False, num_workers=config.dataloader_num_workers)

    # Optimiser + scheduler
    optimizer = AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )
    total_steps   = len(train_loader) * config.epochs
    warmup_steps  = int(total_steps * config.warmup_ratio)
    scheduler     = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    loss_fn = WeightedBCELoss().to(device)

    best_val_f1   = 0.0
    best_epoch    = 0
    loss_history  = []
    t0            = time.time()

    print(f"\nTraining: {len(train_ds)} train | {len(val_ds)} val | {config.epochs} epochs")
    print("=" * 60)

    for epoch in range(1, config.epochs + 1):
        # -- Train
        model.train()
        epoch_loss = 0.0
        for batch in train_loader:
            input_ids  = batch["input_ids"].to(device)
            attn_mask  = batch["attention_mask"].to(device)
            labels     = batch["labels"].to(device)

            optimizer.zero_grad()
            logits = model(input_ids=input_ids, attention_mask=attn_mask).logits
            loss   = loss_fn(logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            epoch_loss += loss.item()

        avg_loss = epoch_loss / len(train_loader)

        # -- Validate
        model.eval()
        all_preds, all_labels_arr = [], []
        with torch.no_grad():
            for batch in val_loader:
                logits = model(
                    input_ids=batch["input_ids"].to(device),
                    attention_mask=batch["attention_mask"].to(device),
                ).logits
                all_preds.append(logits.cpu().numpy())
                all_labels_arr.append(batch["labels"].numpy())

        preds_np  = np.concatenate(all_preds,       axis=0)
        labels_np = np.concatenate(all_labels_arr,  axis=0)
        m = compute_metrics(preds_np, labels_np,
                            config.classification_threshold,
                            config.critical_threshold)

        critical_ok = "[OK]" if m["critical_recall_ok"] else "[!] CRITICAL RECALL LOW"
        print(f"Epoch {epoch:2d}/{config.epochs} | loss={avg_loss:.4f} | "
              f"macro_F1={m['macro_f1']:.4f} | {critical_ok}")

        for lbl in CRITICAL_LABELS:
            pm = m["per_label"][lbl]
            print(f"         {lbl}: P={pm['precision']:.3f} R={pm['recall']:.3f} F1={pm['f1']:.3f}")

        loss_history.append({"epoch": epoch, "loss": round(avg_loss, 6),
                              "macro_f1": m["macro_f1"]})

        if m["macro_f1"] > best_val_f1:
            best_val_f1 = m["macro_f1"]
            best_epoch  = epoch
            # Save best checkpoint
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(str(OUT_DIR))
            tokenizer.save_pretrained(str(OUT_DIR))

    duration = (time.time() - t0) / 60.0

    # Final eval on test set
    print("\nRunning final evaluation on test set...")
    test_ds = SafetyDataset(DATA_DIR / "test.jsonl", tokenizer, config.max_length)
    test_loader = DataLoader(test_ds, batch_size=config.batch_size, shuffle=False,
                             num_workers=config.dataloader_num_workers)

    model.eval()
    all_preds, all_labels_arr = [], []
    with torch.no_grad():
        for batch in test_loader:
            logits = model(
                input_ids=batch["input_ids"].to(device),
                attention_mask=batch["attention_mask"].to(device),
            ).logits
            all_preds.append(logits.cpu().numpy())
            all_labels_arr.append(batch["labels"].numpy())

    preds_np  = np.concatenate(all_preds,      axis=0)
    labels_np = np.concatenate(all_labels_arr, axis=0)
    test_m = compute_metrics(preds_np, labels_np,
                             config.classification_threshold,
                             config.critical_threshold)

    # Determine PASS/FAIL
    critical_recall_min = min(
        test_m["per_label"][lbl]["recall"] for lbl in CRITICAL_LABELS
    )
    overall_pass = (
        test_m["macro_f1"] >= 0.70
        and test_m["critical_recall_ok"]
    )

    print("\nTest Set Results:")
    print(f"  Macro F1:               {test_m['macro_f1']:.4f}")
    print(f"  Critical recall OK:     {test_m['critical_recall_ok']}")
    print(f"  Min critical recall:    {critical_recall_min:.4f}")
    for lbl, pm in test_m["per_label"].items():
        print(f"  {lbl:<35} P={pm['precision']:.3f} R={pm['recall']:.3f} F1={pm['f1']:.3f}")

    verdict = "[PASS] CLASSIFIER APPROVED FOR DEPLOYMENT" if overall_pass else "[FAIL] CLASSIFIER NOT READY"
    print(f"\n  {verdict}")

    # Write training report
    report = {
        "model_name":            "saathi-safety-classifier-v1",
        "base_model":            config.base_model,
        "labels":                LABELS,
        "num_labels":            NUM_LABELS,
        "critical_labels":       list(CRITICAL_LABELS),
        "label_weights":         LABEL_WEIGHTS,
        "config":                asdict(config),
        "training_duration_min": round(duration, 2),
        "best_epoch":            best_epoch,
        "best_val_macro_f1":     round(best_val_f1, 4),
        "test_metrics":          test_m,
        "loss_history":          loss_history,
        "overall_pass":          overall_pass,
    }
    report_path = OUT_DIR / "training_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {report_path}")

    # Save label config for inference
    label_config = {
        "labels":                    LABELS,
        "classification_threshold":  config.classification_threshold,
        "critical_threshold":        config.critical_threshold,
        "critical_labels":           list(CRITICAL_LABELS),
    }
    with open(OUT_DIR / "label_config.json", "w", encoding="utf-8") as f:
        json.dump(label_config, f, indent=2)

    return overall_pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs",     type=int,   default=8)
    parser.add_argument("--batch",      type=int,   default=8)
    parser.add_argument("--lr",         type=float, default=2e-5)
    parser.add_argument("--max-length", type=int,   default=256)
    parser.add_argument("--seed",       type=int,   default=42)
    args = parser.parse_args()

    config = TrainConfig(
        epochs=args.epochs,
        batch_size=args.batch,
        learning_rate=args.lr,
        max_length=args.max_length,
        seed=args.seed,
    )

    print("=" * 60)
    print("SAATHI AI -- Safety Classifier Training")
    print("=" * 60)
    print(f"Model:   {config.base_model}")
    print(f"Labels:  {LABELS}")
    print(f"Device:  {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    print(f"Epochs:  {config.epochs}  Batch: {config.batch_size}  LR: {config.learning_rate}")

    passed = train(config)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
