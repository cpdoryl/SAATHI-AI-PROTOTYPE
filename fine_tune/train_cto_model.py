"""
SAATHI AI — Local Model Fine-tuning Script
Fine-tunes Qwen/Qwen2.5-Coder-7B-Instruct using QLoRA (4-bit) on the CTO knowledge base.
Compatible with: Windows 11 + RTX 5060 8GB VRAM + Python 3.12

Architecture:
  Base model: Qwen/Qwen2.5-Coder-7B-Instruct (HuggingFace)
  Method: QLoRA (4-bit quantization + LoRA adapters)
  LoRA rank: 16, alpha: 32
  VRAM budget: ~7GB (fits RTX 5060 8GB)
  After training: export to GGUF + import to Ollama

Usage:
  python fine_tune/train_cto_model.py                    # Full training
  python fine_tune/train_cto_model.py --quick-test       # 5-step smoke test
"""

import os
import sys
import argparse
import json
from pathlib import Path

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"
OUTPUT_DIR = str(Path(__file__).parent / "outputs" / "saathi-cto-lora")
GGUF_DIR = str(Path(__file__).parent / "outputs" / "gguf")
DATA_DIR = str(Path(__file__).parent / "data")

LORA_CONFIG = dict(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
)

TRAINING_CONFIG = dict(
    num_train_epochs=3,
    per_device_train_batch_size=1,      # Conservative: fits in 8GB
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=8,      # Effective batch = 8
    learning_rate=2e-4,
    warmup_steps=10,
    max_steps=-1,                       # -1 = use num_train_epochs
    fp16=True,                          # Use FP16 on NVIDIA GPU
    bf16=False,                         # BF16 not supported on all Windows drivers
    logging_steps=5,
    eval_strategy="steps",
    eval_steps=50,
    save_strategy="steps",
    save_steps=100,
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    max_seq_length=512,                 # Keep short to save VRAM
    optim="adamw_torch",               # Windows-compatible (not paged_adamw_8bit)
    dataloader_pin_memory=False,        # Avoid memory issues on Windows
    report_to="none",                   # Disable wandb
    group_by_length=True,              # Batch similar-length sequences together
)


def check_dependencies():
    """Verify all required packages are installed."""
    missing = []
    required = [
        ("torch", "torch"),
        ("transformers", "transformers"),
        ("peft", "peft"),
        ("trl", "trl"),
        ("bitsandbytes", "bitsandbytes"),
        ("datasets", "datasets"),
        ("accelerate", "accelerate"),
    ]
    for import_name, pip_name in required:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)
    
    if missing:
        print(f"\n[ERROR] Missing packages: {', '.join(missing)}")
        print("Run: pip install " + " ".join(missing))
        sys.exit(1)
    
    print("[OK] All dependencies installed")


def check_gpu():
    """Check GPU availability and VRAM."""
    import torch
    if not torch.cuda.is_available():
        print("[WARNING] CUDA not available — training will be VERY SLOW on CPU")
        print("Install CUDA toolkit from: https://developer.nvidia.com/cuda-downloads")
        input("Press Enter to continue anyway, or Ctrl+C to abort...")
        return False
    
    device = torch.cuda.get_device_name(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"[OK] GPU: {device}, VRAM: {vram_gb:.1f} GB")
    
    if vram_gb < 6:
        print(f"[WARNING] Only {vram_gb:.1f}GB VRAM. Recommend ≥8GB for 7B QLoRA.")
        print("Consider using a smaller model: Qwen/Qwen2.5-Coder-3B-Instruct")
    
    return True


def generate_data_if_missing():
    """Run the data generator if training data doesn't exist."""
    train_path = Path(DATA_DIR) / "saathi_cto_train.jsonl"
    if not train_path.exists():
        print("[INFO] Training data not found. Generating...")
        script_dir = Path(__file__).parent
        import subprocess
        result = subprocess.run(
            [sys.executable, str(script_dir / "generate_training_data.py")],
            capture_output=True, text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"[ERROR] Data generation failed:\n{result.stderr}")
            sys.exit(1)
    
    train_count = sum(1 for _ in open(train_path, encoding='utf-8'))
    print(f"[OK] Training data: {train_count} examples at {train_path}")
    return str(train_path), str(Path(DATA_DIR) / "saathi_cto_val.jsonl")


def load_and_prepare_model():
    """Load Qwen2.5-Coder-7B with 4-bit quantization and LoRA."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, TaskType

    print(f"\n[INFO] Loading tokenizer: {MODEL_ID}")
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
        padding_side="right",
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"[INFO] Loading model with 4-bit quantization (QLoRA)...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,  # Saves ~20% additional memory
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model.config.use_cache = False  # Required for gradient checkpointing

    # Enable gradient checkpointing before applying LoRA (saves VRAM)
    model.gradient_checkpointing_enable()

    print("[INFO] Applying LoRA adapters...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        **LORA_CONFIG,
    )
    model = get_peft_model(model, lora_config)
    
    trainable, total = sum(p.numel() for p in model.parameters() if p.requires_grad), \
                       sum(p.numel() for p in model.parameters())
    print(f"[OK] Trainable parameters: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    return model, tokenizer


def load_dataset(train_path: str, val_path: str):
    """Load JSONL datasets for training."""
    from datasets import load_dataset as hf_load_dataset
    
    data_files = {"train": train_path}
    if Path(val_path).exists():
        data_files["validation"] = val_path
    
    dataset = hf_load_dataset("json", data_files=data_files)
    print(f"[OK] Dataset loaded: {dataset}")
    return dataset


def format_chat_messages(example, tokenizer):
    """Format messages list into a single training string."""
    messages = example["messages"]
    
    # Use the model's built-in chat template
    try:
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )
    except Exception:
        # Fallback manual format if chat template not available
        parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                parts.append(f"<|im_start|>system\n{content}<|im_end|>")
            elif role == "user":
                parts.append(f"<|im_start|>user\n{content}<|im_end|>")
            elif role == "assistant":
                parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")
        text = "\n".join(parts) + "\n"
    
    return {"text": text}


def run_training(model, tokenizer, dataset, quick_test=False):
    """Run SFTTrainer fine-tuning."""
    from transformers import TrainingArguments
    from trl import SFTTrainer, DataCollatorForCompletionOnlyLM

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    # Prepare formatted dataset
    train_dataset = dataset["train"].map(
        lambda x: format_chat_messages(x, tokenizer),
        remove_columns=dataset["train"].column_names,
    )
    val_dataset = None
    if "validation" in dataset:
        val_dataset = dataset["validation"].map(
            lambda x: format_chat_messages(x, tokenizer),
            remove_columns=dataset["validation"].column_names,
        )

    config = dict(TRAINING_CONFIG)
    if quick_test:
        config["max_steps"] = 5
        config["num_train_epochs"] = 1
        config["eval_steps"] = 3
        config["save_steps"] = 5
        config["logging_steps"] = 1
        print("[INFO] Quick test mode: running only 5 steps")

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        **config,
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        args=training_args,
        max_seq_length=TRAINING_CONFIG["max_seq_length"],
        dataset_text_field="text",
    )

    print("\n[INFO] Starting training...")
    print(f"[INFO] Output: {OUTPUT_DIR}")
    print(f"[INFO] Epochs: {config.get('num_train_epochs', 'auto')}")
    print(f"[INFO] Max steps: {config.get('max_steps', -1)} (-1=use epochs)")
    print("[INFO] Press Ctrl+C to stop and save checkpoint\n")

    trainer.train()

    print(f"\n[INFO] Training complete. Saving final model...")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"[OK] Saved LoRA adapter to: {OUTPUT_DIR}")
    
    return OUTPUT_DIR


def merge_and_export_gguf(lora_output_dir: str):
    """Merge LoRA weights into base model and prepare for GGUF export."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    merged_dir = str(Path(lora_output_dir).parent / "saathi-cto-merged")
    Path(merged_dir).mkdir(parents=True, exist_ok=True)

    print(f"\n[INFO] Merging LoRA into base model...")
    print("[INFO] Loading base model (fp16, no quantization for merge)...")

    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(lora_output_dir, trust_remote_code=True)

    print("[INFO] Loading LoRA adapter and merging...")
    model = PeftModel.from_pretrained(base_model, lora_output_dir)
    model = model.merge_and_unload()

    print(f"[INFO] Saving merged model to: {merged_dir}")
    model.save_pretrained(merged_dir, safe_serialization=True)
    tokenizer.save_pretrained(merged_dir)

    print(f"[OK] Merged model saved. Now converting to GGUF...")
    print("[INFO] GGUF conversion requires llama.cpp. Instructions:")
    print(f"  1. Clone llama.cpp: git clone https://github.com/ggerganov/llama.cpp")
    print(f"  2. Convert: python llama.cpp/convert_hf_to_gguf.py {merged_dir} --outtype q4_k_m --outfile {GGUF_DIR}/saathi-cto.gguf")
    print(f"  3. Import to Ollama: ollama create saathi-cto -f fine_tune/Modelfile")
    
    # Write the Modelfile automatically
    modelfile_path = str(Path(__file__).parent / "Modelfile_trained")
    with open(modelfile_path, 'w') as f:
        f.write(f"FROM {GGUF_DIR}/saathi-cto.gguf\n\n")
        f.write('SYSTEM """\nYou are the expert CTO and lead developer of Saathi AI, ')
        f.write('a B2B SaaS therapeutic co-pilot platform built by RYL NEUROACADEMY PRIVATE LIMITED. ')
        f.write('You have complete knowledge of every file, every architectural decision, and every ')
        f.write('ML model in this codebase. Answer all questions with precise, file-level detail.\n"""\n\n')
        f.write("PARAMETER temperature 0.7\n")
        f.write("PARAMETER top_p 0.9\n")
        f.write("PARAMETER num_ctx 4096\n")
        f.write("PARAMETER stop \"<|im_end|>\"\n")
    print(f"[OK] Modelfile written to: {modelfile_path}")

    return merged_dir


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Qwen2.5-Coder-7B on Saathi AI knowledge")
    parser.add_argument("--quick-test", action="store_true", help="Run only 5 steps as smoke test")
    parser.add_argument("--skip-merge", action="store_true", help="Skip GGUF merge step")
    args = parser.parse_args()

    print("=" * 60)
    print("SAATHI AI — CTO Model Fine-tuning")
    print("=" * 60)

    # 1. Check dependencies
    check_dependencies()

    # 2. Check GPU
    has_gpu = check_gpu()

    # 3. Generate training data if missing
    train_path, val_path = generate_data_if_missing()

    # 4. Load model + LoRA
    model, tokenizer = load_and_prepare_model()

    # 5. Load dataset
    dataset = load_dataset(train_path, val_path)

    # 6. Train
    output_dir = run_training(model, tokenizer, dataset, quick_test=args.quick_test)

    # 7. Merge + GGUF (skip in quick test mode)
    if not args.quick_test and not args.skip_merge:
        import torch
        # Free GPU memory before merge
        del model
        torch.cuda.empty_cache()
        merge_and_export_gguf(output_dir)

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    if args.quick_test:
        print("Quick test passed! Run without --quick-test for full training.")
    else:
        print(f"LoRA adapter: {output_dir}")
        print(f"Next: Convert to GGUF and import to Ollama")
        print(f"See instructions above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
