# Model Document 04: Topic Classifier
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
The **Topic Classifier** identifies the *domain or life area* the user's concern is rooted in. While emotion tells us *how* the user feels and intent tells us *what they want*, topic tells us *what their life situation is about*. This allows the therapeutic AI to apply domain-specific knowledge, techniques, and resources.

### Why It Matters
The appropriate therapeutic technique differs significantly by topic:
- **Workplace stress** → Boundaries, assertiveness training, burnout prevention, occupational therapy frameworks
- **Relationship issues** → Attachment theory, communication skills, couples therapy frameworks (even for individuals)
- **Academic stress** → Performance anxiety, perfectionism, time management, exam anxiety CBT
- **Financial stress** → Cognitive defusion from money shame, practical problem-solving, stress resilience
- **Health concerns** → Health anxiety, somatic symptom awareness, psychosomatic connections

Without topic classification, the LLM defaults to generic therapeutic responses that miss the specific vocabulary, frameworks, and resources most relevant to the user's situation.

### Scope
- **Input**: Single user utterance or conversation context summary (up to 256 tokens)
- **Output**: `topic` (primary), `confidence`, `secondary_topic` (if any), all topic scores
- **Classes**: 5 topic categories (expandable to 8+ in v2)

---

## 2. Why We Chose This Model Architecture

### Architecture: Fine-tuned `distilbert-base-uncased` (Multi-label capable)

#### Multi-Label vs. Multi-Class
The topic classifier is trained as **multi-label** (a user can have both workplace stress AND relationship issues simultaneously). The model outputs independent probabilities for each topic using sigmoid activation instead of softmax.

```python
# Multi-label: sigmoid on each class independently
import torch
logits = model_output  # shape: (batch, 5)
probs = torch.sigmoid(logits)  # each class independently 0-1
# vs. multi-class softmax which forces exactly one class
```

#### Why Multi-Label?
- "My boss keeps micromanaging me and it's affecting my marriage" → workplace_stress + relationship_issues
- "I can't focus on my exams because I'm worried about my health" → academic_stress + health_concerns
- Reality: life stressors rarely exist in isolation

#### Why DistilBERT Again?
- Topic classification is a "gentler" task than emotion or crisis detection — less nuanced, more lexical
- Fast (<12ms) and consistent with the rest of the ML pipeline

---

## 3. Schema Design

### 3.1 Dataset Schema (CSV Format)

```csv
id,utterance,topics,primary_topic,confidence,source,annotator_id,created_at
```

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | string | UUID | `topic_004512` |
| `utterance` | string | User text | `"My manager won't stop criticizing me"` |
| `topics` | list[enum] | All applicable topics | `["workplace_stress"]` |
| `primary_topic` | enum | Most dominant topic | `workplace_stress` |
| `confidence` | float (0.0–1.0) | Label confidence | `0.93` |
| `source` | enum | Data origin | `synthetic`, `forum_scraped` |
| `annotator_id` | string | Annotator ID | `ann_007` |
| `created_at` | ISO datetime | Timestamp | `2024-10-20T11:15:00Z` |

### 3.2 Topic Taxonomy (v1 — 5 Classes)

```
topics/
├── workplace_stress        → job pressure, boss issues, deadlines, burnout, career anxiety
├── relationship_issues     → romantic partner, family conflict, friendship problems, divorce, loneliness
├── academic_stress         → exams, grades, performance pressure, student loans, career uncertainty
├── health_concerns         → illness, chronic pain, medical anxiety, somatic complaints, health fear
└── financial_stress        → debt, job loss, money anxiety, poverty stress, financial shame
```

### 3.3 Future Expansion (v2 Topics)

```
(planned for v2)
├── grief_and_loss          → bereavement, relationship ending, life transitions
├── identity_and_purpose    → existential questions, life meaning, identity confusion
└── trauma_and_ptsd         → past trauma, PTSD triggers, abuse history (handled carefully)
```

### 3.4 Model Output Schema (JSON)

```json
{
  "primary_topic": "workplace_stress",
  "secondary_topic": "relationship_issues",
  "confidence": 0.88,
  "secondary_confidence": 0.51,
  "all_scores": {
    "workplace_stress": 0.88,
    "relationship_issues": 0.51,
    "academic_stress": 0.04,
    "health_concerns": 0.09,
    "financial_stress": 0.12
  },
  "active_topics": ["workplace_stress", "relationship_issues"],
  "processing_time_ms": 10
}
```

---

## 4. Data Preparation

### 4.1 Data Sources

| Source | Examples | Description |
|--------|----------|-------------|
| Synthetic (GPT-4 + domain experts) | 900 | Expert-crafted examples across all 5 topics |
| Reddit/forum posts (r/work, r/relationships etc.) | 600 | Real user posts, labeled by domain |
| Mental health intake questionnaire responses | 300 | Clinical intake notes, de-identified |
| Open-source mental health datasets (filtered) | 200 | Publicly available clinical datasets |
| **Total** | **2,000** | |

### 4.2 Domain Expert Review

Each topic has an assigned domain expert who reviewed examples for authenticity:
- **Workplace stress**: HR professional + occupational psychologist
- **Relationship issues**: Couples therapist
- **Academic stress**: Student counselor
- **Health concerns**: Psychosomatic medicine practitioner
- **Financial stress**: Financial wellness counselor

### 4.3 Multi-Label Annotation Process

```python
# Annotation schema: annotators choose all applicable topics
# Example annotation:
{
    "utterance": "I can't focus on my thesis deadline because my partner and I keep fighting about money",
    "topics": ["academic_stress", "relationship_issues", "financial_stress"],  # 3 labels
    "primary_topic": "academic_stress",  # most dominant
    "confidence": 0.85
}
```

Annotation rules:
1. Select ALL topics clearly present (not just inferred)
2. Primary topic = the one the user seems most focused on
3. Topic must be explicitly or strongly implicitly mentioned — no stretching
4. Minimum 0.70 confidence to include as a label

---

## 5. Data Balance Strategy

### 5.1 Class Distribution

| Topic | Count | % | Notes |
|-------|-------|---|-------|
| workplace_stress | 550 | 27.5% | Common but slightly overrepresented — minor downsample |
| relationship_issues | 500 | 25.0% | Keep as-is |
| academic_stress | 400 | 20.0% | Keep as-is |
| health_concerns | 300 | 15.0% | Keep as-is |
| financial_stress | 250 | 12.5% | Smallest — augment slightly |
| **Total** | **2,000** | | |

### 5.2 Multi-Label Balancing
Because this is multi-label, traditional class balancing must consider label co-occurrence. Use `sklearn`'s `IterativeStratification` for multi-label splits:

```python
from iterstrat.ml_stratifiers import MultilabelStratifiedKFold

# Convert to binary matrix
from sklearn.preprocessing import MultiLabelBinarizer
mlb = MultiLabelBinarizer(classes=TOPICS)
y_matrix = mlb.fit_transform(df['topics'])

# Stratified split preserving multi-label distribution
mskf = MultilabelStratifiedKFold(n_splits=10, shuffle=True, random_state=42)
for train_idx, test_idx in mskf.split(df, y_matrix):
    break  # use first split

X_train = df.iloc[train_idx]['utterance'].values
y_train = y_matrix[train_idx]
X_test = df.iloc[test_idx]['utterance'].values
y_test = y_matrix[test_idx]
```

---

## 6. Dataset Splits

```
Full Dataset: 2,000 examples
├── Training:   1,600 examples (80%)
├── Validation:   200 examples (10%)
└── Test:         200 examples (10%)
```

---

## 7. Dataset Evaluation & Quality Checks

```python
# Check multi-label co-occurrence matrix
import pandas as pd
import numpy as np

co_occurrence = pd.DataFrame(
    np.dot(y_matrix.T, y_matrix),
    index=TOPICS, columns=TOPICS
)
print("Topic Co-occurrence Matrix:")
print(co_occurrence)
# This shows which topics appear together most — validates dataset realism

# Check label frequency
print("\nLabel Frequency:")
for i, topic in enumerate(TOPICS):
    count = y_matrix[:, i].sum()
    print(f"  {topic}: {count} ({count/len(y_matrix)*100:.1f}%)")
```

---

## 8. Training Strategy

### 8.1 Multi-Label Classification Setup

```python
# Multi-label classification uses Binary Cross-Entropy (not Cross-Entropy)
# One sigmoid per class, independent probabilities

training_config = {
    "model_name": "distilbert-base-uncased",
    "num_labels": 5,
    "problem_type": "multi_label_classification",  # key setting
    "max_seq_length": 128,
    "batch_size": 32,
    "num_train_epochs": 4,
    "learning_rate": 3e-5,
    "warmup_ratio": 0.1,
    "fp16": True,
    "eval_metric": "f1_samples",  # multi-label specific metric
    "threshold": 0.50,             # per-class threshold for positive prediction
    "seed": 42
}
```

### 8.2 Loss Function for Multi-Label

```python
import torch.nn as nn

# Binary cross-entropy with logits for each class independently
loss_fn = nn.BCEWithLogitsLoss()

# In forward pass:
# logits shape: (batch_size, 5)
# labels shape: (batch_size, 5) — binary matrix
# loss = BCEWithLogitsLoss(logits, labels)
```

---

## 9. Step-by-Step Training Process

### Step 1: Prepare Multi-Label Dataset

```python
import torch
from torch.utils.data import Dataset

class TopicDataset(Dataset):
    def __init__(self, utterances, labels, tokenizer, max_length=128):
        self.encodings = tokenizer(
            list(utterances), max_length=max_length,
            truncation=True, padding='max_length', return_tensors='pt'
        )
        self.labels = torch.FloatTensor(labels)  # Binary matrix

    def __getitem__(self, idx):
        item = {k: v[idx] for k, v in self.encodings.items()}
        item['labels'] = self.labels[idx]
        return item

    def __len__(self):
        return len(self.labels)

train_dataset = TopicDataset(X_train, y_train, tokenizer)
val_dataset = TopicDataset(X_val, y_val, tokenizer)
test_dataset = TopicDataset(X_test, y_test, tokenizer)
```

### Step 2: Training Loop

```python
from transformers import TrainingArguments, Trainer
import numpy as np
from sklearn.metrics import f1_score

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    probs = torch.sigmoid(torch.FloatTensor(logits)).numpy()
    preds = (probs >= 0.50).astype(int)
    return {
        "f1_samples": f1_score(labels, preds, average='samples'),
        "f1_macro": f1_score(labels, preds, average='macro'),
        "f1_micro": f1_score(labels, preds, average='micro')
    }

args = TrainingArguments(
    output_dir="./models/topic_classifier",
    num_train_epochs=4,
    per_device_train_batch_size=32,
    per_device_eval_batch_size=64,
    learning_rate=3e-5,
    warmup_ratio=0.1,
    evaluation_strategy="epoch",
    save_strategy="best",
    load_best_model_at_end=True,
    metric_for_best_model="eval_f1_samples",
    fp16=True,
    report_to="wandb",
    run_name="topic-classifier-v1"
)

model = AutoModelForSequenceClassification.from_pretrained(
    "distilbert-base-uncased",
    num_labels=5,
    problem_type="multi_label_classification"
)

trainer = Trainer(
    model=model, args=args,
    train_dataset=train_dataset, eval_dataset=val_dataset,
    compute_metrics=compute_metrics
)
trainer.train()
```

### Step 3: Find Optimal Per-Class Thresholds

```python
# Sweep thresholds on validation set to maximize F1 per class
val_logits = trainer.predict(val_dataset).predictions
val_probs = torch.sigmoid(torch.FloatTensor(val_logits)).numpy()

optimal_thresholds = {}
for i, topic in enumerate(TOPICS):
    best_f1, best_t = 0, 0.5
    for t in np.arange(0.3, 0.8, 0.05):
        preds = (val_probs[:, i] >= t).astype(int)
        f1 = f1_score(y_val[:, i], preds)
        if f1 > best_f1:
            best_f1, best_t = f1, t
    optimal_thresholds[topic] = best_t
    print(f"{topic}: optimal threshold={best_t:.2f}, F1={best_f1:.3f}")

import json
with open("models/topic_classifier/thresholds.json", "w") as f:
    json.dump(optimal_thresholds, f, indent=2)
```

### Step 4: Save Model

```python
model.save_pretrained("./models/topic_classifier_saathi_v1")
tokenizer.save_pretrained("./models/topic_classifier_saathi_v1")
```

---

## 10. Model Evaluation

| Metric | Target |
|--------|--------|
| F1 (samples) | ≥ 0.82 |
| F1 (macro) | ≥ 0.80 |
| F1 per class | ≥ 0.75 |
| Multi-label accuracy | ≥ 78% |
| Inference latency | < 15ms |

---

## 11. Downloading & Saving Weights

```
therapeutic-copilot/server/ml_models/
└── topic_classifier/
    ├── config.json
    ├── pytorch_model.bin    (~250MB)
    ├── tokenizer.json
    ├── vocab.txt
    └── thresholds.json      # per-class classification thresholds
```

---

## 12. Integrating Trained Weights into the App Workflow

### 12.1 TopicClassifierService

```python
# therapeutic-copilot/server/services/topic_classifier_service.py

import torch, time, json
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification

TOPICS = ["workplace_stress","relationship_issues","academic_stress","health_concerns","financial_stress"]

class TopicClassifierService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        path = "./ml_models/topic_classifier"
        self.tokenizer = AutoTokenizer.from_pretrained(path)
        self.model = AutoModelForSequenceClassification.from_pretrained(path)
        self.model.eval()
        with open(f"{path}/thresholds.json") as f:
            self.thresholds = json.load(f)
        self._initialized = True

    def classify(self, utterance: str) -> dict:
        start = time.time()
        inputs = self.tokenizer(utterance, max_length=128, truncation=True,
                                 padding='max_length', return_tensors='pt')
        with torch.no_grad():
            probs = torch.sigmoid(self.model(**inputs).logits).numpy()[0]

        active_topics = [t for i, t in enumerate(TOPICS)
                         if probs[i] >= self.thresholds.get(t, 0.50)]

        sorted_idx = np.argsort(probs)[::-1]
        primary_topic = TOPICS[sorted_idx[0]] if probs[sorted_idx[0]] >= 0.40 else None
        secondary_topic = TOPICS[sorted_idx[1]] if (len(sorted_idx) > 1 and
                                                      probs[sorted_idx[1]] >= 0.40 and
                                                      TOPICS[sorted_idx[1]] != primary_topic) else None

        return {
            "primary_topic": primary_topic,
            "secondary_topic": secondary_topic,
            "active_topics": active_topics,
            "confidence": float(probs[sorted_idx[0]]),
            "all_scores": {t: float(probs[i]) for i, t in enumerate(TOPICS)},
            "processing_time_ms": round((time.time()-start)*1000, 1)
        }
```

---

## 13. Building Prompt Context with Model Output

### 13.1 Topic-Specific Therapeutic Frameworks

```python
TOPIC_THERAPEUTIC_CONTEXT = {
    "workplace_stress": {
        "key_frameworks": ["CBT for burnout", "Acceptance and Commitment Therapy (values/flexibility)",
                           "Assertiveness training", "Job demands-resources model"],
        "common_concerns": ["toxic boss/manager", "overwork", "lack of recognition",
                           "job insecurity", "work-life imbalance"],
        "helpful_resources": ["Occupational health psychologist", "EAP programs",
                              "Burnout assessment (MBI)"],
        "prompt_instruction": "Apply occupational psychology frameworks. Explore the specific workplace dynamics. Use ACT to address values-work alignment."
    },
    "relationship_issues": {
        "key_frameworks": ["Attachment theory (Bowlby/Ainsworth)", "Gottman Method",
                           "Emotionally Focused Therapy (EFT)", "DBT interpersonal effectiveness"],
        "common_concerns": ["communication breakdown", "trust issues", "intimacy",
                           "conflict patterns", "codependency", "loneliness"],
        "helpful_resources": ["Couples therapist", "Communication skills workshops"],
        "prompt_instruction": "Explore attachment patterns gently. Use Gottman's Four Horsemen as a framework for relationship conflict understanding."
    },
    "academic_stress": {
        "key_frameworks": ["CBT for performance anxiety", "Growth mindset (Dweck)",
                           "Self-compassion (Neff)", "Pomodoro technique psychoeducation"],
        "common_concerns": ["exam anxiety", "perfectionism", "procrastination",
                           "imposter syndrome", "parental pressure"],
        "helpful_resources": ["Student counseling services", "Academic support"],
        "prompt_instruction": "Distinguish between healthy pressure and unhealthy perfectionism. Explore the fear underneath academic stress."
    },
    "health_concerns": {
        "key_frameworks": ["Health Anxiety CBT", "Somatic symptom awareness",
                           "Psychosomatic connections", "Illness acceptance framework"],
        "common_concerns": ["chronic illness", "health anxiety", "pain",
                           "medical procedures", "fear of dying"],
        "helpful_resources": ["Integrated mental-physical health care", "Pain management programs"],
        "prompt_instruction": "Validate the reality of physical experience while exploring the anxiety component. Be careful not to dismiss physical symptoms."
    },
    "financial_stress": {
        "key_frameworks": ["Cognitive defusion from money shame", "Problem-solving therapy",
                           "Financial resilience", "Mindfulness of scarcity mindset"],
        "common_concerns": ["debt", "job loss", "poverty", "financial shame",
                           "providing for family"],
        "helpful_resources": ["Financial counseling", "Government support resources"],
        "prompt_instruction": "Address shame around financial struggles first — money stress carries significant stigma. Separate the person's worth from their financial situation."
    }
}

def build_topic_context_block(topic_result: dict) -> str:
    topics = topic_result['active_topics']
    if not topics:
        return ""

    blocks = []
    for topic in topics[:2]:  # Max 2 topics in prompt
        config = TOPIC_THERAPEUTIC_CONTEXT.get(topic, {})
        blocks.append(f"""
### Topic: {topic.replace('_', ' ').title()}
- **Frameworks**: {', '.join(config.get('key_frameworks', [])[:2])}
- **Common Concerns in This Domain**: {', '.join(config.get('common_concerns', [])[:4])}
- **Instruction**: {config.get('prompt_instruction', '')}
""")

    return "## Topic Context (ML Classifier)\n" + "\n".join(blocks)
```

### 13.2 Complete Prompt Context Assembly

```python
def build_complete_system_prompt(
    base_prompt: str,
    emotion_result: dict,
    intent_result: dict,
    topic_result: dict,
    therapeutic_step: str,
    session_history: list
) -> str:
    """
    Assembles the complete system prompt with all ML classifier outputs.
    """
    emotion_block = build_emotion_aware_system_prompt("", emotion_result, therapeutic_step, {})
    intent_block = build_intent_context_block(intent_result)
    topic_block = build_topic_context_block(topic_result)

    return f"""{base_prompt}

{emotion_block}

{intent_block}

{topic_block}

## Current Step: {therapeutic_step}
"""
```

---

## Summary

| Aspect | Decision |
|--------|----------|
| Architecture | DistilBERT fine-tuned, multi-label (5 classes) |
| Dataset | 2,000 examples, expert-reviewed per domain |
| Training objective | Binary Cross-Entropy (independent per-class) |
| Threshold | Per-class optimal thresholds (0.35–0.65 range) |
| Integration | Runs alongside emotion/intent classifiers |
| Prompt use | Injects domain-specific therapeutic frameworks and instructions |

---

*Document Version: 1.0 | Model Version: topic_classifier_saathi_v1 | Last Updated: 2025-03*
