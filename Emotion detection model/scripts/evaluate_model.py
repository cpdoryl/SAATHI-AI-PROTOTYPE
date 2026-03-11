"""
SAATHI AI -- Emotion Classifier: Standalone Evaluator
======================================================
Evaluate any saved checkpoint on train / val / test split.

Usage:
    python scripts/evaluate_model.py
    python scripts/evaluate_model.py --split val
    python scripts/evaluate_model.py --model_path models/best_model --split test
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.join(SCRIPT_DIR, "..")

CLASSES  = ["anxiety", "sadness", "anger", "fear",
            "hopelessness", "guilt", "shame", "neutral"]
LABEL2ID = {c: i for i, c in enumerate(CLASSES)}
ID2LABEL = {i: c for i, c in enumerate(CLASSES)}


def load_split(split_name):
    path = os.path.join(BASE_DIR, "data", "splits", f"{split_name}.csv")
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "text":  r["utterance"],
                "label": LABEL2ID[r["primary_emotion"]],
            })
    return rows


def predict_batch(model, tokenizer, texts, device, max_len=128, batch=32):
    import torch
    all_probs = []
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        enc = tokenizer(chunk, max_length=max_len, truncation=True,
                        padding="max_length", return_tensors="pt")
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            logits = model(**enc).logits
            probs  = torch.softmax(logits, dim=-1).cpu().numpy()
        all_probs.extend(probs.tolist())
    return all_probs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", default=None,
                        help="Path to saved model dir (default: models/best_model)")
    parser.add_argument("--split", default="test",
                        choices=["train", "val", "test"])
    args = parser.parse_args()

    model_path = args.model_path or os.path.join(BASE_DIR, "models", "best_model")
    model_path = os.path.normpath(model_path)

    if not os.path.isdir(model_path):
        print(f"ERROR: model directory not found: {model_path}")
        sys.exit(1)

    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        from sklearn.metrics import (accuracy_score, f1_score,
                                     classification_report, confusion_matrix)
    except ImportError as e:
        print(f"Missing dependency: {e}")
        sys.exit(1)

    device = torch.device("cpu")
    print(f"Loading model: {model_path}")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model     = AutoModelForSequenceClassification.from_pretrained(model_path)
    model.to(device)
    model.eval()
    print(f"Model loaded. Evaluating on '{args.split}' split...")

    rows   = load_split(args.split)
    texts  = [r["text"]  for r in rows]
    labels = [r["label"] for r in rows]

    all_probs = predict_batch(model, tokenizer, texts, device)
    preds = [max(range(len(p)), key=lambda i: p[i]) for p in all_probs]

    acc      = accuracy_score(labels, preds)
    macro_f1 = f1_score(labels, preds, average="macro",   zero_division=0)
    wt_f1    = f1_score(labels, preds, average="weighted", zero_division=0)
    per_cls  = f1_score(labels, preds, average=None,
                        labels=list(range(len(CLASSES))), zero_division=0)
    cm       = confusion_matrix(labels, preds,
                                labels=list(range(len(CLASSES))))
    report   = classification_report(labels, preds,
                                     target_names=CLASSES, zero_division=0)

    print(f"\n--- Evaluation: {args.split} split ({len(rows)} samples) ---")
    print(f"Accuracy    : {acc:.4f} ({acc*100:.2f}%)")
    print(f"Weighted F1 : {wt_f1:.4f}")
    print(f"Macro F1    : {macro_f1:.4f}")
    print("\nPer-class F1:")
    for i, cls in enumerate(CLASSES):
        print(f"  {cls:<22}: {per_cls[i]:.4f}")
    print("\nClassification report:")
    print(report)
    print("Confusion matrix (rows=true, cols=predicted):")
    header = "  " + "  ".join(f"{c[:5]:>5}" for c in CLASSES)
    print(header)
    for i, row in enumerate(cm.tolist()):
        print(f"  {CLASSES[i][:5]:>5}  " + "  ".join(f"{v:5d}" for v in row))

    # Save
    results_dir = os.path.join(BASE_DIR, "results")
    os.makedirs(results_dir, exist_ok=True)
    out = {
        "split":       args.split,
        "n_samples":   len(rows),
        "accuracy":    round(acc, 4),
        "macro_f1":    round(macro_f1, 4),
        "weighted_f1": round(wt_f1, 4),
        "per_class_f1": {CLASSES[i]: round(float(v), 4)
                         for i, v in enumerate(per_cls)},
        "confusion_matrix": cm.tolist(),
        "evaluated_at": datetime.now().isoformat(),
    }
    out_path = os.path.join(results_dir, f"eval_{args.split}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved: {out_path}")


if __name__ == "__main__":
    main()
