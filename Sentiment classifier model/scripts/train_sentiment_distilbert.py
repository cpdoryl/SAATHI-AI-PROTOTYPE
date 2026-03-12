#!/usr/bin/env python3
"""
Sentiment Classifier Training Script - Lightweight Version
Trains a DistilBERT model for 3-class sentiment classification.
"""

import os
import json
import time
import numpy as np
import pandas as pd
import torch
from datetime import datetime
from pathlib import Path

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
)
from torch.utils.data import DataLoader, TensorDataset
from torch.optim import AdamW
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
)

# ============================================================================
# PATH & CONFIG
# ============================================================================

PATHS = {
    "train_data": "Sentiment classifier model/data/splits/train.csv",
    "val_data": "Sentiment classifier model/data/splits/val.csv",
    "test_data": "Sentiment classifier model/data/splits/test.csv",
    "best_model_dir": "Sentiment classifier model/models/best_model",
    "results_dir": "Sentiment classifier model/results",
    "logs_dir": "Sentiment classifier model/logs",
}

HYPERPARAMS = {
    "model_name": "distilbert-base-uncased",
    "max_seq_length": 128,
    "batch_size": 32,
    "num_epochs": 3,
    "learning_rate": 2e-5,
    "weight_decay": 0.01,
    "warmup_steps": 100,
}

SENTIMENT_CLASSES = ["negative", "neutral", "positive"]
LABEL2ID = {"negative": 0, "neutral": 1, "positive": 2}
ID2LABEL = {0: "negative", 1: "neutral", 2: "positive"}


def setup_logging():
    """Setup logging."""
    os.makedirs(PATHS["logs_dir"], exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(PATHS["logs_dir"], f"training_{timestamp}.log")


def log_message(log_file, msg):
    """Log message to file and print."""
    with open(log_file, 'a') as f:
        f.write(msg + "\n")
    print(msg)


def load_data_and_tokenize():
    """Load and tokenize all data."""
    print("\nLoading and tokenizing data...")

    tokenizer = AutoTokenizer.from_pretrained(HYPERPARAMS["model_name"])

    # Load datasets
    train_df = pd.read_csv(PATHS["train_data"])
    val_df = pd.read_csv(PATHS["val_data"])
    test_df = pd.read_csv(PATHS["test_data"])

    # Map to label IDs
    train_df['label'] = train_df['sentiment'].map(LABEL2ID)
    val_df['label'] = val_df['sentiment'].map(LABEL2ID)
    test_df['label'] = test_df['sentiment'].map(LABEL2ID)

    print(f"  Train: {len(train_df)} samples")
    print(f"  Val:   {len(val_df)} samples")
    print(f"  Test:  {len(test_df)} samples")

    def tokenize_function(texts, max_len=HYPERPARAMS["max_seq_length"]):
        """Tokenize texts."""
        return tokenizer(
            texts,
            max_length=max_len,
            truncation=True,
            padding='max_length',
            return_tensors='pt'
        )

    # Tokenize
    print("  Tokenizing train set...")
    train_encodings = tokenize_function(train_df['utterance'].tolist())
    print("  Tokenizing val set...")
    val_encodings = tokenize_function(val_df['utterance'].tolist())
    print("  Tokenizing test set...")
    test_encodings = tokenize_function(test_df['utterance'].tolist())

    # Create TensorDatasets
    train_dataset = TensorDataset(
        train_encodings['input_ids'],
        train_encodings['attention_mask'],
        torch.tensor(train_df['label'].values, dtype=torch.long)
    )

    val_dataset = TensorDataset(
        val_encodings['input_ids'],
        val_encodings['attention_mask'],
        torch.tensor(val_df['label'].values, dtype=torch.long)
    )

    test_dataset = TensorDataset(
        test_encodings['input_ids'],
        test_encodings['attention_mask'],
        torch.tensor(test_df['label'].values, dtype=torch.long)
    )

    return (train_dataset, val_dataset, test_dataset, tokenizer,
            test_df['label'].values)


def create_dataloaders(train_dataset, val_dataset):
    """Create DataLoaders."""
    train_loader = DataLoader(
        train_dataset,
        batch_size=HYPERPARAMS["batch_size"],
        shuffle=True
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=HYPERPARAMS["batch_size"] * 2,
        shuffle=False
    )
    return train_loader, val_loader


def train_epoch(model, loader, optimizer, device):
    """Train one epoch."""
    model.train()
    total_loss = 0

    for batch_idx, (input_ids, attention_mask, labels) in enumerate(loader):
        input_ids = input_ids.to(device)
        attention_mask = attention_mask.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        loss = outputs.loss

        loss.backward()
        optimizer.step()

        total_loss += loss.item()

        if (batch_idx + 1) % 10 == 0:
            print(f"    Batch {batch_idx + 1}/{len(loader)}, Loss: {loss.item():.4f}")

    return total_loss / len(loader)


def evaluate(model, loader, device, test_labels=None):
    """Evaluate model."""
    model.eval()
    total_loss = 0
    all_preds = []

    with torch.no_grad():
        for input_ids, attention_mask, labels in loader:
            input_ids = input_ids.to(device)
            attention_mask = attention_mask.to(device)
            labels = labels.to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            logits = outputs.logits

            total_loss += loss.item()
            preds = torch.argmax(logits, dim=-1).cpu().numpy()
            all_preds.extend(preds)

    all_preds = np.array(all_preds)
    avg_loss = total_loss / len(loader)

    if test_labels is not None:
        accuracy = accuracy_score(test_labels, all_preds)
        macro_f1 = f1_score(test_labels, all_preds, average='macro', zero_division=0)
        return avg_loss, accuracy, macro_f1, all_preds
    else:
        # For validation, compute metrics against labels in the loader
        all_labels = []
        for _, _, labels in loader:
            all_labels.extend(labels.cpu().numpy())
        all_labels = np.array(all_labels)

        accuracy = accuracy_score(all_labels, all_preds)
        macro_f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
        return avg_loss, accuracy, macro_f1, all_preds


def main():
    """Main training function."""
    log_file = setup_logging()
    start_time = time.time()

    print("="*70)
    print("SENTIMENT CLASSIFIER TRAINING")
    print("="*70)
    log_message(log_file, "="*70)
    log_message(log_file, "SENTIMENT CLASSIFIER TRAINING")
    log_message(log_file, "="*70)

    # Setup device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\nDevice: {device}")
    log_message(log_file, f"Device: {device}")

    # Load data
    print("\nLoading data...")
    train_dataset, val_dataset, test_dataset, tokenizer, test_labels = load_data_and_tokenize()

    # Create loaders
    train_loader, val_loader = create_dataloaders(train_dataset, val_dataset)
    test_loader = DataLoader(test_dataset, batch_size=HYPERPARAMS["batch_size"] * 2)

    # Load model
    print("\nLoading model...")
    model = AutoModelForSequenceClassification.from_pretrained(
        HYPERPARAMS["model_name"],
        num_labels=3,
        id2label=ID2LABEL,
        label2id=LABEL2ID
    )
    model.to(device)

    # Setup optimizer
    optimizer = AdamW(model.parameters(), lr=HYPERPARAMS["learning_rate"])

    # Training loop
    print("\nStarting training...")
    best_val_f1 = 0
    best_epoch = 0

    for epoch in range(HYPERPARAMS["num_epochs"]):
        print(f"\nEpoch {epoch + 1}/{HYPERPARAMS['num_epochs']}")

        # Train
        train_loss = train_epoch(model, train_loader, optimizer, device)
        print(f"  Train Loss: {train_loss:.4f}")

        # Validate
        val_loss, val_acc, val_f1, _ = evaluate(model, val_loader, device)
        print(f"  Val Loss: {val_loss:.4f}, Acc: {val_acc:.4f}, F1: {val_f1:.4f}")

        # Save best model
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_epoch = epoch
            os.makedirs(PATHS["best_model_dir"], exist_ok=True)
            model.save_pretrained(PATHS["best_model_dir"])
            tokenizer.save_pretrained(PATHS["best_model_dir"])
            print(f"  [Saved best model]")

    # Evaluate on test set
    print(f"\nEvaluating on test set...")
    model.eval()
    test_loss, test_acc, test_f1, test_preds = evaluate(model, test_loader, device, test_labels)

    print(f"\nTest Set Results:")
    print(f"  Accuracy: {test_acc:.4f}")
    print(f"  Macro F1: {test_f1:.4f}")

    # Per-class metrics
    print(f"\nPer-class metrics:")
    class_report = classification_report(
        test_labels, test_preds,
        target_names=SENTIMENT_CLASSES,
        digits=4
    )
    print(class_report)

    # Save results
    os.makedirs(PATHS["results_dir"], exist_ok=True)

    results = {
        "accuracy": float(test_acc),
        "macro_f1": float(test_f1),
        "test_samples": len(test_labels),
        "training_time": time.time() - start_time,
        "best_epoch": best_epoch,
        "best_val_f1": float(best_val_f1),
    }

    with open(os.path.join(PATHS["results_dir"], "training_history.json"), 'w') as f:
        json.dump(results, f, indent=2)

    with open(os.path.join(PATHS["results_dir"], "test_evaluation.txt"), 'w') as f:
        f.write("SENTIMENT CLASSIFIER - TEST SET EVALUATION\n")
        f.write("="*70 + "\n\n")
        f.write(f"Accuracy: {test_acc:.4f}\n")
        f.write(f"Macro F1: {test_f1:.4f}\n\n")
        f.write("Per-class Metrics:\n")
        f.write(class_report)

    print("\n" + "="*70)
    print("TRAINING COMPLETE")
    print("="*70)
    log_message(log_file, "\n" + "="*70)
    log_message(log_file, "TRAINING COMPLETE")
    log_message(log_file, "="*70)

    return results


if __name__ == "__main__":
    result = main()
    print(f"\nFinal Results:")
    print(f"  Accuracy: {result['accuracy']:.4f}")
    print(f"  Macro F1: {result['macro_f1']:.4f}")
    print(f"  Training time: {result['training_time']:.1f}s")
