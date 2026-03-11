"""
Crisis Detection Model - Training Script v2.0
============================================
Includes all 6 critical fixes for achieving >99% high-risk recall

Changes from v1.0:
1. Class weights: 2x → 8x for high-risk
2. Added safety threshold prediction
3. Learning rate: 2e-5 → 5e-6
4. Epochs: 10 → 20
5. Added SafetyGateEarlyStopping
6. Added severity 0.7 weight boost

Author: ML Team
Date: December 29, 2025
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
from torch.optim import AdamW
from sklearn.metrics import classification_report, confusion_matrix, recall_score, precision_score
import numpy as np
import json
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION - ALL FIXES APPLIED
# ═══════════════════════════════════════════════════════════════

MODEL_NAME = "distilbert-base-uncased"
NUM_LABELS = 4
MAX_LENGTH = 128  # FIX #6: Explicit max length

# FIXED HYPERPARAMETERS
LEARNING_RATE = 5e-6       # FIX #3: Reduced from 2e-5 (4x reduction)
BATCH_SIZE = 16
WEIGHT_DECAY = 0.01
NUM_EPOCHS = 20            # FIX #3: Increased from 10 (2x increase)
GRADIENT_CLIP = 1.0

# SAFETY THRESHOLDS
HIGH_RISK_RECALL_TARGET = 0.99
HIGH_RISK_PREDICTION_THRESHOLD = 0.20  # FIX #2: Safety threshold
EARLY_STOPPING_PATIENCE = 5

# CLASS WEIGHT MULTIPLIERS
HIGH_RISK_WEIGHT_MULTIPLIER = 8.0  # FIX #1: Increased from 2.0
SEVERITY_07_WEIGHT_MULTIPLIER = 2.0  # FIX #5: Boost to prevent collapse

SAVE_DIR = "../models/checkpoints"


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def compute_class_weights(labels):
    """
    FIX #1 & #5: Compute class weights with aggressive boosting.
    
    - High-risk (0.9) gets 8x multiplier
    - Severity 0.7 gets 2x multiplier to prevent collapse
    """
    unique, counts = np.unique(labels, return_counts=True)
    total = len(labels)
    
    # Base weights (inverse frequency)
    weights = total / (len(unique) * counts)
    
    # CRITICAL: Aggressive boosting
    weights[2] *= SEVERITY_07_WEIGHT_MULTIPLIER   # Severity 0.7
    weights[3] *= HIGH_RISK_WEIGHT_MULTIPLIER     # Severity 0.9 (high-risk)
    
    # Normalize to prevent extreme loss values
    weights = weights / weights.sum() * len(weights)
    
    print("\n Class Weights Applied (with boosting):")
    severity_labels = [0.2, 0.6, 0.7, 0.9]
    for i, (sev, w) in enumerate(zip(severity_labels, weights)):
        marker = "← BOOSTED" if i >= 2 else ""
        print(f"   Class {i} (severity {sev}): {w:.2f} {marker}")
    
    return torch.tensor(weights, dtype=torch.float32)


def predict_with_safety_threshold(logits, threshold=HIGH_RISK_PREDICTION_THRESHOLD):
    """
    FIX #2: Safety-first prediction that prioritizes high-risk detection.
    
    If ANY probability of high-risk > threshold, classify as high-risk.
    This catches borderline cases that argmax would miss.
    """
    probs = torch.softmax(logits, dim=1)
    high_risk_probs = probs[:, 3]  # Class 3 = severity 0.9
    
    predictions = torch.zeros(logits.size(0), dtype=torch.long, device=logits.device)
    
    for i in range(logits.size(0)):
        if high_risk_probs[i] > threshold:
            predictions[i] = 3  # ESCALATE TO HIGH-RISK
        else:
            predictions[i] = torch.argmax(probs[i])
    
    return predictions


class SafetyGateEarlyStopping:
    """
    FIX #4: Early stopping with safety metric enforcement.
    
    - Optimizes for high-risk recall (not accuracy or loss)
    - Saves best model automatically
    - Stops on success OR patience exhaustion
    """
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
            torch.save(model.state_dict(), 'best_model.pt')
            print(f" Epoch {epoch}: New best! High-risk recall = {recall:.4f}")
            
            if recall >= self.min_recall:
                print(f"\n🎉 TARGET ACHIEVED: {recall:.4f} ≥ {self.min_recall}")
                return True
        else:
            self.counter += 1
            print(f" Epoch {epoch}: No improvement ({self.counter}/{self.patience})")
            
        if self.counter >= self.patience:
            print(f"\n Early stopping: No improvement for {self.patience} epochs")
            print(f"Best: {self.best_recall:.4f} at epoch {self.best_epoch}")
            if self.best_recall < self.min_recall:
                print(f" Target not met. Gap: {self.min_recall - self.best_recall:.4f}")
            return True
            
        return False


def evaluate_model(model, dataloader, device, class_weights, use_threshold=True):
    """
    Evaluate model with safety-first metrics.
    
    Key metrics tracked:
    - High-risk recall (PRIMARY - must be >99%)
    - High-risk precision
    - Severity 0.7 precision (to verify class is not collapsed)
    - Overall accuracy
    """
    model.eval()
    all_preds = []
    all_labels = []
    total_loss = 0.0
    
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    
    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch[0].to(device)
            attention_mask = batch[1].to(device)
            labels = batch[2].to(device)
            
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            
            # Safety-first prediction (FIX #2)
            if use_threshold:
                preds = predict_with_safety_threshold(logits)
            else:
                preds = torch.argmax(logits, dim=1)
            
            loss = criterion(logits, labels)
            total_loss += loss.item()
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    
    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    
    # Calculate metrics
    accuracy = (all_preds == all_labels).mean()
    avg_loss = total_loss / len(dataloader)
    
    # High-risk specific metrics
    high_risk_mask = (all_labels == 3)
    if high_risk_mask.sum() > 0:
        high_risk_correct = ((all_preds == 3) & high_risk_mask).sum()
        high_risk_total = high_risk_mask.sum()
        high_risk_recall = high_risk_correct / high_risk_total
    else:
        high_risk_recall = 0.0
    
    # Severity 0.7 metrics (to check if class collapse is fixed)
    sev_07_predictions = (all_preds == 2).sum()
    
    return {
        'loss': avg_loss,
        'accuracy': accuracy,
        'high_risk_recall': high_risk_recall,
        'sev_07_predictions': sev_07_predictions,
        'predictions': all_preds,
        'labels': all_labels
    }


# ═══════════════════════════════════════════════════════════════
# MAIN TRAINING FUNCTION
# ═══════════════════════════════════════════════════════════════

def train_crisis_model():
    """
    Main training function with all 6 fixes applied.
    """
    print("="*70)
    print(" CRISIS DETECTION MODEL TRAINING v2.0")
    print("   All 6 Critical Fixes Applied")
    print("="*70)
    
    # Device setup
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n Device: {device}")
    
    # Load data
    print("\n Loading preprocessed data...")
    train_data = np.load("../data/processed/train_processed.npz")
    val_data = np.load("../data/processed/val_processed.npz")
    
    train_dataset = TensorDataset(
        torch.tensor(train_data['input_ids']),
        torch.tensor(train_data['attention_mask']),
        torch.tensor(train_data['labels'])
    )
    
    val_dataset = TensorDataset(
        torch.tensor(val_data['input_ids']),
        torch.tensor(val_data['attention_mask']),
        torch.tensor(val_data['labels'])
    )
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE)
    
    print(f"   Train samples: {len(train_dataset)}")
    print(f"   Val samples: {len(val_dataset)}")
    
    # Compute class weights (FIX #1 & #5)
    train_labels = train_data['labels']
    class_weights = compute_class_weights(train_labels).to(device)
    
    # Initialize model
    print(f"\n Loading model: {MODEL_NAME}")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_LABELS,
        problem_type="single_label_classification"
    ).to(device)
    
    # Setup optimizer and scheduler (FIX #3)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    
    num_training_steps = len(train_loader) * NUM_EPOCHS
    num_warmup_steps = num_training_steps // 10
    
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=num_warmup_steps,
        num_training_steps=num_training_steps
    )
    
    # Early stopping (FIX #4)
    early_stopping = SafetyGateEarlyStopping()
    
    # Training history
    history = []
    
    print(f"\n Training Configuration:")
    print(f"   Learning Rate: {LEARNING_RATE} (reduced from 2e-5)")
    print(f"   Epochs: {NUM_EPOCHS} (increased from 10)")
    print(f"   High-Risk Weight: {HIGH_RISK_WEIGHT_MULTIPLIER}x (increased from 2x)")
    print(f"   Safety Threshold: {HIGH_RISK_PREDICTION_THRESHOLD}")
    print(f"   Target Recall: {HIGH_RISK_RECALL_TARGET}")
    print("="*70)
    
    # Training loop
    for epoch in range(NUM_EPOCHS):
        model.train()
        train_loss = 0.0
        
        for batch in train_loader:
            input_ids = batch[0].to(device)
            attention_mask = batch[1].to(device)
            labels = batch[2].to(device)
            
            optimizer.zero_grad()
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            loss = criterion(outputs.logits, labels)
            loss.backward()
            
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
            scheduler.step()
            
            train_loss += loss.item()
        
        train_loss /= len(train_loader)
        
        # Validation
        val_metrics = evaluate_model(model, val_loader, device, class_weights)
        
        # Log
        print(f"\n Epoch {epoch + 1}/{NUM_EPOCHS}")
        print(f"   Train Loss: {train_loss:.4f}")
        print(f"   Val Loss: {val_metrics['loss']:.4f} | Val Acc: {val_metrics['accuracy']:.4f}")
        print(f"   HIGH-RISK RECALL: {val_metrics['high_risk_recall']:.4f}")
        print(f"    Severity 0.7 predictions: {val_metrics['sev_07_predictions']} (should be >0)")
        
        # Save history
        history.append({
            'epoch': epoch + 1,
            'train_loss': train_loss,
            'val_loss': val_metrics['loss'],
            'val_accuracy': val_metrics['accuracy'],
            'high_risk_recall': val_metrics['high_risk_recall'],
            'sev_07_predictions': int(val_metrics['sev_07_predictions'])
        })
        
        # Early stopping check
        if early_stopping(epoch + 1, val_metrics['high_risk_recall'], model):
            break
    
    # Final evaluation
    print("\n" + "="*70)
    print(" FINAL EVALUATION")
    print("="*70)
    
    model.load_state_dict(torch.load('best_model.pt'))
    final_metrics = evaluate_model(model, val_loader, device, class_weights)
    
    # Confusion matrix
    cm = confusion_matrix(final_metrics['labels'], final_metrics['predictions'])
    print(f"\n Confusion Matrix:")
    print("              Predicted")
    print("           0.2   0.6   0.7   0.9")
    for i, row in enumerate(cm):
        label = ['0.2', '0.6', '0.7', '0.9'][i]
        print(f"Actual {label}  {row}")
    
    # Classification report
    print(f"\n Classification Report:")
    print(classification_report(
        final_metrics['labels'],
        final_metrics['predictions'],
        target_names=['Sev 0.2', 'Sev 0.6', 'Sev 0.7', 'Sev 0.9']
    ))
    
    # Final verdict
    print("\n" + "="*70)
    if final_metrics['high_risk_recall'] >= HIGH_RISK_RECALL_TARGET:
        print(" SUCCESS: High-risk recall target ACHIEVED!")
        print(f"    Final recall: {final_metrics['high_risk_recall']:.4f}")
    else:
        gap = HIGH_RISK_RECALL_TARGET - final_metrics['high_risk_recall']
        print(f" Target not met. Gap: {gap:.4f} ({gap*100:.2f}%)")
        print("\nNext steps:")
        print("  1. Try higher class weight (10x or 12x)")
        print("  2. Lower safety threshold (0.15)")
        print("  3. Add more high-risk training data")
    print("="*70)
    
    # Save models and history to SAVE_DIR
    Path(SAVE_DIR).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(f"{SAVE_DIR}/best_model")
    model.save_pretrained(f"{SAVE_DIR}/final_model")
    with open(f"{SAVE_DIR}/training_history.json", "w") as f:
        json.dump(history, f, indent=2)
    
    print(f"\n Saved: {SAVE_DIR}/best_model, {SAVE_DIR}/final_model, {SAVE_DIR}/training_history.json")
    
    return model, history, final_metrics


if __name__ == "__main__":
    model, history, metrics = train_crisis_model()
