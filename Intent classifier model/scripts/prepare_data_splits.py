"""
SAATHI AI -- Intent Classifier: Data Split Preparation
=======================================================
Stratified 80/10/10 split (train/val/test) by primary_intent.
Verifies: zero leakage, all 7 classes in each split, class balance.

Run:
    python "Intent classifier model/scripts/prepare_data_splits.py"
"""

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR   = SCRIPT_DIR.parent
INPUT_CSV  = BASE_DIR / "intent_classifier_v1.csv"
SPLITS_DIR = BASE_DIR / "data" / "splits"

INTENT_CLASSES = [
    "seek_support", "book_appointment", "crisis_emergency",
    "information_request", "feedback_complaint", "general_chat",
    "assessment_request",
]


def verify_no_leakage(train_df, val_df, test_df):
    train_ids = set(train_df["id"])
    val_ids   = set(val_df["id"])
    test_ids  = set(test_df["id"])

    tv = train_ids & val_ids
    tt = train_ids & test_ids
    vt = val_ids   & test_ids

    if tv or tt or vt:
        print(f"ERROR: Data leakage detected!")
        print(f"  Train+Val overlap  : {len(tv)}")
        print(f"  Train+Test overlap : {len(tt)}")
        print(f"  Val+Test overlap   : {len(vt)}")
        sys.exit(1)
    print("  Leakage check      : PASS (zero overlap between all splits)")


def verify_all_classes(split_df, split_name):
    present = set(split_df["primary_intent"].unique())
    missing = set(INTENT_CLASSES) - present
    if missing:
        print(f"ERROR: {split_name} is missing classes: {missing}")
        sys.exit(1)
    print(f"  {split_name} classes check : PASS (all 7 classes present)")


def print_split_stats(train_df, val_df, test_df):
    total = len(train_df) + len(val_df) + len(test_df)
    print(f"\nSplit sizes: Train={len(train_df)} | Val={len(val_df)} | Test={len(test_df)} | Total={total}")
    print(f"\n{'Class':<22} {'Train':>6} {'Val':>6} {'Test':>6}")
    print("-" * 46)
    for intent in INTENT_CLASSES:
        tr = (train_df["primary_intent"] == intent).sum()
        va = (val_df["primary_intent"]   == intent).sum()
        te = (test_df["primary_intent"]  == intent).sum()
        print(f"  {intent:<20} {tr:>6} {va:>6} {te:>6}")


if __name__ == "__main__":
    print("SAATHI AI -- Intent Classifier: Data Split Preparation")
    print("=" * 55)

    if not INPUT_CSV.exists():
        print(f"ERROR: {INPUT_CSV} not found. Run generate_dataset.py first.")
        sys.exit(1)

    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded: {len(df)} examples from {INPUT_CSV.name}")

    # ── Stratified 80/10/10 ──────────────────────────────────────────────────
    train_df, temp_df = train_test_split(
        df, test_size=0.20, stratify=df["primary_intent"], random_state=42
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, stratify=temp_df["primary_intent"], random_state=42
    )

    # ── Quality checks ───────────────────────────────────────────────────────
    print("\nRunning quality checks...")
    verify_no_leakage(train_df, val_df, test_df)
    verify_all_classes(train_df, "train")
    verify_all_classes(val_df,   "val  ")
    verify_all_classes(test_df,  "test ")

    print_split_stats(train_df, val_df, test_df)

    # ── Save splits ──────────────────────────────────────────────────────────
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)

    train_df.to_csv(SPLITS_DIR / "train.csv", index=False)
    val_df.to_csv(SPLITS_DIR / "val.csv",     index=False)
    test_df.to_csv(SPLITS_DIR / "test.csv",   index=False)

    # ── Save metadata ────────────────────────────────────────────────────────
    split_info = {
        "total":      int(len(df)),
        "train":      int(len(train_df)),
        "val":        int(len(val_df)),
        "test":       int(len(test_df)),
        "strategy":   "stratified_80_10_10",
        "seed":       42,
        "split_by":   "primary_intent",
        "classes":    INTENT_CLASSES,
        "class_counts": {
            split: {
                intent: int((split_df["primary_intent"] == intent).sum())
                for intent in INTENT_CLASSES
            }
            for split, split_df in [("train", train_df), ("val", val_df), ("test", test_df)]
        },
    }
    with open(SPLITS_DIR / "split_info.json", "w") as f:
        json.dump(split_info, f, indent=2)

    print(f"\nSaved to {SPLITS_DIR}/")
    print("  train.csv, val.csv, test.csv, split_info.json")
    print("\nAll checks passed. Ready for training.")
    print("Next step: python scripts/train_intent_distilbert.py")
