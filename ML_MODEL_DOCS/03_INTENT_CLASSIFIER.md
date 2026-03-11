# Model Document 03: Intent Classifier
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
The **Intent Classifier** determines *what the user wants to accomplish* with their message — independent of what they are feeling. While the Emotion Classifier answers "how is the user feeling?", the Intent Classifier answers "what does the user want to do right now?" This distinction is critical for routing the conversation to the correct handler.

### Why It Matters
A single message can carry very different intents:
- "I need help" → `seek_support` (route to therapeutic conversation)
- "I need to book a session" → `book_appointment` (route to booking flow)
- "I'm going to hurt myself" → `crisis_emergency` (route to crisis protocol)
- "What is CBT?" → `information_request` (route to knowledge base RAG)
- "This app is terrible" → `feedback_complaint` (route to support)

Without intent classification, the system would apply the same therapeutic response to all of these — wasting a booking opportunity, failing to answer an information request, or (worst case) not recognizing a crisis declaration.

### Scope
- **Input**: Single user utterance (text string, up to 256 tokens)
- **Output**: `intent` (primary), `confidence`, `secondary_intent` (optional), all intent scores
- **Classes**: 7 intent categories
- **Downstream Effect**: Routes to the appropriate response handler

---

## 2. Why We Chose This Model Architecture

### Architecture: Fine-tuned `distilbert-base-uncased` with Multi-Intent Support

#### Why DistilBERT?
- **Speed**: Intent classification runs on every message before routing decisions; needs to complete in <15ms
- **Task complexity**: 7-class classification is well within DistilBERT's capability
- **Conversational text**: DistilBERT handles colloquial, short-text inputs effectively
- **Resource efficiency**: Shares the BERT tokenizer infrastructure with the emotion classifier

#### Why NOT a Zero-Shot Approach?
Zero-shot classification (e.g., `facebook/bart-large-mnli`) is accurate for generic intents but:
- Runs at 200–500ms (too slow)
- Does not understand domain-specific intents like `booking_initiation` or `assessment_request`
- Cannot be fine-tuned on proprietary conversation patterns

#### Multi-Intent Support
Some messages carry multiple intents simultaneously:
- "I've been feeling really down and I think I need to book something" → `seek_support` + `book_appointment`

The architecture outputs soft probabilities for all 7 classes, and we allow detection of a secondary intent when its confidence exceeds 0.35 (a lower threshold than primary).

---

## 3. Schema Design

### 3.1 Dataset Schema (CSV Format)

```csv
id,utterance,primary_intent,secondary_intent,confidence,source,annotator_id,created_at
```

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | string | UUID | `intent_002891` |
| `utterance` | string | User text | `"Can I schedule a session for Thursday?"` |
| `primary_intent` | enum | Main intent | `book_appointment` |
| `secondary_intent` | enum / null | Secondary intent if any | `seek_support` |
| `confidence` | float (0.0–1.0) | Annotator confidence | `0.96` |
| `source` | enum | Data origin | `synthetic`, `user_logs`, `forum` |
| `annotator_id` | string | Annotator ID | `ann_003` |
| `created_at` | ISO datetime | Timestamp | `2024-10-12T09:00:00Z` |

### 3.2 Intent Taxonomy

```
intents/
├── seek_support          → user wants emotional support, help with mental health issue
│   ├── immediate         → "I'm struggling right now"
│   └── general           → "I want to talk about my anxiety"
├── book_appointment      → user wants to schedule a session with therapist
├── crisis_emergency      → user indicates imminent danger (overlaps with Crisis Detector)
├── information_request   → user wants factual info (what is X, how does Y work)
├── feedback_complaint    → user giving feedback or complaining about the app/service
├── general_chat          → casual conversation, no specific goal
└── assessment_request    → user wants to take or continue an assessment (PHQ-9, GAD-7 etc.)
```

### 3.3 Model Output Schema (JSON)

```json
{
  "primary_intent": "book_appointment",
  "secondary_intent": "seek_support",
  "confidence": 0.87,
  "secondary_confidence": 0.42,
  "all_scores": {
    "seek_support": 0.42,
    "book_appointment": 0.87,
    "crisis_emergency": 0.01,
    "information_request": 0.03,
    "feedback_complaint": 0.00,
    "general_chat": 0.05,
    "assessment_request": 0.02
  },
  "processing_time_ms": 11,
  "routing_action": "BOOKING_FLOW"
}
```

---

## 4. Data Preparation

### 4.1 Data Sources

| Source | Examples | Description |
|--------|----------|-------------|
| Synthetic (GPT-4 + clinical review) | 1,800 | Diverse phrasings for each intent category |
| Real user interaction logs (anonymized) | 1,200 | Actual app usage data, relabeled |
| Mental health forum posts (labeled) | 600 | Reddit/forum posts with annotated intent |
| Customer service intent datasets (filtered) | 400 | Open-source datasets adapted for healthcare context |
| **Total** | **4,000** | |

### 4.2 Utterance Diversity Requirements

Each intent class must cover:
1. **Direct statements**: "I want to book a session"
2. **Indirect phrasings**: "Maybe it's time I talked to someone properly"
3. **Implicit signals**: "I've been meaning to get this sorted"
4. **Question forms**: "Is it possible to schedule a time this week?"
5. **Negative/refusal forms**: "I don't want to book yet, just talk"
6. **Multilingual signals**: Common Hinglish variations

```python
# Diversity check per intent class
for intent in INTENT_CLASSES:
    subset = df[df['primary_intent'] == intent]['utterance']
    avg_len = subset.str.split().apply(len).mean()
    unique_starts = subset.str.split().apply(lambda x: x[0].lower()).nunique()
    print(f"{intent}: n={len(subset)}, avg_len={avg_len:.1f}, unique_starts={unique_starts}")
    # Target: unique_starts > 15 per class (variety in phrasing)
```

### 4.3 Ambiguous Case Handling

Certain message patterns are genuinely ambiguous:
- "I need help" → could be `seek_support` OR `crisis_emergency`
- "What do I do?" → could be `information_request` OR `seek_support`

Resolution rule: When genuinely ambiguous, **label as the more supportive/safer intent** (prefer `crisis_emergency` over `seek_support` when any crisis signals exist).

---

## 5. Data Balance Strategy

### 5.1 Class Distribution

| Intent | Count | Target Count | Reason for Target |
|--------|-------|--------------|-------------------|
| seek_support | 1,200 | 1,000 | Most common user intent — slight downsample |
| book_appointment | 800 | 700 | Important commercial intent |
| crisis_emergency | 600 | 600 | Safety-critical — keep all examples |
| information_request | 500 | 500 | Keep as-is |
| feedback_complaint | 400 | 400 | Keep as-is |
| general_chat | 300 | 400 | Upsample with augmentation |
| assessment_request | 200 | 400 | Smallest class — double with augmentation |
| **Total** | **4,000** | **4,000** | |

### 5.2 Augmentation for assessment_request (Minority Class)

```python
ASSESSMENT_PARAPHRASES = [
    "I want to do the {assessment} questionnaire",
    "Can I take the {assessment} test?",
    "Let's do the {assessment} assessment",
    "I think I should complete the {assessment}",
    "Could you give me the {assessment} questions?",
    "I'd like to assess my {condition} levels",
    "Can we evaluate my {condition} today?",
]
ASSESSMENTS = ["PHQ-9", "GAD-7", "depression", "anxiety", "stress", "wellbeing", "PTSD"]
CONDITIONS = ["depression", "anxiety", "stress", "PTSD", "mood", "mental health"]

def generate_assessment_examples(n: int = 200) -> list:
    examples = []
    for _ in range(n):
        template = random.choice(ASSESSMENT_PARAPHRASES)
        assessment = random.choice(ASSESSMENTS)
        condition = random.choice(CONDITIONS)
        text = template.format(assessment=assessment, condition=condition)
        examples.append({"utterance": text, "primary_intent": "assessment_request"})
    return examples
```

---

## 6. Dataset Splits: Training, Validation, Testing

```
Full Dataset: 4,000 examples
├── Training Set:   3,200 examples (80%)
├── Validation Set:   400 examples (10%)
└── Test Set:         400 examples (10%)
```

```python
from sklearn.model_selection import train_test_split

train_df, temp_df = train_test_split(df, test_size=0.20, stratify=df['primary_intent'], random_state=42)
val_df, test_df = train_test_split(temp_df, test_size=0.50, stratify=temp_df['primary_intent'], random_state=42)
```

---

## 7. Dataset Evaluation & Quality Checks

### 7.1 Intent Confusion Matrix Pre-Analysis

Before training, identify inherently confusable intent pairs and ensure sufficient contrastive examples:

```python
# Pairs that need careful contrastive examples:
CONFUSABLE_PAIRS = [
    ("seek_support", "crisis_emergency"),      # "I can't take it anymore"
    ("seek_support", "general_chat"),           # "How are you?" vs "I'm struggling"
    ("book_appointment", "seek_support"),       # "I need to talk to someone"
    ("information_request", "assessment_request"),  # "How do I check my anxiety levels?"
]

# Ensure each confusable pair has ≥ 50 contrastive examples in training set
for a, b in CONFUSABLE_PAIRS:
    a_count = len(train_df[train_df['primary_intent'] == a])
    b_count = len(train_df[train_df['primary_intent'] == b])
    print(f"{a} vs {b}: {a_count} | {b_count}")
```

### 7.2 Intent-to-Route Validation

```python
# Validate that each intent maps to exactly one routing action
INTENT_ROUTING = {
    "seek_support": "THERAPEUTIC_CONVERSATION",
    "book_appointment": "BOOKING_FLOW",
    "crisis_emergency": "CRISIS_PROTOCOL",
    "information_request": "RAG_KNOWLEDGE_BASE",
    "feedback_complaint": "SUPPORT_HANDLER",
    "general_chat": "CONVERSATIONAL",
    "assessment_request": "ASSESSMENT_ROUTER"
}
assert len(INTENT_ROUTING) == len(INTENT_CLASSES), "Every intent must have a routing action"
```

---

## 8. Training Strategy

### 8.1 Training Configuration

```python
training_config = {
    "model_name": "distilbert-base-uncased",
    "num_labels": 7,
    "max_seq_length": 128,
    "batch_size": 32,
    "num_train_epochs": 4,
    "learning_rate": 3e-5,
    "warmup_ratio": 0.1,
    "weight_decay": 0.01,
    "dropout": 0.2,
    "fp16": True,
    "eval_metric": "macro_f1",
    "early_stopping_patience": 3,
    "seed": 42,
    # crisis_emergency gets higher class weight
    "class_weights": [1.5, 1.2, 3.0, 1.0, 1.0, 1.0, 2.0]
}
```

### 8.2 Special Handling for `crisis_emergency`

The `crisis_emergency` intent overlaps with the Crisis Detection Classifier. However, having it in the Intent Classifier serves a different purpose: routing the conversation. Even if the Crisis Classifier runs first and doesn't trigger (borderline cases), the Intent Classifier catching `crisis_emergency` at lower confidence still allows for elevated care routing.

Class weight for `crisis_emergency` is 3.0 (same principle as crisis detection: false negatives are worse than false positives).

---

## 9. Step-by-Step Training Process

### Step 1: Setup and Load Data

```bash
pip install transformers datasets scikit-learn torch wandb
```

```python
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from datasets import Dataset
from sklearn.model_selection import train_test_split

INTENT_CLASSES = ["seek_support","book_appointment","crisis_emergency",
                   "information_request","feedback_complaint","general_chat","assessment_request"]
LABEL2ID = {l:i for i,l in enumerate(INTENT_CLASSES)}

tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
model = AutoModelForSequenceClassification.from_pretrained(
    "distilbert-base-uncased",
    num_labels=7,
    id2label={i:l for i,l in enumerate(INTENT_CLASSES)},
    label2id=LABEL2ID
)

df = pd.read_csv('ml_pipeline/data/intent_classifier_v1.csv')
df['label'] = df['primary_intent'].map(LABEL2ID)

train_df, temp_df = train_test_split(df, test_size=0.2, stratify=df['label'], random_state=42)
val_df, test_df = train_test_split(temp_df, test_size=0.5, stratify=temp_df['label'], random_state=42)

def tokenize(examples):
    return tokenizer(examples['utterance'], max_length=128, truncation=True, padding='max_length')

train_ds = Dataset.from_pandas(train_df[['utterance','label']]).map(tokenize, batched=True)
val_ds = Dataset.from_pandas(val_df[['utterance','label']]).map(tokenize, batched=True)
test_ds = Dataset.from_pandas(test_df[['utterance','label']]).map(tokenize, batched=True)
```

### Step 2: Train with Class Weights

```python
import torch
import numpy as np
from transformers import TrainingArguments, Trainer
from sklearn.metrics import f1_score, accuracy_score

class_weights = torch.FloatTensor([1.5, 1.2, 3.0, 1.0, 1.0, 1.0, 2.0])

class IntentTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False):
        labels = inputs.get("labels")
        outputs = model(**inputs)
        loss = torch.nn.CrossEntropyLoss(
            weight=class_weights.to(self.args.device)
        )(outputs.logits, labels)
        return (loss, outputs) if return_outputs else loss

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "macro_f1": f1_score(labels, preds, average='macro')
    }

args = TrainingArguments(
    output_dir="./models/intent_classifier",
    num_train_epochs=4,
    per_device_train_batch_size=32,
    per_device_eval_batch_size=64,
    learning_rate=3e-5,
    warmup_ratio=0.1,
    evaluation_strategy="epoch",
    save_strategy="best",
    load_best_model_at_end=True,
    metric_for_best_model="eval_macro_f1",
    fp16=True,
    report_to="wandb",
    run_name="intent-classifier-v1",
    seed=42
)

trainer = IntentTrainer(
    model=model, args=args,
    train_dataset=train_ds, eval_dataset=val_ds,
    compute_metrics=compute_metrics
)
trainer.train()
```

### Step 3: Evaluate and Save

```python
from sklearn.metrics import classification_report

test_result = trainer.predict(test_ds)
preds = np.argmax(test_result.predictions, axis=-1)
print(classification_report(test_ds['label'], preds, target_names=INTENT_CLASSES))

model.save_pretrained("./models/intent_classifier_saathi_v1")
tokenizer.save_pretrained("./models/intent_classifier_saathi_v1")
```

---

## 10. Model Evaluation

### 10.1 Target Metrics

| Metric | Target |
|--------|--------|
| Overall Accuracy | ≥ 88% |
| Macro F1 | ≥ 0.85 |
| crisis_emergency Recall | ≥ 95% |
| book_appointment F1 | ≥ 0.90 |
| assessment_request F1 | ≥ 0.80 |

### 10.2 Routing Accuracy Test

```python
# Test that detected intents map to correct routing actions
ROUTING_TESTS = [
    ("I need to book a session this week", "BOOKING_FLOW"),
    ("I want to kill myself", "CRISIS_PROTOCOL"),
    ("What is CBT?", "RAG_KNOWLEDGE_BASE"),
    ("Can I do the depression test?", "ASSESSMENT_ROUTER"),
    ("This app sucks", "SUPPORT_HANDLER"),
]

for utterance, expected_route in ROUTING_TESTS:
    result = intent_service.classify(utterance)
    actual_route = INTENT_ROUTING[result['primary_intent']]
    assert actual_route == expected_route, f"Routing mismatch: '{utterance}' → {actual_route} (expected {expected_route})"
print("All routing tests passed ✅")
```

---

## 11. Downloading & Saving Weights

```python
# Save model
model.save_pretrained("./therapeutic-copilot/server/ml_models/intent_classifier")
tokenizer.save_pretrained("./therapeutic-copilot/server/ml_models/intent_classifier")

# Production structure
# therapeutic-copilot/server/ml_models/
# └── intent_classifier/
#     ├── config.json
#     ├── pytorch_model.bin    (~250MB)
#     ├── tokenizer.json
#     └── vocab.txt
```

---

## 12. Integrating Trained Weights into the App Workflow

### 12.1 IntentClassifierService

```python
# therapeutic-copilot/server/services/intent_classifier_service.py

import torch, time
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification

INTENT_CLASSES = ["seek_support","book_appointment","crisis_emergency",
                   "information_request","feedback_complaint","general_chat","assessment_request"]

INTENT_ROUTING = {
    "seek_support": "THERAPEUTIC_CONVERSATION",
    "book_appointment": "BOOKING_FLOW",
    "crisis_emergency": "CRISIS_PROTOCOL",
    "information_request": "RAG_KNOWLEDGE_BASE",
    "feedback_complaint": "SUPPORT_HANDLER",
    "general_chat": "CONVERSATIONAL",
    "assessment_request": "ASSESSMENT_ROUTER"
}

class IntentClassifierService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        path = "./ml_models/intent_classifier"
        self.tokenizer = AutoTokenizer.from_pretrained(path)
        self.model = AutoModelForSequenceClassification.from_pretrained(path)
        self.model.eval()
        self._initialized = True

    def classify(self, utterance: str) -> dict:
        start = time.time()
        inputs = self.tokenizer(utterance, max_length=128, truncation=True,
                                 padding='max_length', return_tensors='pt')
        with torch.no_grad():
            probs = torch.softmax(self.model(**inputs).logits, dim=-1).numpy()[0]

        sorted_idx = np.argsort(probs)[::-1]
        primary_idx = sorted_idx[0]
        secondary_idx = sorted_idx[1] if probs[sorted_idx[1]] > 0.35 else None

        primary_intent = INTENT_CLASSES[primary_idx]
        return {
            "primary_intent": primary_intent,
            "secondary_intent": INTENT_CLASSES[secondary_idx] if secondary_idx is not None else None,
            "confidence": float(probs[primary_idx]),
            "routing_action": INTENT_ROUTING[primary_intent],
            "all_scores": {cls: float(probs[i]) for i, cls in enumerate(INTENT_CLASSES)},
            "processing_time_ms": round((time.time()-start)*1000, 1)
        }
```

### 12.2 Router Integration

```python
# In chat_routes.py

@router.post("/chat/message")
async def process_message(request: ChatMessageRequest):
    message = request.message

    # Run classifiers in parallel (emotion + intent, after crisis check)
    emotion_result = emotion_service.classify(message)
    intent_result = intent_service.classify(message)

    routing = intent_result['routing_action']

    if routing == "BOOKING_FLOW":
        return await booking_handler(message, intent_result, request.session_id)
    elif routing == "CRISIS_PROTOCOL":
        return await crisis_handler(message, crisis_result)
    elif routing == "RAG_KNOWLEDGE_BASE":
        return await rag_handler(message, intent_result)
    elif routing == "ASSESSMENT_ROUTER":
        return await assessment_handler(message, intent_result, request.session_id)
    else:  # THERAPEUTIC_CONVERSATION, CONVERSATIONAL, SUPPORT_HANDLER
        return await therapeutic_handler(message, emotion_result, intent_result, request.session_id)
```

---

## 13. Building Prompt Context with Model Output

### 13.1 Intent-Aware Prompt Augmentation

```python
INTENT_PROMPT_CONTEXT = {
    "seek_support": {
        "mode": "therapeutic",
        "instruction": "The user is seeking emotional support. Enter therapeutic listening mode. Prioritize validation over information.",
        "response_style": "empathetic, exploratory, non-directive"
    },
    "book_appointment": {
        "mode": "booking",
        "instruction": "The user wants to schedule a session. Acknowledge their readiness, gather availability, and guide them through the booking process warmly.",
        "response_style": "helpful, action-oriented, warm"
    },
    "information_request": {
        "mode": "educational",
        "instruction": "The user wants information. Retrieve from the knowledge base and present clearly. Offer follow-up support after answering.",
        "response_style": "clear, educational, supportive"
    },
    "assessment_request": {
        "mode": "assessment",
        "instruction": "The user wants to take an assessment. Ask which assessment they want, or recommend one based on conversation context.",
        "response_style": "structured, warm, clinical"
    },
    "general_chat": {
        "mode": "conversational",
        "instruction": "The user wants light conversation. Engage warmly but gently explore what brings them here today.",
        "response_style": "casual, curious, warm"
    },
    "feedback_complaint": {
        "mode": "support",
        "instruction": "The user has feedback or a complaint. Acknowledge sincerely, apologize where appropriate, and offer to help resolve.",
        "response_style": "professional, empathetic, solution-oriented"
    }
}

def build_intent_context_block(intent_result: dict) -> str:
    intent = intent_result['primary_intent']
    config = INTENT_PROMPT_CONTEXT.get(intent, {})
    secondary = intent_result.get('secondary_intent')

    block = f"""
## User Intent (ML Classifier)
- **Primary Intent**: {intent} (confidence: {intent_result['confidence']:.0%})
- **Routing**: {intent_result['routing_action']}
- **Mode**: {config.get('mode', 'conversational')}
- **Instruction**: {config.get('instruction', '')}
- **Response Style**: {config.get('response_style', 'empathetic')}
"""
    if secondary:
        secondary_config = INTENT_PROMPT_CONTEXT.get(secondary, {})
        block += f"\n- **Secondary Intent Also Present**: {secondary} — {secondary_config.get('instruction', '')}\n"

    return block
```

---

## Summary

| Aspect | Decision |
|--------|----------|
| Architecture | DistilBERT fine-tuned, 7-class |
| Dataset | 4,000 examples, domain-specific |
| Balance | crisis_emergency and assessment_request weighted/upsampled |
| Primary metric | Macro F1 ≥ 0.85; crisis_emergency recall ≥ 95% |
| Integration | Runs in parallel with emotion classifier, before LLM call |
| Prompt use | Injects intent label, mode, and response style instruction into system prompt |

---

*Document Version: 1.0 | Model Version: intent_classifier_saathi_v1 | Last Updated: 2025-03*
