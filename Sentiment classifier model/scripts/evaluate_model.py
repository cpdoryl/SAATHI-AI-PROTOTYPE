#!/usr/bin/env python3
"""
Sentiment Classifier Evaluation Script

Evaluates trained model on test set with comprehensive metrics.
Can be run standalone: python evaluate_model.py
"""

import os
import json
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "sentiment_classes": ["negative", "neutral", "positive"],
    "label2id": {"negative": 0, "neutral": 1, "positive": 2},
    "id2label": {0: "negative", 1: "neutral", 2: "positive"},
    "max_seq_length": 128,
    "batch_size": 64,

    # Paths
    "model_dir": "Sentiment classifier model/models/best_model",
    "test_data": "Sentiment classifier model/data/splits/test.csv",
    "results_dir": "Sentiment classifier model/results",
}

# Qualification gates
QUALIFICATION_GATES = {
    "accuracy": {"threshold": 0.85, "description": "Overall accuracy >= 85%"},
    "macro_f1": {"threshold": 0.83, "description": "Macro F1 >= 0.83"},
    "negative_f1": {"threshold": 0.87, "description": "Negative class F1 >= 0.87"},
}

# ============================================================================
# EVALUATION
# ============================================================================

def evaluate_model() -> dict:
    """Evaluate trained sentiment classifier on test set."""

    print("="*70)
    print("SENTIMENT CLASSIFIER EVALUATION")
    print("="*70)

    # Load test data
    print("\n1. Loading test data...")
    test_df = pd.read_csv(CONFIG["test_data"])
    print(f"   Test samples: {len(test_df)}")

    # Map sentiment to labels
    test_df['label'] = test_df['sentiment'].map(CONFIG["label2id"])
    test_labels = test_df['label'].values

    # Load model and tokenizer
    print("\n2. Loading model...")
    print(f"   Model directory: {CONFIG['model_dir']}")

    tokenizer = AutoTokenizer.from_pretrained(CONFIG["model_dir"])
    model = AutoModelForSequenceClassification.from_pretrained(CONFIG["model_dir"])
    model.eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    print(f"   Device: {device}")

    # Tokenize and prepare test data
    print("\n3. Tokenizing test data...")
    encodings = tokenizer(
        test_df['utterance'].tolist(),
        max_length=CONFIG["max_seq_length"],
        truncation=True,
        padding="max_length",
        return_tensors="pt"
    )

    # Generate predictions
    print("\n4. Generating predictions...")
    all_logits = []
    all_probs = []

    with torch.no_grad():
        for i in range(0, len(test_df), CONFIG["batch_size"]):
            batch_end = min(i + CONFIG["batch_size"], len(test_df))
            batch = {
                'input_ids': encodings['input_ids'][i:batch_end].to(device),
                'attention_mask': encodings['attention_mask'][i:batch_end].to(device),
            }

            outputs = model(**batch)
            logits = outputs.logits.cpu().numpy()
            probs = torch.softmax(outputs.logits, dim=-1).cpu().numpy()

            all_logits.append(logits)
            all_probs.append(probs)

    all_logits = np.vstack(all_logits)
    all_probs = np.vstack(all_probs)
    test_preds = np.argmax(all_logits, axis=-1)

    print(f"   Predictions generated: {len(test_preds)}")

    # Compute metrics
    print("\n5. Computing metrics...")

    accuracy = accuracy_score(test_labels, test_preds)
    macro_f1 = f1_score(test_labels, test_preds, average='macro', zero_division=0)
    weighted_f1 = f1_score(test_labels, test_preds, average='weighted', zero_division=0)
    micro_f1 = f1_score(test_labels, test_preds, average='micro', zero_division=0)

    print(f"\n   Overall Metrics:")
    print(f"   Accuracy:     {accuracy:.4f}")
    print(f"   Macro F1:     {macro_f1:.4f}")
    print(f"   Weighted F1:  {weighted_f1:.4f}")
    print(f"   Micro F1:     {micro_f1:.4f}")

    # Per-class metrics
    print(f"\n   Per-Class Metrics:")
    per_class_metrics = {}

    for idx, class_name in enumerate(CONFIG["sentiment_classes"]):
        class_mask = test_labels == idx
        if class_mask.sum() == 0:
            continue

        class_preds = test_preds[class_mask]
        class_labels = test_labels[class_mask]

        precision = precision_score(class_labels, class_preds, pos_label=idx, zero_division=0)
        recall = recall_score(class_labels, class_preds, pos_label=idx, zero_division=0)
        f1 = f1_score(class_labels, class_preds, pos_label=idx, zero_division=0)
        support = class_mask.sum()

        per_class_metrics[class_name] = {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "support": int(support),
        }

        print(f"     {class_name:10s}  P={precision:.4f}  R={recall:.4f}  F1={f1:.4f}  "
              f"(n={support})")

    # Distribution of predictions
    print(f"\n6. Prediction distribution:")
    pred_counts = pd.Series(test_preds).value_counts().sort_index()
    true_counts = pd.Series(test_labels).value_counts().sort_index()

    for idx, class_name in enumerate(CONFIG["sentiment_classes"]):
        true_count = true_counts.get(idx, 0)
        pred_count = pred_counts.get(idx, 0)
        print(f"   {class_name:10s}  True={true_count:3d}  Pred={pred_count:3d}")

    # Classification report
    print(f"\n7. Detailed Classification Report:")
    class_report = classification_report(
        test_labels, test_preds,
        target_names=CONFIG["sentiment_classes"],
        digits=4
    )
    print(class_report)

    # Confusion matrix
    cm = confusion_matrix(test_labels, test_preds)
    print(f"\n8. Confusion Matrix:")
    print(f"   (rows=true, cols=predicted)")
    print(f"   {'':12s} negative  neutral  positive")
    for i, class_name in enumerate(CONFIG["sentiment_classes"]):
        row_str = f"   {class_name:12s}"
        for j in range(len(CONFIG["sentiment_classes"])):
            row_str += f"  {cm[i, j]:3d}"
        print(row_str)

    # Check qualification gates
    print(f"\n9. Qualification Gates:")
    print(f"   {'='*70}")

    gate_results = {}
    negative_f1 = per_class_metrics.get("negative", {}).get("f1", 0.0)

    gates_to_check = [
        ("accuracy", accuracy, QUALIFICATION_GATES["accuracy"]),
        ("macro_f1", macro_f1, QUALIFICATION_GATES["macro_f1"]),
        ("negative_f1", negative_f1, QUALIFICATION_GATES["negative_f1"]),
    ]

    all_gates_passed = True
    for gate_name, value, gate_config in gates_to_check:
        threshold = gate_config["threshold"]
        passed = value >= threshold
        all_gates_passed = all_gates_passed and passed

        status = "[PASS]" if passed else "[FAIL]"
        print(f"   {status}  {gate_config['description']:40s} | "
              f"Value={value:.4f}, Threshold={threshold:.4f}")

    print(f"   {'='*70}")

    if all_gates_passed:
        print(f"\n   [OK] ALL GATES PASSED - Model qualifies for deployment!")
    else:
        print(f"\n   [FAIL] SOME GATES FAILED - Review model training")

    # Save results
    print(f"\n10. Saving results...")
    os.makedirs(CONFIG["results_dir"], exist_ok=True)

    evaluation_results = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "test_samples": len(test_labels),
        "overall_metrics": {
            "accuracy": float(accuracy),
            "macro_f1": float(macro_f1),
            "weighted_f1": float(weighted_f1),
            "micro_f1": float(micro_f1),
        },
        "per_class_metrics": per_class_metrics,
        "qualification_gates": {
            "accuracy": {
                "value": float(accuracy),
                "threshold": QUALIFICATION_GATES["accuracy"]["threshold"],
                "passed": accuracy >= QUALIFICATION_GATES["accuracy"]["threshold"],
            },
            "macro_f1": {
                "value": float(macro_f1),
                "threshold": QUALIFICATION_GATES["macro_f1"]["threshold"],
                "passed": macro_f1 >= QUALIFICATION_GATES["macro_f1"]["threshold"],
            },
            "negative_f1": {
                "value": float(negative_f1),
                "threshold": QUALIFICATION_GATES["negative_f1"]["threshold"],
                "passed": negative_f1 >= QUALIFICATION_GATES["negative_f1"]["threshold"],
            },
        },
        "all_gates_passed": all_gates_passed,
    }

    with open(os.path.join(CONFIG["results_dir"], "evaluation_results.json"), 'w') as f:
        json.dump(evaluation_results, f, indent=2)
    print(f"   [OK] Saved: evaluation_results.json")

    with open(os.path.join(CONFIG["results_dir"], "test_evaluation.txt"), 'w') as f:
        f.write("SENTIMENT CLASSIFIER - TEST SET EVALUATION\n")
        f.write("="*70 + "\n\n")
        f.write("OVERALL METRICS\n")
        f.write(f"Accuracy:    {accuracy:.4f}\n")
        f.write(f"Macro F1:    {macro_f1:.4f}\n")
        f.write(f"Weighted F1: {weighted_f1:.4f}\n")
        f.write(f"Micro F1:    {micro_f1:.4f}\n\n")
        f.write("QUALIFICATION GATES\n")
        for gate_name, value, gate_config in gates_to_check:
            passed = value >= gate_config["threshold"]
            f.write(f"  {'[PASS]' if passed else '[FAIL]'} {gate_config['description']} "
                    f"| Value={value:.4f}\n")
        f.write(f"\nAll gates passed: {all_gates_passed}\n\n")
        f.write("PER-CLASS METRICS\n")
        f.write(class_report)
    print(f"   [OK] Saved: test_evaluation.txt")

    print(f"\n{'='*70}")
    print(f"EVALUATION COMPLETE")
    print(f"{'='*70}\n")

    return evaluation_results

if __name__ == "__main__":
    results = evaluate_model()
