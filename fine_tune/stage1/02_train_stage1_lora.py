#!/usr/bin/env python3
"""
SAATHI AI — Stage 1 QLoRA Training Script
==========================================
Fine-tunes Qwen/Qwen2.5-7B-Instruct with LoRA (r=8) on Stage 1 sales
conversations using 4-bit quantization (QLoRA) + SFTTrainer.

Requirements:
    GPU: 1x A100 40GB (recommended) | 1x A10G 24GB (minimum)
    pip install -r requirements.txt

Usage:
    python 02_train_stage1_lora.py
    python 02_train_stage1_lora.py --epochs 3 --batch-size 4 --wandb
    python 02_train_stage1_lora.py --resume-from-checkpoint ./checkpoints/checkpoint-100

Output:
    ./output/qwen-lora-stage1/
        adapter_config.json
        adapter_model.safetensors  (~17MB)
        tokenizer_config.json
        tokenizer.json
        training_args.bin
        trainer_state.json
"""

import os
import json
import argparse
import math
from pathlib import Path
from dataclasses import dataclass, field

# ─── Guard: verify GPU environment ────────────────────────────────────────────
try:
    import torch
    if not torch.cuda.is_available():
        print("[WARNING] No CUDA GPU detected. Training will be extremely slow on CPU.")
        print("          Recommended: A100 40GB or A10G 24GB. Exiting for safety.")
        print("          To force CPU training: set FORCE_CPU=1")
        if not os.environ.get("FORCE_CPU"):
            raise SystemExit(1)
    else:
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"GPU detected: {gpu_name} ({gpu_mem_gb:.1f} GB VRAM)")
        if gpu_mem_gb < 20:
            print(f"[WARNING] Only {gpu_mem_gb:.1f}GB VRAM — minimum 24GB recommended.")
            print("          Reduce batch_size to 1 and gradient_accumulation_steps to 32.")
except ImportError:
    raise SystemExit("PyTorch not installed. Run: pip install -r requirements.txt")

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainingArguments,
    EarlyStoppingCallback,
)
from peft import (
    LoraConfig,
    TaskType,
    get_peft_model,
    prepare_model_for_kbit_training,
)
from trl import SFTTrainer
from datasets import Dataset, load_dataset

# ─── Training Configuration ────────────────────────────────────────────────────

@dataclass
class Stage1TrainingConfig:
    # Model
    base_model: str = "Qwen/Qwen2.5-7B-Instruct"
    trust_remote_code: bool = True

    # LoRA
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.1
    lora_target_modules: list = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",   # MLP projections for Qwen
    ])

    # Data
    train_file: str = "./data/train_chatml.jsonl"
    val_file: str   = "./data/val_chatml.jsonl"
    max_seq_length: int = 2048

    # Training
    output_dir: str = "./output/qwen-lora-stage1"
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 4
    gradient_accumulation_steps: int = 8   # effective batch = 32
    learning_rate: float = 2e-4
    warmup_ratio: float = 0.05
    lr_scheduler_type: str = "cosine"
    weight_decay: float = 0.01

    # Precision
    fp16: bool = True
    bf16: bool = False                    # Use bf16 on A100 instead of fp16
    load_in_4bit: bool = True             # QLoRA
    bnb_4bit_quant_type: str = "nf4"
    bnb_4bit_use_double_quant: bool = True

    # Logging
    logging_steps: int = 10
    eval_steps: int = 50
    save_steps: int = 50
    save_total_limit: int = 3
    report_to: str = "none"              # "wandb" if W&B configured
    run_name: str = "qwen-lora-stage1-saathi"

    # Misc
    seed: int = 42
    gradient_checkpointing: bool = True
    packing: bool = False                 # Don't pack conversations


CFG = Stage1TrainingConfig()


def detect_bf16_support() -> bool:
    """Return True if GPU supports bfloat16 (Ampere+)."""
    if not torch.cuda.is_available():
        return False
    cc = torch.cuda.get_device_capability()
    return cc[0] >= 8   # sm_80 = A100


def build_bnb_config() -> BitsAndBytesConfig:
    """4-bit NF4 quantization config for QLoRA."""
    return BitsAndBytesConfig(
        load_in_4bit=CFG.load_in_4bit,
        bnb_4bit_compute_dtype=torch.bfloat16 if detect_bf16_support() else torch.float16,
        bnb_4bit_use_double_quant=CFG.bnb_4bit_use_double_quant,
        bnb_4bit_quant_type=CFG.bnb_4bit_quant_type,
    )


def load_tokenizer() -> AutoTokenizer:
    print(f"\nLoading tokenizer: {CFG.base_model}")
    tokenizer = AutoTokenizer.from_pretrained(
        CFG.base_model,
        trust_remote_code=CFG.trust_remote_code,
    )
    # Qwen uses its own pad/eos tokens
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"  # Right-padding for causal LM
    print(f"  Vocab size: {tokenizer.vocab_size:,}")
    print(f"  EOS token: {tokenizer.eos_token!r} (id={tokenizer.eos_token_id})")
    return tokenizer


def load_model(tokenizer) -> AutoModelForCausalLM:
    print(f"\nLoading base model: {CFG.base_model}")
    bnb_config = build_bnb_config()
    use_bf16 = detect_bf16_support()
    dtype = torch.bfloat16 if use_bf16 else torch.float16
    print(f"  Precision: {'bfloat16 (A100)' if use_bf16 else 'float16'}")

    model = AutoModelForCausalLM.from_pretrained(
        CFG.base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=CFG.trust_remote_code,
        torch_dtype=dtype,
        attn_implementation="flash_attention_2" if use_bf16 else "eager",
    )

    model.config.use_cache = False
    model.config.pretraining_tp = 1  # Qwen recommendation

    # Resize embeddings if needed
    model.resize_token_embeddings(len(tokenizer))

    print(f"  Parameters: {sum(p.numel() for p in model.parameters()) / 1e9:.2f}B")
    return model


def apply_lora(model) -> "PeftModel":
    print("\nApplying LoRA adapter (r=8)...")
    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=CFG.gradient_checkpointing
    )

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=CFG.lora_r,
        lora_alpha=CFG.lora_alpha,
        lora_dropout=CFG.lora_dropout,
        target_modules=CFG.lora_target_modules,
        bias="none",
        inference_mode=False,
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total     = sum(p.numel() for p in model.parameters())
    print(f"  Trainable parameters: {trainable / 1e6:.2f}M / {total / 1e9:.2f}B ({trainable/total*100:.3f}%)")

    return model


def load_datasets(tokenizer) -> tuple:
    """Load ChatML datasets from JSONL files."""
    print(f"\nLoading datasets...")

    def load_jsonl_dataset(path: str) -> Dataset:
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return Dataset.from_list(records)

    train_path = Path(CFG.train_file)
    val_path   = Path(CFG.val_file)

    if not train_path.exists():
        raise FileNotFoundError(
            f"Training file not found: {train_path}\n"
            "Run: python 01_prepare_dataset.py first"
        )
    if not val_path.exists():
        raise FileNotFoundError(f"Validation file not found: {val_path}")

    train_ds = load_jsonl_dataset(str(train_path))
    val_ds   = load_jsonl_dataset(str(val_path))

    print(f"  Train: {len(train_ds):,} conversations")
    print(f"  Val:   {len(val_ds):,} conversations")

    # Verify the 'text' column exists (ChatML format)
    assert "text" in train_ds.column_names, "Dataset must have a 'text' column (ChatML format)"

    # Log token length statistics
    sample_tokens = tokenizer(train_ds[0]["text"], return_tensors="pt")
    print(f"  Sample sequence length: {sample_tokens['input_ids'].shape[1]} tokens")

    return train_ds, val_ds


def build_training_args(resume_from: str = None) -> TrainingArguments:
    use_bf16 = detect_bf16_support()
    return TrainingArguments(
        output_dir=CFG.output_dir,
        num_train_epochs=CFG.num_train_epochs,
        per_device_train_batch_size=CFG.per_device_train_batch_size,
        per_device_eval_batch_size=CFG.per_device_eval_batch_size,
        gradient_accumulation_steps=CFG.gradient_accumulation_steps,
        learning_rate=CFG.learning_rate,
        warmup_ratio=CFG.warmup_ratio,
        lr_scheduler_type=CFG.lr_scheduler_type,
        weight_decay=CFG.weight_decay,
        bf16=use_bf16,
        fp16=not use_bf16,
        gradient_checkpointing=CFG.gradient_checkpointing,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        evaluation_strategy="steps",
        eval_steps=CFG.eval_steps,
        save_strategy="steps",
        save_steps=CFG.save_steps,
        save_total_limit=CFG.save_total_limit,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        logging_steps=CFG.logging_steps,
        logging_dir=f"{CFG.output_dir}/logs",
        report_to=CFG.report_to,
        run_name=CFG.run_name,
        seed=CFG.seed,
        dataloader_pin_memory=True,
        dataloader_num_workers=2,
        remove_unused_columns=False,
        resume_from_checkpoint=resume_from,
        optim="paged_adamw_32bit",  # Memory-efficient optimizer for QLoRA
    )


def compute_metrics(eval_pred) -> dict:
    """Compute perplexity from eval loss (Trainer passes logits)."""
    # SFTTrainer with causal LM returns loss directly
    return {}


def main():
    parser = argparse.ArgumentParser(description="Stage 1 QLoRA Training")
    parser.add_argument("--epochs", type=int, default=CFG.num_train_epochs)
    parser.add_argument("--batch-size", type=int, default=CFG.per_device_train_batch_size)
    parser.add_argument("--lr", type=float, default=CFG.learning_rate)
    parser.add_argument("--wandb", action="store_true", help="Enable W&B logging")
    parser.add_argument("--resume-from-checkpoint", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=CFG.output_dir)
    args = parser.parse_args()

    # Apply CLI overrides
    CFG.num_train_epochs = args.epochs
    CFG.per_device_train_batch_size = args.batch_size
    CFG.learning_rate = args.lr
    CFG.output_dir = args.output_dir
    if args.wandb:
        CFG.report_to = "wandb"

    print("=" * 60)
    print("SAATHI AI — Stage 1 QLoRA Training")
    print("=" * 60)
    print(f"Base model:  {CFG.base_model}")
    print(f"LoRA rank:   r={CFG.lora_r}, alpha={CFG.lora_alpha}")
    print(f"Epochs:      {CFG.num_train_epochs}")
    print(f"Batch size:  {CFG.per_device_train_batch_size} x {CFG.gradient_accumulation_steps} = "
          f"{CFG.per_device_train_batch_size * CFG.gradient_accumulation_steps} effective")
    print(f"LR:          {CFG.learning_rate}")
    print(f"Output:      {CFG.output_dir}")
    print(f"W&B:         {CFG.report_to}")

    # ── Load components ───────────────────────────────────────────────────────
    tokenizer = load_tokenizer()
    model = load_model(tokenizer)
    model = apply_lora(model)
    train_ds, val_ds = load_datasets(tokenizer)
    training_args = build_training_args(resume_from=args.resume_from_checkpoint)

    # ── Effective steps ───────────────────────────────────────────────────────
    steps_per_epoch = math.ceil(len(train_ds) / (
        CFG.per_device_train_batch_size * CFG.gradient_accumulation_steps
    ))
    total_steps = steps_per_epoch * CFG.num_train_epochs
    print(f"\nEstimated training steps: {total_steps} ({steps_per_epoch}/epoch)")

    # ── Create SFTTrainer ─────────────────────────────────────────────────────
    print("\nInitialising SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        tokenizer=tokenizer,
        dataset_text_field="text",
        max_seq_length=CFG.max_seq_length,
        packing=CFG.packing,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
    )

    # ── Train ─────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Starting training...")
    print("=" * 60)

    train_result = trainer.train(
        resume_from_checkpoint=args.resume_from_checkpoint
    )

    # ── Log metrics ───────────────────────────────────────────────────────────
    metrics = train_result.metrics
    trainer.log_metrics("train", metrics)
    trainer.save_metrics("train", metrics)

    # ── Save LoRA adapter ─────────────────────────────────────────────────────
    print(f"\nSaving LoRA adapter to {CFG.output_dir}...")
    trainer.model.save_pretrained(CFG.output_dir)
    tokenizer.save_pretrained(CFG.output_dir)

    # Save training config
    config_path = Path(CFG.output_dir) / "saathi_training_config.json"
    with open(config_path, "w") as f:
        import dataclasses
        json.dump(dataclasses.asdict(CFG), f, indent=2)

    print("\n" + "=" * 60)
    print("Training complete!")
    print(f"  Final train loss:  {metrics.get('train_loss', 'N/A'):.4f}")
    print(f"  Adapter saved to:  {CFG.output_dir}")
    print(f"  Run evaluation:    python 03_evaluate_stage1.py --adapter {CFG.output_dir}")
    print(f"  Deploy to server:  python 04_deploy_adapter.py --adapter {CFG.output_dir}")
    print("=" * 60)

    # ── Eval on test set (quick perplexity check) ─────────────────────────────
    print("\nRunning final evaluation on validation set...")
    eval_results = trainer.evaluate()
    eval_loss = eval_results.get("eval_loss", float("inf"))
    perplexity = math.exp(eval_loss) if eval_loss < 100 else float("inf")

    print(f"  Eval loss:    {eval_loss:.4f}")
    print(f"  Perplexity:   {perplexity:.2f} (target: < 45)")

    trainer.save_metrics("eval", eval_results)

    final_report = {
        "model": CFG.base_model,
        "lora_rank": CFG.lora_r,
        "lora_alpha": CFG.lora_alpha,
        "epochs_trained": CFG.num_train_epochs,
        "train_loss": metrics.get("train_loss"),
        "eval_loss": eval_loss,
        "perplexity": perplexity,
        "perplexity_target": 45,
        "perplexity_pass": perplexity < 45,
        "adapter_path": CFG.output_dir,
    }
    with open(Path(CFG.output_dir) / "training_report.json", "w") as f:
        json.dump(final_report, f, indent=2)

    print(f"\nTraining report saved: {CFG.output_dir}/training_report.json")

    return final_report


if __name__ == "__main__":
    main()
