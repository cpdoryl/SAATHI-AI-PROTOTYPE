#!/usr/bin/env python3
"""
Simple GPU-Optimized Training Script - Windows Compatible
No Unicode characters to avoid encoding issues
"""

import os
import torch
import json
from datetime import datetime
from pathlib import Path
from datasets import Dataset
from transformers import (
    T5ForConditionalGeneration,
    T5Tokenizer,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    DataCollatorForSeq2Seq
)
from peft import LoraConfig, get_peft_model, TaskType

def preprocess_function(examples, tokenizer, max_input_length=512, max_output_length=256):
    """Fixed preprocessing function"""
    input_text = examples["input"]
    target_text = examples["output"]

    model_inputs = tokenizer(
        input_text,
        max_length=max_input_length,
        truncation=True,
        padding="max_length"
    )

    labels = tokenizer(
        target_text,
        max_length=max_output_length,
        truncation=True,
        padding="max_length"
    )

    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

def main():
    print("META-MODEL PATTERN DETECTOR - GPU TRAINING")
    print("=" * 60)

    # GPU Detection
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"PyTorch Version: {torch.__version__}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    print(f"Training Device: {device}")

    if torch.cuda.is_available():
        print(f"GPU Name: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f}GB")
        # GPU Settings
        batch_size = 8
        grad_accum = 4
        learning_rate = 3e-4
        lora_rank = 16
        max_input = 512
        max_output = 256
        fp16 = True
        print("Configuration: GPU Optimized")
    else:
        print("Configuration: CPU Optimized")
        # CPU Settings
        batch_size = 4
        grad_accum = 8
        learning_rate = 2e-4
        lora_rank = 8
        max_input = 384
        max_output = 192
        fp16 = False

    print(f"Batch Size: {batch_size} x {grad_accum} = {batch_size * grad_accum} effective")
    print(f"LoRA Rank: {lora_rank}")
    print(f"Learning Rate: {learning_rate}")
    print()

    # Setup paths
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    model_dir = base_dir / "models" / f"gpu_model_{timestamp}"
    model_dir.mkdir(parents=True, exist_ok=True)

    print("LOADING DATA AND MODEL")
    print("=" * 40)

    # Load data
    print("Loading datasets...")

    # Load JSON data files
    with open(data_dir / "seq2seq" / "train.json", 'r') as f:
        train_data = json.load(f)
    with open(data_dir / "seq2seq" / "val.json", 'r') as f:
        val_data = json.load(f)

    # Create datasets
    train_dataset = Dataset.from_dict({
        "input": [item["input"] for item in train_data],
        "output": [item["output"] for item in train_data]
    })

    val_dataset = Dataset.from_dict({
        "input": [item["input"] for item in val_data],
        "output": [item["output"] for item in val_data]
    })

    print(f"Train: {len(train_dataset)}, Validation: {len(val_dataset)}")

    # Load model
    print("Loading T5-base model...")
    tokenizer = T5Tokenizer.from_pretrained("t5-base")
    model = T5ForConditionalGeneration.from_pretrained("t5-base")

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"Model Parameters: {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M")

    # Apply LoRA
    print(f"Applying LoRA (rank={lora_rank})...")
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM,
        r=lora_rank,
        lora_alpha=lora_rank * 2,
        lora_dropout=0.1,
        target_modules=["q", "v", "k", "o"]
    )
    model = get_peft_model(model, lora_config)

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Trainable: {trainable_params:,} ({trainable_params/total_params*100:.2f}%)")

    # Move to device
    model = model.to(device)
    print(f"Model moved to {device}")

    # Tokenize datasets
    print("Tokenizing datasets...")
    def preprocess_wrapper(examples):
        return preprocess_function(examples, tokenizer, max_input, max_output)

    train_dataset = train_dataset.map(preprocess_wrapper, batched=False)
    val_dataset = val_dataset.map(preprocess_wrapper, batched=False)
    print("Tokenization complete")

    print()
    print("STARTING TRAINING")
    print("=" * 30)

    # Training arguments - FIXED: No report_to parameter
    training_args = Seq2SeqTrainingArguments(
        output_dir=str(model_dir),
        learning_rate=learning_rate,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        num_train_epochs=3,
        warmup_steps=50,
        logging_steps=5,
        save_steps=25,
        eval_steps=25,
        eval_strategy="steps",
        save_strategy="steps",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        save_total_limit=3,
        gradient_checkpointing=True,
        fp16=fp16,
        dataloader_num_workers=0,  # Fixed: Python 3.14 multiprocessing issue
        remove_unused_columns=False,
        predict_with_generate=True,
        generation_max_length=max_output,
    )

    # Data collator
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True
    )

    # Trainer
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator
    )

    # Clear GPU cache
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # Train
    print(f"Training on {device.upper()}...")
    expected_time = "30-45 minutes" if torch.cuda.is_available() else "2-4 hours"
    print(f"Expected time: {expected_time}")
    print()

    train_result = trainer.train()

    print()
    print("TRAINING COMPLETED!")
    print("=" * 30)

    # Save
    print("Saving model...")
    trainer.save_model()
    tokenizer.save_pretrained(str(model_dir))

    # Results
    results = {
        "model": "t5-base-lora-gpu-optimized",
        "device": device,
        "final_loss": train_result.training_loss,
        "lora_rank": lora_rank,
        "trainable_params": trainable_params,
        "efficiency_percent": trainable_params/total_params*100,
        "timestamp": timestamp,
        "batch_size": batch_size,
        "gradient_accumulation": grad_accum,
        "effective_batch_size": batch_size * grad_accum
    }

    with open(model_dir / "training_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"Model saved to: {model_dir}")
    print(f"Final loss: {train_result.training_loss:.4f}")
    print(f"Efficiency: {results['efficiency_percent']:.2f}%")
    print("Training successful!")

    return str(model_dir), results

if __name__ == "__main__":
    main()