#!/usr/bin/env python3
"""
GPU-Optimized Training Script for Meta-Model Pattern Detector
RTX 5060 8GB VRAM Optimized | Automatic CPU/GPU Detection | Production Ready

This script automatically detects and utilizes GPU acceleration when available,
with intelligent memory management for RTX 5060 8GB VRAM constraints.
"""

import os
import sys
import torch
import json
from datetime import datetime
from pathlib import Path
from datasets import Dataset, load_from_disk
from transformers import (
    T5ForConditionalGeneration,
    T5Tokenizer,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    DataCollatorForSeq2Seq
)
from peft import LoraConfig, get_peft_model, TaskType
import gc

def setup_gpu_environment():
    """Configure optimal GPU settings for RTX 5060"""
    print("GPU-OPTIMIZED TRAINING SETUP")
    print("=" * 60)

    # GPU Detection
    gpu_available = torch.cuda.is_available()
    if gpu_available:
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"[OK] GPU Detected: {gpu_name}")
        print(f"[INFO] VRAM: {gpu_memory:.1f}GB")

        # RTX 5060 Optimizations
        if "5060" in gpu_name:
            print("[OPT] RTX 5060 Optimizations Enabled!")
            # Clear GPU cache
            torch.cuda.empty_cache()
            # Enable memory efficient attention if available
            if hasattr(torch.nn.functional, 'scaled_dot_product_attention'):
                torch.backends.cuda.enable_flash_sdp(True)

        device = "cuda"
    else:
        print("⚠️  GPU not available, falling back to CPU")
        print("💡 For GPU support, install: pip install torch --index-url https://download.pytorch.org/whl/cu121")
        device = "cpu"

    print(f"🎯 Training Device: {device}")
    print()
    return device, gpu_available

def get_gpu_optimized_config(device, gpu_available):
    """Get training configuration optimized for RTX 5060 8GB"""
    if gpu_available and "cuda" in device:
        # RTX 5060 8GB VRAM Optimized Settings
        config = {
            "model_name": "t5-base",  # 220M params, fits in 8GB with LoRA
            "max_input_length": 512,   # Increased for GPU
            "max_output_length": 256,  # Increased for GPU
            "batch_size": 8,           # Larger batch for GPU
            "gradient_accumulation_steps": 4,  # 8*4=32 effective batch
            "learning_rate": 3e-4,     # Slightly higher for GPU
            "num_epochs": 3,
            "lora_rank": 16,           # Higher rank for better quality
            "lora_alpha": 32,
            "lora_dropout": 0.1,
            "gradient_checkpointing": True,
            "fp16": True,              # Memory optimization for GPU
            "dataloader_num_workers": 4,
            "save_steps": 25,          # More frequent saves
            "eval_steps": 25,
            "warmup_steps": 50,
            "logging_steps": 5,
        }
        print("⚡ GPU Configuration: High Performance")
    else:
        # CPU Fallback Configuration
        config = {
            "model_name": "t5-base",
            "max_input_length": 384,
            "max_output_length": 192,
            "batch_size": 4,
            "gradient_accumulation_steps": 8,
            "learning_rate": 2e-4,
            "num_epochs": 3,
            "lora_rank": 8,
            "lora_alpha": 16,
            "lora_dropout": 0.1,
            "gradient_checkpointing": True,
            "fp16": False,
            "dataloader_num_workers": 2,
            "save_steps": 50,
            "eval_steps": 50,
            "warmup_steps": 30,
            "logging_steps": 10,
        }
        print("🔄 CPU Configuration: Memory Optimized")

    # Print configuration
    effective_batch = config["batch_size"] * config["gradient_accumulation_steps"]
    print(f"📦 Model: {config['model_name']} | LoRA Rank: {config['lora_rank']}")
    print(f"📊 Batch: {config['batch_size']} (×{config['gradient_accumulation_steps']} = {effective_batch} effective)")
    print(f"🎯 Sequences: {config['max_input_length']}→{config['max_output_length']}")
    print(f"⏱️  Epochs: {config['num_epochs']} | LR: {config['learning_rate']}")
    print()

    return config

def preprocess_function(examples, tokenizer, max_input_length=512, max_output_length=256):
    """Fixed preprocessing function that handles single examples correctly"""
    input_text = examples["input"]
    target_text = examples["output"]

    # Tokenize inputs
    model_inputs = tokenizer(
        input_text,
        max_length=max_input_length,
        truncation=True,
        padding="max_length"
    )

    # Tokenize targets
    labels = tokenizer(
        target_text,
        max_length=max_output_length,
        truncation=True,
        padding="max_length"
    )

    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

def train_gpu_optimized_model():
    """Main training function with GPU optimization"""

    # Setup
    device, gpu_available = setup_gpu_environment()
    config = get_gpu_optimized_config(device, gpu_available)

    # Create timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Paths
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    model_dir = base_dir / "models" / f"gpu_optimized_model_{timestamp}"
    log_dir = base_dir / "logs"

    # Create directories
    model_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    print("📂 LOADING DATA AND MODEL")
    print("=" * 40)

    try:
        # 1. Load datasets
        print("Loading datasets...")
        train_dataset = load_from_disk(str(data_dir / "train"))
        val_dataset = load_from_disk(str(data_dir / "validation"))
        print(f"✅ Train: {len(train_dataset)} | Validation: {len(val_dataset)}")

        # 2. Load tokenizer and model
        print(f"Loading {config['model_name']}...")
        tokenizer = T5Tokenizer.from_pretrained(config['model_name'])
        model = T5ForConditionalGeneration.from_pretrained(config['model_name'])

        # Add special tokens if needed
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        print(f"✅ Model: {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M parameters")

        # 3. Apply LoRA
        print(f"Applying LoRA (rank={config['lora_rank']})...")
        lora_config = LoraConfig(
            task_type=TaskType.SEQ_2_SEQ_LM,
            r=config['lora_rank'],
            lora_alpha=config['lora_alpha'],
            lora_dropout=config['lora_dropout'],
            target_modules=["q", "v", "k", "o"]
        )
        model = get_peft_model(model, lora_config)

        # Print trainable parameters
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in model.parameters())
        print(f"🎛️  Trainable: {trainable_params:,} | Total: {total_params:,} | Efficiency: {trainable_params/total_params*100:.2f}%")

        # 4. Move model to device
        model = model.to(device)
        if gpu_available:
            print(f"📱 Model moved to GPU")

        # 5. Preprocess datasets
        print("Tokenizing datasets...")

        def preprocess_wrapper(examples):
            return preprocess_function(
                examples,
                tokenizer,
                config['max_input_length'],
                config['max_output_length']
            )

        train_dataset = train_dataset.map(preprocess_wrapper, batched=False)
        val_dataset = val_dataset.map(preprocess_wrapper, batched=False)
        print("✅ Tokenization complete")

        print()
        print("⚡ STARTING GPU-OPTIMIZED TRAINING")
        print("=" * 50)

        # 6. Training arguments
        training_args = Seq2SeqTrainingArguments(
            output_dir=str(model_dir),
            learning_rate=config['learning_rate'],
            per_device_train_batch_size=config['batch_size'],
            per_device_eval_batch_size=config['batch_size'],
            gradient_accumulation_steps=config['gradient_accumulation_steps'],
            num_train_epochs=config['num_epochs'],
            warmup_steps=config['warmup_steps'],
            logging_steps=config['logging_steps'],
            save_steps=config['save_steps'],
            eval_steps=config['eval_steps'],
            evaluation_strategy="steps",
            save_strategy="steps",
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            save_total_limit=3,
            gradient_checkpointing=config['gradient_checkpointing'],
            fp16=config['fp16'],
            dataloader_num_workers=config['dataloader_num_workers'],
            remove_unused_columns=False,
            predict_with_generate=True,
            generation_max_length=config['max_output_length'],
            # Fixed: Remove report_to parameter that caused the bug
            logging_dir=str(log_dir / f"tensorboard_{timestamp}"),
        )

        # 7. Data collator
        data_collator = DataCollatorForSeq2Seq(
            tokenizer=tokenizer,
            model=model,
            padding=True
        )

        # 8. Initialize trainer
        trainer = Seq2SeqTrainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            data_collator=data_collator
        )

        # 9. Clear GPU cache before training
        if gpu_available:
            torch.cuda.empty_cache()
            print(f"🧹 GPU cache cleared")

        # 10. Start training
        print(f"🚀 Training on {device.upper()}...")
        print(f"⏱️  Expected time: {'~30-45 minutes' if gpu_available else '~2-4 hours'}")
        print()

        # Training
        train_result = trainer.train()

        print()
        print("✅ TRAINING COMPLETED!")
        print("=" * 30)

        # 11. Save model
        print("Saving model...")
        trainer.save_model()
        tokenizer.save_pretrained(str(model_dir))

        # 12. Save training results
        results = {
            "model": f"{config['model_name']}-lora-gpu-optimized",
            "device": device,
            "gpu_name": torch.cuda.get_device_name(0) if gpu_available else "CPU",
            "epochs": config['num_epochs'],
            "final_loss": train_result.training_loss,
            "lora_rank": config['lora_rank'],
            "trainable_params": trainable_params,
            "total_params": total_params,
            "efficiency_percent": trainable_params/total_params*100,
            "timestamp": timestamp,
            "config": config
        }

        with open(model_dir / "training_results.json", "w") as f:
            json.dump(results, f, indent=2)

        print(f"📁 Model saved to: {model_dir}")
        print(f"📊 Final loss: {train_result.training_loss:.4f}")

        # 13. Memory cleanup
        if gpu_available:
            del model, trainer
            torch.cuda.empty_cache()
            gc.collect()
            print("🧹 GPU memory cleaned")

        return str(model_dir), results

    except Exception as e:
        print(f"❌ Error during training: {e}")
        if gpu_available:
            torch.cuda.empty_cache()
        raise

if __name__ == "__main__":
    print("🤖 META-MODEL PATTERN DETECTOR")
    print("🎯 GPU-Optimized Training Pipeline")
    print("💻 RTX 5060 8GB VRAM Optimized")
    print("=" * 60)
    print()

    try:
        model_path, results = train_gpu_optimized_model()

        print("\n" + "=" * 60)
        print("🎉 TRAINING SUCCESS!")
        print("=" * 60)
        print(f"📁 Model: {model_path}")
        print(f"🎯 Device: {results['device'].upper()}")
        print(f"📊 Final Loss: {results['final_loss']:.4f}")
        print(f"⚡ Efficiency: {results['efficiency_percent']:.2f}%")
        print("\n✅ Ready for evaluation and deployment!")

    except KeyboardInterrupt:
        print("\n⏹️  Training interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        sys.exit(1)