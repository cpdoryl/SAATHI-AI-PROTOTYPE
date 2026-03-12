#!/usr/bin/env python3
"""
Meta-Model Pattern Detector - Data Splitting Script

Creates 70/15/15 train/val/test splits with stratification by pattern categories.
Uses JSONL format for efficient handling of nested JSON structures.
"""

import json
import os
import random
from pathlib import Path
from collections import Counter

def load_jsonl(path):
    """Load JSONL file into list of dicts."""
    data = []
    with open(path, 'r') as f:
        for line in f:
            data.append(json.loads(line.strip()))
    return data

def get_primary_pattern_category(patterns):
    """Get primary (first) pattern category for stratification."""
    if patterns and len(patterns) > 0:
        return patterns[0]['pattern_category']
    return 'unknown'

def prepare_data_splits(
    dataset_path: str,
    output_dir: str,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_state: int = 42
) -> dict:
    """Split dataset into train/val/test with stratification."""

    random.seed(random_state)

    print("="*70)
    print("PREPARING DATA SPLITS FOR META-MODEL PATTERN DETECTOR")
    print("="*70)

    # Load dataset
    print(f"\n1. Loading dataset from: {dataset_path}")
    data = load_jsonl(dataset_path)
    print(f"   Total examples: {len(data)}")

    # Add stratification key
    print(f"\n2. Adding stratification keys (primary pattern category)")
    for item in data:
        item['_strat_key'] = get_primary_pattern_category(item['patterns'])

    strat_counts = Counter(item['_strat_key'] for item in data)
    print(f"   Category distribution:")
    for cat in ['deletion', 'generalization', 'distortion']:
        print(f"     {cat}: {strat_counts.get(cat, 0)}")

    # Stratified split implementation
    print(f"\n3. Performing stratified split (70/15/15)")

    # Group by stratification key
    cat_groups = {}
    for item in data:
        cat = item['_strat_key']
        if cat not in cat_groups:
            cat_groups[cat] = []
        cat_groups[cat].append(item)

    train_data = []
    val_data = []
    test_data = []

    # Stratified split per category
    for cat, items in cat_groups.items():
        random.shuffle(items)

        train_end = int(len(items) * train_ratio)
        val_end = train_end + int(len(items) * val_ratio)

        train_data.extend(items[:train_end])
        val_data.extend(items[train_end:val_end])
        test_data.extend(items[val_end:])

        print(f"   {cat:15s}: {len(items):4d} total --> {len(items[:train_end]):4d} train, "
              f"{len(items[train_end:val_end]):3d} val, {len(items[val_end:]):3d} test")

    # Final shuffle
    random.shuffle(train_data)
    random.shuffle(val_data)
    random.shuffle(test_data)

    print(f"\n4. Final split proportions:")
    print(f"   Train: {len(train_data):4d} ({len(train_data)/len(data)*100:5.1f}%)")
    print(f"   Val:   {len(val_data):4d} ({len(val_data)/len(data)*100:5.1f}%)")
    print(f"   Test:  {len(test_data):4d} ({len(test_data)/len(data)*100:5.1f}%)")
    print(f"   Total: {len(train_data) + len(val_data) + len(test_data):4d}")

    # Verify stratification maintained
    print(f"\n5. Category distribution per split:")
    for split_name, split_data in [("Train", train_data), ("Val", val_data), ("Test", test_data)]:
        print(f"\n   {split_name}:")
        split_cats = Counter(item['_strat_key'] for item in split_data)
        for cat in ['deletion', 'generalization', 'distortion']:
            count = split_cats.get(cat, 0)
            pct = count / len(split_data) * 100 if split_data else 0
            print(f"     {cat:15s}: {count:3d} ({pct:5.1f}%)")

    # Check for leakage
    print(f"\n6. Data leakage check:")
    train_ids = set(d['id'] for d in train_data)
    val_ids = set(d['id'] for d in val_data)
    test_ids = set(d['id'] for d in test_data)

    overlap_tv = len(train_ids & val_ids)
    overlap_tt = len(train_ids & test_ids)
    overlap_vt = len(val_ids & test_ids)

    print(f"   train & val:  {overlap_tv} [OK]" if overlap_tv == 0 else f"   train & val:  {overlap_tv} [FAIL]")
    print(f"   train & test: {overlap_tt} [OK]" if overlap_tt == 0 else f"   train & test: {overlap_tt} [FAIL]")
    print(f"   val & test:   {overlap_vt} [OK]" if overlap_vt == 0 else f"   val & test:   {overlap_vt} [FAIL]")

    # Save splits
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n7. Saving splits to: {output_dir}/")

    def save_jsonl(data, filepath):
        with open(filepath, 'w') as f:
            for item in data:
                # Remove stratification key before saving
                item_copy = {k: v for k, v in item.items() if k != '_strat_key'}
                f.write(json.dumps(item_copy, default=str) + "\n")

    train_path = os.path.join(output_dir, "train.jsonl")
    val_path = os.path.join(output_dir, "val.jsonl")
    test_path = os.path.join(output_dir, "test.jsonl")

    save_jsonl(train_data, train_path)
    save_jsonl(val_data, val_path)
    save_jsonl(test_data, test_path)

    print(f"   [OK] {train_path}")
    print(f"   [OK] {val_path}")
    print(f"   [OK] {test_path}")

    # Compute category distribution BEFORE removing _strat_key
    train_cat_dist = dict(Counter(d['_strat_key'] for d in train_data))
    val_cat_dist = dict(Counter(d['_strat_key'] for d in val_data))
    test_cat_dist = dict(Counter(d['_strat_key'] for d in test_data))

    # Create metadata
    split_info = {
        "total_examples": len(data),
        "train": {
            "examples": len(train_data),
            "ratio": float(len(train_data) / len(data)),
            "category_distribution": train_cat_dist
        },
        "validation": {
            "examples": len(val_data),
            "ratio": float(len(val_data) / len(data)),
            "category_distribution": val_cat_dist
        },
        "test": {
            "examples": len(test_data),
            "ratio": float(len(test_data) / len(data)),
            "category_distribution": test_cat_dist
        },
        "stratification_column": "pattern_category",
        "random_state": random_state,
        "no_leakage": overlap_tv == 0 and overlap_tt == 0 and overlap_vt == 0
    }

    split_info_path = os.path.join(output_dir, "split_info.json")
    with open(split_info_path, 'w') as f:
        json.dump(split_info, f, indent=2)
    print(f"   [OK] {split_info_path}")

    print(f"\n{'='*70}")
    print(f"DATA SPLITTING COMPLETE")
    print(f"{'='*70}\n")

    return split_info


if __name__ == "__main__":
    dataset_path = "Meta model pattern detector/meta_model_patterns_v1.jsonl"
    output_dir = "Meta model pattern detector/data/splits"

    split_info = prepare_data_splits(dataset_path, output_dir)

    print(f"Split Information Summary:")
    print(json.dumps(split_info, indent=2))
