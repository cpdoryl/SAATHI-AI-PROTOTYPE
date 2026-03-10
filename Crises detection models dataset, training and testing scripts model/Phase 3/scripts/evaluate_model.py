"""
SAATHI AI — Phase 3 Model Evaluation Script
============================================
Evaluate a saved Phase 3 checkpoint on any CSV split.

Usage:
    python scripts/evaluate_model.py                             # evaluate best_model on test set
    python scripts/evaluate_model.py --split val                 # use val split
    python scripts/evaluate_model.py --model_path models/best_model
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

BASE_DIR    = Path(__file__).resolve().parent.parent
DATA_DIR    = BASE_DIR / "data" / "splits"
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

NUM_LABELS        = 6
MAX_LENGTH        = 128
BATCH_SIZE        = 16
HIGH_RISK_CLASSES = [4, 5]
SAFETY_THRESHOLD  = 0.15

CLASS_NAMES = [
    "safe",
    "passive_ideation",
    "mild_distress",
    "moderate_concern",
    "elevated_monitoring",
    "pre_crisis_intervention",
]


class Phase3Dataset(Dataset):
    def __init__(self, csv_path, tokenizer, max_length=128):
        self.rows = []
        self.tokenizer = tokenizer
        with open(csv_path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                self.rows.append({"text": row["utterance"].strip(), "label": int(row["crisis_label"])})

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        item = self.rows[idx]
        enc  = self.tokenizer(item["text"], max_length=MAX_LENGTH, padding="max_length",
                              truncation=True, return_tensors="pt")
        return {
            "input_ids":      enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "label":          torch.tensor(item["label"], dtype=torch.long),
        }


def safety_gate_predict(logits):
    probs    = torch.softmax(logits, dim=1)
    hr_probs = probs[:, HIGH_RISK_CLASSES]
    hr_max, hr_argmax = hr_probs.max(dim=1)
    normal   = probs.argmax(dim=1)
    forced   = torch.tensor([HIGH_RISK_CLASSES[i] for i in hr_argmax.tolist()],
                             dtype=torch.long, device=logits.device)
    return torch.where(hr_max > SAFETY_THRESHOLD, forced, normal)


@torch.no_grad()
def run_evaluation(model_path: Path, csv_path: Path) -> dict:
    device    = torch.device("cpu")
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    model     = AutoModelForSequenceClassification.from_pretrained(str(model_path), num_labels=NUM_LABELS)
    model.to(device).eval()

    ds     = Phase3Dataset(csv_path, tokenizer, MAX_LENGTH)
    loader = DataLoader(ds, batch_size=BATCH_SIZE, shuffle=False)

    all_labels, all_preds = [], []
    for batch in loader:
        out    = model(input_ids=batch["input_ids"].to(device),
                       attention_mask=batch["attention_mask"].to(device))
        preds  = safety_gate_predict(out.logits)
        all_labels.extend(batch["label"].tolist())
        all_preds.extend(preds.cpu().tolist())

    labels = np.array(all_labels)
    preds  = np.array(all_preds)

    hr_true    = np.isin(labels, HIGH_RISK_CLASSES).astype(int)
    hr_pred    = np.isin(preds,  HIGH_RISK_CLASSES).astype(int)
    tp = int(((hr_true == 1) & (hr_pred == 1)).sum())
    fn = int(((hr_true == 1) & (hr_pred == 0)).sum())
    hr_recall  = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    return {
        "accuracy":         float((labels == preds).mean()),
        "weighted_f1":      float(f1_score(labels, preds, average="weighted", zero_division=0)),
        "macro_f1":         float(f1_score(labels, preds, average="macro",    zero_division=0)),
        "high_risk_recall": hr_recall,
        "false_negatives_high_risk": fn,
        "per_class_report": classification_report(labels, preds, target_names=CLASS_NAMES,
                                                  zero_division=0, output_dict=True),
        "confusion_matrix": confusion_matrix(labels, preds).tolist(),
        "n_samples":        len(ds),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate Phase 3 crisis model")
    parser.add_argument("--model_path", default=str(BASE_DIR / "models" / "best_model"),
                        help="Path to saved HuggingFace model directory")
    parser.add_argument("--split", default="test", choices=["train", "val", "test"],
                        help="Which data split to evaluate")
    args = parser.parse_args()

    model_path = Path(args.model_path)
    csv_path   = DATA_DIR / f"{args.split}.csv"

    print(f"Model: {model_path}")
    print(f"Split: {csv_path}")

    if not model_path.exists():
        print(f"ERROR: model not found at {model_path}")
        return
    if not csv_path.exists():
        print(f"ERROR: split CSV not found at {csv_path}")
        print("Run: python scripts/prepare_data_splits.py")
        return

    print("Running evaluation ...")
    m = run_evaluation(model_path, csv_path)

    print("\n" + "=" * 60)
    print(f"PHASE 3 EVALUATION — {args.split.upper()} SET ({m['n_samples']} samples)")
    print("=" * 60)
    print(f"Accuracy        : {m['accuracy']:.4f} ({m['accuracy']*100:.1f}%)")
    print(f"Weighted F1     : {m['weighted_f1']:.4f}")
    print(f"Macro F1        : {m['macro_f1']:.4f}")
    print(f"HR Recall (4+5) : {m['high_risk_recall']:.4f}")
    print(f"HR False Neg.   : {m['false_negatives_high_risk']}")

    print("\nPer-class breakdown:")
    for cls, stats in m["per_class_report"].items():
        if isinstance(stats, dict):
            print(f"  {cls:<30} P:{stats.get('precision',0):.2f}  "
                  f"R:{stats.get('recall',0):.2f}  "
                  f"F1:{stats.get('f1-score',0):.2f}  "
                  f"N:{int(stats.get('support',0))}")

    hr_pass  = m["high_risk_recall"] >= 0.98
    fn_pass  = m["false_negatives_high_risk"] == 0
    wf1_pass = m["weighted_f1"] >= 0.75
    print(f"\nSafety gate: HR-recall>=0.98={'PASS' if hr_pass else 'FAIL'}  "
          f"Zero-FN={'PASS' if fn_pass else 'FAIL'}  "
          f"W-F1>=0.75={'PASS' if wf1_pass else 'FAIL'}")

    out_path = RESULTS_DIR / f"eval_{args.split}.json"
    with open(out_path, "w") as f:
        json.dump(m, f, indent=2, default=str)
    print(f"\nResults saved: {out_path}")


if __name__ == "__main__":
    main()
