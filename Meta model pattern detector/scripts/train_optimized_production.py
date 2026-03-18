#!/usr/bin/env python3
"""
Meta-Model Pattern Detector - Memory-Optimized Production Training

Uses T5-base (220M parameters) instead of Flan-T5-large (783M) to avoid memory issues
while still providing much better performance than the T5-small demo (60M).

Expected training time: 2-4 hours (CPU), 15-30 min (GPU)
"""

import json
import os
import torch
import numpy as np
from pathlib import Path
from typing import Optional

try:
    from transformers import (
        T5Tokenizer,
        T5ForConditionalGeneration,
        DataCollatorForSeq2Seq,
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
        set_seed
    )
    from datasets import Dataset
    from peft import get_peft_model, LoraConfig, TaskType
except ImportError as e:
    print(f"[ERROR] Required library missing: {e}")
    print("Install with: pip install transformers datasets peft torch")
    exit(1)


def load_seq2seq_data(json_path):
    """Load Seq2Seq format data from JSON file."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data


def preprocess_function(examples, tokenizer, max_input_length=512, max_output_length=256):
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


def train_optimized_production(
    train_data_path: str = "Meta model pattern detector/data/seq2seq/train.json",
    val_data_path: str = "Meta model pattern detector/data/seq2seq/val.json",
    output_dir: str = "Meta model pattern detector/models/optimized_model",
    num_epochs: int = 3,  # Reduced from 5
    batch_size: int = 4,  # Reduced from 8
    gradient_accumulation_steps: int = 8,  # Increased to maintain effective batch size
    learning_rate: float = 2e-4,  # Slightly reduced
    lora_rank: int = 8,  # Reduced from 16
    max_input_length: int = 384,  # Reduced from 512
    max_output_length: int = 192,  # Reduced from 256
    seed: int = 42
):
    """Train memory-optimized production model."""

    set_seed(seed)

    print("=" * 70)
    print("MEMORY-OPTIMIZED PRODUCTION TRAINING")
    print("=" * 70)
    print("\nModel: T5-base (220M params) - 3.5x larger than demo, 3.5x smaller than flan-t5-large")
    print("Memory optimizations: Smaller batch, reduced sequence length, lower LoRA rank")

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\nDevice: {device}")

    # Use T5-base instead of Flan-T5-large (220M vs 783M parameters)
    model_name = "t5-base"
    print(f"\n1. Loading base model: {model_name}")
    tokenizer = T5Tokenizer.from_pretrained(model_name)
    model = T5ForConditionalGeneration.from_pretrained(model_name)
    print(f"   Model parameters: {model.num_parameters() / 1e6:.1f}M")

    # Apply LoRA with lower rank to save memory
    print(f"\n2. Applying LoRA (rank={lora_rank})")
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM,
        r=lora_rank,  # Reduced rank
        lora_alpha=16,  # Reduced from 32
        lora_dropout=0.05,
        target_modules=["q", "v"],
        bias="none"
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Load data
    print(f"\n3. Loading training data")
    train_data_raw = load_seq2seq_data(train_data_path)
    train_dataset = Dataset.from_dict({
        "input": [ex["input"] for ex in train_data_raw],
        "output": [ex["output"] for ex in train_data_raw]
    })
    print(f"   Loaded {len(train_dataset)} training examples")

    val_data_raw = load_seq2seq_data(val_data_path)
    val_dataset = Dataset.from_dict({
        "input": [ex["input"] for ex in val_data_raw],
        "output": [ex["output"] for ex in val_data_raw]
    })
    print(f"   Loaded {len(val_dataset)} validation examples")

    # Tokenize
    print(f"\n4. Tokenizing datasets (max_input={max_input_length}, max_output={max_output_length})")

    def preprocess_train(examples):
        return preprocess_function(examples, tokenizer, max_input_length, max_output_length)

    train_dataset = train_dataset.map(
        preprocess_train,
        batched=False,  # Disable batching for stability
        remove_columns=["input", "output"]
    )
    val_dataset = val_dataset.map(
        preprocess_train,
        batched=False,
        remove_columns=["input", "output"]
    )

    # Training arguments - optimized for memory
    print(f"\n5. Setting memory-optimized training arguments")
    os.makedirs(output_dir, exist_ok=True)

    training_args = Seq2SeqTrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=4,  # Small eval batch
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        warmup_steps=100,  # Use steps instead of ratio
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        predict_with_generate=True,
        generation_max_length=max_output_length,
        fp16=torch.cuda.is_available(),  # Use FP16 on GPU for memory savings
        dataloader_pin_memory=False,
        gradient_checkpointing=True,  # Enable gradient checkpointing
        seed=seed,
        logging_steps=25,
        save_total_limit=2
    )

    print(f"   Epochs: {num_epochs}")
    print(f"   Batch size: {batch_size} (gradient_accumulation={gradient_accumulation_steps})")
    print(f"   Effective batch size: {batch_size * gradient_accumulation_steps}")
    print(f"   Learning rate: {learning_rate}")
    print(f"   Gradient checkpointing: Enabled")

    # Data collator
    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    # Trainer
    print(f"\n6. Initializing Seq2SeqTrainer")
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator
    )

    # Train
    print(f"\n7. Starting optimized training...")
    print(f"{'=' * 70}")
    train_result = trainer.train()

    # Save final model
    print(f"\n8. Saving model")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    # Training summary
    print(f"\n{'=' * 70}")
    print(f"OPTIMIZED TRAINING COMPLETE")
    print(f"{'=' * 70}")
    print(f"Final training loss: {train_result.training_loss:.4f}")
    print(f"Output directory: {output_dir}")
    print(f"Model size: T5-base (220M parameters)")
    print(f"Trainable parameters: ~{lora_rank * 2 * 512 / 1e3:.1f}K LoRA params")

    # Save training results
    results_file = os.path.join(output_dir, "training_results.json")
    with open(results_file, 'w') as f:
        json.dump({
            "model": "t5-base (optimized production)",
            "epochs": num_epochs,
            "training_loss": train_result.training_loss,
            "is_production": True,
            "optimization": "Memory-optimized for CPU training",
            "parameters": "220M base + LoRA",
            "note": "Production model with memory optimizations"
        }, f, indent=2)
    print(f"Results saved: {results_file}")

    return True


if __name__ == "__main__":
    train_optimized_production()