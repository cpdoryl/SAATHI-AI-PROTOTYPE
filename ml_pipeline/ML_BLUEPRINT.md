# SAATHI AI — ML/AI Blueprint
## LoRA Fine-tuning + Inference Pipeline
### Version: 1.0 | Date: 2026-03-08 | Status: In Progress

---

## PURPOSE
This blueprint defines the complete ML pipeline for SAATHI AI — from raw
conversation data to deployed therapeutic AI models. The agent reads this
before any ML/AI task.

---

## 1. MODEL ARCHITECTURE OVERVIEW

```
Base Model: Qwen 2.5-7B (GGUF Q4_K_M quantized for production)
    │
    ├── Stage 1 LoRA Adapter (r=8)
    │   Purpose: Lead generation — empathetic intake conversations
    │   Training examples: 634
    │   Target: Convert LEAD patients to ACTIVE
    │
    └── Stage 2 LoRA Adapter (r=16)
        Purpose: Therapeutic co-pilot — structured CBT protocol
        Training examples: 3,017
        Target: Guide patient through 11-step CBT program
```

---

## 2. TRAINING DATA REQUIREMENTS

**You must provide datasets before training can begin.**

### Stage 1 Dataset — Lead Generation (634 conversations)
**File**: `ml_pipeline/data/stage1_leads.jsonl`
**Format**:
```jsonl
{"messages": [{"role": "user", "content": "I've been feeling very anxious lately"}, {"role": "assistant", "content": "I hear you — anxiety can feel overwhelming. Can you tell me a bit more about when these feelings started?"}]}
{"messages": [{"role": "user", "content": "I don't know if therapy is right for me"}, {"role": "assistant", "content": "That's a completely understandable feeling. Many people feel uncertain at first. What made you reach out today?"}]}
```
**Content requirements**:
- First-contact conversations (patient reaches out for first time)
- Empathetic, non-clinical language
- Goal: build rapport + gather presenting problem
- Short exchanges (3–8 turns)
- Cultural context: Indian patients (mention family pressures, work stress, arranged marriage, etc.)
- Mix of English, Hinglish (English + Hindi code-switching)
- Avoid clinical diagnoses in Stage 1 responses

### Stage 2 Dataset — Therapeutic Protocol (3,017 conversations)
**File**: `ml_pipeline/data/stage2_therapy.jsonl`
**Format**: Same as Stage 1 (multi-turn)
**Content requirements**:
- Full CBT session conversations (11 structured steps)
- Each conversation should map to one or more of the 11 steps:
  1. Rapport building
  2. Problem identification
  3. Thought monitoring
  4. Cognitive restructuring
  5. Behavioral activation
  6. Relaxation techniques
  7. Problem-solving
  8. Interpersonal effectiveness
  9. Mindfulness introduction
  10. Relapse prevention
  11. Session closure
- Longer exchanges (10–25 turns)
- Clinician-level therapeutic responses
- Include examples of handling: depression, anxiety, OCD, PTSD, relationship issues
- Cultural sensitivity: joint family dynamics, career pressure, gender roles in Indian context

### Stage 3 Dataset — Dropout Re-engagement (optional, 200+ conversations)
**File**: `ml_pipeline/data/stage3_reengagement.jsonl`
**Content**: Re-engagement messages after 7/14/30 days of patient inactivity

### Data Quality Requirements
- All conversations must be anonymized (no real names, phone numbers, locations)
- Balanced across presenting problems (not all depression)
- Balanced across demographics (gender, age group, urban/rural)
- Crisis conversations must NOT be in training data (use rule-based system for crisis)
- Minimum 60/20/20 train/val/test split

---

## 3. DATA PREPARATION PIPELINE

### Step 1: Data Collection (HUMAN TASK — you provide data)
Ask: "Please provide conversation examples in the format above"

### Step 2: Data Cleaning (`ml_pipeline/scripts/clean_data.py`)
```python
# Check format validity (every item has "messages" key)
# Remove duplicates (exact match on first user message)
# Remove conversations shorter than 3 turns
# Remove conversations with PII (regex: phone numbers, emails, Aadhaar)
# Tokenize and check max length (filter > 2048 tokens)
```

### Step 3: Dataset Balance Check (`ml_pipeline/scripts/check_balance.py`)
```python
# Count by: topic (depression/anxiety/OCD/PTSD/relationship/other)
# Count by: conversation length (short 3-8 / medium 9-15 / long 16+)
# Count by: language (English / Hinglish / mixed)
# Report imbalances
# Target: no category < 10% of total
```

### Step 4: Train/Val/Test Split (`ml_pipeline/scripts/split_data.py`)
```python
# 60% train, 20% validation, 20% test
# Stratified by topic category
# Output: stage1_train.jsonl, stage1_val.jsonl, stage1_test.jsonl
```

### Step 5: Quality Evaluation (`ml_pipeline/scripts/evaluate_data.py`)
```python
# Metrics per sample:
# - Therapeutic alignment score (does response match CBT principles?)
# - Empathy score (does response acknowledge patient emotion?)
# - Safety score (does response avoid harmful advice?)
# Flag samples scoring < 0.5 for manual review
```

---

## 4. TRAINING PIPELINE (`ml_pipeline/train_lora.py`)

**Current status: 100% pseudocode — needs full implementation**

### Required Libraries
```bash
pip install transformers==4.44.0 peft==0.12.0 trl==0.9.4 \
            bitsandbytes==0.43.0 datasets==2.21.0 accelerate==0.33.0 \
            torch==2.3.1 sentencepiece wandb
```

### Full Implementation Target
```python
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer
from datasets import load_dataset
import bitsandbytes as bnb
import torch

LORA_CONFIGS = {
    "stage1": LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        task_type=TaskType.CAUSAL_LM,
    ),
    "stage2": LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        task_type=TaskType.CAUSAL_LM,
    ),
}

def train(stage: str, data_path: str):
    # 1. Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct")

    # 2. Load model in 4-bit quantization (QLoRA)
    model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen2.5-7B-Instruct",
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        device_map="auto",
    )

    # 3. Apply LoRA
    model = get_peft_model(model, LORA_CONFIGS[stage])
    model.print_trainable_parameters()

    # 4. Load dataset
    dataset = load_dataset("json", data_files={"train": f"{data_path}_train.jsonl",
                                                "validation": f"{data_path}_val.jsonl"})

    # 5. Training args
    args = TrainingArguments(
        output_dir=f"./outputs/{stage}",
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        bf16=True,
        logging_steps=10,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        report_to="wandb",
    )

    # 6. Train
    trainer = SFTTrainer(
        model=model,
        args=args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        tokenizer=tokenizer,
        max_seq_length=2048,
    )
    trainer.train()

    # 7. Save adapter
    model.save_pretrained(f"./adapters/{stage}_adapter")
    tokenizer.save_pretrained(f"./adapters/{stage}_adapter")
```

---

## 5. MODEL CONVERSION PIPELINE

### HuggingFace → GGUF for llama.cpp

```bash
# Step 1: Merge LoRA adapter into base model
python merge_lora.py \
  --base Qwen/Qwen2.5-7B-Instruct \
  --adapter ./adapters/stage2_adapter \
  --output ./merged/saathi-stage2

# Step 2: Convert to GGUF
python llama.cpp/convert_hf_to_gguf.py ./merged/saathi-stage2 \
  --outfile ./models/saathi-stage2-q4.gguf \
  --outtype q4_k_m

# Step 3: Verify GGUF
llama-cli -m ./models/saathi-stage2-q4.gguf \
  -p "Patient: I'm feeling very sad today.\nTherapist:" \
  -n 200
```

---

## 6. MODEL EVALUATION

### Automated Metrics (`ml_pipeline/scripts/evaluate_model.py`)

| Metric | Tool | Target |
|--------|------|--------|
| Perplexity | HuggingFace `evaluate` | < 8.0 |
| BLEU-4 (vs test set) | sacrebleu | > 0.15 |
| ROUGE-L | rouge-score | > 0.35 |
| Therapeutic alignment | Custom classifier | > 0.80 |
| Safety (no harmful content) | LlamaGuard | 100% |
| Response latency (GGUF) | benchmark script | < 3s first token |

### Human Evaluation Checklist (manual review)
- [ ] Does response acknowledge patient emotion?
- [ ] Is response culturally appropriate for Indian context?
- [ ] Does response avoid giving medical diagnoses?
- [ ] Does response follow the correct CBT step for the session stage?
- [ ] Is response safe? (No instructions for self-harm, no toxic content)

---

## 7. DEPLOYMENT INTO APP

Once models trained + converted to GGUF:

1. Place GGUF file at path set in `.env`:
   ```
   LLAMA_CPP_PYTHON_MODEL_PATH=/models/saathi-stage2-q4.gguf
   ```

2. `QwenInferenceService` automatically uses native llama-cpp-python path
   when this env var is set (already implemented in `qwen_inference.py`)

3. LoRA adapter switching per stage: `lora_model_service.py`
   needs the hot-swap API call completed (TASK-BE-07)

---

## 8. REQUIRED FILES TO CREATE

| File | Purpose | Status |
|------|---------|--------|
| `ml_pipeline/data/stage1_leads.jsonl` | Stage 1 training data | **NEEDS DATA FROM USER** |
| `ml_pipeline/data/stage2_therapy.jsonl` | Stage 2 training data | **NEEDS DATA FROM USER** |
| `ml_pipeline/train_lora.py` | Real training script | Replace pseudocode |
| `ml_pipeline/scripts/clean_data.py` | Data cleaning | CREATE |
| `ml_pipeline/scripts/check_balance.py` | Balance analysis | CREATE |
| `ml_pipeline/scripts/split_data.py` | Train/val/test split | CREATE |
| `ml_pipeline/scripts/evaluate_data.py` | Data quality check | CREATE |
| `ml_pipeline/scripts/evaluate_model.py` | Model evaluation | CREATE |
| `ml_pipeline/scripts/merge_lora.py` | Merge adapter into base | CREATE |
| `ml_pipeline/requirements-ml.txt` | ML dependencies | CREATE |

---

## 9. COMPLETION CRITERIA

ML pipeline is complete when:
- [ ] `stage1_leads.jsonl` has 634+ samples (provided by human)
- [ ] `stage2_therapy.jsonl` has 3,017+ samples (provided by human)
- [ ] Data cleaning passes with 0 PII-flagged samples
- [ ] Balance check shows no category < 10%
- [ ] `train_lora.py` runs end-to-end without errors
- [ ] Stage 1 adapter saved to `adapters/stage1_adapter/`
- [ ] Stage 2 adapter saved to `adapters/stage2_adapter/`
- [ ] GGUF models pass perplexity < 8.0
- [ ] Safety evaluation: 100% pass on test set
- [ ] Model loaded in app: `LLAMA_CPP_PYTHON_MODEL_PATH` set + server starts
- [ ] End-to-end chat test passes with GGUF model

---

## 10. DATA REQUEST TO USER

**Before ML work can start, provide:**

> "I need conversation datasets for training. Please provide or share:
> 1. **Stage 1** (634 examples): First-contact conversations between a patient
>    and a therapist. Patient: presents problem. Therapist: empathetic response.
>    Can be from existing chat logs, anonymized clinical transcripts, or synthetically
>    generated with your guidance.
>
> 2. **Stage 2** (3,017 examples): Full therapy session transcripts (10-25 turns each)
>    following CBT structure. Indian cultural context preferred.
>
> Format: plain text or JSONL (I'll convert any format you provide).
> Privacy: ensure no real patient names/contacts are included."
