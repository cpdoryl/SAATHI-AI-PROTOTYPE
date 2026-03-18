#!/usr/bin/env python3
"""
Meta-Model Pattern Detector - LIGHTWEIGHT DEMO Training

This script trains a lightweight version for TESTING THE PIPELINE ONLY.
Uses distilbert-base-uncased as encoder (20x smaller than Flan-T5-large)
for rapid prototyping and pipeline validation.

Expected time: 5-10 minutes CPU, 30 seconds GPU
Production: Use full train_flan_t5_lora.py with Flan-T5-large

Usage:
    python train_lightweight_demo.py
"""

import json
import os
import torch
import numpy as np
from pathlib import Path
from typing import Optional

try:
    from transformers import (
        AutoTokenizer,
        AutoModelForSeq2SeqLM,
        DataCollatorForSeq2Seq,
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
        set_seed
    )
    from datasets import Dataset
except ImportError as e:
    print(f"[ERROR] Required library missing: {e}")
    print("Install with: pip install transformers datasets torch")
    exit(1)


def load_seq2seq_data(json_path, max_examples: int = None):
    """Load Seq2Seq format data from JSON file."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    if max_examples:
        data = data[:max_examples]
    return data


def preprocess_function(examples, tokenizer, max_input_length=256, max_output_length=128):
    """Tokenize inputs and targets."""
    # Simple single example processing (batched=False)
    input_text = examples["input"]
    target_text = examples["output"]

    model_inputs = tokenizer(
        input_text,
        max_length=max_input_length,
        truncation=True,
        padding="max_length"
    )

    # T5 tokenizer doesn't need as_target_tokenizer context
    labels = tokenizer(
        target_text,
        max_length=max_output_length,
        truncation=True,
        padding="max_length"
    )

    model_inputs["labels"] = labels["input_ids"]
    return model_inputs


def train_lightweight_demo(
    train_data_path: str = "Meta model pattern detector/data/seq2seq/train.json",
    val_data_path: str = "Meta model pattern detector/data/seq2seq/val.json",
    output_dir: str = "Meta model pattern detector/models/demo_model",
    num_epochs: int = 1,  # Just 1 epoch for demo
    batch_size: int = 4,  # Smaller batch
    max_train_examples: int = 200,  # Subset for speed
    max_val_examples: int = 50,
    seed: int = 42
):
    """Train lightweight demo model for pipeline validation."""

    set_seed(seed)

    print("=" * 70)
    print("LIGHTWEIGHT DEMO TRAINING - FOR PIPELINE VALIDATION ONLY")
    print("=" * 70)
    print("\nNOTE: This uses a small model for rapid prototyping.")
    print("Production uses full train_flan_t5_lora.py with Flan-T5-large")

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\nDevice: {device}")

    # Use smaller model for demo
    model_name = "t5-small"  # 60M params vs 770M for Flan-T5-large
    print(f"\n1. Loading base model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    print(f"   Model parameters: {model.num_parameters() / 1e6:.1f}M (demo size)")

    # Load data
    print(f"\n2. Loading training data (subset for demo)")
    train_data_raw = load_seq2seq_data(train_data_path, max_train_examples)
    train_dataset = Dataset.from_dict({
        "input": [ex["input"] for ex in train_data_raw],
        "output": [ex["output"] for ex in train_data_raw]
    })
    print(f"   Using {len(train_dataset)} training examples (full: 2100)")

    val_data_raw = load_seq2seq_data(val_data_path, max_val_examples)
    val_dataset = Dataset.from_dict({
        "input": [ex["input"] for ex in val_data_raw],
        "output": [ex["output"] for ex in val_data_raw]
    })
    print(f"   Using {len(val_dataset)} validation examples (full: 449)")

    # Tokenize
    print(f"\n3. Tokenizing datasets")

    def preprocess_train(examples):
        return preprocess_function(examples, tokenizer, 256, 128)

    train_dataset = train_dataset.map(
        preprocess_train,
        batched=False,  # Disable batching to avoid complexity
        remove_columns=["input", "output"]
    )
    val_dataset = val_dataset.map(
        preprocess_train,
        batched=False,  # Disable batching to avoid complexity
        remove_columns=["input", "output"]
    )

    # Training arguments
    print(f"\n4. Setting training arguments")
    os.makedirs(output_dir, exist_ok=True)

    training_args = Seq2SeqTrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=8,
        eval_strategy="epoch",  # Changed from evaluation_strategy
        save_strategy="epoch",  # Changed from "best" which may not be supported
        load_best_model_at_end=True,
        predict_with_generate=True,
        generation_max_length=128,
        fp16=torch.cuda.is_available(),
        seed=seed,
        logging_steps=5,
        save_total_limit=1,
        dataloader_pin_memory=False
    )

    print(f"   Epochs: {num_epochs}")
    print(f"   Batch size: {batch_size}")
    print(f"   Learning rate: 5e-5 (default)")

    # Data collator
    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    # Trainer
    print(f"\n5. Initializing Seq2SeqTrainer")
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator
    )

    # Train
    print(f"\n6. Starting 1-epoch demo training...")
    print(f"{'=' * 70}")
    train_result = trainer.train()

    # Save final model
    print(f"\n7. Saving model")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    # Training summary
    print(f"\n{'=' * 70}")
    print(f"DEMO TRAINING COMPLETE")
    print(f"{'=' * 70}")
    print(f"Final training loss: {train_result.training_loss:.4f}")
    print(f"Output directory: {output_dir}")
    print(f"\nIMPORTANT: This is a small demo model (T5-small, 60M params)")
    print(f"For production, run: train_flan_t5_lora.py (Flan-T5-large, 770M params)")

    # Save training results
    results_file = os.path.join(output_dir, "training_results.json")
    with open(results_file, 'w') as f:
        json.dump({
            "model": "t5-small (demo)",
            "epochs": num_epochs,
            "training_loss": train_result.training_loss,
            "is_production": False,
            "note": "Small demo model for pipeline testing only"
        }, f, indent=2)
    print(f"Results saved: {results_file}")

    return True


if __name__ == "__main__":
    train_lightweight_demo()
