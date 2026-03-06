# SAATHI AI — ML Pipeline

## Overview

Fine-tunes Qwen 2.5-7B-Instruct with LoRA adapters on 3,651 therapeutic conversations.

## Dataset Split

| Adapter | Stage | Rank | Training Examples | Purpose |
|---------|-------|------|-------------------|---------|
| stage1-r8.gguf | Lead Generation | r=8 | 634 | Booking conversion, FAQ, lead qualification |
| stage2-r16.gguf | Therapeutic | r=16 | 3,017 | 11-step therapy, CBT/DBT, meta-model |

## Training Infrastructure

- **GPU**: NVIDIA A100 40GB (recommended) or RTX 3090 24GB
- **Training time**: ~4h (Stage 1) + ~12h (Stage 2)
- **Framework**: HuggingFace PEFT + Transformers + BitsAndBytes (4-bit QLoRA)

## Inference (Production)

Adapters are exported to GGUF format and served by llama.cpp on E2E Networks Mumbai:
- Base: `Qwen2.5-7B-Instruct.Q4_K_M.gguf`
- Stage 1 adapter: `/models/lora-adapters/stage1-r8.gguf`
- Stage 2 adapter: `/models/lora-adapters/stage2-r16.gguf`

## Usage

```bash
cd therapeutic-copilot/ml_pipeline

# Stage 1 training
python train_lora.py --stage 1 --data data/stage1_conversations.jsonl

# Stage 2 training
python train_lora.py --stage 2 --data data/stage2_conversations.jsonl
```

## Data Format

```json
{"instruction": "...", "input": "Patient: ...", "output": "Saathi: ..."}
```
