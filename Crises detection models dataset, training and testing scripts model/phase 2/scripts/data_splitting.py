"""
Create Train/Validation/Test Splits
70% Train / 15% Validation / 15% Test
Stratified by severity_score
"""

import pandas as pd
from sklearn.model_selection import train_test_split
import json

# Configuration
INPUT_PATH = 'combined_crisis_dataset_3500.csv'
TRAIN_OUTPUT = 'data/splits/train_combined.csv'
VAL_OUTPUT = 'data/splits/val_combined.csv'
TEST_OUTPUT = 'data/splits/test_combined.csv'

TRAIN_SIZE = 0.70
VAL_SIZE = 0.15
TEST_SIZE = 0.15
RANDOM_SEED = 42

def create_splits():
    """Create stratified train/val/test splits"""
    
    print("="*70)
    print("CREATING TRAIN/VAL/TEST SPLITS")
    print("="*70)
    
    # Load combined dataset
    df = pd.read_csv(INPUT_PATH, encoding='utf-8')
    print(f"\n Loaded {len(df)} records")
    
    # Create severity bins for stratification
    # Combine severity 0.9 and 1.0 as "high-risk" for stratification
    df['strat_label'] = df['severity_score'].apply(
        lambda x: 'high_risk' if x >= 0.9 else f'sev_{x}'
    )
    
    # Stage 1: Split train from (val + test)
    train_df, temp_df = train_test_split(
        df,
        train_size=TRAIN_SIZE,
        stratify=df['strat_label'],
        random_state=RANDOM_SEED
    )
    
    # Stage 2: Split val from test
    relative_test_size = TEST_SIZE / (VAL_SIZE + TEST_SIZE)  # 0.5
    
    val_df, test_df = train_test_split(
        temp_df,
        test_size=relative_test_size,
        stratify=temp_df['strat_label'],
        random_state=RANDOM_SEED
    )
    
    # Remove stratification column
    train_df = train_df.drop('strat_label', axis=1)
    val_df = val_df.drop('strat_label', axis=1)
    test_df = test_df.drop('strat_label', axis=1)
    
    # Print distributions
    print(f"\n Split Sizes:")
    print(f"   Train: {len(train_df)} ({len(train_df)/len(df)*100:.1f}%)")
    print(f"   Val:   {len(val_df)} ({len(val_df)/len(df)*100:.1f}%)")
    print(f"   Test:  {len(test_df)} ({len(test_df)/len(df)*100:.1f}%)")
    
    # Verify high-risk distribution maintained
    print(f"\n High-Risk Distribution:")
    print(f"   Train: {train_df['high_risk_flag'].sum()} ({train_df['high_risk_flag'].mean()*100:.1f}%)")
    print(f"   Val:   {val_df['high_risk_flag'].sum()} ({val_df['high_risk_flag'].mean()*100:.1f}%)")
    print(f"   Test:  {test_df['high_risk_flag'].sum()} ({test_df['high_risk_flag'].mean()*100:.1f}%)")
    
    # Save splits
    import os
    os.makedirs('data/splits', exist_ok=True)
    
    train_df.to_csv(TRAIN_OUTPUT, index=False, encoding='utf-8')
    val_df.to_csv(VAL_OUTPUT, index=False, encoding='utf-8')
    test_df.to_csv(TEST_OUTPUT, index=False, encoding='utf-8')
    
    print(f"\n Saved:")
    print(f"   {TRAIN_OUTPUT}")
    print(f"   {VAL_OUTPUT}")
    print(f"   {TEST_OUTPUT}")
    
    # Save split info
    split_info = {
        "created_at": pd.Timestamp.now().isoformat(),
        "source": INPUT_PATH,
        "random_seed": RANDOM_SEED,
        "splits": {
            "train": {"file": TRAIN_OUTPUT, "records": len(train_df)},
            "val": {"file": VAL_OUTPUT, "records": len(val_df)},
            "test": {"file": TEST_OUTPUT, "records": len(test_df)}
        }
    }
    
    with open('data/splits/split_info.json', 'w') as f:
        json.dump(split_info, f, indent=2)
    
    print("\n" + "="*70)
    print(" SPLITS CREATED SUCCESSFULLY")
    print("="*70)
    
    return train_df, val_df, test_df

if __name__ == "__main__":
    train_df, val_df, test_df = create_splits()