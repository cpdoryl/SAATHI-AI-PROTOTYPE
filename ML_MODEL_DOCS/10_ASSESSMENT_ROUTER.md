# Model Document 10: Assessment Router
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
The **Assessment Router** analyzes a user's conversation context and recommends which of the 8 validated clinical assessments the user should be guided through. Instead of presenting all 8 assessments indiscriminately or waiting for explicit user request, it proactively identifies the most clinically relevant assessment based on what the user has shared.

### The 8 Clinical Assessments Available in Saathi

| Assessment | Measures | Full Name |
|------------|----------|-----------|
| PHQ-9 | Depression | Patient Health Questionnaire-9 |
| GAD-7 | Anxiety | Generalized Anxiety Disorder-7 |
| DASS-21 | Depression + Anxiety + Stress | Depression Anxiety Stress Scales |
| PSS-10 | Stress | Perceived Stress Scale |
| WEMWBS | Mental Wellbeing | Warwick-Edinburgh Mental Well-Being Scale |
| PCL-5 | PTSD | PTSD Checklist for DSM-5 |
| AUDIT | Alcohol use | Alcohol Use Disorders Identification Test |
| CAGE-AID | Drug/Alcohol screening | CAGE Adapted to Include Drugs |

### Why a Router Model?
Without a router, the system either:
1. Always offers all 8 assessments — overwhelming and clinically inappropriate
2. Waits for the user to ask — misses screening opportunities

The router solves this by detecting from natural conversation which condition the user is most likely presenting with, and recommending the most appropriate validated assessment — just as a clinician would based on the presenting complaint.

**Example**:
- User: "I've been having nightmares about the accident and can't stop thinking about it" → Route to PCL-5
- User: "I've been drinking way more than usual to cope" → Route to AUDIT
- User: "Everything feels pointless and I haven't left my house in weeks" → Route to PHQ-9

### Scope
- **Input**: Last 3–5 conversation turns (context window, not just single utterance)
- **Output**: Recommended assessments (ordered list), with confidence and clinical rationale
- **Classes**: 8 assessments + no_assessment_needed
- **Dataset Size**: 4,000 examples

---

## 2. Why We Chose This Model Architecture

### Architecture: Fine-tuned `roberta-base` (Multi-Label Classification with Context Window)

#### Why RoBERTa-base (Not DistilBERT)?
- Assessment routing requires **clinical reasoning** over context, not just keyword matching
- "I've been feeling really low lately and keep thinking about whether things would be better without me" is not just depression (PHQ-9) — it may also warrant PCL-5 if trauma history is present
- RoBERTa's larger capacity handles the multi-label reasoning across clinical dimensions better
- Acceptable latency (<50ms) since assessment routing only triggers at specific points in the conversation, not every message

#### Why Multi-Label?
- A user may present with comorbidities: anxiety + depression (both GAD-7 and PHQ-9)
- DASS-21 covers both depression and anxiety — may be recommended alongside PHQ-9 for comprehensive picture
- PCL-5 and PHQ-9 frequently co-occur (trauma + depression)

#### Why Context Window Input?
Assessment routing cannot be done from a single utterance — it requires understanding the pattern of what a user has shared across multiple turns:

```python
# Single turn might not indicate assessment need:
# Turn 1: "I've been feeling off lately"
# Turn 2: "More anxious than usual"
# Turn 3: "Can't stop thinking about what happened"
# Turn 4: "Haven't been sleeping since the incident"
# → Only with turns 1-4 context is PCL-5 clearly indicated
```

---

## 3. Schema Design

### 3.1 Dataset Schema (JSON)

```json
{
  "id": "assess_router_001234",
  "conversation_context": [
    {"role": "user", "content": "I've been feeling really low and exhausted for months"},
    {"role": "assistant", "content": "That sounds really draining. How has this been affecting your daily life?"},
    {"role": "user", "content": "I can barely get out of bed, I've lost all interest in things I used to love"},
    {"role": "assistant", "content": "I hear you. Have you also noticed changes in your appetite or sleep?"},
    {"role": "user", "content": "Yes, I sleep 12 hours but wake up exhausted. I've also had thoughts about whether I deserve to be here"}
  ],
  "recommended_assessments": ["PHQ-9", "DASS-21"],
  "primary_assessment": "PHQ-9",
  "rationale": "Persistent low mood, anhedonia, hypersomnia, passive suicidal ideation — PHQ-9 indicated; DASS-21 for broader picture",
  "confidence": 0.94,
  "urgency": "high",
  "crisis_indicators": ["passive_suicidal_ideation"],
  "source": "clinical_transcripts_annotated",
  "annotator_id": "ann_clin_001",
  "created_at": "2024-10-18T15:00:00Z"
}
```

### 3.2 Assessment Indication Schema

| Assessment | Primary Indicators | Clinical Signals |
|------------|-------------------|-----------------|
| PHQ-9 | Depression symptoms | Low mood, anhedonia, fatigue, worthlessness, suicidal ideation, appetite/sleep changes |
| GAD-7 | Anxiety symptoms | Worry, nervousness, restlessness, irritability, difficulty concentrating, muscle tension |
| DASS-21 | Broad screening | Combination of depression + anxiety + stress; good for initial screening |
| PSS-10 | Stress levels | Workplace stress, overwhelm, feeling out of control, "stressed out" |
| WEMWBS | Wellbeing/resilience | Generally wants to check wellbeing, track progress, positive functioning |
| PCL-5 | PTSD symptoms | Trauma history, nightmares, flashbacks, hypervigilance, avoidance |
| AUDIT | Alcohol use | Mentions drinking, "drinking more than usual", drinking to cope |
| CAGE-AID | Substance screening | Drug/alcohol mentions, dependency language, withdrawal symptoms |

### 3.3 Model Output Schema (JSON)

```json
{
  "recommended_assessments": [
    {
      "assessment": "PHQ-9",
      "confidence": 0.94,
      "rationale": "Low mood, anhedonia, fatigue, and passive suicidal ideation strongly indicate depression screening",
      "urgency": "high",
      "sequence": 1
    },
    {
      "assessment": "DASS-21",
      "confidence": 0.71,
      "rationale": "Broad picture useful alongside PHQ-9; stress component may also be relevant",
      "urgency": "medium",
      "sequence": 2
    }
  ],
  "no_assessment_needed": false,
  "crisis_indicators": ["passive_suicidal_ideation"],
  "defer_to_clinician": false,
  "processing_time_ms": 42
}
```

---

## 4. Data Preparation

### 4.1 Data Sources

| Source | Examples | Description |
|--------|----------|-------------|
| Clinical intake conversation transcripts | 1,500 | Real clinical transcripts with diagnostic routing (de-identified) |
| Synthetic (GPT-4 + clinical review) | 1,500 | Multi-turn conversations presenting specific clinical pictures |
| Open clinical datasets (adapted) | 600 | Public mental health conversation datasets with clinical annotations |
| Edge cases (comorbid presentations) | 400 | Specifically crafted comorbid presentations (depression+PTSD, anxiety+alcohol) |
| **Total** | **4,000** | |

### 4.2 Annotation Requirements

All dataset examples require annotation by **clinically qualified** reviewers:
- Mental health nurse practitioners
- Clinical psychologists
- Psychiatry residents
- Licensed counselors with clinical assessment experience

Annotators were provided with the clinical indications for each of the 8 assessments and trained on how to recognize presenting complaints from conversational text.

### 4.3 Context Window Preparation

```python
def prepare_context_window(conversation_history: list, max_turns: int = 5) -> str:
    """
    Prepare multi-turn conversation context for assessment routing.
    Takes last N user messages + assistant responses.
    """
    # Take last max_turns user+assistant pairs
    recent = conversation_history[-(max_turns*2):]
    context = ""
    for msg in recent:
        role_prefix = "User: " if msg['role'] == 'user' else "Saathi: "
        context += f"{role_prefix}{msg['content']}\n"
    return context.strip()

# Example context:
# "User: I've been feeling really low for months
# Saathi: I hear that, how has it been affecting your day-to-day?
# User: I can barely function, I've lost interest in everything
# Saathi: That sounds very difficult. Are there thoughts of harming yourself?
# User: I've had thoughts that it would be easier if I wasn't here"
```

---

## 5. Data Balance Strategy

### 5.1 Assessment Distribution

| Assessment | Count (primary) | Notes |
|------------|----------------|-------|
| PHQ-9 | 950 | Most common presenting condition |
| GAD-7 | 750 | Second most common |
| DASS-21 | 600 | Broad screener, often paired |
| PSS-10 | 450 | Workplace/life stress |
| PCL-5 | 400 | Trauma-related, important but less common |
| WEMWBS | 300 | Wellbeing-focused, lighter presentations |
| AUDIT | 300 | Alcohol-related |
| CAGE-AID | 200 | Substance screening |
| no_assessment | 150 | User in chat mode, no clinical need |
| **Total primary** | **4,100** | (some examples have multiple primaries) |

### 5.2 Handling Rare Assessments (CAGE-AID, WEMWBS)

```python
# Augment CAGE-AID and WEMWBS examples using paraphrasing
def augment_rare_assessment_examples(examples: list, target_n: int, assessment: str) -> list:
    augmented = list(examples)  # start with existing
    while len(augmented) < target_n:
        original = random.choice(examples)
        # Back-translate user messages in context
        augmented_context = []
        for msg in original['conversation_context']:
            if msg['role'] == 'user':
                augmented_context.append({
                    "role": "user",
                    "content": back_translate(msg['content'])
                })
            else:
                augmented_context.append(msg)
        augmented.append({**original, "conversation_context": augmented_context,
                          "id": f"{assessment}_aug_{len(augmented)}"})
    return augmented
```

---

## 6. Dataset Splits

```
Full Dataset: 4,000 examples
├── Training:   3,200 examples (80%)
├── Validation:   400 examples (10%)
└── Test:         400 examples (10%)
```

Stratified by `primary_assessment` to ensure all 9 classes (8 assessments + no_assessment) are represented in each split.

---

## 7. Dataset Evaluation & Quality Checks

```python
# Clinical consistency check: if PHQ-9 is recommended, depression signals must be present
ASSESSMENT_REQUIRED_SIGNALS = {
    "PHQ-9": ["low mood", "depression", "sad", "hopeless", "worthless",
               "no interest", "tired", "suicidal", "sleep", "appetite"],
    "PCL-5": ["trauma", "accident", "assault", "nightmare", "flashback",
               "hypervigilant", "avoid", "incident", "happened"],
    "AUDIT": ["drink", "alcohol", "beer", "wine", "drunk", "sober"],
    "GAD-7": ["worried", "anxious", "nervous", "tense", "panic", "fear"],
}

def verify_signal_presence(examples: list) -> list:
    """Check that recommended assessments have supporting signals in context."""
    issues = []
    for ex in examples:
        context_lower = ' '.join([m['content'].lower()
                                   for m in ex['conversation_context']
                                   if m['role'] == 'user'])
        primary = ex['primary_assessment']
        required = ASSESSMENT_REQUIRED_SIGNALS.get(primary, [])
        if required:
            found = any(sig in context_lower for sig in required)
            if not found:
                issues.append({"id": ex['id'], "assessment": primary,
                               "issue": "No supporting signal found in context"})
    return issues
```

---

## 8. Training Strategy

### 8.1 Architecture: RoBERTa with Context Pooling

```python
from transformers import RobertaModel
import torch.nn as nn

class AssessmentRouterModel(nn.Module):
    def __init__(self, n_assessments: int = 9, dropout: float = 0.3):
        super().__init__()
        self.roberta = RobertaModel.from_pretrained('roberta-base')

        # Multi-label classification head
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(768, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, n_assessments)
            # No sigmoid here — applied in loss (BCEWithLogitsLoss)
        )

    def forward(self, input_ids, attention_mask):
        outputs = self.roberta(input_ids=input_ids, attention_mask=attention_mask)
        pooled = outputs.pooler_output  # [CLS] representation
        return self.classifier(pooled)
```

### 8.2 Training Configuration

```python
training_config = {
    "model_name": "roberta-base",
    "num_labels": 9,  # 8 assessments + no_assessment
    "problem_type": "multi_label_classification",
    "max_seq_length": 512,   # longer for multi-turn context
    "batch_size": 16,
    "num_epochs": 5,
    "learning_rate": 1e-5,
    "warmup_ratio": 0.1,
    "weight_decay": 0.01,
    "fp16": True,
    "eval_metric": "f1_macro",
    "assessment_thresholds": {  # per-assessment classification thresholds
        "PHQ-9": 0.55,
        "GAD-7": 0.55,
        "DASS-21": 0.50,
        "PSS-10": 0.55,
        "WEMWBS": 0.60,
        "PCL-5": 0.50,  # lower threshold for PTSD (safety)
        "AUDIT": 0.55,
        "CAGE-AID": 0.50,  # lower threshold for substance (safety)
        "no_assessment": 0.65
    },
    "seed": 42
}
```

---

## 9. Step-by-Step Training Process

### Step 1: Setup

```bash
pip install torch transformers datasets scikit-learn wandb iterstrat
```

### Step 2: Load Data

```python
import json
from transformers import AutoTokenizer, RobertaForSequenceClassification
from datasets import Dataset
from sklearn.model_selection import train_test_split
import numpy as np

ASSESSMENTS = ["PHQ-9","GAD-7","DASS-21","PSS-10","WEMWBS","PCL-5","AUDIT","CAGE-AID","no_assessment"]

tokenizer = AutoTokenizer.from_pretrained("roberta-base")

data = []
with open('ml_pipeline/data/assessment_router_v1.jsonl') as f:
    for line in f:
        item = json.loads(line)
        context = prepare_context_window(item['conversation_context'])
        label_vector = [0] * 9
        for assess in item.get('recommended_assessments', [{'assessment':'no_assessment'}]):
            idx = ASSESSMENTS.index(assess['assessment'])
            label_vector[idx] = 1
        data.append({"text": context, "labels": label_vector})

def tokenize_fn(examples):
    enc = tokenizer(examples['text'], max_length=512, truncation=True, padding='max_length')
    enc['labels'] = [float(l) for l in examples['labels']]  # BCEWithLogits needs float
    return enc

dataset = Dataset.from_list(data).map(tokenize_fn, batched=False)
dataset = dataset.train_test_split(test_size=0.2, seed=42)
```

### Step 3: Multi-Label Training

```python
from transformers import TrainingArguments, Trainer
from sklearn.metrics import f1_score
import torch

model = RobertaForSequenceClassification.from_pretrained(
    "roberta-base", num_labels=9,
    problem_type="multi_label_classification"
)

class AssessmentTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        loss = torch.nn.BCEWithLogitsLoss()(outputs.logits, labels.float())
        return (loss, outputs) if return_outputs else loss

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    probs = torch.sigmoid(torch.FloatTensor(logits)).numpy()
    preds = (probs >= 0.50).astype(int)
    return {
        "f1_macro": f1_score(labels, preds, average='macro'),
        "f1_micro": f1_score(labels, preds, average='micro'),
        "f1_samples": f1_score(labels, preds, average='samples')
    }

args = TrainingArguments(
    output_dir="./models/assessment_router",
    num_train_epochs=5,
    per_device_train_batch_size=16,
    learning_rate=1e-5,
    warmup_ratio=0.1,
    evaluation_strategy="epoch",
    save_strategy="best",
    load_best_model_at_end=True,
    metric_for_best_model="eval_f1_macro",
    fp16=True,
    report_to="wandb",
    run_name="assessment-router-roberta-v1",
    seed=42
)

trainer = AssessmentTrainer(
    model=model, args=args,
    train_dataset=dataset['train'],
    eval_dataset=dataset['test'],
    compute_metrics=compute_metrics
)
trainer.train()
```

### Step 4: Optimize Per-Assessment Thresholds

```python
# Sweep thresholds on validation set
val_logits = trainer.predict(val_dataset).predictions
val_probs = torch.sigmoid(torch.FloatTensor(val_logits)).numpy()

optimal_thresholds = {}
for i, assess in enumerate(ASSESSMENTS):
    best_f1, best_t = 0, 0.5
    for t in np.arange(0.30, 0.80, 0.05):
        preds = (val_probs[:, i] >= t).astype(int)
        labels_i = [l[i] for l in val_dataset['labels']]
        f1 = f1_score(labels_i, preds, zero_division=0)
        if f1 > best_f1:
            best_f1, best_t = f1, t
    optimal_thresholds[assess] = best_t
    print(f"{assess}: threshold={best_t:.2f}, F1={best_f1:.3f}")

# Safety overrides: PTSD and substance detection use lower thresholds
optimal_thresholds['PCL-5'] = min(optimal_thresholds['PCL-5'], 0.45)
optimal_thresholds['CAGE-AID'] = min(optimal_thresholds['CAGE-AID'], 0.45)

import json
with open("models/assessment_router/thresholds.json", "w") as f:
    json.dump(optimal_thresholds, f, indent=2)
```

### Step 5: Save Model

```python
model.save_pretrained("./models/assessment_router_saathi_v1")
tokenizer.save_pretrained("./models/assessment_router_saathi_v1")
```

---

## 10. Model Evaluation

| Metric | Target |
|--------|--------|
| Macro F1 | ≥ 0.82 |
| PHQ-9 F1 | ≥ 0.88 |
| GAD-7 F1 | ≥ 0.85 |
| PCL-5 Recall | ≥ 0.90 (safety-critical) |
| CAGE-AID Recall | ≥ 0.88 (safety-critical) |
| Unnecessary routing rate | < 10% |

---

## 11. Downloading & Saving Weights

```
therapeutic-copilot/server/ml_models/
└── assessment_router/
    ├── config.json
    ├── pytorch_model.bin    (~476MB for RoBERTa-base)
    ├── tokenizer.json
    ├── vocab.json
    └── thresholds.json
```

---

## 12. Integrating Trained Weights into the App Workflow

### 12.1 AssessmentRouterService

```python
# therapeutic-copilot/server/services/assessment_router_service.py

import torch, time, json
import numpy as np
from transformers import AutoTokenizer, RobertaForSequenceClassification

ASSESSMENTS = ["PHQ-9","GAD-7","DASS-21","PSS-10","WEMWBS","PCL-5","AUDIT","CAGE-AID","no_assessment"]

ASSESSMENT_DESCRIPTIONS = {
    "PHQ-9": "depression screening (9 questions, ~3 minutes)",
    "GAD-7": "anxiety screening (7 questions, ~2 minutes)",
    "DASS-21": "depression, anxiety, and stress screening (21 questions, ~5 minutes)",
    "PSS-10": "perceived stress assessment (10 questions, ~3 minutes)",
    "WEMWBS": "mental wellbeing check (14 questions, ~4 minutes)",
    "PCL-5": "trauma and PTSD screening (20 questions, ~7 minutes)",
    "AUDIT": "alcohol use assessment (10 questions, ~3 minutes)",
    "CAGE-AID": "brief drug/alcohol screening (4 questions, ~1 minute)",
}

class AssessmentRouterService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        path = "./ml_models/assessment_router"
        self.tokenizer = AutoTokenizer.from_pretrained(path)
        self.model = RobertaForSequenceClassification.from_pretrained(path)
        self.model.eval()
        with open(f"{path}/thresholds.json") as f:
            self.thresholds = json.load(f)
        self._initialized = True

    def route(self, conversation_history: list) -> dict:
        start = time.time()
        context = prepare_context_window(conversation_history, max_turns=5)
        inputs = self.tokenizer(context, max_length=512, truncation=True,
                                 padding='max_length', return_tensors='pt')
        with torch.no_grad():
            probs = torch.sigmoid(self.model(**inputs).logits).numpy()[0]

        recommended = []
        for i, assess in enumerate(ASSESSMENTS):
            if assess != 'no_assessment' and probs[i] >= self.thresholds.get(assess, 0.50):
                recommended.append({
                    "assessment": assess,
                    "confidence": float(probs[i]),
                    "description": ASSESSMENT_DESCRIPTIONS.get(assess, ""),
                    "urgency": "high" if probs[i] >= 0.80 else "medium"
                })

        # Sort by confidence (highest first)
        recommended.sort(key=lambda x: x['confidence'], reverse=True)

        # Primary recommendation
        primary = recommended[0]['assessment'] if recommended else None

        return {
            "recommended_assessments": recommended[:3],  # max 3 at once
            "primary_assessment": primary,
            "no_assessment_needed": len(recommended) == 0,
            "processing_time_ms": round((time.time()-start)*1000, 1)
        }
```

### 12.2 Integration into Assessment Flow

```python
# In chat_routes.py — triggers after 3+ therapeutic turns in Stage 2

if intent_result['routing_action'] == "ASSESSMENT_ROUTER" or \
   (session['turn_count'] > 3 and session.get('assessment_not_done')):

    assessment_result = assessment_router_service.route(session.get_history())

    if not assessment_result['no_assessment_needed']:
        # Offer assessment naturally in conversation
        primary = assessment_result['primary_assessment']
        desc = ASSESSMENT_DESCRIPTIONS.get(primary, "")
        offer_message = f"I'd like to suggest we take a brief {desc} to get a clearer picture of how you're doing. This takes just a few minutes and helps me support you better. Would you be open to that?"

        return {
            "message": offer_message,
            "assessment_suggested": primary,
            "assessment_result": assessment_result
        }
```

---

## 13. Building Prompt Context with Model Output

### 13.1 Assessment Context Block

```python
ASSESSMENT_CLINICAL_CONTEXT = {
    "PHQ-9": {
        "condition": "depression",
        "focus": "depressive symptoms: mood, interest, energy, sleep, appetite, concentration, worthlessness, suicidal ideation",
        "prompt_instruction": "Administer PHQ-9 gently. For Q9 (thoughts of self-harm), approach with extra care and follow up on any elevated response."
    },
    "GAD-7": {
        "condition": "generalized anxiety",
        "focus": "anxiety symptoms: worry, nervousness, irritability, concentration, restlessness, physical tension",
        "prompt_instruction": "Administer GAD-7 in a calm, normalizing tone. Anxiety about taking an anxiety assessment is common — normalize it."
    },
    "PCL-5": {
        "condition": "PTSD",
        "focus": "trauma response: intrusions, avoidance, negative cognitions, hyperarousal",
        "prompt_instruction": "PCL-5 involves asking about trauma symptoms. Proceed with extra care. Ask permission before each cluster. Allow pacing. Have safety resources ready."
    },
    "AUDIT": {
        "condition": "alcohol use",
        "focus": "drinking frequency, quantity, dependency indicators",
        "prompt_instruction": "Approach alcohol screening without judgment. Normalize that many people drink. Explain that this helps understand how alcohol may be affecting their wellbeing."
    }
}

def build_assessment_context_block(assessment_result: dict) -> str:
    if assessment_result.get('no_assessment_needed'):
        return ""

    primary = assessment_result.get('primary_assessment')
    if not primary:
        return ""

    config = ASSESSMENT_CLINICAL_CONTEXT.get(primary, {})
    recommendations = assessment_result.get('recommended_assessments', [])

    block = f"""
## Assessment Router Recommendation

**Primary Assessment**: {primary}
- Condition: {config.get('condition', 'general mental health')}
- What it measures: {config.get('focus', 'general wellbeing')}
- **Instruction**: {config.get('prompt_instruction', 'Administer the assessment warmly and at the user's pace.')}

"""
    if len(recommendations) > 1:
        block += "**Additional Assessments Considered** (in priority order):\n"
        for r in recommendations[1:3]:
            block += f"- {r['assessment']} (confidence: {r['confidence']:.0%})\n"

    return block
```

### 13.2 Post-Assessment Scoring Integration

```python
def build_post_assessment_context(assessment_name: str, score_result: dict) -> str:
    """
    After scoring (handled by assessment_scoring_service.py),
    build context for therapeutic response to the score.
    """
    severity = score_result.get('severity', 'unknown')
    score = score_result.get('total_score', 0)
    crisis_flag = score_result.get('crisis_flag', False)

    block = f"""
## Assessment Completed: {assessment_name}
- Score: {score}
- Severity: {severity}
- Crisis Flag: {'⚠️ YES - immediate action required' if crisis_flag else 'No'}

**How to respond to this score**:
"""
    if crisis_flag:
        block += "PRIORITY: Crisis indicators present. Address safety immediately before discussing score.\n"
    elif severity in ['severe', 'moderately_severe']:
        block += f"This score indicates {severity} {assessment_name.split('-')[0].lower()} symptoms. Validate the difficulty. Express genuine concern. Discuss next steps (professional referral, urgent session).\n"
    elif severity in ['moderate', 'mild']:
        block += f"This score indicates {severity} symptoms. Validate that these are real and impactful. Introduce relevant coping strategies. Discuss treatment options.\n"
    else:
        block += "Mild or minimal symptoms. Validate the user's self-awareness in seeking assessment. Discuss preventative strategies and wellbeing maintenance.\n"

    return block
```

---

## Summary

| Aspect | Decision |
|--------|----------|
| Architecture | RoBERTa-base, multi-label (9 classes) |
| Dataset | 4,000 examples with multi-turn context windows |
| Key innovation | Context window input (last 5 turns, not single utterance) |
| Safety | PCL-5 and CAGE-AID use lower thresholds (safety-first) |
| Integration | Triggers proactively based on conversation content, not just user request |
| Prompt use | Injects assessment name, clinical instructions, and scoring context into LLM |

---

*Document Version: 1.0 | Model Version: assessment_router_saathi_v1 | Last Updated: 2025-03*
