"""
═══════════════════════════════════════════════════════════════
CRISIS DETECTION MODEL - COMBINED DATASET TRAINING SCRIPT v2.0
═══════════════════════════════════════════════════════════════

CPDO Approved: December 29, 2025

This script implements:
1. Combined Phase 1 + Phase 2 dataset (3,500 records)
2. All 6 critical fixes for >99% high-risk recall
3. 6-class classification (severity levels)

Run this script after creating the combined dataset splits.
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup
from torch.optim import AdamW
from sklearn.metrics import classification_report, confusion_matrix, recall_score
import pandas as pd
import numpy as np
import json
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

MODEL_NAME = "distilbert-base-uncased"
NUM_LABELS = 6
MAX_LENGTH = 128

# FIXED HYPERPARAMETERS
LEARNING_RATE = 5e-6
BATCH_SIZE = 16
NUM_EPOCHS = 20
WEIGHT_DECAY = 0.01
GRADIENT_CLIP = 1.0

# CLASS WEIGHT MULTIPLIERS
HIGH_RISK_WEIGHT_MULTIPLIER = 8.0
SEVERITY_07_WEIGHT_MULTIPLIER = 2.0

# SAFETY THRESHOLDS
HIGH_RISK_PREDICTION_THRESHOLD = 0.20
HIGH_RISK_RECALL_TARGET = 0.99
EARLY_STOPPING_PATIENCE = 5

# PATHS
TRAIN_PATH = 'data/splits/train_combined.csv'
VAL_PATH = 'data/splits/val_combined.csv'
MODEL_SAVE_PATH = 'models/best_crisis_model_combined.pt'

# MAPPINGS
SEVERITY_TO_CLASS = {0.1: 0, 0.2: 1, 0.6: 2, 0.7: 3, 0.9: 4, 1.0: 5}
CLASS_TO_SEVERITY = {v: k for k, v in SEVERITY_TO_CLASS.items()}
HIGH_RISK_CLASSES = [4, 5]
CLASS_NAMES = ['self_harm', 'passive', 'active', 'method', 'intent', 'plan/attempt']


# ═══════════════════════════════════════════════════════════════
# DATASET CLASS
# ═══════════════════════════════════════════════════════════════

class CrisisDataset(Dataset):
    def __init__(self, csv_path, tokenizer, max_length=MAX_LENGTH):
        self.df = pd.read_csv(csv_path, encoding='utf-8')
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Convert severity to class
        self.df['class_label'] = self.df['severity_score'].map(SEVERITY_TO_CLASS)
        
    def __len__(self):
        return len(self.df)
    
    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        
        encoding = self.tokenizer(
            row['utterance'],
            padding='max_length',
            truncation=True,
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'labels': torch.tensor(row['class_label'], dtype=torch.long)
        }


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def compute_class_weights(dataset):
    labels = dataset.df['class_label'].values
    unique, counts = np.unique(labels, return_counts=True)
    total = len(labels)
    
    weights = total / (len(unique) * counts)
    
    for i, cls in enumerate(unique):
        severity = CLASS_TO_SEVERITY.get(cls, 0.5)
        if severity >= 0.9:
            weights[i] *= HIGH_RISK_WEIGHT_MULTIPLIER
        elif severity == 0.7:
            weights[i] *= SEVERITY_07_WEIGHT_MULTIPLIER
    
    weights = weights / weights.sum() * len(weights)
    
    print("\n Class Weights:")
    for i, (cls, w) in enumerate(zip(unique, weights)):
        print(f"   Class {cls} ({CLASS_NAMES[cls]}): {w:.2f}")
    
    return torch.tensor(weights, dtype=torch.float32)


def predict_with_safety_threshold(logits, threshold=HIGH_RISK_PREDICTION_THRESHOLD):
    probs = torch.softmax(logits, dim=1)
    predictions = torch.zeros(logits.size(0), dtype=torch.long, device=logits.device)
    
    for i in range(logits.size(0)):
        high_risk_probs = probs[i, 4:6]
        if high_risk_probs.max() > threshold:
            predictions[i] = 4 + high_risk_probs.argmax()
        else:
            predictions[i] = torch.argmax(probs[i])
    
    return predictions


class SafetyGateEarlyStopping:
    def __init__(self, patience=EARLY_STOPPING_PATIENCE, min_recall=HIGH_RISK_RECALL_TARGET):
        self.patience = patience
        self.min_recall = min_recall
        self.best_recall = 0.0
        self.counter = 0
        self.best_epoch = 0
        
    def __call__(self, epoch, recall, model):
        if recall > self.best_recall:
            self.best_recall = recall
            self.counter = 0
            self.best_epoch = epoch
            torch.save(model.state_dict(), MODEL_SAVE_PATH)
            print(f"    New best: High-risk recall = {recall:.4f}")
            
            if recall >= self.min_recall:
                print(f"\n    TARGET ACHIEVED: {recall:.4f} ≥ {self.min_recall}")
                return True
        else:
            self.counter += 1
            
        if self.counter >= self.patience:
            print(f"\n    Early stopping: No improvement for {self.patience} epochs")
            return True
            
        return False


def evaluate(model, dataloader, device, class_weights):
    model.eval()
    all_preds = []
    all_labels = []
    total_loss = 0.0
    
    criterion = nn.CrossEntropyLoss(weight=class_weights.to(device))
    
    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            preds = predict_with_safety_threshold(outputs.logits)
            
            loss = criterion(outputs.logits, labels)
            total_loss += loss.item()
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    
    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    
    accuracy = (all_preds == all_labels).mean()
    
    # High-risk recall (classes 4 and 5)
    high_risk_mask = np.isin(all_labels, HIGH_RISK_CLASSES)
    if high_risk_mask.sum() > 0:
        high_risk_correct = np.isin(all_preds[high_risk_mask], HIGH_RISK_CLASSES).sum()
        high_risk_recall = high_risk_correct / high_risk_mask.sum()
    else:
        high_risk_recall = 0.0
    
    return {
        'loss': total_loss / len(dataloader),
        'accuracy': accuracy,
        'high_risk_recall': high_risk_recall,
        'predictions': all_preds,
        'labels': all_labels
    }


# ═══════════════════════════════════════════════════════════════
# MAIN TRAINING
# ═══════════════════════════════════════════════════════════════

def train():
    print("="*70)
    print(" CRISIS DETECTION MODEL - COMBINED DATASET TRAINING")
    print("   Phase 1 + Phase 2 = 3,500 records | 6-class classification")
    print("="*70)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n Device: {device}")
    
    # Load tokenizer and datasets
    print("\n Loading data...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    train_dataset = CrisisDataset(TRAIN_PATH, tokenizer)
    val_dataset = CrisisDataset(VAL_PATH, tokenizer)
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE)
    
    print(f"   Train: {len(train_dataset)} | Val: {len(val_dataset)}")
    
    # Class weights
    class_weights = compute_class_weights(train_dataset)
    
    # Model
    print(f"\n🤖 Loading {MODEL_NAME}...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=NUM_LABELS
    ).to(device)
    
    # Optimizer and scheduler
    criterion = nn.CrossEntropyLoss(weight=class_weights.to(device))
    optimizer = AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    
    num_training_steps = len(train_loader) * NUM_EPOCHS
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=num_training_steps // 10,
        num_training_steps=num_training_steps
    )
    
    early_stopping = SafetyGateEarlyStopping()
    history = []
    
    print(f"\n Configuration:")
    print(f"   LR: {LEARNING_RATE} | Epochs: {NUM_EPOCHS}")
    print(f"   High-Risk Weight: {HIGH_RISK_WEIGHT_MULTIPLIER}x")
    print(f"   Safety Threshold: {HIGH_RISK_PREDICTION_THRESHOLD}")
    print("="*70)
    
    # Training loop
    Path('models').mkdir(exist_ok=True)
    
    for epoch in range(NUM_EPOCHS):
        model.train()
        train_loss = 0.0
        
        for batch in train_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            optimizer.zero_grad()
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            loss = criterion(outputs.logits, labels)
            loss.backward()
            
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
            scheduler.step()
            
            train_loss += loss.item()
        
        # Evaluate
        val_metrics = evaluate(model, val_loader, device, class_weights)
        
        print(f"\n Epoch {epoch+1}/{NUM_EPOCHS}")
        print(f"   Train Loss: {train_loss/len(train_loader):.4f}")
        print(f"   Val Loss: {val_metrics['loss']:.4f} | Acc: {val_metrics['accuracy']:.4f}")
        print(f"    HIGH-RISK RECALL: {val_metrics['high_risk_recall']:.4f}")
        
        history.append({
            'epoch': epoch + 1,
            'train_loss': train_loss / len(train_loader),
            'val_loss': val_metrics['loss'],
            'val_accuracy': val_metrics['accuracy'],
            'high_risk_recall': val_metrics['high_risk_recall']
        })
        
        if early_stopping(epoch + 1, val_metrics['high_risk_recall'], model):
            break
    
    # Final evaluation
    print("\n" + "="*70)
    print(" FINAL EVALUATION")
    print("="*70)
    
    model.load_state_dict(torch.load(MODEL_SAVE_PATH))
    final_metrics = evaluate(model, val_loader, device, class_weights)
    
    print(f"\n Final High-Risk Recall: {final_metrics['high_risk_recall']:.4f}")
    print(f" Final Accuracy: {final_metrics['accuracy']:.4f}")
    
    print("\n Classification Report:")
    print(classification_report(
        final_metrics['labels'], final_metrics['predictions'],
        target_names=CLASS_NAMES
    ))
    
    print("\n Confusion Matrix:")
    print(confusion_matrix(final_metrics['labels'], final_metrics['predictions']))
    
    # Save history
    with open('models/training_history_combined.json', 'w') as f:
        json.dump(history, f, indent=2)
    
    print(f"\n Model saved: {MODEL_SAVE_PATH}")
    print("="*70)
    
    return model, history

if __name__ == "__main__":
    model, history = train()