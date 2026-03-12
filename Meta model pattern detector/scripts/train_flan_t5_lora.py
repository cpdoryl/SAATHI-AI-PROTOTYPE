#!/usr/bin/env python3
"""
Meta-Model Pattern Detector - Flan-T5 LoRA Fine-Tuning

Fine-tunes google/flan-t5-large with LoRA (rank=16) on meta-model pattern detection.
Expected training time: 45-60 min (GPU A100), 2-3 hours (GPU T4), 12-16 hours (CPU)
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
    inputs = [ex["input"] for ex in examples]
    targets = [ex["output"] for ex in examples]

    model_inputs = tokenizer(
        inputs,
        max_length=max_input_length,
        truncation=True,
        padding="max_length"
    )

    with tokenizer.as_target_tokenizer():
        labels = tokenizer(
            targets,
            max_length=max_output_length,
            truncation=True,
            padding="max_length"
        )

    model_inputs["labels"] = labels["input_ids"]
    return model_inputs


def train_flan_t5_lora(
    train_data_path: str = "Meta model pattern detector/data/seq2seq/train.json",
    val_data_path: str = "Meta model pattern detector/data/seq2seq/val.json",
    output_dir: str = "Meta model pattern detector/models/best_model",
    num_epochs: int = 5,
    batch_size: int = 8,
    gradient_accumulation_steps: int = 4,
    learning_rate: float = 3e-4,
    lora_rank: int = 16,
    max_input_length: int = 512,
    max_output_length: int = 256,
    seed: int = 42
):
    """Fine-tune Flan-T5 with LoRA."""

    set_seed(seed)

    print("=" * 70)
    print("FLAN-T5 LoRA FINE-TUNING FOR META-MODEL PATTERN DETECTION")
    print("=" * 70)

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\nDevice: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # Load model and tokenizer
    print("\n1. Loading base model: google/flan-t5-large")
    model_name = "google/flan-t5-large"
    tokenizer = T5Tokenizer.from_pretrained(model_name)
    model = T5ForConditionalGeneration.from_pretrained(model_name)
    print(f"   Model parameters: {model.num_parameters() / 1e6:.1f}M")

    # Apply LoRA
    print(f"\n2. Applying LoRA (rank={lora_rank})")
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM,
        r=lora_rank,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q", "v"],  # Attention query and value projections
        bias="none"
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Load data
    print(f"\n3. Loading training data")
    print(f"   Train: {train_data_path}")
    train_data_raw = load_seq2seq_data(train_data_path)
    train_dataset = Dataset.from_dict({
        "input": [ex["input"] for ex in train_data_raw],
        "output": [ex["output"] for ex in train_data_raw]
    })
    print(f"   Loaded {len(train_dataset)} training examples")

    print(f"   Val: {val_data_path}")
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
        batched=True,
        remove_columns=["input", "output"],
        batch_size=64
    )
    val_dataset = val_dataset.map(
        preprocess_train,
        batched=True,
        remove_columns=["input", "output"],
        batch_size=64
    )

    # Training arguments
    print(f"\n5. Setting training arguments")
    os.makedirs(output_dir, exist_ok=True)

    training_args = Seq2SeqTrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=16,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        warmup_ratio=0.1,
        evaluation_strategy="epoch",
        save_strategy="best",
        load_best_model_at_end=True,
        predict_with_generate=True,
        generation_max_length=max_output_length,
        fp16=torch.cuda.is_available(),
        seed=seed,
        logging_steps=50,
        save_total_limit=3,
        dataloader_pin_memory=True
    )

    print(f"   Epochs: {num_epochs}")
    print(f"   Batch size: {batch_size} (gradient_accumulation={gradient_accumulation_steps})")
    print(f"   Learning rate: {learning_rate}")
    print(f"   Effective batch size: {batch_size * gradient_accumulation_steps}")

    # Data collator
    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    # Trainer
    print(f"\n6. Initializing Seq2SeqTrainer")
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer
    )

    # Train
    print(f"\n7. Starting training...")
    print(f"{'=' * 70}")
    train_result = trainer.train()

    # Save final model
    print(f"\n8. Saving model")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    # Training summary
    print(f"\n{'=' * 70}")
    print(f"TRAINING COMPLETE")
    print(f"{'=' * 70}")
    print(f"Final training loss: {train_result.training_loss:.4f}")
    print(f"Output directory: {output_dir}")

    # Save training results
    results_file = os.path.join(output_dir, "training_results.json")
    with open(results_file, 'w') as f:
        json.dump(train_result.metrics, f, indent=2)
    print(f"Results saved: {results_file}")

    return True


if __name__ == "__main__":
    train_flan_t5_lora()
