"""
SAATHI AI -- Phase 3 Crisis Detection
Dataset Splitting Script
=================================
Stratified 70/15/15 train/val/test split of phase_3_lower_risk_1500.csv.

Run:
    python scripts/prepare_data_splits.py

Output:
    data/splits/train.csv
    data/splits/val.csv
    data/splits/test.csv
    data/splits/split_info.json
"""

import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

# -- Paths ---------------------------------------------------------------------
BASE_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = BASE_DIR / "data" / "splits"
SOURCE_CSV = BASE_DIR / "phase_3_lower_risk_1500.csv"

RANDOM_SEED   = 42
TRAIN_RATIO   = 0.70
VAL_RATIO     = 0.15
# TEST_RATIO  = 0.15  (remainder)

CLASS_NAMES = {
    "0": "safe",
    "1": "passive_ideation",
    "2": "mild_distress",
    "3": "moderate_concern",
    "4": "elevated_monitoring",
    "5": "pre_crisis_intervention",
}


def load_csv(path: Path) -> list:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save_csv(rows: list, path: Path):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def stratified_split(rows: list, train_r: float, val_r: float, seed: int):
    """Stratified split that preserves class distribution in each split."""
    rng = random.Random(seed)

    # Group by class label
    by_class = defaultdict(list)
    for row in rows:
        by_class[row["crisis_label"]].append(row)

    train, val, test = [], [], []

    for label in sorted(by_class.keys()):
        group = by_class[label][:]
        rng.shuffle(group)
        n = len(group)
        n_train = max(1, round(n * train_r))
        n_val   = max(1, round(n * val_r))
        # Ensure at least 1 sample in test for each class
        n_val   = min(n_val, n - n_train - 1)
        train  += group[:n_train]
        val    += group[n_train : n_train + n_val]
        test   += group[n_train + n_val :]

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test


def distribution(rows: list) -> dict:
    counts = Counter(r["crisis_label"] for r in rows)
    total  = len(rows)
    return {
        CLASS_NAMES.get(k, k): {
            "count": v,
            "pct":   round(v / total * 100, 1),
        }
        for k, v in sorted(counts.items())
    }


def main():
    print("=" * 60)
    print("SAATHI AI -- Phase 3 Dataset Split")
    print("=" * 60)

    print(f"Loading: {SOURCE_CSV}")
    rows = load_csv(SOURCE_CSV)
    print(f"Total records: {len(rows)}")

    # Source distribution
    src_dist = Counter(r["crisis_label"] for r in rows)
    print("\nSource class distribution:")
    for k in sorted(src_dist):
        print(f"  Class {k} ({CLASS_NAMES.get(k, '?')}): {src_dist[k]}")

    # Split
    print(f"\nSplitting with seed={RANDOM_SEED}, {int(TRAIN_RATIO*100)}/{int(VAL_RATIO*100)}/15 ...")
    train, val, test = stratified_split(rows, TRAIN_RATIO, VAL_RATIO, RANDOM_SEED)
    print(f"  Train: {len(train)}")
    print(f"  Val  : {len(val)}")
    print(f"  Test : {len(test)}")

    # Verify no overlap
    train_ids = {r["id"] for r in train}
    val_ids   = {r["id"] for r in val}
    test_ids  = {r["id"] for r in test}
    assert not (train_ids & val_ids), "Train/Val overlap detected!"
    assert not (train_ids & test_ids), "Train/Test overlap detected!"
    assert not (val_ids  & test_ids), "Val/Test overlap detected!"
    print("  [OK] No data leakage -- all splits disjoint")

    # Save splits
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    save_csv(train, DATA_DIR / "train.csv")
    save_csv(val,   DATA_DIR / "val.csv")
    save_csv(test,  DATA_DIR / "test.csv")
    print(f"\nSaved to: {DATA_DIR}")

    # Save split_info.json
    split_info = {
        "created_at":   __import__("datetime").datetime.now().isoformat(),
        "source":       str(SOURCE_CSV.name),
        "random_seed":  RANDOM_SEED,
        "splits": {
            "train": {"file": "train.csv", "records": len(train), "distribution": distribution(train)},
            "val":   {"file": "val.csv",   "records": len(val),   "distribution": distribution(val)},
            "test":  {"file": "test.csv",  "records": len(test),  "distribution": distribution(test)},
        },
    }
    info_path = DATA_DIR / "split_info.json"
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(split_info, f, indent=2)
    print(f"Split info saved: {info_path}")

    # Verify class coverage
    for split_name, split_rows in [("train", train), ("val", val), ("test", test)]:
        labels = set(r["crisis_label"] for r in split_rows)
        missing = set(src_dist.keys()) - labels
        if missing:
            print(f"  WARNING: {split_name} is missing classes: {missing}")
        else:
            print(f"  [OK] {split_name}: all 6 classes present")

    print("\nDone. Run train_phase3_distilbert.py next.")


if __name__ == "__main__":
    main()
