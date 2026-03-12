#!/usr/bin/env python3
"""
Sentiment Classifier Data Splitting Script

Splits the dataset into train/validation/test sets with:
- 80% training (1,600 examples)
- 10% validation (200 examples)
- 10% testing (200 examples)

Uses stratified splitting to preserve sentiment distribution across splits.
"""

import pandas as pd
import json
import os
from sklearn.model_selection import train_test_split

def prepare_data_splits(
    dataset_path: str,
    output_dir: str,
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
    test_ratio: float = 0.10,
    random_state: int = 42
) -> dict:
    """
    Split dataset into train/val/test with stratification by sentiment.

    Args:
        dataset_path: Path to sentiment_classifier_v1.csv
        output_dir: Output directory for splits
        train_ratio: Training ratio (default 0.80)
        val_ratio: Validation ratio (default 0.10)
        test_ratio: Test ratio (default 0.10)
        random_state: Random seed for reproducibility

    Returns:
        dict: Metadata about the splits
    """

    print("="*70)
    print("PREPARING DATA SPLITS")
    print("="*70)

    # Load dataset
    print(f"\n1. Loading dataset from: {dataset_path}")
    df = pd.read_csv(dataset_path)
    print(f"   Total examples: {len(df)}")
    print(f"   Columns: {list(df.columns)}")

    # Check sentiment distribution
    print(f"\n2. Sentiment distribution (before split):")
    counts = df['sentiment'].value_counts()
    for sentiment in ['negative', 'positive', 'neutral']:
        count = counts.get(sentiment, 0)
        pct = count / len(df) * 100
        print(f"   {sentiment:10s}: {count:4d} ({pct:5.1f}%)")

    # First split: train (80%) vs temp (20%)
    print(f"\n3. First split: 80% train, 20% temp")
    train_df, temp_df = train_test_split(
        df,
        test_size=0.20,
        stratify=df['sentiment'],
        random_state=random_state
    )
    print(f"   Train split: {len(train_df)} examples")
    print(f"   Temp split:  {len(temp_df)} examples")

    # Second split: val (10%) vs test (10%) from temp
    print(f"\n4. Second split: 50% val, 50% test from temp (10%/10% of total)")
    val_df, test_df = train_test_split(
        temp_df,
        test_size=0.50,
        stratify=temp_df['sentiment'],
        random_state=random_state
    )
    print(f"   Validation split: {len(val_df)} examples")
    print(f"   Test split:       {len(test_df)} examples")

    # Verify proportions
    print(f"\n5. Final split proportions:")
    print(f"   Train: {len(train_df):4d} ({len(train_df)/len(df)*100:5.1f}%)")
    print(f"   Val:   {len(val_df):4d} ({len(val_df)/len(df)*100:5.1f}%)")
    print(f"   Test:  {len(test_df):4d} ({len(test_df)/len(df)*100:5.1f}%)")
    print(f"   Total: {len(train_df) + len(val_df) + len(test_df):4d}")

    # Check sentiment distribution in each split
    print(f"\n6. Sentiment distribution per split:")
    for split_name, split_df in [("Train", train_df), ("Val", val_df), ("Test", test_df)]:
        print(f"\n   {split_name}:")
        counts = split_df['sentiment'].value_counts()
        for sentiment in ['negative', 'positive', 'neutral']:
            count = counts.get(sentiment, 0)
            pct = count / len(split_df) * 100
            print(f"     {sentiment:10s}: {count:3d} ({pct:5.1f}%)")

    # Check for leakage (no overlapping IDs)
    print(f"\n7. Data leakage check (no row-level overlap):")
    train_ids = set(train_df['id'])
    val_ids = set(val_df['id'])
    test_ids = set(test_df['id'])

    overlap_tv = len(train_ids & val_ids)
    overlap_tt = len(train_ids & test_ids)
    overlap_vt = len(val_ids & test_ids)

    print(f"   train & val:  {overlap_tv} (expected: 0) {'[OK]' if overlap_tv == 0 else '[FAIL]'}")
    print(f"   train & test: {overlap_tt} (expected: 0) {'[OK]' if overlap_tt == 0 else '[FAIL]'}")
    print(f"   val & test:   {overlap_vt} (expected: 0) {'[OK]' if overlap_vt == 0 else '[FAIL]'}")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Save splits
    print(f"\n8. Saving splits to: {output_dir}/")
    train_path = os.path.join(output_dir, "train.csv")
    val_path = os.path.join(output_dir, "val.csv")
    test_path = os.path.join(output_dir, "test.csv")

    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)

    print(f"   [OK] {train_path}")
    print(f"   [OK] {val_path}")
    print(f"   [OK] {test_path}")

    # Create metadata
    split_info = {
        "total_examples": len(df),
        "train": {
            "examples": len(train_df),
            "ratio": float(len(train_df) / len(df)),
            "sentiment_distribution": {
                sentiment: int(count)
                for sentiment, count in train_df['sentiment'].value_counts().items()
            }
        },
        "validation": {
            "examples": len(val_df),
            "ratio": float(len(val_df) / len(df)),
            "sentiment_distribution": {
                sentiment: int(count)
                for sentiment, count in val_df['sentiment'].value_counts().items()
            }
        },
        "test": {
            "examples": len(test_df),
            "ratio": float(len(test_df) / len(df)),
            "sentiment_distribution": {
                sentiment: int(count)
                for sentiment, count in test_df['sentiment'].value_counts().items()
            }
        },
        "stratification_column": "sentiment",
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
    dataset_path = "Sentiment classifier model/sentiment_classifier_v1.csv"
    output_dir = "Sentiment classifier model/data/splits"

    # Run splitting
    split_info = prepare_data_splits(dataset_path, output_dir)

    # Print summary
    print(f"Split Information Summary:")
    print(json.dumps(split_info, indent=2))
