"""
Unsloth Fine-Tuning Script — Llama-3-8B
========================================
Optimised for 8 GB VRAM (RTX 5060 Laptop GPU) using:
  - 4-bit QLoRA quantisation via Unsloth
  - Gradient checkpointing
  - Mixed precision (bf16/fp16)

Usage:
  python train_unsloth_llama3.py
  python train_unsloth_llama3.py --dataset path/to/dataset.jsonl --output ./output --epochs 3

Dataset format (dataset.jsonl) — each line is ONE of:
  {"text": "### Instruction:\n...\n\n### Response:\n..."}           # plain text
  {"instruction": "...", "input": "...", "output": "..."}           # alpaca format
  {"messages": [{"role":"user","content":"..."}, ...]}              # chat format
"""

import argparse
import os
import sys
import json

# ── Argument parsing ──────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Unsloth Llama-3-8B fine-tuner")
parser.add_argument("--model",    default="unsloth/Meta-Llama-3-8B-Instruct-bnb-4bit",
                    help="HuggingFace model ID or local path")
parser.add_argument("--dataset",  default="dataset.jsonl",
                    help="Path to local JSONL dataset file")
parser.add_argument("--output",   default="./output/llama3_finetuned",
                    help="Output directory for trained model")
parser.add_argument("--gguf_dir", default="./output/gguf",
                    help="Output directory for exported GGUF model")
parser.add_argument("--epochs",   type=int,   default=3)
parser.add_argument("--max_seq",  type=int,   default=2048)
parser.add_argument("--batch",    type=int,   default=2,
                    help="Per-device train batch size (reduce to 1 if OOM)")
parser.add_argument("--grad_acc", type=int,   default=4,
                    help="Gradient accumulation steps (effective batch = batch * grad_acc)")
parser.add_argument("--lora_r",   type=int,   default=16,
                    help="LoRA rank (8 = less VRAM, 32 = more capacity)")
parser.add_argument("--gguf_quant", default="q4_k_m",
                    choices=["q4_k_m","q5_k_m","q8_0","f16"],
                    help="GGUF quantisation method for Ollama export")
args = parser.parse_args()

# ── Sanity checks before heavy imports ───────────────────────────────────────
if not os.path.exists(args.dataset):
    print(f"[ERROR] Dataset not found: {args.dataset}")
    print("  Place your dataset.jsonl next to this script or pass --dataset <path>")
    sys.exit(1)

# ── GPU check ─────────────────────────────────────────────────────────────────
import torch
if not torch.cuda.is_available():
    print("[ERROR] No CUDA GPU detected. Aborting — training requires a GPU.")
    sys.exit(1)

gpu_name  = torch.cuda.get_device_name(0)
gpu_vram  = torch.cuda.get_device_properties(0).total_memory / 1e9
print(f"[GPU] {gpu_name}  |  VRAM: {gpu_vram:.1f} GB")
print(f"[CFG] Model       : {args.model}")
print(f"[CFG] Dataset     : {args.dataset}")
print(f"[CFG] Output      : {args.output}")
print(f"[CFG] GGUF dir    : {args.gguf_dir}")
print(f"[CFG] Epochs      : {args.epochs}")
print(f"[CFG] Max seq len : {args.max_seq}")
print(f"[CFG] Batch size  : {args.batch}  (grad acc: {args.grad_acc})")
print(f"[CFG] LoRA rank   : {args.lora_r}")
print(f"[CFG] GGUF quant  : {args.gguf_quant}")
print()

# ── Imports ───────────────────────────────────────────────────────────────────
try:
    from unsloth import FastLanguageModel
    from unsloth.chat_templates import get_chat_template
except ImportError:
    print("[ERROR] Unsloth not installed. Run: pip install unsloth")
    print("  Or use the automated setup: .\\train.ps1 --setup")
    sys.exit(1)

from datasets import load_dataset, Dataset
from trl import SFTTrainer, SFTConfig
from transformers import TrainingArguments

# ── Load model with Unsloth 4-bit QLoRA ──────────────────────────────────────
print("[STEP 1/5] Loading base model with 4-bit quantisation...")

dtype = None  # auto-detect: bf16 on Ampere+, fp16 otherwise
use_4bit = True

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name       = args.model,
    max_seq_length   = args.max_seq,
    dtype            = dtype,
    load_in_4bit     = use_4bit,
    device_map       = "cuda",       # always use GPU
)

# ── Apply LoRA adapters ───────────────────────────────────────────────────────
print("[STEP 2/5] Applying LoRA adapters...")

model = FastLanguageModel.get_peft_model(
    model,
    r                   = args.lora_r,
    target_modules      = ["q_proj", "k_proj", "v_proj", "o_proj",
                           "gate_proj", "up_proj", "down_proj"],
    lora_alpha          = args.lora_r * 2,          # standard: 2× rank
    lora_dropout        = 0.05,
    bias                = "none",
    use_gradient_checkpointing = "unsloth",          # Unsloth's memory-efficient impl
    random_state        = 42,
    use_rslora          = False,
)

print(f"[INFO] Trainable parameters: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

# ── Load & preprocess dataset ─────────────────────────────────────────────────
print(f"[STEP 3/5] Loading dataset from {args.dataset}...")

# Set chat template for Llama-3 instruction style
tokenizer = get_chat_template(tokenizer, chat_template="llama-3")

EOS = tokenizer.eos_token

def _alpaca_to_text(example):
    """Convert alpaca {instruction, input, output} → text."""
    prompt = example.get("instruction", "").strip()
    inp    = example.get("input", "").strip()
    out    = example.get("output", "").strip()
    if inp:
        return {"text": f"### Instruction:\n{prompt}\n\n### Input:\n{inp}\n\n### Response:\n{out}{EOS}"}
    return {"text": f"### Instruction:\n{prompt}\n\n### Response:\n{out}{EOS}"}

def _chat_to_text(example):
    """Convert messages list → text via tokenizer chat template."""
    messages = example.get("messages", [])
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    return {"text": text}

# Detect format from first record
with open(args.dataset, "r", encoding="utf-8") as fh:
    first = json.loads(fh.readline())

raw_dataset = load_dataset("json", data_files=args.dataset, split="train")
total = len(raw_dataset)
print(f"[INFO] Loaded {total} examples")

if "text" in first:
    dataset = raw_dataset
    print("[INFO] Format: plain text (using 'text' field directly)")
elif "messages" in first:
    dataset = raw_dataset.map(_chat_to_text, batched=False)
    print("[INFO] Format: chat messages (applying Llama-3 chat template)")
elif "instruction" in first:
    dataset = raw_dataset.map(_alpaca_to_text, batched=False)
    print("[INFO] Format: Alpaca (instruction / input / output)")
else:
    print(f"[ERROR] Unrecognised dataset format. Expected keys: 'text', 'messages', or 'instruction'")
    print(f"  Found keys: {list(first.keys())}")
    sys.exit(1)

# ── Training ──────────────────────────────────────────────────────────────────
print("[STEP 4/5] Starting training...")

os.makedirs(args.output, exist_ok=True)

# Determine precision flags
use_bf16 = torch.cuda.is_bf16_supported()
use_fp16 = not use_bf16

trainer = SFTTrainer(
    model            = model,
    tokenizer        = tokenizer,
    train_dataset    = dataset,
    dataset_text_field = "text",
    max_seq_length   = args.max_seq,
    dataset_num_proc = 2,
    packing          = False,           # set True to pack short sequences (faster, more VRAM)
    args             = TrainingArguments(
        per_device_train_batch_size   = args.batch,
        gradient_accumulation_steps   = args.grad_acc,
        warmup_steps                  = max(1, int(total * args.epochs * 0.05 / (args.batch * args.grad_acc))),
        num_train_epochs              = args.epochs,
        learning_rate                 = 2e-4,
        fp16                          = use_fp16,
        bf16                          = use_bf16,
        logging_steps                 = 10,
        optim                         = "adamw_8bit",   # bitsandbytes 8-bit Adam = less VRAM
        weight_decay                  = 0.01,
        lr_scheduler_type             = "cosine",
        seed                          = 42,
        output_dir                    = args.output,
        save_strategy                 = "epoch",
        save_total_limit              = 2,
        report_to                     = "none",         # disable wandb/tensorboard by default
    ),
)

# Show GPU usage before training
torch.cuda.reset_peak_memory_stats()
train_result = trainer.train()

peak_vram = torch.cuda.max_memory_reserved() / 1e9
print(f"\n[INFO] Peak VRAM used : {peak_vram:.2f} GB")
print(f"[INFO] Training steps : {train_result.global_step}")
print(f"[INFO] Final loss     : {train_result.training_loss:.4f}")

# Save LoRA adapter weights
model.save_pretrained(args.output)
tokenizer.save_pretrained(args.output)
print(f"[INFO] LoRA adapter saved to: {args.output}")

# ── Export to GGUF for Ollama ─────────────────────────────────────────────────
print(f"\n[STEP 5/5] Exporting to GGUF ({args.gguf_quant})...")

os.makedirs(args.gguf_dir, exist_ok=True)

# Unsloth merges LoRA + base and exports directly to GGUF
model.save_pretrained_gguf(
    save_directory      = args.gguf_dir,
    tokenizer           = tokenizer,
    quantization_method = args.gguf_quant,
)

# Find the generated .gguf file
gguf_files = [f for f in os.listdir(args.gguf_dir) if f.endswith(".gguf")]
if gguf_files:
    gguf_path = os.path.join(args.gguf_dir, gguf_files[0])
    print(f"\n[SUCCESS] GGUF model ready: {gguf_path}")
    print(f"  Size: {os.path.getsize(gguf_path) / 1e9:.2f} GB")
    print()
    print("─────────────────────────────────────────────────")
    print("  Load into Ollama:")
    print(f'    echo FROM {gguf_path} > Modelfile')
    print(f'    ollama create saath-llama3 -f Modelfile')
    print(f'    ollama run saath-llama3')
    print("─────────────────────────────────────────────────")
else:
    print(f"[WARNING] No .gguf file found in {args.gguf_dir} — check Unsloth logs above")

print("\n[DONE] Training complete!")
