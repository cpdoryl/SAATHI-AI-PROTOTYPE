"""
SAATHI AI -- Emotion Detection Classifier Training
===================================================
2-phase DistilBERT fine-tuning for 8-class emotion classification.

Phase 1: Freeze DistilBERT encoder, train classifier head only (2 epochs, lr=1e-3)
Phase 2: Unfreeze all layers, full fine-tuning (5 epochs, lr=2e-5, weighted loss)

Early stopping: monitors val macro_f1 (patience=3)
Output: models/best_model/ (HuggingFace format)

Usage:
    python scripts/train_emotion_distilbert.py
"""

import csv
import json
import logging
import os
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.join(SCRIPT_DIR, "..")

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

RUN_TS  = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_PATH = os.path.join(LOG_DIR, f"training_{RUN_TS}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# Force stdout to handle ascii safely on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODEL_NAME   = "distilbert-base-uncased"
NUM_LABELS   = 8
MAX_LENGTH   = 128
BATCH_SIZE   = 16      # CPU-friendly
P1_EPOCHS    = 2       # Phase 1: head only
P2_EPOCHS    = 5       # Phase 2: full fine-tune (early stopping governs)
P1_LR        = 1e-3
P2_LR        = 2e-5
WEIGHT_DECAY = 0.01
WARMUP_FRAC  = 0.10
GRAD_CLIP    = 1.0
PATIENCE     = 3
SEED         = 42

SPLITS_DIR  = os.path.join(BASE_DIR, "data", "splits")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
MODEL_DIR   = os.path.join(BASE_DIR, "models", "best_model")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

CLASSES = ["anxiety", "sadness", "anger", "fear",
           "hopelessness", "guilt", "shame", "neutral"]
LABEL2ID = {c: i for i, c in enumerate(CLASSES)}
ID2LABEL = {i: c for i, c in enumerate(CLASSES)}

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
import random
import numpy as np

random.seed(SEED)
np.random.seed(SEED)


def set_seed():
    try:
        import torch
        torch.manual_seed(SEED)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_split(name):
    path = os.path.join(SPLITS_DIR, f"{name}.csv")
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "text":  r["utterance"],
                "label": LABEL2ID[r["primary_emotion"]],
            })
    return rows


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class EmotionDataset:
    def __init__(self, rows, tokenizer):
        self.rows      = rows
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        import torch
        row    = self.rows[idx]
        enc    = self.tokenizer(
            row["text"],
            max_length=MAX_LENGTH,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        )
        return {
            "input_ids":      enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels":         torch.tensor(row["label"], dtype=torch.long),
        }


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(all_labels, all_preds):
    from sklearn.metrics import (accuracy_score, f1_score,
                                  classification_report)
    acc      = accuracy_score(all_labels, all_preds)
    macro_f1 = f1_score(all_labels, all_preds, average="macro",
                        zero_division=0)
    wt_f1    = f1_score(all_labels, all_preds, average="weighted",
                        zero_division=0)
    per_class_f1 = f1_score(all_labels, all_preds, average=None,
                             labels=list(range(NUM_LABELS)),
                             zero_division=0)
    report = classification_report(
        all_labels, all_preds,
        target_names=CLASSES, zero_division=0,
    )
    return {
        "accuracy":      round(acc, 4),
        "macro_f1":      round(macro_f1, 4),
        "weighted_f1":   round(wt_f1, 4),
        "per_class_f1":  {CLASSES[i]: round(float(v), 4)
                          for i, v in enumerate(per_class_f1)},
        "report":        report,
    }


# ---------------------------------------------------------------------------
# Train / eval loops
# ---------------------------------------------------------------------------

def run_epoch(model, loader, optimizer, scheduler, loss_fn,
              device, train=True):
    import torch
    model.train() if train else model.eval()
    total_loss  = 0.0
    all_labels  = []
    all_preds   = []
    n_batches   = 0

    ctx = torch.no_grad() if not train else torch.enable_grad()
    with ctx:
        for batch in loader:
            input_ids  = batch["input_ids"].to(device)
            attn_mask  = batch["attention_mask"].to(device)
            labels     = batch["labels"].to(device)

            outputs    = model(input_ids=input_ids,
                               attention_mask=attn_mask)
            logits     = outputs.logits
            loss       = loss_fn(logits, labels)

            if train:
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(),
                                               GRAD_CLIP)
                optimizer.step()
                if scheduler is not None:
                    scheduler.step()

            total_loss += loss.item()
            preds       = logits.argmax(dim=-1).cpu().numpy()
            all_labels.extend(labels.cpu().numpy().tolist())
            all_preds.extend(preds.tolist())
            n_batches  += 1

    avg_loss = total_loss / max(n_batches, 1)
    metrics  = compute_metrics(all_labels, all_preds)
    metrics["loss"] = round(avg_loss, 4)
    return metrics


# ---------------------------------------------------------------------------
# Main training entry point
# ---------------------------------------------------------------------------

def main():
    set_seed()
    log.info("=" * 60)
    log.info("SAATHI AI -- Emotion Detection Classifier Training")
    log.info("=" * 60)
    log.info(f"Model      : {MODEL_NAME}")
    log.info(f"Classes    : {CLASSES}")
    log.info(f"P1 epochs  : {P1_EPOCHS}  lr={P1_LR}")
    log.info(f"P2 epochs  : {P2_EPOCHS}  lr={P2_LR}")
    log.info(f"Batch size : {BATCH_SIZE} | Max length: {MAX_LENGTH}")
    log.info(f"Early stop : patience={PATIENCE} on val macro_f1")
    log.info(f"Seed       : {SEED}")
    log.info(f"Log        : {LOG_PATH}")

    try:
        import torch
        from torch.utils.data import DataLoader
        from transformers import (AutoModelForSequenceClassification,
                                   AutoTokenizer,
                                   get_linear_schedule_with_warmup)
        from sklearn.utils.class_weight import compute_class_weight
        from sklearn.metrics import confusion_matrix
    except ImportError as e:
        log.error(f"Missing dependency: {e}")
        log.error("Run: pip install torch transformers scikit-learn")
        sys.exit(1)

    device = torch.device("cpu")
    log.info(f"Device     : {device}")

    # ---- Load data ----------------------------------------------------------
    log.info("\nLoading data splits...")
    train_rows = load_split("train")
    val_rows   = load_split("val")
    test_rows  = load_split("test")
    log.info(f"  Train: {len(train_rows)} | Val: {len(val_rows)} "
             f"| Test: {len(test_rows)}")

    # ---- Tokenizer ----------------------------------------------------------
    log.info(f"\nLoading tokenizer: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    train_ds = EmotionDataset(train_rows, tokenizer)
    val_ds   = EmotionDataset(val_rows,   tokenizer)
    test_ds  = EmotionDataset(test_rows,  tokenizer)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE,
                              shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE,
                              shuffle=False)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE,
                              shuffle=False)

    # ---- Class weights -------------------------------------------------------
    train_labels = [r["label"] for r in train_rows]
    class_weights = compute_class_weight(
        class_weight="balanced",
        classes=np.array(list(range(NUM_LABELS))),
        y=np.array(train_labels),
    )
    cw_tensor = torch.FloatTensor(class_weights).to(device)
    log.info("\nClass weights (for weighted loss):")
    for i, cls in enumerate(CLASSES):
        log.info(f"  {cls:<22}: {class_weights[i]:.4f}")

    # ---- Model --------------------------------------------------------------
    log.info(f"\nLoading model: {MODEL_NAME} (num_labels={NUM_LABELS})")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )
    model.to(device)
    total_params = sum(p.numel() for p in model.parameters())
    log.info(f"Total parameters: {total_params:,}")

    loss_fn_weighted = torch.nn.CrossEntropyLoss(weight=cw_tensor)
    loss_fn_plain    = torch.nn.CrossEntropyLoss()

    training_history = []
    best_macro_f1    = 0.0
    patience_counter = 0
    training_start   = time.time()

    # =========================================================================
    # PHASE 1: Freeze encoder, train classifier head only
    # =========================================================================
    log.info("\n" + "=" * 60)
    log.info("PHASE 1: Train classifier head only (encoder frozen)")
    log.info("=" * 60)

    for param in model.distilbert.parameters():
        param.requires_grad = False
    trainable_p1 = sum(p.numel() for p in model.parameters()
                       if p.requires_grad)
    log.info(f"Trainable params (Phase 1): {trainable_p1:,}")

    optimizer_p1 = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=P1_LR, weight_decay=WEIGHT_DECAY,
    )

    for epoch in range(1, P1_EPOCHS + 1):
        ep_start = time.time()
        tr = run_epoch(model, train_loader, optimizer_p1, None,
                       loss_fn_plain, device, train=True)
        va = run_epoch(model, val_loader, None, None,
                       loss_fn_plain, device, train=False)
        ep_sec = time.time() - ep_start

        log.info(
            f"P1 Epoch {epoch}/{P1_EPOCHS} | "
            f"TrLoss={tr['loss']:.4f} TrAcc={tr['accuracy']:.4f} "
            f"TrF1={tr['macro_f1']:.4f} | "
            f"ValLoss={va['loss']:.4f} ValAcc={va['accuracy']:.4f} "
            f"ValF1={va['macro_f1']:.4f} | "
            f"{ep_sec:.0f}s"
        )
        training_history.append({
            "phase": 1, "epoch": epoch,
            "train": {k: v for k, v in tr.items() if k != "report"},
            "val":   {k: v for k, v in va.items() if k != "report"},
            "epoch_seconds": round(ep_sec, 1),
        })

    # =========================================================================
    # PHASE 2: Unfreeze all layers, full fine-tuning
    # =========================================================================
    log.info("\n" + "=" * 60)
    log.info("PHASE 2: Full fine-tuning (all layers unfrozen)")
    log.info("=" * 60)

    for param in model.parameters():
        param.requires_grad = True
    trainable_p2 = sum(p.numel() for p in model.parameters()
                       if p.requires_grad)
    log.info(f"Trainable params (Phase 2): {trainable_p2:,}")

    optimizer_p2 = torch.optim.AdamW(
        model.parameters(), lr=P2_LR, weight_decay=WEIGHT_DECAY,
    )

    total_steps  = len(train_loader) * P2_EPOCHS
    warmup_steps = int(total_steps * WARMUP_FRAC)
    scheduler_p2 = get_linear_schedule_with_warmup(
        optimizer_p2,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )
    log.info(f"Total P2 steps: {total_steps} | "
             f"Warmup steps: {warmup_steps}")

    best_epoch       = 0
    best_macro_f1    = 0.0
    patience_counter = 0

    for epoch in range(1, P2_EPOCHS + 1):
        ep_start = time.time()
        tr = run_epoch(model, train_loader, optimizer_p2, scheduler_p2,
                       loss_fn_weighted, device, train=True)
        va = run_epoch(model, val_loader, None, None,
                       loss_fn_weighted, device, train=False)
        ep_sec = time.time() - ep_start

        improved = va["macro_f1"] > best_macro_f1
        if improved:
            best_macro_f1    = va["macro_f1"]
            best_epoch       = epoch
            patience_counter = 0
            model.save_pretrained(MODEL_DIR)
            tokenizer.save_pretrained(MODEL_DIR)
            checkpoint_meta = {
                "epoch":           epoch,
                "val_macro_f1":    va["macro_f1"],
                "val_accuracy":    va["accuracy"],
                "val_weighted_f1": va["weighted_f1"],
                "saved_at":        datetime.now().isoformat(),
            }
            with open(os.path.join(MODEL_DIR, "checkpoint_meta.json"),
                      "w") as f:
                json.dump(checkpoint_meta, f, indent=2)
            flag = " -- NEW BEST -- checkpoint saved"
        else:
            patience_counter += 1
            flag = (f" -- No improve ({patience_counter}/{PATIENCE})")

        log.info(
            f"P2 Epoch {epoch}/{P2_EPOCHS} | "
            f"TrLoss={tr['loss']:.4f} TrAcc={tr['accuracy']:.4f} "
            f"TrF1={tr['macro_f1']:.4f} | "
            f"ValLoss={va['loss']:.4f} ValAcc={va['accuracy']:.4f} "
            f"ValF1={va['macro_f1']:.4f} | "
            f"{ep_sec:.0f}s{flag}"
        )
        training_history.append({
            "phase": 2, "epoch": epoch,
            "train": {k: v for k, v in tr.items() if k != "report"},
            "val":   {k: v for k, v in va.items() if k != "report"},
            "epoch_seconds": round(ep_sec, 1),
        })

        if patience_counter >= PATIENCE:
            log.info(f"Early stopping triggered at P2 epoch {epoch} "
                     f"(patience={PATIENCE})")
            break

    # =========================================================================
    # Save training history
    # =========================================================================
    hist_path = os.path.join(RESULTS_DIR, "training_history.json")
    with open(hist_path, "w") as f:
        json.dump(training_history, f, indent=2)
    log.info(f"\nTraining history saved: {hist_path}")

    # =========================================================================
    # Test evaluation (reload best checkpoint)
    # =========================================================================
    log.info("\n" + "=" * 60)
    log.info(f"TEST EVALUATION (best checkpoint: P2 Epoch {best_epoch})")
    log.info("=" * 60)

    log.info("Reloading best checkpoint from disk...")
    model_best = AutoModelForSequenceClassification.from_pretrained(
        MODEL_DIR)
    model_best.to(device)
    model_best.eval()

    te = run_epoch(model_best, test_loader, None, None,
                   loss_fn_weighted, device, train=False)

    log.info(f"\nTest Accuracy    : {te['accuracy']:.4f} "
             f"({te['accuracy']*100:.2f}%)")
    log.info(f"Test Weighted F1 : {te['weighted_f1']:.4f}")
    log.info(f"Test Macro F1    : {te['macro_f1']:.4f}")
    log.info("\nPer-class F1 scores (test set):")
    for cls in CLASSES:
        f1v = te["per_class_f1"][cls]
        flag = " << CRITICAL" if cls == "hopelessness" and f1v < 0.80 else ""
        log.info(f"  {cls:<22}: {f1v:.4f}{flag}")
    log.info("\nFull Classification Report:")
    log.info(te["report"])

    # ---- Qualification gates ------------------------------------------------
    acc_pass   = te["accuracy"]    >= 0.80
    macro_pass = te["macro_f1"]    >= 0.75
    hope_pass  = te["per_class_f1"]["hopelessness"] >= 0.70
    approved   = acc_pass and macro_pass and hope_pass

    log.info("QUALIFICATION GATES:")
    log.info(f"  Accuracy >= 80%       : {'PASS' if acc_pass else 'FAIL'} "
             f"({te['accuracy']*100:.2f}%)")
    log.info(f"  Macro F1 >= 0.75      : {'PASS' if macro_pass else 'FAIL'} "
             f"({te['macro_f1']:.4f})")
    log.info(f"  Hopelessness F1 >= 0.70: {'PASS' if hope_pass else 'FAIL'} "
             f"({te['per_class_f1']['hopelessness']:.4f})")
    log.info(f"  OVERALL APPROVED      : {'YES' if approved else 'NO'}")

    # ---- Save test results ---------------------------------------------------
    total_wall = time.time() - training_start
    eval_json = {
        "model":       MODEL_NAME,
        "phase":       "Emotion Detection 8-Class",
        "trained_at":  datetime.now().isoformat(),
        "training_seconds": round(total_wall, 0),
        "best_epoch":  best_epoch,
        "test_metrics": {
            "accuracy":     te["accuracy"],
            "weighted_f1":  te["weighted_f1"],
            "macro_f1":     te["macro_f1"],
            "per_class_f1": te["per_class_f1"],
            "loss":         te["loss"],
        },
        "qualification": {
            "accuracy_pass":     acc_pass,
            "macro_f1_pass":     macro_pass,
            "hopelessness_pass": hope_pass,
            "overall_approved":  approved,
        },
        "config": {
            "num_labels":     NUM_LABELS,
            "max_length":     MAX_LENGTH,
            "batch_size":     BATCH_SIZE,
            "p1_epochs":      P1_EPOCHS,
            "p2_epochs":      P2_EPOCHS,
            "p1_lr":          P1_LR,
            "p2_lr":          P2_LR,
            "early_stopping_patience": PATIENCE,
            "random_seed":    SEED,
        },
    }

    json_path = os.path.join(RESULTS_DIR, "test_evaluation.json")
    with open(json_path, "w") as f:
        json.dump(eval_json, f, indent=2)

    # Build confusion matrix
    try:
        import torch
        from torch.utils.data import DataLoader as _DL
        all_labels_test, all_preds_test = [], []
        model_best.eval()
        with torch.no_grad():
            for batch in test_loader:
                out = model_best(
                    input_ids=batch["input_ids"].to(device),
                    attention_mask=batch["attention_mask"].to(device),
                )
                all_labels_test.extend(batch["labels"].numpy().tolist())
                all_preds_test.extend(
                    out.logits.argmax(dim=-1).cpu().numpy().tolist()
                )
        cm = confusion_matrix(all_labels_test, all_preds_test,
                              labels=list(range(NUM_LABELS)))
        eval_json["test_metrics"]["confusion_matrix"] = cm.tolist()
        with open(json_path, "w") as f:
            json.dump(eval_json, f, indent=2)
    except Exception as ex:
        log.warning(f"Could not compute confusion matrix: {ex}")

    # Human-readable summary
    txt_path = os.path.join(RESULTS_DIR, "test_evaluation.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("SAATHI AI -- EMOTION DETECTION MODEL -- TEST EVALUATION\n")
        f.write("=" * 56 + "\n\n")
        f.write(f"Model     : {MODEL_NAME} fine-tuned (8-class)\n")
        f.write(f"Phase     : Emotion Detection\n")
        f.write(f"Test set  : {len(test_rows)} samples\n")
        f.write(f"Trained   : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Duration  : {total_wall/3600:.2f} hours\n\n")
        f.write("RESULTS\n")
        f.write("-" * 30 + "\n")
        f.write(f"Accuracy        : {te['accuracy']:.4f} "
                f"({te['accuracy']*100:.2f}%)\n")
        f.write(f"Weighted F1     : {te['weighted_f1']:.4f}\n")
        f.write(f"Macro F1        : {te['macro_f1']:.4f}\n\n")
        f.write("Per-class F1:\n")
        for cls in CLASSES:
            f.write(f"  {cls:<22}: {te['per_class_f1'][cls]:.4f}\n")
        f.write("\nQUALIFICATION GATES\n")
        f.write("-" * 30 + "\n")
        f.write(f"Accuracy >= 80%        : {'PASS' if acc_pass else 'FAIL'}\n")
        f.write(f"Macro F1 >= 0.75       : {'PASS' if macro_pass else 'FAIL'}\n")
        f.write(f"Hopelessness F1 >= 0.70: {'PASS' if hope_pass else 'FAIL'}\n")
        f.write(f"APPROVED               : {'YES' if approved else 'NO'}\n\n")
        f.write("Model saved: models/best_model/\n")

    log.info(f"\nResults saved: {json_path}")
    log.info(f"Summary saved: {txt_path}")
    log.info(f"Best model  : {MODEL_DIR}")
    log.info(f"Total time  : {total_wall/60:.1f} minutes")
    log.info("\nTraining complete.")


if __name__ == "__main__":
    main()
