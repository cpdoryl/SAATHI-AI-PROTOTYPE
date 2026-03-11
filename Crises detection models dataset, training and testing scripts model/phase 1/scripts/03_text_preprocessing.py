"""
Crisis Detection Dataset - Text Preprocessing
==============================================
Prepares utterances for transformer model training
"""

import pandas as pd
import numpy as np
import re
from transformers import AutoTokenizer

# Configuration
TRAIN_PATH = "../data/splits/train.csv"
VAL_PATH = "../data/splits/validation.csv"
MODEL_NAME = "distilbert-base-uncased"
MAX_LENGTH = 128

def load_splits():
    """Load train and validation splits"""
    print("Loading splits...")
    train_df = pd.read_csv(TRAIN_PATH, encoding='utf-8')
    val_df = pd.read_csv(VAL_PATH, encoding='utf-8')
    
    print(f"✅ Training: {len(train_df)} records")
    print(f"✅ Validation: {len(val_df)} records")
    
    return train_df, val_df

def create_label_mapping(train_df):
    """Create severity score to label ID mapping"""
    unique_severities = sorted(train_df['severity_score'].unique())
    
    label2id = {severity: idx for idx, severity in enumerate(unique_severities)}
    id2label = {idx: severity for severity, idx in label2id.items()}
    
    print("\n" + "="*60)
    print("LABEL MAPPING")
    print("="*60)
    print(f"Number of classes: {len(label2id)}")
    print("\nMapping:")
    for severity, idx in label2id.items():
        risk = get_risk_description(severity)
        print(f"  Label {idx}: Severity {severity} ({risk})")
    
    return label2id, id2label

def get_risk_description(severity):
    """Get risk description for severity score"""
    if severity <= 0.2:
        return "Passive Ideation"
    elif severity <= 0.6:
        return "Active Ideation"
    elif severity <= 0.7:
        return "Active with Method"
    else:
        return "Intent to Act - HIGH RISK"

def preprocess_text(text):
    """Basic text preprocessing"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Keep as-is for transformer (handles multilingual)
    return text

def prepare_dataset(df, label2id, tokenizer):
    """Prepare dataset for training"""
    print("\nPreparing dataset...")
    
    # Preprocess utterances
    df['processed_text'] = df['utterance'].apply(preprocess_text)
    
    # Create label IDs
    df['label_id'] = df['severity_score'].map(label2id)
    
    # Tokenize texts
    print(f"Tokenizing with {MODEL_NAME}...")
    encodings = tokenizer(
        df['processed_text'].tolist(),
        truncation=True,
        padding='max_length',
        max_length=MAX_LENGTH,
        return_tensors=None
    )
    
    # Create dataset dict
    dataset_dict = {
        'input_ids': encodings['input_ids'],
        'attention_mask': encodings['attention_mask'],
        'labels': df['label_id'].tolist(),
        'severity_score': df['severity_score'].tolist(),
        'high_risk_flag': df['high_risk_flag'].tolist(),
        'id': df['id'].tolist()
    }
    
    print(f"✅ Prepared {len(df)} samples")
    print(f"   Max sequence length: {MAX_LENGTH}")
    print(f"   Vocab size: {tokenizer.vocab_size}")
    
    return dataset_dict

def analyze_tokenization(train_dict, val_dict, tokenizer):
    """Analyze tokenization statistics"""
    print("\n" + "="*60)
    print("TOKENIZATION ANALYSIS")
    print("="*60)
    
    # Calculate sequence lengths
    train_lengths = [sum(mask) for mask in train_dict['attention_mask']]
    val_lengths = [sum(mask) for mask in val_dict['attention_mask']]
    
    print(f"\nTraining set:")
    print(f"  Avg tokens: {np.mean(train_lengths):.1f}")
    print(f"  Max tokens: {max(train_lengths)}")
    print(f"  Min tokens: {min(train_lengths)}")
    
    print(f"\nValidation set:")
    print(f"  Avg tokens: {np.mean(val_lengths):.1f}")
    print(f"  Max tokens: {max(val_lengths)}")
    print(f"  Min tokens: {min(val_lengths)}")
    
    # Check for truncation
    truncated = sum(1 for length in train_lengths + val_lengths if length == MAX_LENGTH)
    total = len(train_lengths) + len(val_lengths)
    print(f"\nTruncated sequences: {truncated}/{total} ({truncated/total*100:.1f}%)")

def save_processed_data(train_dict, val_dict, label2id, id2label):
    """Save processed datasets"""
    print("\n" + "="*60)
    print("SAVING PROCESSED DATA")
    print("="*60)
    
    # Save as numpy arrays for fast loading
    np.savez_compressed(
        '../data/processed/train_processed.npz',
        **{k: np.array(v) for k, v in train_dict.items()}
    )
    print("✅ Saved: data/processed/train_processed.npz")
    
    np.savez_compressed(
        '../data/processed/val_processed.npz',
        **{k: np.array(v) for k, v in val_dict.items()}
    )
    print("✅ Saved: data/processed/val_processed.npz")
    
    # Save label mappings
    import json
    with open('../data/processed/label_mapping.json', 'w') as f:
        json.dump({
            'label2id': {str(k): v for k, v in label2id.items()},
            'id2label': {str(k): float(v) for k, v in id2label.items()},
            'num_labels': len(label2id)
        }, f, indent=2)
    print("✅ Saved: data/processed/label_mapping.json")

def main():
    """Main execution"""
    print("="*60)
    print("CRISIS DETECTION - TEXT PREPROCESSING")
    print("="*60)
    
    # Load datasets
    train_df, val_df = load_splits()
    
    # Create label mapping
    label2id, id2label = create_label_mapping(train_df)
    
    # Initialize tokenizer
    print(f"\nInitializing tokenizer: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    print(f"✅ Tokenizer loaded")
    
    # Prepare datasets
    train_dict = prepare_dataset(train_df, label2id, tokenizer)
    val_dict = prepare_dataset(val_df, label2id, tokenizer)
    
    # Analyze tokenization
    analyze_tokenization(train_dict, val_dict, tokenizer)
    
    # Save processed data
    save_processed_data(train_dict, val_dict, label2id, id2label)
    
    print("\n" + "="*60)
    print("✅ TEXT PREPROCESSING COMPLETE")
    print("="*60)
    print(f"\nReady for model training: ✅")

if __name__ == "__main__":
    main()