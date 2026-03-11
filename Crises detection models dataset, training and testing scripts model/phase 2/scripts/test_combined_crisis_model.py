"""
CRISIS DETECTION MODEL – TEST EVALUATION (COMBINED DATASET)
==========================================================

• 6-class severity classification
• Safety-gated high-risk detection
• Test CSV evaluation ONLY
• Compatible with combined training script v2.0

Author: ML Team
"""

import torch
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader, TensorDataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import classification_report, confusion_matrix

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

BASE_MODEL_NAME = "distilbert-base-uncased"
MODEL_PATH = "models/best_crisis_model_combined.pt"
TEST_CSV_PATH = "data/splits/test_combined.csv"

TEXT_COLUMN = "utterance"
LABEL_COLUMN = "severity_score"

NUM_LABELS = 6
BATCH_SIZE = 16
MAX_LENGTH = 128

HIGH_RISK_CLASSES = [4, 5]      # intent, plan/attempt
SAFETY_THRESHOLD = 0.20

SEVERITY_TO_CLASS = {
    0.1: 0,
    0.2: 1,
    0.6: 2,
    0.7: 3,
    0.9: 4,
    1.0: 5
}

CLASS_NAMES = [
    "self_harm",
    "passive",
    "active",
    "method",
    "intent",
    "plan/attempt"
]

# ─────────────────────────────────────────────
# SAFETY THRESHOLD PREDICTION
# ─────────────────────────────────────────────

def predict_with_safety_threshold(logits, threshold=SAFETY_THRESHOLD):
    probs = torch.softmax(logits, dim=1)
    preds = torch.zeros(logits.size(0), dtype=torch.long, device=logits.device)

    for i in range(logits.size(0)):
        high_risk_probs = probs[i, HIGH_RISK_CLASSES]
        if high_risk_probs.max() > threshold:
            preds[i] = HIGH_RISK_CLASSES[high_risk_probs.argmax()]
        else:
            preds[i] = torch.argmax(probs[i])

    return preds


# ─────────────────────────────────────────────
# EVALUATION
# ─────────────────────────────────────────────

def evaluate(model, dataloader, device):
    model.eval()
    all_preds, all_labels = [], []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch[0].to(device)
            attention_mask = batch[1].to(device)
            labels = batch[2].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            preds = predict_with_safety_threshold(outputs.logits)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    accuracy = (all_preds == all_labels).mean()

    high_risk_mask = np.isin(all_labels, HIGH_RISK_CLASSES)
    high_risk_recall = (
        np.isin(all_preds[high_risk_mask], HIGH_RISK_CLASSES).sum()
        / max(1, high_risk_mask.sum())
    )

    return accuracy, high_risk_recall, all_labels, all_preds


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 70)
    print(" CRISIS DETECTION MODEL – TEST EVALUATION (6-CLASS)")
    print("=" * 70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n Device: {device}")

    # Load CSV
    print("\n Loading test dataset...")
    df = pd.read_csv(TEST_CSV_PATH)
    print(" Columns:", df.columns.tolist())

    texts = df[TEXT_COLUMN].astype(str).tolist()

    labels = []
    for v in df[LABEL_COLUMN]:
        if v not in SEVERITY_TO_CLASS:
            raise ValueError(f"Invalid severity score: {v}")
        labels.append(SEVERITY_TO_CLASS[v])

    print(f" Test samples: {len(texts)}")

    # Tokenizer (base model)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)

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

    # Load model
    print("\n Loading trained combined model...")
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL_NAME,
        num_labels=NUM_LABELS
    )
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.to(device)

    # Evaluate
    print("\n Running test evaluation...")
    accuracy, high_risk_recall, y_true, y_pred = evaluate(
        model, test_loader, device
    )

    # Results
    print("\n" + "=" * 70)
    print(" FINAL TEST RESULTS")
    print("=" * 70)

    print(f" Test Accuracy        : {accuracy:.4f}")
    print(f" High-Risk Recall     : {high_risk_recall:.4f}")

    print("\n Confusion Matrix:")
    print(confusion_matrix(y_true, y_pred))

    print("\n Classification Report:")
    print(classification_report(y_true, y_pred, target_names=CLASS_NAMES))

    print("\n" + "=" * 70)
    if high_risk_recall >= 0.99:
        print(" ✅ SAFETY OBJECTIVE ACHIEVED")
    else:
        print(" ❌ SAFETY OBJECTIVE NOT MET")

    print("=" * 70)


if __name__ == "__main__":
    main()
