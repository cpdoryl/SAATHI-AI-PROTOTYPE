"""
Crisis Detection Model - TEST EVALUATION (CSV INPUT)
FINAL FIXED VERSION
===================================================

✔ FIXED tokenizer loading
✔ FIXED protobuf crash
✔ Uses utterance + severity_score
✔ Safety-threshold evaluation
✔ Full metrics

Author: ML Team
"""

import torch
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader, TensorDataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer
)
from sklearn.metrics import classification_report, confusion_matrix

# ─────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────

BASE_MODEL_NAME = "distilbert-base-uncased"   # 🔑 IMPORTANT
MODEL_DIR = "../models/checkpoints/best_model"
TEST_CSV_PATH = "../data/splits/test.csv"

TEXT_COLUMN = "utterance"
LABEL_COLUMN = "severity_score"

BATCH_SIZE = 16
MAX_LENGTH = 128
NUM_LABELS = 4

HIGH_RISK_CLASS = 3
SAFETY_THRESHOLD = 0.20

SEVERITY_MAP = {
    0.2: 0,
    0.6: 1,
    0.7: 2,
    0.9: 3
}

# ─────────────────────────────────────────────────
# SAFETY THRESHOLD LOGIC
# ─────────────────────────────────────────────────

def predict_with_safety_threshold(logits, threshold=SAFETY_THRESHOLD):
    probs = torch.softmax(logits, dim=1)
    high_risk_probs = probs[:, HIGH_RISK_CLASS]

    preds = torch.zeros(logits.size(0), dtype=torch.long, device=logits.device)

    for i in range(len(preds)):
        if high_risk_probs[i] > threshold:
            preds[i] = HIGH_RISK_CLASS
        else:
            preds[i] = torch.argmax(probs[i])

    return preds


# ─────────────────────────────────────────────────
# EVALUATION
# ─────────────────────────────────────────────────

def evaluate_on_test(model, dataloader, device):
    model.eval()
    all_preds, all_labels = [], []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch[0].to(device)
            attention_mask = batch[1].to(device)
            labels = batch[2].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )

            preds = predict_with_safety_threshold(outputs.logits)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    accuracy = (all_preds == all_labels).mean()

    high_risk_mask = (all_labels == HIGH_RISK_CLASS)
    high_risk_recall = (
        ((all_preds == HIGH_RISK_CLASS) & high_risk_mask).sum()
        / max(1, high_risk_mask.sum())
    )

    return {
        "accuracy": accuracy,
        "high_risk_recall": high_risk_recall,
        "predictions": all_preds,
        "labels": all_labels
    }


# ─────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────

def main():
    print("=" * 70)
    print(" CRISIS DETECTION MODEL - TEST EVALUATION (CSV)")
    print("=" * 70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n Device: {device}")

    # ─── Load CSV ───
    print("\n Loading test CSV...")
    df = pd.read_csv(TEST_CSV_PATH)
    print(" Available columns:", df.columns.tolist())

    texts = df[TEXT_COLUMN].astype(str).tolist()

    labels = []
    for v in df[LABEL_COLUMN]:
        if v not in SEVERITY_MAP:
            raise ValueError(f"❌ Invalid severity_score: {v}")
        labels.append(SEVERITY_MAP[v])

    print(f" Test samples: {len(texts)}")

    # ─── Tokenizer (LOAD FROM BASE MODEL) ───
    print("\n Loading tokenizer from base model...")
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL_NAME,
        use_fast=True
    )

    encodings = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt"
    )

    test_dataset = TensorDataset(
        encodings["input_ids"],
        encodings["attention_mask"],
        torch.tensor(labels)
    )

    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE)

    # ─── Model (LOAD FROM CHECKPOINT) ───
    print("\n Loading trained model...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_DIR,
        num_labels=NUM_LABELS
    ).to(device)

    # ─── Evaluate ───
    print("\n Running test evaluation...")
    results = evaluate_on_test(model, test_loader, device)

    # ─── Results ───
    print("\n" + "=" * 70)
    print(" FINAL TEST RESULTS")
    print("=" * 70)

    print(f" Test Accuracy    : {results['accuracy']:.4f}")
    print(f" High-Risk Recall : {results['high_risk_recall']:.4f}")

    cm = confusion_matrix(results["labels"], results["predictions"])
    print("\n Confusion Matrix:")
    print("              Predicted")
    print("           0.2   0.6   0.7   0.9")
    for i, row in enumerate(cm):
        print(f"Actual {['0.2','0.6','0.7','0.9'][i]}  {row}")

    print("\n Classification Report:")
    print(classification_report(
        results["labels"],
        results["predictions"],
        target_names=["Sev 0.2", "Sev 0.6", "Sev 0.7", "Sev 0.9"]
    ))

    print("\n" + "=" * 70)
    if results["high_risk_recall"] >= 0.99:
        print(" ✅ SUCCESS: Model is SAFETY-READY")
    else:
        print(" ❌ NOT READY: Improve recall")
        print("  • Lower safety threshold (0.15)")
        print("  • Increase class weights")
        print("  • Add high-risk samples")

    print("=" * 70)


if __name__ == "__main__":
    main()
