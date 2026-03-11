"""
SAATHI AI -- Topic Classifier Standalone Evaluator
====================================================
Multi-label DistilBERT (5-class) evaluator.
Run after training to get full classification report.

Usage:
    python "Topic classifier model/scripts/evaluate_model.py"
    (from repo root: c:/saath ai prototype/)
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    classification_report,
    f1_score,
    hamming_loss,
    accuracy_score,
)
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# --- Paths --------------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).resolve().parent
MODEL_DIR    = SCRIPT_DIR.parent / "models" / "best_model"
DATA_DIR     = SCRIPT_DIR.parent / "data" / "splits"
TEST_CSV     = DATA_DIR / "test.csv"
RESULTS_DIR  = SCRIPT_DIR.parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# --- Topic Labels -------------------------------------------------------------
TOPICS = [
    "workplace_stress",
    "relationship_issues",
    "academic_stress",
    "health_concerns",
    "financial_stress",
]
NUM_LABELS = len(TOPICS)

# --- Qualification Gates -------------------------------------------------------
GATE_F1_SAMPLES = 0.82
GATE_F1_MACRO   = 0.80
GATE_PER_CLASS  = 0.75

# --- Helpers ------------------------------------------------------------------

def sigmoid_np(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def load_labels(df: pd.DataFrame) -> np.ndarray:
    labels = np.zeros((len(df), NUM_LABELS), dtype=np.float32)
    for i, row in enumerate(df["topics"]):
        for t in json.loads(row):
            if t in TOPICS:
                labels[i, TOPICS.index(t)] = 1.0
    return labels


def load_thresholds() -> np.ndarray:
    thr_path = MODEL_DIR / "thresholds.json"
    if thr_path.exists():
        with open(thr_path) as f:
            d = json.load(f)
        thresholds = np.array([d.get(t, 0.50) for t in TOPICS])
        print(f"Loaded thresholds from {thr_path}")
    else:
        thresholds = np.full(NUM_LABELS, 0.50)
        print("No thresholds.json found; using 0.50 for all classes.")
    return thresholds


def evaluate():
    print("\n" + "=" * 60)
    print("SAATHI AI — Topic Classifier Evaluation")
    print("=" * 60)

    # -- 1. Load test data ------------------------------------------------------
    if not TEST_CSV.exists():
        print(f"ERROR: Test file not found: {TEST_CSV}")
        sys.exit(1)

    df = pd.read_csv(TEST_CSV)
    print(f"\nTest samples : {len(df)}")
    true_labels = load_labels(df)

    # -- 2. Load model ----------------------------------------------------------
    if not MODEL_DIR.exists():
        print(f"ERROR: Model not found at {MODEL_DIR}")
        print("Run train_topic_distilbert.py first.")
        sys.exit(1)

    print(f"\nLoading model from {MODEL_DIR} ...")
    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
    model     = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR))
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    print(f"Device: {device}")

    # -- 3. Load thresholds -----------------------------------------------------
    thresholds = load_thresholds()
    print(f"Thresholds  : {dict(zip(TOPICS, thresholds.round(3)))}")

    # -- 4. Run inference -------------------------------------------------------
    print("\nRunning inference ...")
    all_logits = []
    t_start = time.time()
    batch_size = 32

    for start in range(0, len(df), batch_size):
        batch_texts = df["utterance"].iloc[start : start + batch_size].tolist()
        enc = tokenizer(
            batch_texts,
            max_length=128,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        )
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            logits = model(**enc).logits.cpu().numpy()
        all_logits.append(logits)

    inference_ms = (time.time() - t_start) * 1000
    all_logits = np.vstack(all_logits)

    # -- 5. Apply thresholds ----------------------------------------------------
    probs       = sigmoid_np(all_logits)
    pred_labels = (probs >= thresholds).astype(int)

    # Handle edge case: no positive predicted — assign highest prob class
    zero_rows = pred_labels.sum(axis=1) == 0
    if zero_rows.any():
        best = np.argmax(probs[zero_rows], axis=1)
        pred_labels[zero_rows, best] = 1
        print(f"Note: {zero_rows.sum()} samples had 0 positive predictions; assigned top class.")

    # -- 6. Compute metrics -----------------------------------------------------
    f1_samples = f1_score(true_labels, pred_labels, average="samples", zero_division=0)
    f1_macro   = f1_score(true_labels, pred_labels, average="macro",   zero_division=0)
    f1_micro   = f1_score(true_labels, pred_labels, average="micro",   zero_division=0)
    h_loss     = hamming_loss(true_labels, pred_labels)
    subset_acc = accuracy_score(true_labels, pred_labels)

    per_class_f1 = f1_score(true_labels, pred_labels, average=None, zero_division=0)

    # -- 7. Print report --------------------------------------------------------
    print("\n" + "-" * 60)
    print("MULTI-LABEL METRICS")
    print("-" * 60)
    print(f"  F1 (samples)   : {f1_samples:.4f}")
    print(f"  F1 (macro)     : {f1_macro:.4f}")
    print(f"  F1 (micro)     : {f1_micro:.4f}")
    print(f"  Hamming Loss   : {h_loss:.4f}")
    print(f"  Subset Accuracy: {subset_acc:.4f}")
    print(f"  Inference Time : {inference_ms:.0f} ms ({len(df)} samples)")
    print(f"  Per-sample avg : {inference_ms / len(df):.1f} ms")

    print("\n" + "-" * 60)
    print("PER-CLASS F1 SCORES")
    print("-" * 60)
    for topic, f1 in zip(TOPICS, per_class_f1):
        status = "PASS" if f1 >= GATE_PER_CLASS else "FAIL"
        print(f"  {topic:<25} F1={f1:.4f}  [{status}]")

    # -- 8. Qualification gates -------------------------------------------------
    print("\n" + "-" * 60)
    print("QUALIFICATION GATES")
    print("-" * 60)
    gates = {
        f"F1_samples >= {GATE_F1_SAMPLES}": f1_samples >= GATE_F1_SAMPLES,
        f"F1_macro   >= {GATE_F1_MACRO}":   f1_macro   >= GATE_F1_MACRO,
        f"All per-class F1 >= {GATE_PER_CLASS}": all(per_class_f1 >= GATE_PER_CLASS),
    }
    all_passed = True
    for gate_name, passed in gates.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {gate_name}")
        if not passed:
            all_passed = False

    overall = "ALL GATES PASSED — MODEL APPROVED" if all_passed else "SOME GATES FAILED — REVIEW NEEDED"
    print(f"\n  *** {overall} ***")

    # -- 9. Full sklearn classification report ----------------------------------
    print("\n" + "-" * 60)
    print("SKLEARN CLASSIFICATION REPORT (per label)")
    print("-" * 60)
    print(
        classification_report(
            true_labels, pred_labels, target_names=TOPICS, zero_division=0
        )
    )

    # -- 10. Multi-label distribution ------------------------------------------
    labels_per_sample = pred_labels.sum(axis=1)
    print("-" * 60)
    print("PREDICTED LABEL COUNT DISTRIBUTION")
    print("-" * 60)
    for n in sorted(set(labels_per_sample)):
        count = (labels_per_sample == n).sum()
        pct   = count / len(df) * 100
        print(f"  {n} label(s) : {count:4d} samples  ({pct:.1f}%)")

    # -- 11. Save JSON results --------------------------------------------------
    results = {
        "model_path": str(MODEL_DIR),
        "test_samples": len(df),
        "metrics": {
            "f1_samples": round(f1_samples, 4),
            "f1_macro":   round(f1_macro, 4),
            "f1_micro":   round(f1_micro, 4),
            "hamming_loss": round(h_loss, 4),
            "subset_accuracy": round(subset_acc, 4),
            "inference_ms_total": round(inference_ms, 1),
            "inference_ms_per_sample": round(inference_ms / len(df), 2),
        },
        "per_class_f1": {t: round(float(f), 4) for t, f in zip(TOPICS, per_class_f1)},
        "thresholds": {t: round(float(v), 4) for t, v in zip(TOPICS, thresholds)},
        "qualification_gates": {k: bool(v) for k, v in gates.items()},
        "all_gates_passed": all_passed,
    }

    out_path = RESULTS_DIR / "evaluation_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {out_path}")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    passed = evaluate()
    sys.exit(0 if passed else 1)
