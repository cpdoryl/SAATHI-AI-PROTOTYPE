"""
Crisis Detection Dataset - Train/Validation/Test Split
========================================================
Creates stratified 70/15/15 split preserving severity distribution
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import json

# Configuration
DATA_PATH = "../data/raw/phase1_suicidal_ideation.csv"
TRAIN_OUTPUT = "../data/splits/train.csv"
VAL_OUTPUT = "../data/splits/validation.csv"
TEST_OUTPUT = "../data/splits/test.csv"
SPLIT_INFO_OUTPUT = "../data/splits/split_info.json"

# Split ratios: 70% train, 15% validation, 15% test
TRAIN_SIZE = 0.70
VAL_SIZE = 0.15
TEST_SIZE = 0.15
RANDOM_SEED = 42

def load_dataset():
    """Load Phase 1 dataset"""
    print("Loading Phase 1 dataset...")
    df = pd.read_csv(DATA_PATH, encoding='utf-8')
    print(f"✅ Loaded {len(df)} records")
    return df

def create_stratified_split(df):
    """Create stratified train/val/test split"""
    print("\nCreating stratified 3-way split...")
    print(f"  Train size: {TRAIN_SIZE*100}%")
    print(f"  Validation size: {VAL_SIZE*100}%")
    print(f"  Test size: {TEST_SIZE*100}%")
    print(f"  Stratify by: severity_score")
    print(f"  Random seed: {RANDOM_SEED}")
    
    # First split: separate train from (validation + test)
    train_df, temp_df = train_test_split(
        df,
        train_size=TRAIN_SIZE,
        stratify=df['severity_score'],
        random_state=RANDOM_SEED
    )
    
    # Second split: separate validation from test
    # Calculate relative size: test should be 50% of temp_df to get 15% of total
    relative_test_size = TEST_SIZE / (VAL_SIZE + TEST_SIZE)
    
    val_df, test_df = train_test_split(
        temp_df,
        test_size=relative_test_size,
        stratify=temp_df['severity_score'],
        random_state=RANDOM_SEED
    )
    
    print(f"\n✅ Split complete:")
    print(f"  Training records: {len(train_df)} ({len(train_df)/len(df)*100:.1f}%)")
    print(f"  Validation records: {len(val_df)} ({len(val_df)/len(df)*100:.1f}%)")
    print(f"  Test records: {len(test_df)} ({len(test_df)/len(df)*100:.1f}%)")
    print(f"  Total: {len(train_df) + len(val_df) + len(test_df)}")
    
    return train_df, val_df, test_df

def verify_split_distribution(train_df, val_df, test_df, original_df):
    """Verify that split preserves severity distribution across all three sets"""
    print("\n" + "="*80)
    print("SPLIT DISTRIBUTION VERIFICATION")
    print("="*80)
    
    print("\nSeverity Distribution:")
    print(f"{'Severity':<12} {'Original':<15} {'Train':<15} {'Validation':<15} {'Test':<15}")
    print("-" * 80)
    
    for severity in sorted(original_df['severity_score'].unique()):
        orig_pct = (original_df['severity_score'] == severity).sum() / len(original_df) * 100
        train_pct = (train_df['severity_score'] == severity).sum() / len(train_df) * 100
        val_pct = (val_df['severity_score'] == severity).sum() / len(val_df) * 100
        test_pct = (test_df['severity_score'] == severity).sum() / len(test_df) * 100
        
        print(f"{severity:<12.1f} {orig_pct:<15.1f} {train_pct:<15.1f} {val_pct:<15.1f} {test_pct:<15.1f}")
    
    # Check high-risk distribution
    print("\nHigh Risk Distribution:")
    orig_hr = (original_df['high_risk_flag'] == True).sum()
    train_hr = (train_df['high_risk_flag'] == True).sum()
    val_hr = (val_df['high_risk_flag'] == True).sum()
    test_hr = (test_df['high_risk_flag'] == True).sum()
    
    print(f"  Original: {orig_hr} ({orig_hr/len(original_df)*100:.1f}%)")
    print(f"  Training: {train_hr} ({train_hr/len(train_df)*100:.1f}%)")
    print(f"  Validation: {val_hr} ({val_hr/len(val_df)*100:.1f}%)")
    print(f"  Test: {test_hr} ({test_hr/len(test_df)*100:.1f}%)")

def save_splits(train_df, val_df, test_df):
    """Save train, validation, and test datasets"""
    print("\n" + "="*80)
    print("SAVING SPLITS")
    print("="*80)
    
    # Save train
    train_df.to_csv(TRAIN_OUTPUT, index=False, encoding='utf-8')
    print(f"✅ Training set saved: {TRAIN_OUTPUT}")
    print(f"   Records: {len(train_df)}")
    
    # Save validation
    val_df.to_csv(VAL_OUTPUT, index=False, encoding='utf-8')
    print(f"✅ Validation set saved: {VAL_OUTPUT}")
    print(f"   Records: {len(val_df)}")
    
    # Save test
    test_df.to_csv(TEST_OUTPUT, index=False, encoding='utf-8')
    print(f"✅ Test set saved: {TEST_OUTPUT}")
    print(f"   Records: {len(test_df)}")
    
    # Save split info
    split_info = {
        "total_records": len(train_df) + len(val_df) + len(test_df),
        "train_records": len(train_df),
        "validation_records": len(val_df),
        "test_records": len(test_df),
        "train_ratio": TRAIN_SIZE,
        "validation_ratio": VAL_SIZE,
        "test_ratio": TEST_SIZE,
        "random_seed": RANDOM_SEED,
        "stratify_column": "severity_score",
        "severity_distribution": {
            "train": train_df['severity_score'].value_counts().to_dict(),
            "validation": val_df['severity_score'].value_counts().to_dict(),
            "test": test_df['severity_score'].value_counts().to_dict()
        },
        "high_risk_distribution": {
            "train": int((train_df['high_risk_flag'] == True).sum()),
            "validation": int((val_df['high_risk_flag'] == True).sum()),
            "test": int((test_df['high_risk_flag'] == True).sum())
        }
    }
    
    with open(SPLIT_INFO_OUTPUT, 'w') as f:
        json.dump(split_info, f, indent=2)
    print(f"✅ Split info saved: {SPLIT_INFO_OUTPUT}")

def main():
    """Main execution"""
    print("="*80)
    print("CRISIS DETECTION DATASET - TRAIN/VAL/TEST SPLIT (70/15/15)")
    print("="*80)
    
    # Load dataset
    df = load_dataset()
    
    # Create split
    train_df, val_df, test_df = create_stratified_split(df)
    
    # Verify distribution
    verify_split_distribution(train_df, val_df, test_df, df)
    
    # Save splits
    save_splits(train_df, val_df, test_df)
    
    print("\n" + "="*80)
    print("✅ SPLIT CREATION COMPLETE")
    print("="*80)
    print(f"\nFiles created:")
    print(f"  1. {TRAIN_OUTPUT} - Training set (70%)")
    print(f"  2. {VAL_OUTPUT} - Validation set (15%)")
    print(f"  3. {TEST_OUTPUT} - Test set (15%)")
    print(f"  4. {SPLIT_INFO_OUTPUT} - Split metadata")
    print(f"\nReady for model training: ✅")
    print(f"\nIMPORTANT: Test set should ONLY be used for final evaluation!")

if __name__ == "__main__":
    main()