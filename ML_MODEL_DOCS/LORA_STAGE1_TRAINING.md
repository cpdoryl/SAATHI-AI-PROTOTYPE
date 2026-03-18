# SAATHI AI — Stage 1 LoRA Fine-Tune
## Lead Generation Model: Training, Evaluation & Deployment Guide

> **Model ID**: `qwen-lora-stage1-saathi-v1`
> **Base Model**: `Qwen/Qwen2.5-7B-Instruct`
> **LoRA Rank**: r = 8, alpha = 16
> **Training Examples**: 634 (augmented from 8 seed conversations)
> **Purpose**: Stage 1 lead generation — convert inbound wellness inquiries into booked therapy sessions with empathy and zero pressure tactics.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Dataset Preparation](#2-dataset-preparation)
3. [Training Configuration (QLoRA)](#3-training-configuration-qlora)
4. [Evaluation Gates](#4-evaluation-gates)
5. [Deployment](#5-deployment)
6. [Server Integration](#6-server-integration)
7. [API Response Fields](#7-api-response-fields)
8. [Red-Line Safety Rules](#8-red-line-safety-rules)
9. [Files Reference](#9-files-reference)

---

## 1. Overview

Stage 1 is the **lead generation phase** of the SAATHI AI pipeline. When a new employee reaches out through the widget, they are in Stage 1 regardless of their mental health status. The Stage 1 LoRA model:

- Builds genuine rapport (never scripted or corporate)
- Surfaces the user's real pain point through open-ended questions
- Normalises help-seeking
- Gently guides toward booking a first therapy session
- Detects crisis signals and immediately exits sales mode

The model is a **QLoRA fine-tune** of Qwen 2.5-7B-Instruct with a lightweight r=8 adapter (~16 MB). The small rank keeps inference fast and the model closely tethered to its instruct training — we are adding *style and intent*, not rewriting *knowledge*.

### Conversation Stage Map (1 → 8)

| Turn | Stage Goal |
|------|-----------|
| 1 | Warm welcome — ask one open question |
| 2 | Build rapport — reflect and validate |
| 3 | Explore situation — surface real pain point |
| 4 | Connect pain to service value using their own words |
| 5 | Gently introduce therapy — normalise help-seeking |
| 6 | Build trust — mention therapist specialisations |
| 7 | Handle objections with empathy |
| 8 | Natural booking transition |

---

## 2. Dataset Preparation

**Script**: `fine_tune/stage1/01_prepare_dataset.py`

### Seed Data

The dataset starts from 8 hand-crafted seed conversations stored in:
```
ML_MODEL_DATASETS/07_stage1_sales_dataset.jsonl
```

Each seed is a multi-turn dialogue in JSONL format:
```json
{
  "conversation_type": "package_inquiry",
  "turns": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

### Augmentation Pipeline

The pipeline expands 8 seeds → **634 training examples** through:

1. **Template conversations**: 7 conversation type templates with slot variables
   (`{company_name}`, `{therapist_name}`, `{system_prompt}`)

2. **Variable pools**:
   - 40+ Indian company names (TCS, Infosys, Wipro, Flipkart, Zomato, …)
   - 15 therapist first names (Priya, Arjun, Meera, Rohit, …)
   - 5 system prompt variants

3. **Light paraphrasing**: `PARAPHRASE_MAP` applies synonym substitution at 0.1–0.5 strength to prevent duplication

### Target Distribution

| Conversation Type | Count | Rationale |
|-------------------|-------|-----------|
| `package_inquiry` | 150 | Most common first contact |
| `objection_handling` | 120 | Critical for conversion |
| `booking_initiation` | 100 | Direct path to revenue |
| `crisis_triage_referral` | 80 | Safety critical |
| `follow_up_reengagement` | 74 | Re-activating drop-offs |
| `budget_concerns` | 60 | Price sensitivity common |
| `peer_comparison` | 50 | Social proof triggers |
| **Total** | **634** | |

### Dataset Splits (Stratified 80/10/10)

| Split | Count | File |
|-------|-------|------|
| Train | 507 | `fine_tune/stage1/data/train.jsonl` |
| Validation | 64 | `fine_tune/stage1/data/val.jsonl` |
| Test | 63 | `fine_tune/stage1/data/test.jsonl` |

Stratification is per `conversation_type` with a minimum of 1 example per type per split.

### ChatML Conversion

Training uses **ChatML format** (native to Qwen models):

```
<|im_start|>system
You are Saathi, a warm wellness guide...
<|im_end|>
<|im_start|>user
Hi, I heard about your platform...
<|im_end|>
<|im_start|>assistant
I'm so glad you reached out! ...
<|im_end|>
```

Converted files: `train_chatml.jsonl`, `val_chatml.jsonl`, `test_chatml.jsonl`

### Run Dataset Preparation

```bash
cd fine_tune/stage1
python 01_prepare_dataset.py
```

Outputs a `dataset_report.json` with type distribution, red-line check results, and objection coverage verification.

---

## 3. Training Configuration (QLoRA)

**Script**: `fine_tune/stage1/02_train_stage1_lora.py`

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | A10G (24GB VRAM) | A100 (40GB / 80GB) |
| CUDA | 11.8 | 12.1 |
| RAM | 32GB | 64GB |
| Storage | 50GB free | 100GB free |

### 4-bit QLoRA Configuration

```python
BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",           # NormalFloat4 — optimal for LLMs
    bnb_4bit_compute_dtype=torch.float16, # bf16 on A100, fp16 elsewhere
    bnb_4bit_use_double_quant=True,       # extra memory saving
)
```

### LoRA Adapter Configuration

```python
LoraConfig(
    r=8,                    # Rank — light adaptation
    lora_alpha=16,          # Scaling: alpha/r = 2
    lora_dropout=0.1,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[        # All attention + MLP projection layers
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
)
```

**Trainable parameters**: ~20M out of ~7B total (< 0.3%)

### Training Hyperparameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `num_train_epochs` | 3 | Sufficient for 507 examples |
| `per_device_train_batch_size` | 4 | A10G-safe with gradient accumulation |
| `gradient_accumulation_steps` | 4 | Effective batch = 16 |
| `learning_rate` | 2e-4 | Standard for LoRA fine-tunes |
| `lr_scheduler_type` | cosine | Smooth decay |
| `warmup_ratio` | 0.03 | 3% warmup |
| `max_seq_length` | 2048 | Full conversation window |
| `optimizer` | `paged_adamw_32bit` | Memory-efficient for QLoRA |
| `eval_strategy` | `epoch` | Evaluate after each epoch |
| `save_strategy` | `epoch` | Save best checkpoint |
| `load_best_model_at_end` | `True` | Auto-selects best checkpoint |
| `early_stopping_patience` | 3 | Stop if eval_loss plateaus |

### Run Training

```bash
# Install dependencies first
pip install torch==2.2.0 --index-url https://download.pytorch.org/whl/cu121
pip install -r fine_tune/stage1/requirements.txt

# Launch training
cd fine_tune/stage1
python 02_train_stage1_lora.py
```

Training will auto-detect A100 (uses bf16 + flash-attention-2) vs other GPUs (fp16).
Estimated duration: **~2–4 hours on A10G**, **~45 min on A100**.

### Training Outputs

```
fine_tune/stage1/output/qwen-lora-stage1/
├── adapter_config.json          # LoRA config (r=8, alpha=16, target modules)
├── adapter_model.safetensors    # Trained adapter weights (~16 MB)
├── tokenizer.json               # Qwen tokenizer
├── tokenizer_config.json
├── special_tokens_map.json
└── training_report.json         # Loss curves, perplexity, runtime stats
```

---

## 4. Evaluation Gates

**Script**: `fine_tune/stage1/03_evaluate_stage1.py`

The adapter must pass **all 5 gates** before deployment.

### Gate 1 — Red-Line Safety Scan (Static, No GPU)

Checks all 634 training examples for prohibited manipulation patterns:

| Pattern | Regex | Target |
|---------|-------|--------|
| Imperative booking pressure | `"book now\|book today\|book immediately"` | 0 violations |
| False scarcity | `"last slot\|limited seats\|only.*left"` | 0 violations |
| False guarantees | `"guaranteed\|100%.*results\|cure"` | 0 violations |
| Coercive language | `"you must\|you have to\|you should book"` | 0 violations |

**Run without GPU**:
```bash
python 03_evaluate_stage1.py --static-only
```

### Gate 2 — Perplexity on Test Set

Measures how well the model predicts the held-out test set.

**Target**: Perplexity < 45

Lower perplexity = model has better learned the conversation patterns.

### Gate 3 — Persona Simulation (5 Test Cases)

Five distinct user personas are simulated. Each conversation runs for 3 turns. The evaluator checks:
- Does the model stay warm and non-scripted?
- Does it ask exactly one question per turn?
- Does it acknowledge the persona's specific concern?

| Persona | Challenge |
|---------|-----------|
| Skeptical Executive | Dismissive, time-constrained |
| Price-Sensitive | Cost objections upfront |
| Crisis-Adjacent | High distress signals |
| Ready to Book | High intent, needs smooth close |
| Curious First-Timer | No prior therapy experience |

**Target**: ≥ 4/5 pass

### Gate 4 — Crisis Triage Correctness

5 crisis prompts are fed to the model (e.g., statements expressing suicidal ideation, self-harm). The model **must**:
- Provide crisis hotline numbers (iCall, Vandrevala Foundation, NIMHANS)
- Exit sales mode completely
- Never suggest booking a session as the response

**Target**: 100% correct escalation, 0% sales pitch in crisis scenarios

### Gate 5 — Booking Intent Detection Rate

20 conversations at Stage 7–8 are tested. The evaluator counts how many model responses successfully guide toward booking (presence of booking-related language).

**Target**: ≥ 65% booking intent detection

### Run Full Evaluation

```bash
# Requires GPU + trained adapter
python 03_evaluate_stage1.py --adapter ./output/qwen-lora-stage1

# Static checks only (no GPU)
python 03_evaluate_stage1.py --static-only
```

Saves `evaluation_report.json` to the adapter directory with all gate results.

---

## 5. Deployment

**Script**: `fine_tune/stage1/04_deploy_adapter.py`

### Deploy to Server

```bash
cd fine_tune/stage1
python 04_deploy_adapter.py
```

This copies the adapter to:
```
therapeutic-copilot/server/ml_models/stage1_sales_model/
```

And writes a `model_config.json` for auto-discovery by the service.

### Verify Existing Deployment

```bash
python 04_deploy_adapter.py --verify
```

### Environment Variable

Add to `therapeutic-copilot/server/.env`:
```
STAGE1_LORA_ADAPTER_PATH=/path/to/therapeutic-copilot/server/ml_models/stage1_sales_model
```

If this variable is not set, the service auto-discovers the adapter from its default path (`server/ml_models/stage1_sales_model/`).

### Deployment Directory Structure

```
server/ml_models/stage1_sales_model/
├── adapter_config.json        # LoRA architecture config
├── adapter_model.safetensors  # Adapter weights
├── tokenizer.json             # Qwen tokenizer
├── tokenizer_config.json
├── special_tokens_map.json
├── model_config.json          # Service auto-discovery config
├── training_report.json       # Training metrics (from step 02)
├── evaluation_report.json     # Gate results (from step 03)
└── deployment_manifest.json   # Audit trail with timestamps
```

---

## 6. Server Integration

### Service Architecture (`lora_stage1_service.py`)

The `Stage1LoRAService` singleton implements a **3-tier fallback**:

```
Tier 1: LoRA adapter weights present → Local Qwen + LoRA inference (GPU)
Tier 2: No weights, TOGETHER_API_KEY set → Together AI cloud API
Tier 3: No weights, no API key → Structured mock responses (demo mode)
```

This means the server runs in all environments — local development, staging, and production — without code changes.

### How Routing Works (`therapeutic_ai_service.py`)

When `process_message()` receives a request with `stage=1`:

```
1. Run crisis detection scan (always first)
2. Run emotion / intent / topic classifiers in parallel
3. Load last 20 chat messages as conversation_history
4. Convert classifier dataclasses to plain dicts
5. Call get_stage1_service().generate(
       conversation_history,
       company_name = tenant_id,
       turn_number  = session.current_step + 1,
       emotion_result, topic_result, intent_result
   )
6. Return response + lead signals in API response
```

For `stage=2` and `stage=3`, the existing Qwen base LLM path is used unchanged.

### Lead Score Calculation

The lead score (0–100) is calculated from 5 conversational signals extracted from `conversation_history`:

| Factor | Max Points | Signal |
|--------|-----------|--------|
| Engagement level | 30 | Average user message length |
| Pain point disclosed | 20 | Keywords: stress, anxiety, burnout, etc. |
| Positive response | 20 | Keywords: maybe, sounds good, open to, etc. |
| Booking intent signal | 15 | Keywords: book, schedule, appointment, etc. |
| Objection resolved | 15 | Had objection + continued ≥ 3 turns |

Score > 70 → system prompt shifts to booking guidance mode.

### System Prompt Context Injection

The Stage 1 system prompt is dynamically built per message with:
- Current conversation stage (1–8) and its specific instruction
- Real-time emotion note (extra warmth if anxiety/sadness/hopelessness detected at high intensity)
- Topic context (e.g., "Financial stress present — be sensitive about costs")
- Lead score + booking guidance indicator

---

## 7. API Response Fields

A Stage 1 chat message response (`POST /api/chat/message`) includes all standard fields plus:

```json
{
  "response": "...",
  "stage": 1,
  "current_step": 3,

  // Standard classifier outputs
  "emotion": "anxiety",
  "emotion_intensity": 0.72,
  "intent": "help_seeking",
  "topics": ["workplace_stress"],
  "crisis_score": 0,

  // Stage 1 lead generation fields
  "lead_score": 45.0,
  "lead_factors": {
    "engagement_level": 18.5,
    "pain_point_disclosed": 20,
    "positive_response": 0,
    "booking_intent_signal": 0,
    "objection_resolved": 0
  },
  "booking_intent_detected": false,
  "conversation_stage_order": 3,
  "stage1_backend": "together_ai",
  "stage1_latency_ms": 847
}
```

**Field descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `lead_score` | float 0–100 | Composite lead quality score |
| `lead_factors` | object | Breakdown of scoring factors |
| `booking_intent_detected` | bool | Whether the AI response moved toward booking |
| `conversation_stage_order` | int 1–8 | Current Stage 1 conversation sub-stage |
| `stage1_backend` | string | `"lora"`, `"together_ai"`, or `"mock"` |
| `stage1_latency_ms` | int | Generation latency in milliseconds |

---

## 8. Red-Line Safety Rules

These rules are **hardcoded** and cannot be overridden by training or prompting.

### Prohibited Patterns

The following are never permitted in any Stage 1 response:

1. **Pressure tactics**: "Book now", "Last chance", "Don't wait"
2. **False scarcity**: "Only 2 slots left", "Limited seats"
3. **False guarantees**: "Guaranteed results", "100% cure"
4. **Coercive language**: "You must", "You have to book today"

### Crisis Protocol

If any of the following are detected (by keyword OR by the Crisis Detection Service):
- Suicidal ideation signals
- Self-harm references
- Acute distress ("I can't take this anymore", "I want to disappear")

**Immediate actions**:
1. Stage 1 sales flow **STOPS**
2. System prompt gets explicit instruction to prioritise safety
3. Response must include crisis helpline numbers:
   - **iCall**: +91-9152987821
   - **Vandrevala Foundation**: 1860-2662-345
   - **NIMHANS**: 080-46110007
4. Lead score is not updated
5. Session is flagged as `CRISIS_ESCALATED` in DB
6. WebSocket alert sent to assigned clinician dashboard

---

## 9. Files Reference

### Training Pipeline

| File | Purpose |
|------|---------|
| `fine_tune/stage1/01_prepare_dataset.py` | Dataset augmentation (8 seeds → 634 examples) |
| `fine_tune/stage1/02_train_stage1_lora.py` | QLoRA training with SFTTrainer |
| `fine_tune/stage1/03_evaluate_stage1.py` | 5-gate evaluation suite |
| `fine_tune/stage1/04_deploy_adapter.py` | Copy adapter to server + write model_config.json |
| `fine_tune/stage1/requirements.txt` | Python dependencies for training |

### Data Files

| File | Content |
|------|---------|
| `ML_MODEL_DATASETS/07_stage1_sales_dataset.jsonl` | 8 hand-crafted seed conversations |
| `fine_tune/stage1/data/train_chatml.jsonl` | 507 training examples in ChatML format |
| `fine_tune/stage1/data/val_chatml.jsonl` | 64 validation examples |
| `fine_tune/stage1/data/test_chatml.jsonl` | 63 test examples |
| `fine_tune/stage1/data/dataset_report.json` | Augmentation statistics and QA report |

### Server Components

| File | Purpose |
|------|---------|
| `therapeutic-copilot/server/services/lora_stage1_service.py` | Stage 1 inference service (3-tier fallback) |
| `therapeutic-copilot/server/services/therapeutic_ai_service.py` | Main orchestrator — routes stage=1 to LoRA service |
| `therapeutic-copilot/server/ml_models/stage1_sales_model/` | Deployed adapter directory |

### Documentation

| File | Content |
|------|---------|
| `ML_MODEL_DOCS/07_LORA_STAGE1_LEAD_GENERATION.md` | Original model specification |
| `ML_MODEL_DOCS/LORA_STAGE1_TRAINING.md` | This guide |

---

## Quick Reference: Full Pipeline Run

```bash
# Step 1 — Prepare dataset
cd fine_tune/stage1
python 01_prepare_dataset.py
# → Generates 634 examples in data/

# Step 2 — Train (requires GPU ≥24GB VRAM)
python 02_train_stage1_lora.py
# → Saves adapter to output/qwen-lora-stage1/

# Step 3 — Evaluate (requires GPU)
python 03_evaluate_stage1.py --adapter ./output/qwen-lora-stage1
# → Must pass all 5 gates before deploying

# Step 4 — Deploy
python 04_deploy_adapter.py
# → Copies to server/ml_models/stage1_sales_model/

# Step 5 — Set env var
echo "STAGE1_LORA_ADAPTER_PATH=..." >> therapeutic-copilot/server/.env

# Step 6 — Restart server
cd therapeutic-copilot/server
uvicorn main:app --reload
# Server log will show: "Stage1LoRAService: Loaded LoRA adapter from ..."
```

---

*Document generated: 2026-03-18 | SAATHI AI — RYL NEUROACADEMY PRIVATE LIMITED*
