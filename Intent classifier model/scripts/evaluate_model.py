"""
SAATHI AI -- Intent Classifier: Standalone Evaluator
=====================================================
Evaluates any saved checkpoint on any split (train/val/test).

Usage:
    python scripts/evaluate_model.py
    python scripts/evaluate_model.py --split val
    python scripts/evaluate_model.py --model_path models/best_model --split test
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, f1_score
)
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR   = SCRIPT_DIR.parent

INTENT_CLASSES = [
    "seek_support", "book_appointment", "crisis_emergency",
    "information_request", "feedback_complaint", "general_chat",
    "assessment_request",
]
LABEL2ID = {c: i for i, c in enumerate(INTENT_CLASSES)}


class IntentDataset(Dataset):
    def __init__(self, df, tokenizer):
        self.texts  = df["utterance"].tolist()
        self.labels = df["label"].tolist()
        self.tok    = tokenizer

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        enc = self.tok(
            self.texts[idx], max_length=128,
            truncation=True, padding="max_length", return_tensors="pt",
        )
        return {
            "input_ids":      enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels":         torch.tensor(self.labels[idx], dtype=torch.long),
        }


def evaluate(model_path: Path, split: str):
    csv_path = BASE_DIR / "data" / "splits" / f"{split}.csv"
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found.")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    df["label"] = df["primary_intent"].map(LABEL2ID)

    print(f"Model : {model_path}")
    print(f"Split : {split} ({len(df)} examples)")

    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    model     = AutoModelForSequenceClassification.from_pretrained(str(model_path))
    model.eval()

    ds     = IntentDataset(df, tokenizer)
    loader = DataLoader(ds, batch_size=32)

    all_preds, all_labels = [], []
    with torch.no_grad():
        for batch in loader:
            outputs = model(
                input_ids=batch["input_ids"],
                attention_mask=batch["attention_mask"],
            )
            preds = torch.argmax(outputs.logits, dim=-1).numpy()
            all_preds.extend(preds)
            all_labels.extend(batch["labels"].numpy())

    acc        = accuracy_score(all_labels, all_preds)
    macro_f1   = f1_score(all_labels, all_preds, average="macro",     zero_division=0)
    weighted_f1= f1_score(all_labels, all_preds, average="weighted",  zero_division=0)
    report     = classification_report(
        all_labels, all_preds, target_names=INTENT_CLASSES,
        output_dict=True, zero_division=0,
    )
    cm = confusion_matrix(all_labels, all_preds)

    print(f"\nAccuracy  : {acc:.4f} ({acc * 100:.2f}%)")
    print(f"Macro F1  : {macro_f1:.4f}")
    print(f"Weighted F1: {weighted_f1:.4f}")
    print("\nPer-class F1:")
    for intent in INTENT_CLASSES:
        print(f"  {intent:<22}: {report[intent]['f1-score']:.4f}  "
              f"(P={report[intent]['precision']:.2f} R={report[intent]['recall']:.2f})")

    print(f"\n{classification_report(all_labels, all_preds, target_names=INTENT_CLASSES, zero_division=0)}")

    out = {
        "split": split, "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4), "weighted_f1": round(weighted_f1, 4),
        "per_class": {k: {m: round(v, 4) for m, v in vs.items()}
                      for k, vs in report.items() if k in INTENT_CLASSES},
        "confusion_matrix": cm.tolist(),
    }

    out_path = BASE_DIR / "results" / f"eval_{split}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", default=str(BASE_DIR / "models" / "best_model"))
    parser.add_argument("--split", choices=["train", "val", "test"], default="test")
    args = parser.parse_args()
    evaluate(Path(args.model_path), args.split)
