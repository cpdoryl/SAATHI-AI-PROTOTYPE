# Model Document 07: LoRA Stage 1 — Lead Generation & Sales Conversation Model
## Saathi AI Therapeutic Co-Pilot Platform

---

## Table of Contents
1. [Overview & Motivation](#1-overview--motivation)
2. [Why We Chose This Model Architecture](#2-why-we-chose-this-model-architecture)
3. [Schema Design](#3-schema-design)
4. [Data Preparation](#4-data-preparation)
5. [Data Balance Strategy](#5-data-balance-strategy)
6. [Dataset Splits: Training, Validation, Testing](#6-dataset-splits-training-validation-testing)
7. [Dataset Evaluation & Quality Checks](#7-dataset-evaluation--quality-checks)
8. [Training Strategy](#8-training-strategy)
9. [Step-by-Step Training Process](#9-step-by-step-training-process)
10. [Model Evaluation](#10-model-evaluation)
11. [Downloading & Saving Weights](#11-downloading--saving-weights)
12. [Integrating Trained Weights into the App Workflow](#12-integrating-trained-weights-into-the-app-workflow)
13. [Building Prompt Context with Model Output](#13-building-prompt-context-with-model-output)

---

## 1. Overview & Motivation

### What It Does
The **Stage 1 LoRA model** is a fine-tuned conversational LLM specialized for the **pre-appointment, lead generation phase** of the Saathi platform. It engages prospective clients (B2B employees accessing the platform through their employer's wellness program), builds rapport, surfaces their needs and pain points, presents the value of therapy, handles objections, and guides them toward booking their first session.

This is NOT a general chatbot. It is a **neuromarketing-optimized therapeutic lead conversion model** trained on the specific conversation patterns of mental health service intake specialists.

### Business Context
In the B2B SaaS mental health model:
1. Company purchases Saathi for their employees
2. Employee lands on the chat widget
3. **Stage 1**: AI engages employee, understands their situation, and converts them to a booked appointment
4. **Stage 2**: Post-booking, AI operates as therapeutic co-pilot during sessions

Stage 1's success is measured in booking conversion rate. The model must be empathetic (not pushy), clinically-informed, and commercially effective — a rare combination that requires fine-tuning on specialist data.

### Scope
- **Input**: Conversation history (system + user + assistant turns in ChatML format)
- **Output**: Next assistant turn (conversational response)
- **Base Model**: Qwen/Qwen2.5-7B-Instruct
- **Dataset Size**: 634 examples (each a full conversation of 6–12 turns)
- **LoRA Rank**: r=8 (light, fast, efficient)

---

## 2. Why We Chose This Model Architecture

### Architecture: Qwen2.5-7B-Instruct + LoRA (r=8)

#### Why Qwen2.5-7B-Instruct as Base?

| Property | Value |
|----------|-------|
| Parameters | 7.6B |
| Context window | 128K tokens |
| Instruction following | Excellent (Instruct variant) |
| Multilingual | Strong Hindi/Hinglish support |
| License | Apache 2.0 (commercial use allowed) |
| Size (quantized) | ~4GB at 4-bit |
| Inference on consumer GPU | Yes (RTX 3090/4090) |

**Key reasons for Qwen2.5-7B:**

1. **Multilingual capability**: Indian users frequently switch between English and Hindi (Hinglish). Qwen2.5 has stronger South Asian language support than LLaMA-3 or Mistral on Hindi benchmarks.

2. **Instruction-tuned base**: The Instruct variant already understands conversation structure, system prompts, and role-following — critical for Stage 1 sales conversations.

3. **Commercial license**: Apache 2.0 allows unrestricted commercial use, which is essential for a B2B SaaS product.

4. **Context window (128K)**: Allows full conversation history even in long sessions.

5. **Strong reasoning**: 7B parameter model with Qwen's architectural improvements outperforms many larger models on conversational coherence.

#### Why LoRA (Low-Rank Adaptation)?

Full fine-tuning of 7.6B parameters requires:
- ~150GB of VRAM (for BF16 + optimizer states)
- Multiple H100 GPUs
- Days of training time

LoRA at rank=8 for Stage 1:
- Trains only ~4.7M parameters (0.06% of total)
- Requires 1x A100 40GB (or 2x RTX 4090)
- Completes in ~2 hours
- Retains all general knowledge from base model
- Adds domain-specific sales/therapeutic vocabulary and conversation patterns

#### Why Rank=8 (Light) for Stage 1?
Stage 1 is a relatively constrained task:
- Fixed 8-step conversation flow
- Well-defined objection handling patterns
- Specific vocabulary (therapy packages, pricing, booking)
- 634 training examples (smaller dataset)

A low-rank adaptation (r=8) is sufficient. Stage 2 (therapeutic support) uses r=16 due to its greater complexity.

#### Why NOT GPT-4 for Stage 1?
- Cost: At scale (10K+ conversations/month), GPT-4 costs would be prohibitive
- Customization: LoRA-trained model embeds Saathi's specific packages, pricing, and conversation style — impossible with GPT-4 prompting alone
- Latency: Self-hosted LoRA model gives consistent sub-500ms responses vs. unpredictable GPT-4 API latency
- Data privacy: Conversation data never leaves infrastructure

---

## 3. Schema Design

### 3.1 Training Dataset Schema (JSONL Format)

```json
{
  "conversation_id": "stage1_sales_001",
  "conversation_type": "package_inquiry",
  "stage": 1,
  "intent": "therapy_package_recommendation",
  "messages": [
    {
      "role": "system",
      "content": "You are Saathi, a warm, empathetic AI wellness guide for [Company Name]'s employee assistance program..."
    },
    {
      "role": "user",
      "content": "Hi, I saw this in the company portal. What is this exactly?"
    },
    {
      "role": "assistant",
      "content": "Hi! I'm Saathi, your company's wellness companion. I'm here to support you through any stress, anxiety, or personal challenges you might be navigating..."
    }
  ],
  "metadata": {
    "package_recommended": "monthly_support",
    "booking_initiated": true,
    "objections_handled": ["price", "time_commitment"],
    "sentiment": "positive",
    "conversion_probability": 0.78,
    "conversation_length": 8,
    "outcome": "booked"
  }
}
```

### 3.2 Conversation Types (Categories)

| Category | Count | Description |
|----------|-------|-------------|
| package_inquiry | 150 | User asks what the service is, what's included |
| objection_handling | 120 | Price, time, skepticism about therapy |
| booking_initiation | 100 | User ready to book or needs light guidance |
| crisis_triage_referral | 80 | Pre-crisis or sub-threshold distress → warm handoff |
| peer_comparison | 50 | "Does this actually help people like me?" |
| budget_concerns | 60 | "Is this covered by insurance/company?" |
| follow_up_reengagement | 74 | User who didn't book initially, returning |
| **Total** | **634** | |

### 3.3 8-Step Conversation Architecture

The Stage 1 model is trained to naturally execute these 8 steps:

```
Step 1: Gratitude         → Thank user for reaching out, normalize seeking help
Step 2: Connection        → Build rapport, create psychological safety
Step 3: Discovery         → Open-ended questions to understand situation
Step 4: Values Alignment  → Connect therapy to what matters to the user
Step 5: Education         → What is therapy, what results can they expect
Step 6: Credentials       → Build trust in Saathi/therapist quality
Step 7: Objection Handling → Address price/time/stigma/skepticism
Step 8: Conversion        → Warm transition to booking
```

### 3.4 Lead Score Schema

```python
lead_score_schema = {
    "score": float,          # 0-100
    "factors": {
        "engagement_level": float,      # message length/quality (0-30)
        "pain_point_disclosed": bool,   # shared a real problem (0/20)
        "positive_response": bool,      # responded positively to therapy idea (0/20)
        "booking_intent_signal": bool,  # asked about booking/availability (0/15)
        "objection_resolved": bool,     # had objection that was resolved (0/15)
    }
}
```

---

## 4. Data Preparation

### 4.1 Data Sources

| Source | Examples | Description |
|--------|----------|-------------|
| Expert-written sales conversations | 250 | Written by trained mental health sales specialists |
| Real intake call transcripts (anonymized) | 200 | Actual pre-booking calls with human intake staff |
| Synthetic (GPT-4 + clinical/sales review) | 184 | Generated with expert review for edge cases |
| **Total** | **634** | |

### 4.2 Expert Requirements for Data Creation

Data creators for Stage 1 must have:
- Training in neuromarketing or motivational interviewing
- Familiarity with mental health stigma and common objections
- Knowledge of the specific Saathi service packages and pricing
- Understanding of corporate wellness program context (B2B)

### 4.3 Conversation Quality Standards

Each training conversation must:
1. Follow the 8-step flow (not necessarily all 8 in every conversation)
2. Never pressure or manipulate the user
3. Always maintain clinical empathy even in the sales context
4. Handle at least one objection gracefully in the dataset
5. End with either a booking or a graceful "come back when ready" close
6. Be 6–16 turns long (too short = insufficient context; too long = edge case)

### 4.4 ChatML Format Conversion

```python
def convert_to_chatml(conversation: dict) -> str:
    """Convert dataset entry to ChatML format for Qwen training."""
    chatml = ""
    for msg in conversation['messages']:
        role = msg['role']
        content = msg['content']
        chatml += f"<|im_start|>{role}\n{content}<|im_end|>\n"
    return chatml

# Example ChatML output:
# <|im_start|>system
# You are Saathi, a warm empathetic AI wellness guide...
# <|im_end|>
# <|im_start|>user
# Hi, I saw this in the company portal. What is this?
# <|im_end|>
# <|im_start|>assistant
# Hi! I'm Saathi, your company's wellness companion...
# <|im_end|>
```

---

## 5. Data Balance Strategy

### 5.1 Conversation Type Balance

The 634 examples are weighted to ensure all conversation scenarios are well-represented. Since this is generative (not classification), balance means ensuring each scenario has enough examples to influence the model's behavior, not statistical class parity.

**Minimum examples per category**: 50 (below this, the model may not generalize)
**Key gap to address**: `crisis_triage_referral` needs careful coverage — the model must recognize when to shift from sales to genuine support.

### 5.2 Objection Coverage

```python
# Verify objection types are covered in training data
REQUIRED_OBJECTIONS = [
    "price_too_high",
    "not_sure_therapy_helps_me",
    "not_enough_time",
    "therapy_is_for_weak_people",
    "my_problems_arent_serious_enough",
    "skeptical_about_ai",
    "company_is_watching",  # privacy concern in corporate context
]

def check_objection_coverage(dataset):
    covered = {obj: 0 for obj in REQUIRED_OBJECTIONS}
    for item in dataset:
        for obj in item['metadata'].get('objections_handled', []):
            if obj in covered:
                covered[obj] += 1
    for obj, count in covered.items():
        if count < 15:
            print(f"WARNING: {obj} only has {count} examples (min 15)")
    return covered
```

---

## 6. Dataset Splits

```
Full Dataset: 634 conversations
├── Training:   508 examples (80%)
├── Validation:  64 examples (10%)
└── Test:        62 examples (10%)
```

**Note**: Due to the small dataset size, k-fold cross-validation (k=5) is used during hyperparameter tuning rather than relying solely on the fixed validation split.

---

## 7. Dataset Evaluation & Quality Checks

### 7.1 Response Quality Rubric

Each assistant turn in the training data is rated by expert reviewers on:

| Criterion | Scale | Minimum Score |
|-----------|-------|---------------|
| Empathy/warmth | 1-5 | 4 |
| Naturalness (sounds human) | 1-5 | 4 |
| Clinical appropriateness | 1-5 | 4 |
| Commercial effectiveness | 1-5 | 3 |
| Non-manipulative | Pass/Fail | Pass |
| Privacy-preserving | Pass/Fail | Pass |

Any conversation with an assistant turn scoring < 4 on empathy or failing Pass/Fail criteria is excluded.

### 7.2 Red-Line Content Checks

```python
# Automated checks on all assistant turns

RED_LINE_PATTERNS = [
    r"you (should|must|need to) (book|sign up)",  # imperative booking
    r"(only|just|limited) (spots|availability)",   # false scarcity
    r"(discount|offer) expires",                    # pressure tactics
    r"other people like you",                       # peer pressure
    r"guarantee (results|improvement)",             # false guarantees
]

def check_red_lines(assistant_text: str) -> list:
    import re
    violations = []
    for pattern in RED_LINE_PATTERNS:
        if re.search(pattern, assistant_text.lower()):
            violations.append(pattern)
    return violations
```

---

## 8. Training Strategy

### 8.1 LoRA Configuration

```python
from peft import LoraConfig, TaskType

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=8,                      # rank — light adaptation for Stage 1
    lora_alpha=16,            # alpha = 2 * r (standard)
    lora_dropout=0.1,
    target_modules=[
        "q_proj", "k_proj",   # query and key attention projections
        "v_proj", "o_proj"    # value and output projections
    ],
    bias="none",
    inference_mode=False
)
```

### 8.2 Training Configuration

```python
training_config = {
    "base_model": "Qwen/Qwen2.5-7B-Instruct",
    "lora_rank": 8,
    "lora_alpha": 16,
    "lora_dropout": 0.1,
    "max_seq_length": 2048,      # sufficient for 8-12 turn conversation
    "batch_size": 4,
    "gradient_accumulation_steps": 8,  # effective batch = 32
    "num_train_epochs": 3,
    "learning_rate": 2e-4,
    "warmup_ratio": 0.05,
    "lr_scheduler": "cosine",
    "weight_decay": 0.01,
    "fp16": True,
    "gradient_checkpointing": True,
    "train_on_inputs": False,    # only compute loss on assistant turns
    "report_to": "wandb",
    "run_name": "qwen-lora-stage1-sales",
    "seed": 42
}
```

### 8.3 Hardware Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| GPU VRAM | 24GB (1x A10G) | 40GB (1x A100) |
| RAM | 32GB | 64GB |
| Storage | 30GB | 50GB |
| Training time | ~2 hours | ~1.5 hours |

---

## 9. Step-by-Step Training Process

### Step 1: Environment Setup

```bash
pip install torch==2.1.0 --index-url https://download.pytorch.org/whl/cu118
pip install transformers==4.36.0 peft==0.7.1
pip install trl==0.7.4  # TRL (Transformer Reinforcement Learning) for SFT
pip install datasets accelerate bitsandbytes wandb
```

### Step 2: Load Base Model with Quantization

```python
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

model_name = "Qwen/Qwen2.5-7B-Instruct"

# 4-bit quantization for memory efficiency during training
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4"
)

tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    torch_dtype=torch.float16
)
```

### Step 3: Prepare Training Data with SFTTrainer Format

```python
import json
from datasets import Dataset

# Load JSONL dataset
conversations = []
with open('ml_pipeline/data/stage1_sales_dataset.jsonl', 'r') as f:
    for line in f:
        conversations.append(json.loads(line))

def format_conversation(conv: dict) -> str:
    """Format as ChatML for Qwen."""
    text = ""
    for msg in conv['messages']:
        text += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
    return text

# Create Dataset
dataset_dict = {"text": [format_conversation(c) for c in conversations]}
dataset = Dataset.from_dict(dataset_dict)

# Split
dataset = dataset.train_test_split(test_size=0.2, seed=42)
train_dataset = dataset['train']
eval_dataset = dataset['test']

print(f"Training examples: {len(train_dataset)}")
print(f"Sample conversation (first 500 chars):\n{train_dataset[0]['text'][:500]}")
```

### Step 4: Apply LoRA and Setup SFT Trainer

```python
from peft import get_peft_model, LoraConfig, TaskType, prepare_model_for_kbit_training
from trl import SFTTrainer
from transformers import TrainingArguments

# Prepare model for quantized LoRA training
model = prepare_model_for_kbit_training(model)
model.config.use_cache = False

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=8, lora_alpha=16, lora_dropout=0.1,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    bias="none"
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# Expected: ~8M trainable / ~7600M total (0.1%)

training_args = TrainingArguments(
    output_dir="./models/stage1_lora_training",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    warmup_ratio=0.05,
    lr_scheduler_type="cosine",
    weight_decay=0.01,
    fp16=True,
    gradient_checkpointing=True,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    logging_steps=20,
    report_to="wandb",
    run_name="qwen-lora-stage1-sales",
    seed=42
)

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    tokenizer=tokenizer,
    dataset_text_field="text",
    max_seq_length=2048,
    packing=False  # don't pack conversations together
)

trainer.train()
```

### Step 5: Save LoRA Adapter

```python
# Save LoRA adapter only (lightweight)
model.save_pretrained("./models/qwen-lora-stage1")
tokenizer.save_pretrained("./models/qwen-lora-stage1")

print("Saved adapter files:")
# adapter_config.json     (~1KB)
# adapter_model.safetensors  (~17MB for r=8)
```

### Step 6: Merge and Save Full Model (Optional, for Production)

```python
from peft import AutoPeftModelForCausalLM

# Load and merge LoRA into base model
merged_model = AutoPeftModelForCausalLM.from_pretrained(
    "./models/qwen-lora-stage1",
    device_map="auto",
    torch_dtype=torch.float16
)
merged_model = merged_model.merge_and_unload()
merged_model.save_pretrained("./models/qwen-stage1-merged")
tokenizer.save_pretrained("./models/qwen-stage1-merged")
# Size: ~15GB in FP16; ~4GB in GPTQ 4-bit
```

### Step 7: Test Inference

```python
from transformers import pipeline

pipe = pipeline(
    "text-generation",
    model="./models/qwen-stage1-merged",
    tokenizer=tokenizer,
    max_new_tokens=300,
    temperature=0.8,
    top_p=0.92,
    do_sample=True,
    device_map="auto"
)

test_prompt = """<|im_start|>system
You are Saathi, a warm wellness guide for Acme Corp employees.
<|im_end|>
<|im_start|>user
Hi, I got an email about this. What is Saathi?
<|im_end|>
<|im_start|>assistant
"""

response = pipe(test_prompt)[0]['generated_text']
print(response[len(test_prompt):])
```

---

## 10. Model Evaluation

### 10.1 Automated Evaluation

```python
EVALUATION_CRITERIA = {
    "empathy_score": {
        "method": "classifier",  # Use sentiment/emotion classifier on response
        "target": "positive sentiment on user messages + empathetic tone"
    },
    "booking_conversion": {
        "method": "conversation_simulation",
        "target": "booking_initiated=True in ≥65% of simulated conversations"
    },
    "red_line_violations": {
        "method": "regex",
        "target": "0 violations in 100 test conversations"
    },
    "response_naturalness": {
        "method": "perplexity",  # lower perplexity = more natural
        "target": "<45 perplexity on held-out test set"
    }
}
```

### 10.2 Human Evaluation

10% of generated responses are reviewed by a sales/clinical expert panel:

| Metric | Target |
|--------|--------|
| Empathy score | ≥ 4.0/5.0 |
| Naturalness | ≥ 4.0/5.0 |
| Objection handling quality | ≥ 3.8/5.0 |
| Booking guidance quality | ≥ 4.0/5.0 |
| Would you book after this? | ≥ 70% YES |

### 10.3 Conversation Simulation Testing

```python
# Simulate full conversations with test user personas
TEST_PERSONAS = [
    {"name": "Skeptical Executive", "scenario": "Too busy, therapy is for weak people"},
    {"name": "Price-Sensitive Employee", "scenario": "This costs money I don't have"},
    {"name": "Curious First-Timer", "scenario": "Never tried therapy, open but unsure"},
    {"name": "Crisis-Adjacent", "scenario": "Struggling significantly, needs triage"},
    {"name": "Ready to Book", "scenario": "Already decided, needs logistics help"},
]
```

---

## 11. Downloading & Saving Weights

### 11.1 What to Save

```
therapeutic-copilot/server/ml_models/
└── stage1_sales_model/
    ├── adapter_config.json          # LoRA configuration
    ├── adapter_model.safetensors    # LoRA weights (~17MB for r=8)
    ├── tokenizer_config.json
    ├── tokenizer.json
    └── special_tokens_map.json
```

**Note**: Base model (Qwen2.5-7B-Instruct) is downloaded separately from HuggingFace at runtime and cached. Only the LoRA adapter is stored in the repo.

### 11.2 Download Base Model at Deployment

```bash
# At server startup or in Dockerfile
python -c "
from transformers import AutoTokenizer, AutoModelForCausalLM
AutoTokenizer.from_pretrained('Qwen/Qwen2.5-7B-Instruct', trust_remote_code=True)
AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-7B-Instruct', trust_remote_code=True)
print('Base model cached')
"
```

---

## 12. Integrating Trained Weights into the App Workflow

### 12.1 LoRA Model Service (Stage 1 Loading)

The existing [lora_model_service.py](therapeutic-copilot/server/services/lora_model_service.py) handles model loading. Key method `load_stage1_model()`:

```python
# Excerpt from lora_model_service.py

def load_stage1_model(self):
    """Load Stage 1 LoRA adapter on top of base Qwen model."""
    from peft import PeftModel

    # Load base model (from cache or HuggingFace)
    self.base_model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen2.5-7B-Instruct",
        device_map="auto",
        torch_dtype=torch.float16,
        trust_remote_code=True
    )

    # Load Stage 1 LoRA adapter
    self.stage1_model = PeftModel.from_pretrained(
        self.base_model,
        "models/qwen-lora-stage1",
        adapter_name="stage1"
    )
    self.stage1_model.eval()
    self.current_stage = 1
    print("Stage 1 Sales LoRA loaded ✅")
```

### 12.2 Inference Call

```python
def generate_stage1_response(
    self,
    conversation_history: list,
    company_name: str,
    user_info: dict,
    max_tokens: int = 300
) -> dict:
    """Generate Stage 1 sales response."""

    system_prompt = self._build_stage1_system_prompt(company_name, user_info)
    messages = [{"role": "system", "content": system_prompt}] + conversation_history

    # Format as ChatML
    prompt = self._format_chatml(messages)

    inputs = self.tokenizer(prompt, return_tensors='pt').to(self.device)
    with torch.no_grad():
        outputs = self.stage1_model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.8,
            top_p=0.92,
            top_k=50,
            repetition_penalty=1.1,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id
        )

    response_text = self.tokenizer.decode(
        outputs[0][inputs['input_ids'].shape[1]:],
        skip_special_tokens=True
    )

    # Calculate lead score
    lead_score = self._calculate_lead_score(conversation_history, response_text)

    return {
        "response": response_text,
        "stage": "lead_generation",
        "stage_order": len(conversation_history) // 2,
        "lead_score": lead_score,
        "booking_intent_detected": "book" in response_text.lower() or "schedule" in response_text.lower(),
        "tokens_generated": len(outputs[0]) - inputs['input_ids'].shape[1]
    }
```

---

## 13. Building Prompt Context with Model Output

### 13.1 Stage 1 System Prompt Assembly

```python
def build_stage1_system_prompt(
    company_name: str,
    conversation_stage: int,
    emotion_result: dict,
    intent_result: dict,
    topic_result: dict,
    lead_score: float
) -> str:
    """
    Build the complete system prompt for Stage 1.
    The LoRA model already knows how to behave; this prompt adds
    real-time context from the classifier pipeline.
    """

    stage_instructions = {
        1: "Focus on warm welcome and curiosity. Ask one open question about what brought them here.",
        2: "Build rapport. Reflect back what they've shared. Make them feel heard.",
        3: "Explore their situation deeply. Use open-ended questions. Surface the real pain point.",
        4: "Connect what they've shared to the value of the service. Use their own words.",
        5: "Gently introduce therapy as a solution. Normalize help-seeking.",
        6: "Build trust and credibility of the platform and therapist.",
        7: "Address any objections with empathy. Don't argue — validate and reframe.",
        8: "Warm transition to booking. Make it easy and natural."
    }

    emotion_tone = ""
    if emotion_result:
        primary = emotion_result.get('primary_emotion', 'neutral')
        intensity = emotion_result.get('intensity', 0.5)
        if primary in ['anxiety', 'sadness'] and intensity > 0.6:
            emotion_tone = f"\nNote: User shows {primary} (intensity {intensity:.0%}). Be extra warm, slow down, validate before any suggestion."
        elif primary == 'hopelessness' and intensity > 0.7:
            emotion_tone = "\n⚠️ User showing high distress. Pause sales flow. Prioritize emotional safety and support."

    prompt = f"""You are Saathi, a warm, empathetic wellness guide for {company_name}'s employee wellness program.

## Your Role
You are in the initial conversation with a {company_name} employee. Your goal is to understand their needs, build genuine connection, and gently guide them toward booking a therapy session — but NEVER at the cost of their wellbeing or trust.

## Current Conversation Stage: {conversation_stage}/8
{stage_instructions.get(conversation_stage, "Follow natural conversation flow.")}

## Conversation Guidelines
- Be warm and human — not corporate or scripted
- Ask ONE question at a time
- Never pressure or use urgency tactics
- If crisis signals appear, immediately shift to support mode
- Keep responses to 2-4 sentences maximum
- Use the user's name if known

## Lead Score Context (internal use only, not mentioned to user)
Current lead score: {lead_score:.0f}/100
{"→ Ready to guide toward booking" if lead_score > 70 else "→ Still building rapport and trust"}
{emotion_tone}
"""

    # Add topic context if available
    if topic_result and topic_result.get('primary_topic'):
        topic = topic_result['primary_topic']
        topic_map = {
            "workplace_stress": "They seem to be dealing with work-related stress. Acknowledge workplace pressures.",
            "relationship_issues": "Relationship challenges seem present. Be especially warm and non-judgmental.",
            "academic_stress": "Academic pressure is their primary concern. Normalize performance anxiety.",
            "health_concerns": "Health-related anxiety. Validate the mind-body connection.",
            "financial_stress": "Financial stress detected. Be sensitive about cost discussions."
        }
        prompt += f"\n## Topic Context\n{topic_map.get(topic, '')}\n"

    return prompt
```

### 13.2 How Lead Score Feeds Back Into Prompt

```python
def update_lead_score_context(prompt: str, new_lead_score: float, booking_signals: list) -> str:
    """Update system prompt with latest lead scoring on each turn."""
    score_context = f"\n[Updated Lead Score: {new_lead_score:.0f}/100"
    if booking_signals:
        score_context += f" | Booking signals: {', '.join(booking_signals)}"
    score_context += "]"
    return prompt + score_context
```

---

## Summary

| Aspect | Decision |
|--------|----------|
| Architecture | Qwen2.5-7B-Instruct + LoRA (r=8) |
| Dataset | 634 expert-crafted sales conversations in ChatML format |
| Training | SFTTrainer with 4-bit quantization; 3 epochs |
| LoRA adapter size | ~17MB |
| Purpose | 8-step neuromarketing-optimized pre-appointment conversation |
| Integration | LoraModelService loads adapter on base Qwen model |
| Prompt use | System prompt enriched with emotion, topic, lead score, and conversation stage |

---

*Document Version: 1.0 | Model Version: qwen-lora-stage1-saathi-v1 | Last Updated: 2025-03*
