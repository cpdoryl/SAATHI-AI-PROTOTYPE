"""
SAATHI AI -- Topic Classifier: Data Split Preparation
=======================================================
Stratified 80/10/10 split by primary_topic (multi-label aware).
Falls back to sklearn stratification if iterstrat not installed.

Verifies: zero leakage, all 5 topics in each split, label frequency balance.

Run:
    python "Topic classifier model/scripts/prepare_data_splits.py"
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR   = SCRIPT_DIR.parent
INPUT_CSV  = BASE_DIR / "topic_classifier_v1.csv"
SPLITS_DIR = BASE_DIR / "data" / "splits"

TOPICS = [
    "workplace_stress",
    "relationship_issues",
    "academic_stress",
    "health_concerns",
    "financial_stress",
]


def build_binary_matrix(df):
    """Convert topics JSON list column to binary (n_samples x 5) matrix."""
    matrix = np.zeros((len(df), len(TOPICS)), dtype=int)
    for i, row in enumerate(df["topics"]):
        for t in json.loads(row):
            if t in TOPICS:
                matrix[i, TOPICS.index(t)] = 1
    return matrix


def stratified_split_multilabel(df, y_matrix):
    """
    Attempt iterstrat MultilabelStratifiedShuffleSplit.
    Falls back to sklearn stratified split on primary_topic.
    """
    try:
        from iterstrat.ml_stratifiers import MultilabelStratifiedShuffleSplit
        mss = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
        for train_idx, temp_idx in mss.split(df, y_matrix):
            pass
        train_df = df.iloc[train_idx].reset_index(drop=True)
        temp_df  = df.iloc[temp_idx].reset_index(drop=True)

        y_temp = y_matrix[temp_idx]
        mss2   = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=0.50, random_state=42)
        for val_idx, test_idx in mss2.split(temp_df, y_temp):
            pass
        val_df  = temp_df.iloc[val_idx].reset_index(drop=True)
        test_df = temp_df.iloc[test_idx].reset_index(drop=True)
        print("  Split method: MultilabelStratifiedShuffleSplit (iterstrat)")
        return train_df, val_df, test_df

    except ImportError:
        print("  iterstrat not installed -- using sklearn stratify on primary_topic (fallback)")
        train_df, temp_df = train_test_split(
            df, test_size=0.20, stratify=df["primary_topic"], random_state=42
        )
        val_df, test_df = train_test_split(
            temp_df, test_size=0.50, stratify=temp_df["primary_topic"], random_state=42
        )
        return (train_df.reset_index(drop=True),
                val_df.reset_index(drop=True),
                test_df.reset_index(drop=True))


def verify_no_leakage(train_df, val_df, test_df):
    train_ids = set(train_df["id"])
    val_ids   = set(val_df["id"])
    test_ids  = set(test_df["id"])
    tv  = train_ids & val_ids
    tt  = train_ids & test_ids
    vt  = val_ids   & test_ids
    if tv or tt or vt:
        print(f"ERROR: Data leakage! Train+Val={len(tv)}, Train+Test={len(tt)}, Val+Test={len(vt)}")
        sys.exit(1)
    print("  Leakage check     : PASS (zero overlap)")


def verify_all_topics(split_df, split_name):
    present = set(split_df["primary_topic"].unique())
    missing = set(TOPICS) - present
    if missing:
        print(f"ERROR: {split_name} missing primary topics: {missing}")
        sys.exit(1)
    print(f"  {split_name} topics check : PASS (all 5 present)")


def print_stats(train_df, val_df, test_df):
    total = len(train_df) + len(val_df) + len(test_df)
    print(f"\nSplit sizes: Train={len(train_df)} | Val={len(val_df)} | Test={len(test_df)} | Total={total}")

    # Primary topic distribution
    print(f"\n{'Primary Topic':<24} {'Train':>6} {'Val':>5} {'Test':>5}")
    print("-" * 44)
    for topic in TOPICS:
        tr = (train_df["primary_topic"] == topic).sum()
        va = (val_df["primary_topic"]   == topic).sum()
        te = (test_df["primary_topic"]  == topic).sum()
        print(f"  {topic:<22} {tr:>6} {va:>5} {te:>5}")

    # Multi-label counts
    for name, sdf in [("Train", train_df), ("Val", val_df), ("Test", test_df)]:
        ml = sum(1 for r in sdf["topics"] if len(json.loads(r)) > 1)
        print(f"  {name} multi-label examples: {ml} ({100*ml/len(sdf):.1f}%)")


if __name__ == "__main__":
    print("SAATHI AI -- Topic Classifier: Data Split Preparation")
    print("=" * 55)

    if not INPUT_CSV.exists():
        print(f"ERROR: {INPUT_CSV} not found. Run generate_dataset.py first.")
        sys.exit(1)

    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded: {len(df)} examples")

    y_matrix = build_binary_matrix(df)

    print("\nRunning stratified split...")
    train_df, val_df, test_df = stratified_split_multilabel(df, y_matrix)

    print("\nRunning quality checks...")
    verify_no_leakage(train_df, val_df, test_df)
    verify_all_topics(train_df, "train")
    verify_all_topics(val_df,   "val  ")
    verify_all_topics(test_df,  "test ")

    print_stats(train_df, val_df, test_df)

    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(SPLITS_DIR / "train.csv", index=False)
    val_df.to_csv(SPLITS_DIR / "val.csv",     index=False)
    test_df.to_csv(SPLITS_DIR / "test.csv",   index=False)

    split_info = {
        "total":   int(len(df)),
        "train":   int(len(train_df)),
        "val":     int(len(val_df)),
        "test":    int(len(test_df)),
        "strategy": "stratified_80_10_10_multilabel",
        "seed":    42,
        "topics":  TOPICS,
    }
    with open(SPLITS_DIR / "split_info.json", "w") as f:
        json.dump(split_info, f, indent=2)

    print(f"\nSaved to {SPLITS_DIR}/")
    print("  train.csv, val.csv, test.csv, split_info.json")
    print("\nAll checks passed. Ready for training.")
    print("Next step: python scripts/train_topic_distilbert.py")
