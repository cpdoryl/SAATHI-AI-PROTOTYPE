"""
SAATHI AI -- Emotion Detection Dataset Splitter
================================================
Stratified 80/10/10 (train/val/test) split.
Verifies no leakage between splits.
Saves splits to data/splits/.

Usage:
    python scripts/prepare_data_splits.py
"""

import csv
import json
import os
import random
from collections import Counter

random.seed(42)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.join(SCRIPT_DIR, "..")
CSV_PATH   = os.path.join(BASE_DIR, "emotion_detection_v2_comprehensive.csv")
SPLITS_DIR = os.path.join(BASE_DIR, "data", "splits")

LABEL_COL  = "primary_emotion"
CLASSES    = ["anxiety", "sadness", "anger", "fear",
              "hopelessness", "guilt", "shame", "neutral"]

TRAIN_FRAC = 0.80
VAL_FRAC   = 0.10
# TEST_FRAC  = 0.10 (remainder)


def read_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(rows, path, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def stratified_split(rows, train_f, val_f, label_col):
    """Stratified split: train / val / test by label."""
    by_class = {}
    for r in rows:
        lbl = r[label_col]
        by_class.setdefault(lbl, []).append(r)

    train, val, test = [], [], []
    for lbl, items in by_class.items():
        random.shuffle(items)
        n = len(items)
        n_train = int(n * train_f)
        n_val   = int(n * val_f)
        train.extend(items[:n_train])
        val.extend(items[n_train:n_train + n_val])
        test.extend(items[n_train + n_val:])

    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)
    return train, val, test


def verify_no_leakage(train, val, test, id_col="id"):
    train_ids = {r[id_col] for r in train}
    val_ids   = {r[id_col] for r in val}
    test_ids  = {r[id_col] for r in test}
    tv = train_ids & val_ids
    tt = train_ids & test_ids
    vt = val_ids   & test_ids
    print(f"  Train+Val  overlap: {len(tv)}")
    print(f"  Train+Test overlap: {len(tt)}")
    print(f"  Val+Test   overlap: {len(vt)}")
    assert len(tv) == 0, "LEAKAGE: train and val share IDs"
    assert len(tt) == 0, "LEAKAGE: train and test share IDs"
    assert len(vt) == 0, "LEAKAGE: val and test share IDs"
    print("  No leakage detected -- PASS")


def dist_table(rows, label_col):
    counts = Counter(r[label_col] for r in rows)
    n = len(rows)
    return {cls: {"count": counts.get(cls, 0),
                  "pct": round(counts.get(cls, 0) / n * 100, 1) if n else 0}
            for cls in CLASSES}


def main():
    rows = read_csv(CSV_PATH)
    fieldnames = list(rows[0].keys())
    total = len(rows)
    print(f"Source dataset: {CSV_PATH}")
    print(f"Total records : {total}")

    # Check all 8 classes present
    present = set(r[LABEL_COL] for r in rows)
    for cls in CLASSES:
        assert cls in present, f"Missing class in source: {cls}"
    print(f"All {len(CLASSES)} classes present -- PASS\n")

    train, val, test = stratified_split(rows, TRAIN_FRAC, VAL_FRAC, LABEL_COL)

    print(f"Split sizes  : train={len(train)} | val={len(val)} | test={len(test)}")
    print(f"Expected     : train~{int(total*0.80)} | val~{int(total*0.10)} | test~{int(total*0.10)}\n")

    print("Verifying no data leakage...")
    verify_no_leakage(train, val, test)

    # Verify all classes in all splits
    for name, split in [("train", train), ("val", val), ("test", test)]:
        present_s = set(r[LABEL_COL] for r in split)
        for cls in CLASSES:
            assert cls in present_s, f"Class '{cls}' missing from {name} split"
    print("  All classes present in all 3 splits -- PASS\n")

    # Write splits
    os.makedirs(SPLITS_DIR, exist_ok=True)
    write_csv(train, os.path.join(SPLITS_DIR, "train.csv"), fieldnames)
    write_csv(val,   os.path.join(SPLITS_DIR, "val.csv"),   fieldnames)
    write_csv(test,  os.path.join(SPLITS_DIR, "test.csv"),  fieldnames)
    print(f"Splits saved to: {SPLITS_DIR}")

    # Distribution tables
    print("\n--- Class distribution per split ---")
    print(f"{'Class':<24} {'Total':>6}  {'Train':>6}  {'Val':>6}  {'Test':>6}")
    print("-" * 60)
    for cls in CLASSES:
        total_n = Counter(r[LABEL_COL] for r in rows)[cls]
        tr_n    = Counter(r[LABEL_COL] for r in train)[cls]
        va_n    = Counter(r[LABEL_COL] for r in val)[cls]
        te_n    = Counter(r[LABEL_COL] for r in test)[cls]
        print(f"{cls:<24} {total_n:>6}  {tr_n:>6}  {va_n:>6}  {te_n:>6}")
    print("-" * 60)
    print(f"{'TOTAL':<24} {total:>6}  {len(train):>6}  {len(val):>6}  {len(test):>6}")

    # Save split_info.json
    split_info = {
        "source_file": "emotion_detection_v2_comprehensive.csv",
        "total": total,
        "splits": {
            "train": len(train),
            "val":   len(val),
            "test":  len(test),
        },
        "strategy": "stratified 80/10/10",
        "random_seed": 42,
        "train_dist": dist_table(train, LABEL_COL),
        "val_dist":   dist_table(val,   LABEL_COL),
        "test_dist":  dist_table(test,  LABEL_COL),
        "leakage_check": {
            "train_val_overlap": 0,
            "train_test_overlap": 0,
            "val_test_overlap": 0,
        },
        "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
    }
    info_path = os.path.join(SPLITS_DIR, "split_info.json")
    with open(info_path, "w") as f:
        json.dump(split_info, f, indent=2)
    print(f"\nSplit info saved: {info_path}")
    print("\nData split complete.")


if __name__ == "__main__":
    main()
