#!/usr/bin/env python3
"""
SAATHI AI — Stage 2 LoRA Training Script
=========================================
QLoRA fine-tune of Qwen2.5-7B-Instruct with r=16 adapter for
therapeutic support conversations.

Key differences from Stage 1:
  - LoRA r=16 (deeper adaptation for 11-step clinical protocol)
  - max_seq_length=4096 (longer multi-turn therapy sessions)
  - 4 training epochs, LR=1e-4 (more data, clinical precision)
  - TherapeuticQualityTrainer: adds penalty for harmful clinical patterns
  - train_on_inputs=False: only compute loss on assistant tokens

Usage:
    python 02_train_stage2_lora.py
    python 02_train_stage2_lora.py --data ./data --out ./output --epochs 4

Requires GPU with >=24GB VRAM (A10G minimum, A100 recommended).
"""

import os
import re
import json
import time
import math
import argparse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from loguru import logger

# ─── Configuration ────────────────────────────────────────────────────────────

@dataclass
class Stage2TrainingConfig:
    # Paths
    data_dir:   str = str(Path(__file__).parent / "data")
    output_dir: str = str(Path(__file__).parent / "output" / "qwen-lora-stage2")
    # Qwen2.5-3B fits comfortably on 8 GB VRAM for QLoRA training
    base_model: str = "Qwen/Qwen2.5-3B-Instruct"

    # LoRA — r=16 for deeper clinical adaptation
    lora_rank:        int   = 16
    lora_alpha:       int   = 32       # alpha = 2 × rank
    lora_dropout:     float = 0.05
    target_modules: tuple = (
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    )

    # Training — tuned for 8 GB VRAM (RTX 5060 / RTX 3060 class)
    num_train_epochs:           int   = 4
    per_device_train_batch_size: int  = 1   # 8 GB: keep batch=1 for safety
    per_device_eval_batch_size:  int  = 1
    gradient_accumulation_steps: int  = 32  # effective batch = 32
    learning_rate:              float = 1e-4
    warmup_ratio:               float = 0.05
    lr_scheduler_type:          str   = "cosine"
    weight_decay:               float = 0.01
    max_seq_length:             int   = 2048   # 2048 fits 8 GB comfortably
    train_on_inputs:            bool  = False  # only compute loss on assistant tokens
    gradient_checkpointing:     bool  = True
    seed:                       int   = 42

    # Evaluation and saving
    eval_strategy:              str   = "epoch"
    save_strategy:              str   = "epoch"
    save_total_limit:           int   = 3
    load_best_model_at_end:     bool  = True
    metric_for_best_model:      str   = "eval_loss"
    early_stopping_patience:    int   = 3

    # Logging — no WandB required for local training
    logging_steps:    int  = 30
    report_to:        str  = "none"
    wandb_project:    str  = "saathi-ai-stage2"
    run_name:         str  = "qwen-lora-stage2-therapy"

    # Generation (for eval)
    temperature:       float = 0.75    # slightly lower for clinical precision
    top_p:             float = 0.90
    top_k:             int   = 40
    repetition_penalty: float = 1.15   # prevent repetitive therapeutic phrases


HARMFUL_PATTERNS_TRAIN = [
    r"\byou should (leave|divorce|quit|stop)\b",
    r"\bthat'?s? (stupid|wrong|irrational|silly)\b",
    r"\bi (know|understand) exactly how you feel\b",
    r"\bthings will definitely get better\b",
    r"\byou'?re? (broken|damaged|flawed|crazy)\b",
    r"\bother people have it worse\b",
    r"\bjust (cheer up|calm down|snap out of it)\b",
    r"\b(guaranteed|100%) (results?|cure|fix)\b",
]


# ─── GPU / Precision Detection ────────────────────────────────────────────────

def detect_gpu_capabilities() -> dict:
    try:
        import torch
        if not torch.cuda.is_available():
            return {"available": False, "bf16": False, "flash_attn": False, "device": "cpu"}

        compute_cap = torch.cuda.get_device_capability()
        device_name = torch.cuda.get_device_name(0)
        # bf16 available on Ampere (sm_80+)
        bf16 = compute_cap[0] >= 8
        # Flash Attention 2 requires the flash_attn package — check if importable
        try:
            import flash_attn  # noqa: F401
            flash_attn_ok = bf16
        except ImportError:
            flash_attn_ok = False
            logger.warning("flash_attn not installed — using standard attention (still fast with bf16)")
        logger.info(f"GPU: {device_name} | sm_{compute_cap[0]}{compute_cap[1]} | "
                    f"bf16={bf16} | flash_attn2={flash_attn_ok}")
        return {"available": True, "bf16": bf16, "flash_attn": flash_attn_ok, "device": "cuda"}
    except Exception as e:
        logger.warning(f"GPU detection failed: {e}")
        return {"available": False, "bf16": False, "flash_attn": False, "device": "cpu"}


def build_bnb_config(bf16: bool = False):
    """Build BitsAndBytes 4-bit QLoRA configuration."""
    import torch
    from transformers import BitsAndBytesConfig
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if bf16 else torch.float16,
        bnb_4bit_use_double_quant=True,
    )


# ─── Model and Tokenizer Loading ──────────────────────────────────────────────

def load_tokenizer(model_name: str):
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    logger.info(f"Tokenizer loaded: vocab_size={tokenizer.vocab_size}")
    return tokenizer


def load_base_model(model_name: str, bnb_config, bf16: bool, flash_attn: bool):
    import torch
    from transformers import AutoModelForCausalLM

    kwargs = {
        "quantization_config": bnb_config,
        "device_map":          "auto",
        "trust_remote_code":   True,
        "dtype":               torch.bfloat16 if bf16 else torch.float16,
    }
    if flash_attn:
        kwargs["attn_implementation"] = "flash_attention_2"
        logger.info("Using Flash Attention 2")
    else:
        logger.info("Using standard attention (eager)")

    model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs)
    model.config.use_cache = False  # required for gradient checkpointing
    logger.info(f"Base model loaded: {model_name}")
    return model


def apply_lora(model, config: Stage2TrainingConfig):
    from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training

    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=config.gradient_checkpointing)

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=config.lora_rank,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=list(config.target_modules),
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    trainable, total = model.get_nb_trainable_parameters()
    logger.info(f"LoRA applied: r={config.lora_rank}, alpha={config.lora_alpha}")
    logger.info(f"Trainable params: {trainable:,} / {total:,} ({100*trainable/total:.3f}%)")
    return model


# ─── Dataset Loading ──────────────────────────────────────────────────────────

def load_datasets(data_dir: str, tokenizer):
    """Load ChatML-formatted JSONL splits."""
    from datasets import load_dataset

    data_path = Path(data_dir)

    train_file = str(data_path / "train_chatml.jsonl")
    val_file   = str(data_path / "val_chatml.jsonl")

    if not Path(train_file).exists():
        raise FileNotFoundError(
            f"Training data not found at {train_file}\n"
            "Run: python 01_prepare_stage2_dataset.py first"
        )

    dataset = load_dataset("json", data_files={"train": train_file, "validation": val_file})

    # Verify text field
    sample = dataset["train"][0]
    assert "text" in sample, "Dataset must have 'text' field (ChatML string)"

    logger.info(f"Dataset loaded: train={len(dataset['train']):,} | val={len(dataset['validation']):,}")
    return dataset["train"], dataset["validation"]


# ─── Therapeutic Quality Trainer ──────────────────────────────────────────────

class TherapeuticQualityTrainer:
    """
    Wrapper that adds a harmful-pattern penalty on top of SFTTrainer loss.

    Inherits from SFTTrainer. The penalty is added as a non-differentiable
    scalar so it does not corrupt gradients — it's an informational loss
    signal for monitoring, not backpropagation.
    """

    @staticmethod
    def get_trainer_class():
        """Returns a patched SFTTrainer class with therapeutic loss."""
        import torch
        import re as _re
        from trl import SFTTrainer

        _patterns = [_re.compile(p, _re.IGNORECASE) for p in HARMFUL_PATTERNS_TRAIN]

        class _TherapeuticTrainer(SFTTrainer):
            def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
                # Standard cross-entropy loss on assistant tokens
                outputs = model(**inputs)
                base_loss = outputs.loss if hasattr(outputs, "loss") else outputs[0]

                # Decode predicted tokens (no_grad, purely for monitoring)
                penalty = torch.tensor(0.0, device=base_loss.device)
                try:
                    with torch.no_grad():
                        pred_ids = torch.argmax(outputs.logits, dim=-1)
                        decoded  = self.tokenizer.batch_decode(pred_ids, skip_special_tokens=True)
                        for text in decoded:
                            for pat in _patterns:
                                if pat.search(text):
                                    penalty += 0.5
                        penalty = penalty / max(len(decoded), 1)
                except Exception:
                    pass  # Never let monitoring crash training

                total_loss = base_loss + penalty
                if self.state.global_step % 30 == 0 and penalty.item() > 0:
                    logger.warning(f"Step {self.state.global_step}: harmful pattern penalty = {penalty.item():.3f}")

                return (total_loss, outputs) if return_outputs else total_loss

        return _TherapeuticTrainer


# ─── Training Arguments ───────────────────────────────────────────────────────

def build_training_args(config: Stage2TrainingConfig, bf16: bool):
    # TRL >=0.26: use SFTConfig (extends TrainingArguments) so that
    # dataset_text_field, max_length, packing live in the args object.
    from trl import SFTConfig

    return SFTConfig(
        output_dir=config.output_dir,
        num_train_epochs=config.num_train_epochs,
        per_device_train_batch_size=config.per_device_train_batch_size,
        per_device_eval_batch_size=config.per_device_eval_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        warmup_steps=max(1, int(config.warmup_ratio * config.num_train_epochs * 2408 // config.gradient_accumulation_steps)),
        lr_scheduler_type=config.lr_scheduler_type,
        weight_decay=config.weight_decay,
        bf16=bf16,
        fp16=not bf16,
        gradient_checkpointing=config.gradient_checkpointing,
        eval_strategy=config.eval_strategy,
        save_strategy=config.save_strategy,
        save_total_limit=config.save_total_limit,
        load_best_model_at_end=config.load_best_model_at_end,
        metric_for_best_model=config.metric_for_best_model,
        logging_steps=config.logging_steps,
        report_to=config.report_to,
        run_name=config.run_name,
        seed=config.seed,
        dataloader_num_workers=0,     # 0 = no multiprocessing (Windows-safe)
        remove_unused_columns=False,
        # SFTConfig-specific fields
        dataset_text_field="text",
        max_length=config.max_seq_length,
        packing=False,
    )


# ─── Post-Training Report ─────────────────────────────────────────────────────

def compute_perplexity(trainer) -> float:
    """Compute perplexity on validation set from trainer eval metrics."""
    try:
        metrics = trainer.evaluate()
        eval_loss = metrics.get("eval_loss", 0.0)
        ppl = math.exp(eval_loss)
        logger.info(f"Validation loss: {eval_loss:.4f} | Perplexity: {ppl:.2f}")
        return round(ppl, 2)
    except Exception as e:
        logger.warning(f"Could not compute perplexity: {e}")
        return -1.0


def save_training_report(config: Stage2TrainingConfig, trainer, perplexity: float, start_time: float):
    """Save training metrics to training_report.json in the adapter directory."""
    adapter_path = Path(config.output_dir)
    adapter_path.mkdir(parents=True, exist_ok=True)

    # Extract loss history
    loss_history = []
    if hasattr(trainer, "state") and hasattr(trainer.state, "log_history"):
        for entry in trainer.state.log_history:
            if "loss" in entry:
                loss_history.append({
                    "step": entry.get("step", 0),
                    "loss": round(entry["loss"], 4),
                    "learning_rate": entry.get("learning_rate", 0),
                    "epoch": round(entry.get("epoch", 0), 2),
                })

    report = {
        "model_name":       "qwen-lora-stage2-saathi-v1",
        "base_model":       config.base_model,
        "lora_rank":        config.lora_rank,
        "lora_alpha":       config.lora_alpha,
        "target_modules":   list(config.target_modules),
        "num_epochs":       config.num_train_epochs,
        "batch_size_eff":   config.per_device_train_batch_size * config.gradient_accumulation_steps,
        "learning_rate":    config.learning_rate,
        "max_seq_length":   config.max_seq_length,
        "perplexity":       perplexity,
        "perplexity_target": 30,
        "perplexity_pass":  perplexity < 30 if perplexity > 0 else None,
        "training_time_minutes": round((time.time() - start_time) / 60, 1),
        "loss_history":     loss_history[-50:] if len(loss_history) > 50 else loss_history,
    }

    report_path = adapter_path / "training_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Training report saved: {report_path}")
    logger.info(f"Perplexity: {perplexity:.2f} (target: <30)")
    return report


# ─── Main Training Entry Point ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Train Stage 2 LoRA adapter")
    parser.add_argument("--data",   default=str(Path(__file__).parent / "data"))
    parser.add_argument("--out",    default=str(Path(__file__).parent / "output" / "qwen-lora-stage2"))
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--rank",   type=int, default=16)
    parser.add_argument("--lr",     type=float, default=1e-4)
    parser.add_argument("--no-wandb", action="store_true")
    args = parser.parse_args()

    config              = Stage2TrainingConfig()
    config.data_dir     = args.data
    config.output_dir   = args.out
    config.num_train_epochs = args.epochs
    config.lora_rank    = args.rank
    config.learning_rate = args.lr
    if args.no_wandb:
        config.report_to = "tensorboard"

    print("=" * 60)
    print("SAATHI AI — Stage 2 LoRA Training")
    print("=" * 60)
    print(f"Base model:   {config.base_model}")
    print(f"LoRA rank:    r={config.lora_rank}, alpha={config.lora_alpha}")
    print(f"Epochs:       {config.num_train_epochs}")
    print(f"LR:           {config.learning_rate}")
    print(f"Max seq len:  {config.max_seq_length}")
    print(f"Output:       {config.output_dir}")

    start_time = time.time()

    # ── GPU detection ────────────────────────────────────────────────────
    gpu = detect_gpu_capabilities()
    if not gpu["available"]:
        logger.error("No GPU detected. Stage 2 training requires a CUDA GPU (8 GB+ VRAM).")
        return

    # ── Load components ──────────────────────────────────────────────────
    print("\n[1/5] Loading tokenizer and model...")
    bnb_config = build_bnb_config(bf16=gpu["bf16"])
    tokenizer  = load_tokenizer(config.base_model)
    model      = load_base_model(config.base_model, bnb_config, bf16=gpu["bf16"], flash_attn=gpu["flash_attn"])
    model      = apply_lora(model, config)

    # ── Load datasets ────────────────────────────────────────────────────
    print("\n[2/5] Loading datasets...")
    train_dataset, val_dataset = load_datasets(config.data_dir, tokenizer)

    # ── Build trainer ────────────────────────────────────────────────────
    print("\n[3/5] Building TherapeuticQualityTrainer...")
    from transformers import EarlyStoppingCallback

    training_args = build_training_args(config, bf16=gpu["bf16"])

    TherapeuticTrainer = TherapeuticQualityTrainer.get_trainer_class()

    trainer = TherapeuticTrainer(
        model=model,
        args=training_args,          # SFTConfig carries dataset_text_field, max_length, packing
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        processing_class=tokenizer,  # TRL ≥0.26 renamed from 'tokenizer'
        callbacks=[EarlyStoppingCallback(early_stopping_patience=config.early_stopping_patience)],
    )

    # ── Train ────────────────────────────────────────────────────────────
    print("\n[4/5] Training...")
    print(f"  Effective batch size: {config.per_device_train_batch_size * config.gradient_accumulation_steps}")
    print(f"  Expected duration: ~3-5h on A10G, ~60-90min on A100")
    print()

    trainer.train()
    logger.info("Training complete.")

    # ── Save adapter ─────────────────────────────────────────────────────
    print("\n[5/5] Saving adapter and report...")
    Path(config.output_dir).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(config.output_dir)
    tokenizer.save_pretrained(config.output_dir)
    logger.info(f"Adapter saved: {config.output_dir}")

    perplexity = compute_perplexity(trainer)
    report = save_training_report(config, trainer, perplexity, start_time)

    # ── Summary ──────────────────────────────────────────────────────────
    duration = (time.time() - start_time) / 60
    ppl_status = "[PASS]" if perplexity < 30 else "[FAIL]"

    print("\n" + "=" * 60)
    print("Training COMPLETE")
    print("=" * 60)
    print(f"  Duration:      {duration:.1f} minutes")
    print(f"  Perplexity:    {perplexity:.2f} (target: <30) {ppl_status}")
    print(f"  Adapter saved: {config.output_dir}")
    print()
    print("Next step:")
    print(f"  python 03_evaluate_stage2.py --adapter {config.output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
