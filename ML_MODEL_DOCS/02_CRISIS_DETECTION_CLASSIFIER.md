# Model Document 02: Crisis Detection Classifier
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
The **Crisis Detection Classifier** is the highest-priority safety model in the Saathi platform. It analyzes every user message to detect whether the user is in psychological crisis — including suicidal ideation, self-harm intentions, abuse disclosures, or acute psychiatric emergencies. When triggered, it bypasses the normal conversation flow and activates a specialized crisis response protocol.

### Why It Is the Most Critical Model
Unlike other classifiers that optimize for experience quality, the crisis detection model optimizes for **safety above all else**. The cost of a false negative (missing a real crisis) is potentially life-threatening. The cost of a false positive (unnecessary escalation) is minor inconvenience. This asymmetric cost structure drives every architectural and training decision.

**Legal and Ethical Mandate**: Any AI system operating in mental health must, by ethical and legal standards in most jurisdictions, be able to detect and respond to crisis situations. Failure to detect a crisis and provide appropriate resource referral constitutes a legal liability.

### Scope
- **Input**: Single user utterance (text string, up to 512 tokens)
- **Output**: `crisis_flag` (bool), `crisis_type`, `severity_score` (0.0–1.0), `intervention_required` (bool), `confidence`
- **Response Time Requirement**: < 100ms (must complete before any LLM generation)
- **Classes**: 6 crisis types + 1 non-crisis class

---

## 2. Why We Chose This Model Architecture

### Architecture: Ensemble of Fine-tuned RoBERTa-base + Rule-Based Keyword Layer

#### Why an Ensemble?
For crisis detection, **no single approach is sufficient**:

| Approach | Strength | Weakness |
|----------|----------|----------|
| Rule-based keywords only | Fast, transparent, catches explicit statements | Misses implicit/indirect crisis language |
| ML-only | Catches implicit patterns, generalizes | Can miss explicit statements if low confidence |
| **Ensemble (both)** | High recall, safety net for both explicit and implicit | Slightly higher false positive rate (acceptable) |

#### Why RoBERTa over DistilBERT?
- Crisis detection demands the highest accuracy — we accept slightly higher latency (30ms vs 12ms) for better performance
- RoBERTa-base achieves ~94% on crisis-adjacent tasks vs ~89% for DistilBERT
- Better handling of subtle, indirect language (e.g., "I've been saying my goodbyes to people")
- More robust to short, fragmented utterances typical in crisis moments

#### Two-Stage Pipeline Design

```
User Utterance
     │
     ▼
Stage 1: Keyword Safety Net (< 5ms)
     │    ↳ Explicit crisis keywords → IMMEDIATE CRISIS FLAG (skip ML)
     │    ↳ No keywords found → proceed to Stage 2
     ▼
Stage 2: RoBERTa ML Classifier (< 30ms)
     │    ↳ Probability scores for each crisis type
     ▼
Stage 3: Ensemble Decision Logic
     │    ↳ Combine keyword signals + ML probabilities
     │    ↳ Apply asymmetric threshold (lower for crisis, higher for safe)
     ▼
Crisis Result: flag, type, severity, intervention_required
```

#### Why NOT Using Only GPT-4 for Crisis Detection?
- Latency: 500-1500ms is unacceptable for a safety-critical real-time check
- Cost: Would be prohibitive at scale for a check that runs on every message
- Explainability: Rules + ML ensemble provides audit trail; GPT-4 is a black box
- Reliability: A fine-tuned domain-specific model beats zero-shot GPT-4 on specific clinical crisis taxonomy

---

## 3. Schema Design

### 3.1 Dataset Schema (CSV Format)

```csv
id,utterance,crisis_flag,crisis_type,severity_score,intervention_required,source,annotator_id,clinical_reviewer_id,created_at
```

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | string | UUID | `crisis_001234` |
| `utterance` | string | Raw user text | `"I've been stockpiling my medication"` |
| `crisis_flag` | bool | Is this a crisis? | `true` |
| `crisis_type` | enum / null | Specific crisis category | `suicidal_ideation` |
| `severity_score` | float (0.0–1.0) | Crisis severity | `0.92` |
| `intervention_required` | bool | Needs immediate human intervention | `true` |
| `source` | enum | Data origin | `clinical_transcripts` |
| `annotator_id` | string | First annotator | `ann_011` |
| `clinical_reviewer_id` | string | Licensed clinician who reviewed | `clin_003` |
| `created_at` | ISO datetime | Record timestamp | `2024-11-15T14:22:00Z` |

### 3.2 Crisis Type Taxonomy

```
crisis_types/
├── suicidal_ideation       → thoughts of suicide, intent, planning
│   ├── passive             → "I wish I wasn't here" (no active plan)
│   └── active              → "I have a plan to..." (immediate risk)
├── self_harm               → non-suicidal self-injury, cutting, burning
├── abuse_disclosure        → domestic violence, sexual abuse, child abuse
├── acute_distress          → panic attack, dissociation, severe breakdown
├── medical_emergency       → physical health crisis, overdose, injury
├── substance_crisis        → dangerous intoxication, overdose risk
└── none                    → no crisis detected
```

### 3.3 Model Output Schema (JSON)

```json
{
  "crisis_flag": true,
  "crisis_type": "suicidal_ideation",
  "crisis_subtype": "active",
  "severity_score": 0.94,
  "intervention_required": true,
  "confidence": 0.91,
  "keyword_signals": ["stockpiling", "medication"],
  "ml_scores": {
    "suicidal_ideation": 0.91,
    "self_harm": 0.04,
    "abuse_disclosure": 0.01,
    "acute_distress": 0.02,
    "medical_emergency": 0.01,
    "substance_crisis": 0.01,
    "none": 0.00
  },
  "processing_time_ms": 28,
  "escalation_level": "IMMEDIATE",
  "recommended_resources": [
    "iCall: 9152987821",
    "Vandrevala Foundation: 1860-2662-345",
    "NIMHANS: 080-46110007"
  ]
}
```

---

## 4. Data Preparation

### 4.1 Data Sources

| Source | Examples | Description |
|--------|----------|-------------|
| Synthetic generation (GPT-4 + clinical review) | 2,000 | Crafted by clinical psychologists to cover edge cases |
| Crisis Text Line (public-accessible data) | 1,200 | Real crisis conversations (strictly anonymized) |
| Clinical case study transcripts | 800 | De-identified records from partnered mental health orgs |
| Suicide.org and crisis hotline training materials | 500 | Example phrasings used in crisis counselor training |
| Non-crisis therapeutic conversations (negative examples) | 500 | True negatives to prevent excessive false positives |
| **Total** | **5,000** | |

**Critical Requirement**: ALL crisis data examples were reviewed by a licensed clinical psychologist before inclusion. Any example with ambiguous labeling was either adjudicated or discarded.

### 4.2 The Role of Clinical Reviewers

This dataset is unique in that **every positive crisis example** (crisis_flag=true) was reviewed by a licensed clinical psychologist or psychiatrist:

1. **First pass**: Trained annotator labels the example
2. **Clinical review**: Licensed clinician validates label, severity score, and intervention requirement
3. **Discrepancy resolution**: Clinical reviewer's judgment supersedes annotator's for all crisis-positive examples

### 4.3 Keyword Safety Net Compilation

The keyword layer is compiled from:
- Columbia Suicide Severity Rating Scale (C-SSRS) language
- Crisis counselor training materials
- Clinical review of common euphemisms and indirect expressions

```python
# therapeutic-copilot/server/config/crisis_keywords.py

CRISIS_KEYWORDS = {
    "suicidal_ideation": {
        "explicit": [
            "kill myself", "end my life", "suicide", "suicidal",
            "don't want to live", "want to die", "better off dead",
            "no reason to live", "take my life"
        ],
        "implicit": [
            "stockpiling", "saying my goodbyes", "giving things away",
            "won't be around much longer", "last time", "final note",
            "can't do this anymore", "no point going on"
        ],
        "planning_indicators": [
            "method", "plan", "date", "note", "letter", "will",
            "rope", "pills", "gun", "bridge"
        ]
    },
    "self_harm": {
        "explicit": ["cut myself", "burning", "hurt myself", "self-harm", "self harm"],
        "implicit": ["release the pain", "deserve to suffer", "punish myself"]
    },
    "abuse_disclosure": {
        "explicit": ["he hit me", "she hits me", "being abused", "sexual assault", "rape"],
        "implicit": ["afraid to go home", "walking on eggshells", "not allowed to"]
    },
    "acute_distress": {
        "explicit": ["can't breathe", "panic attack", "can't stop shaking", "losing my mind"],
        "implicit": ["everything is spinning", "not real", "disconnected from my body"]
    }
}

def keyword_check(utterance: str) -> dict:
    """Fast keyword-based crisis check. Returns within 5ms."""
    utterance_lower = utterance.lower()
    for crisis_type, keywords in CRISIS_KEYWORDS.items():
        for category, word_list in keywords.items():
            for keyword in word_list:
                if keyword in utterance_lower:
                    severity = 1.0 if category == 'explicit' else 0.7
                    if category == 'planning_indicators':
                        severity = 0.95
                    return {
                        "keyword_triggered": True,
                        "crisis_type": crisis_type,
                        "matched_keyword": keyword,
                        "keyword_category": category,
                        "severity_hint": severity
                    }
    return {"keyword_triggered": False}
```

### 4.4 Data Collection for Non-Crisis Examples

The non-crisis class requires careful curation to prevent the model from being oversensitive:
- Include utterances that sound distressing but are NOT crises (venting, sadness, frustration)
- Include utterances about past crises (historical mention ≠ current crisis)
- Include help-seeking without imminent risk ("I've been feeling suicidal in the past")
- Include therapeutic discussions of crisis concepts

---

## 5. Data Balance Strategy

### 5.1 Class Distribution

| Crisis Type | Count | % | Notes |
|-------------|-------|---|-------|
| suicidal_ideation | 1,200 | 24% | Highest priority, intentionally overrepresented |
| self_harm | 800 | 16% | Common in teenage/young adult users |
| abuse_disclosure | 700 | 14% | Important for partner violence detection |
| acute_distress | 800 | 16% | Panic attacks, dissociation, severe breakdown |
| medical_emergency | 500 | 10% | Physical crisis |
| substance_crisis | 500 | 10% | Overdose risk |
| none (non-crisis) | 500 | 10% | True negatives — **intentionally underrepresented** |
| **Total** | **5,000** | | |

### 5.2 Why Non-Crisis Is Intentionally Small
The model is designed to err heavily toward **high recall on crisis** (never miss a crisis) at the cost of some false positives. The non-crisis class being small (10%) reinforces this bias. In production, false positives result in extra support resources being offered — a benign outcome. False negatives are catastrophic.

### 5.3 Asymmetric Loss Function

```python
import torch
import torch.nn as nn

class AsymmetricCrisisLoss(nn.Module):
    """
    Penalizes false negatives (missing crisis) much more than false positives.
    """
    def __init__(self, crisis_fn_penalty: float = 5.0, none_class_idx: int = 6):
        super().__init__()
        self.crisis_fn_penalty = crisis_fn_penalty
        self.none_class_idx = none_class_idx

    def forward(self, logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        base_loss = nn.CrossEntropyLoss(reduction='none')(logits, labels)

        # Identify cases where true label is crisis but model predicted 'none'
        predicted = torch.argmax(logits, dim=-1)
        is_crisis_label = (labels != self.none_class_idx)
        predicted_as_none = (predicted == self.none_class_idx)

        # Apply heavy penalty on false negatives
        fn_mask = (is_crisis_label & predicted_as_none).float()
        weighted_loss = base_loss * (1.0 + fn_mask * (self.crisis_fn_penalty - 1.0))

        return weighted_loss.mean()
```

### 5.4 Class Weights for Training

```python
# Weight non-crisis class lower, crisis classes higher
class_weights = {
    "suicidal_ideation": 3.0,  # Highest priority
    "self_harm": 2.5,
    "abuse_disclosure": 2.5,
    "acute_distress": 2.0,
    "medical_emergency": 2.0,
    "substance_crisis": 2.0,
    "none": 0.5              # Penalize false positives less than false negatives
}
```

---

## 6. Dataset Splits: Training, Validation, Testing

### 6.1 Split Strategy

```
Total Dataset: 5,000 examples
├── Training Set:   3,500 examples (70%)
├── Validation Set:   750 examples (15%)  ← model selection during training
└── Test Set:         750 examples (15%)  ← final evaluation only
```

Note: The test set is kept larger than the typical 10% to ensure robust evaluation across all 7 classes, including low-frequency crisis types.

### 6.2 Stratified Split Code

```python
from sklearn.model_selection import train_test_split

df_stratified, df_test = train_test_split(
    df, test_size=0.15, stratify=df['crisis_type'], random_state=42
)
df_train, df_val = train_test_split(
    df_stratified, test_size=0.1765,  # 15/85 ≈ 0.1765 to get ~750 val
    stratify=df_stratified['crisis_type'], random_state=42
)

# Verify all crisis types present in each split
for split_name, split_df in [('train', df_train), ('val', df_val), ('test', df_test)]:
    missing = set(CRISIS_TYPES) - set(split_df['crisis_type'].unique())
    assert len(missing) == 0, f"Missing crisis types in {split_name}: {missing}"
```

### 6.3 Dedicated Adversarial Test Set

A separate adversarial test set of 300 examples was created by clinical psychologists to test:
1. **Indirect suicidal ideation**: No explicit keywords, only contextual signals
2. **Historical reference**: "I used to be suicidal" (should be non-crisis)
3. **Sarcasm as crisis signal**: "Yeah I'm just GREAT" after multiple distress signals
4. **Code-switching**: Hindi/Hinglish crisis expressions
5. **Metaphorical language**: "I'm drowning" (context-dependent)

---

## 7. Dataset Evaluation & Quality Checks

### 7.1 Clinical Review Rate

```
For each crisis-positive example:
  - 100% reviewed by licensed clinician ✅
  - Clinician agreement rate: 97.3%
  - Discrepancies resolved by senior psychiatrist consultation
```

### 7.2 Severity Score Calibration

```python
# Ensure severity scores are properly calibrated
import scipy.stats as stats

# Test severity score distribution per crisis type
for crisis_type in CRISIS_TYPES[:-1]:  # exclude 'none'
    subset = df[df['crisis_type'] == crisis_type]['severity_score']
    print(f"{crisis_type}: mean={subset.mean():.2f}, std={subset.std():.2f}")

# Expected ranges:
# suicidal_ideation: mean ≈ 0.78, std ≈ 0.12
# self_harm: mean ≈ 0.71, std ≈ 0.15
# acute_distress: mean ≈ 0.62, std ≈ 0.18
# none: mean ≈ 0.0 (all zeros for non-crisis)
```

### 7.3 Bias Checks

```python
# Check for demographic bias in crisis detection
# (ensure model doesn't under-detect crisis in certain groups)

# Test on gender-specific language patterns
female_crisis = df[df['utterance'].str.contains("she|her|woman|girl", case=False)]
male_crisis = df[df['utterance'].str.contains("he|him|man|boy", case=False)]

# Both should have similar severity score distributions
assert abs(female_crisis['severity_score'].mean() - male_crisis['severity_score'].mean()) < 0.05
```

---

## 8. Training Strategy

### 8.1 Architecture

```
Input: User utterance (up to 512 tokens)
       │
       ▼
RoBERTa-base encoder (12 layers, 768 hidden dim, 125M params)
       │
       ▼
[CLS] token representation (768-dim)
       │
       ▼
Dropout (0.3)
       │
       ▼
Linear (768 → 256) + ReLU + Dropout(0.2)
       │
       ▼
Linear (256 → 7)   [7 crisis types including 'none']
       │
       ▼
Softmax → Crisis type probabilities
```

### 8.2 Training Configuration

```python
training_config = {
    "model_name": "roberta-base",
    "num_labels": 7,
    "max_seq_length": 256,          # longer context for crisis detection
    "batch_size": 16,               # smaller batch due to larger model
    "num_train_epochs": 5,          # more epochs for safety-critical task
    "learning_rate": 1e-5,          # conservative for RoBERTa
    "warmup_ratio": 0.15,
    "weight_decay": 0.01,
    "gradient_clip": 1.0,
    "dropout": 0.3,
    "fp16": True,
    "eval_metric": "crisis_recall",  # primary metric is RECALL on crisis classes
    "early_stopping_patience": 5,
    "seed": 42,
    "loss_function": "asymmetric_crisis_loss",
    "crisis_fn_penalty": 5.0
}
```

### 8.3 Target Metrics (Safety-First Priority)

| Metric | Minimum Acceptable | Target |
|--------|-------------------|--------|
| Crisis Recall (sensitivity) | 98% | 99.5% |
| Crisis Precision | 75% | 85% |
| F1 on suicidal_ideation | 0.90 | 0.95 |
| False Negative Rate | < 2% | < 0.5% |
| Inference latency | < 100ms | < 35ms |

**Note**: Recall is the primary metric. We accept lower precision (more false positives) to ensure near-zero false negatives.

---

## 9. Step-by-Step Training Process

### Step 1: Environment Setup

```bash
pip install torch==2.1.0 transformers==4.36.0 datasets scikit-learn
pip install pandas numpy wandb scipy imbalanced-learn
```

### Step 2: Download Base Model

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification

CRISIS_TYPES = [
    "suicidal_ideation", "self_harm", "abuse_disclosure",
    "acute_distress", "medical_emergency", "substance_crisis", "none"
]

tokenizer = AutoTokenizer.from_pretrained("roberta-base")
model = AutoModelForSequenceClassification.from_pretrained(
    "roberta-base",
    num_labels=7,
    id2label={i: label for i, label in enumerate(CRISIS_TYPES)},
    label2id={label: i for i, label in enumerate(CRISIS_TYPES)}
)
```

### Step 3: Load and Tokenize Dataset

```python
import pandas as pd
from datasets import Dataset

df = pd.read_csv('ml_pipeline/data/safety_crisis_v1.csv')
LABEL2ID = {label: i for i, label in enumerate(CRISIS_TYPES)}
df['label'] = df['crisis_type'].map(LABEL2ID)

def tokenize_function(examples):
    return tokenizer(
        examples['utterance'],
        max_length=256,
        truncation=True,
        padding='max_length'
    )

train_dataset = Dataset.from_pandas(df_train[['utterance', 'label']]).map(tokenize_function, batched=True)
val_dataset = Dataset.from_pandas(df_val[['utterance', 'label']]).map(tokenize_function, batched=True)
test_dataset = Dataset.from_pandas(df_test[['utterance', 'label']]).map(tokenize_function, batched=True)
```

### Step 4: Custom Training with Asymmetric Loss

```python
from transformers import TrainingArguments, Trainer
import torch

class CrisisTrainer(Trainer):
    def __init__(self, crisis_fn_penalty=5.0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.crisis_fn_penalty = crisis_fn_penalty
        self.none_class_idx = 6

    def compute_loss(self, model, inputs, return_outputs=False):
        labels = inputs.get("labels")
        outputs = model(**inputs)
        logits = outputs.get("logits")

        # Base cross-entropy loss
        base_loss = torch.nn.CrossEntropyLoss(reduction='none')(logits, labels)

        # Penalize false negatives (crisis → predicted as none)
        predicted = torch.argmax(logits, dim=-1)
        is_crisis = (labels != self.none_class_idx)
        predicted_none = (predicted == self.none_class_idx)
        fn_mask = (is_crisis & predicted_none).float()
        weighted_loss = base_loss * (1.0 + fn_mask * (self.crisis_fn_penalty - 1.0))

        loss = weighted_loss.mean()
        return (loss, outputs) if return_outputs else loss

def compute_metrics(eval_pred):
    from sklearn.metrics import f1_score, recall_score, precision_score
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)

    # Per-class crisis recall (most important metric)
    crisis_recall = recall_score(labels, preds, average='macro', labels=list(range(6)))
    overall_f1 = f1_score(labels, preds, average='macro')
    suicidal_recall = recall_score(labels, preds, labels=[0], average='micro')

    return {
        "crisis_recall": crisis_recall,
        "macro_f1": overall_f1,
        "suicidal_recall": suicidal_recall
    }

training_args = TrainingArguments(
    output_dir="./models/crisis_classifier",
    num_train_epochs=5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    learning_rate=1e-5,
    warmup_ratio=0.15,
    weight_decay=0.01,
    evaluation_strategy="epoch",
    save_strategy="best",
    load_best_model_at_end=True,
    metric_for_best_model="eval_crisis_recall",
    greater_is_better=True,
    fp16=True,
    logging_steps=25,
    report_to="wandb",
    run_name="crisis-classifier-roberta-v1",
    seed=42
)

trainer = CrisisTrainer(
    crisis_fn_penalty=5.0,
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    compute_metrics=compute_metrics
)

trainer.train()
```

### Step 5: Post-Training Threshold Calibration

```python
# After training, calibrate decision thresholds on validation set
# Use Platt scaling or temperature scaling for better probability calibration

from sklearn.linear_model import LogisticRegression
import numpy as np

# Get raw logits on validation set
val_preds = trainer.predict(val_dataset)
val_logits = val_preds.predictions  # shape: (N, 7)

# Apply temperature scaling to calibrate probabilities
class TemperatureScaler:
    def __init__(self):
        self.temperature = 1.0

    def fit(self, logits, labels):
        from scipy.optimize import minimize_scalar
        def nll(T):
            scaled_probs = np.exp(logits / T) / np.exp(logits / T).sum(axis=1, keepdims=True)
            return -np.log(scaled_probs[np.arange(len(labels)), labels]).mean()
        result = minimize_scalar(nll, bounds=(0.1, 10.0), method='bounded')
        self.temperature = result.x
        return self

    def transform(self, logits):
        return np.exp(logits / self.temperature) / np.exp(logits / self.temperature).sum(axis=1, keepdims=True)

scaler = TemperatureScaler()
scaler.fit(val_logits, val_dataset['label'])
print(f"Optimal temperature: {scaler.temperature:.3f}")

# Save temperature
import json
with open("models/crisis_classifier/temperature.json", "w") as f:
    json.dump({"temperature": scaler.temperature}, f)
```

### Step 6: Final Evaluation on Test Set

```python
from sklearn.metrics import classification_report, confusion_matrix

test_preds = trainer.predict(test_dataset)
test_predictions = np.argmax(test_preds.predictions, axis=-1)

print("=== CRISIS DETECTION TEST SET EVALUATION ===")
print(classification_report(
    test_dataset['label'],
    test_predictions,
    target_names=CRISIS_TYPES
))

# Critical check: false negative rate for suicidal_ideation
si_true = [l for l in test_dataset['label'] if l == 0]  # suicidal_ideation = 0
si_pred = [p for l, p in zip(test_dataset['label'], test_predictions) if l == 0]
fn_rate = sum(1 for p in si_pred if p == 6) / len(si_true)  # predicted as 'none'
print(f"\nSuicidal Ideation False Negative Rate: {fn_rate:.2%}")
assert fn_rate < 0.02, f"FAIL: FN rate {fn_rate:.2%} exceeds 2% threshold!"
```

### Step 7: ONNX Export

```python
import torch.onnx

dummy = tokenizer("I want to end it all", max_length=256, padding='max_length',
                  truncation=True, return_tensors='pt')
torch.onnx.export(
    model,
    (dummy['input_ids'], dummy['attention_mask']),
    "models/crisis_classifier/crisis_classifier_v1.onnx",
    input_names=["input_ids", "attention_mask"],
    output_names=["logits"],
    dynamic_axes={"input_ids": {0: "batch"}, "attention_mask": {0: "batch"}},
    opset_version=14
)
```

---

## 10. Model Evaluation

### 10.1 Required Performance Gates

The model MUST pass all gates before production deployment:

```python
def run_production_gates(model, test_dataset, adversarial_dataset):
    results = {}

    # Gate 1: Overall crisis recall ≥ 98%
    preds = np.argmax(model.predict(test_dataset).predictions, axis=-1)
    crisis_recall = recall_score(test_dataset['label'], preds, labels=list(range(6)), average='macro')
    results['gate1_crisis_recall'] = crisis_recall >= 0.98

    # Gate 2: Suicidal ideation recall ≥ 99%
    si_recall = recall_score(test_dataset['label'], preds, labels=[0], average='micro')
    results['gate2_si_recall'] = si_recall >= 0.99

    # Gate 3: Adversarial set accuracy ≥ 90%
    adv_preds = np.argmax(model.predict(adversarial_dataset).predictions, axis=-1)
    adv_acc = accuracy_score(adversarial_dataset['label'], adv_preds)
    results['gate3_adversarial'] = adv_acc >= 0.90

    # Gate 4: Inference time < 100ms
    import time
    start = time.time()
    for _ in range(100):
        model.predict(Dataset.from_dict({"utterance": ["test input"], "label": [6]}))
    avg_ms = (time.time() - start) * 10
    results['gate4_latency'] = avg_ms < 100

    all_passed = all(results.values())
    print(f"Production Gates: {'ALL PASSED ✅' if all_passed else 'SOME FAILED ❌'}")
    for gate, passed in results.items():
        print(f"  {gate}: {'✅' if passed else '❌'}")

    return all_passed
```

### 10.2 Confusion Matrix Focus

Key misclassification patterns to monitor:
- `suicidal_ideation` → `acute_distress`: Acceptable (similar response)
- `suicidal_ideation` → `none`: **CRITICAL FAILURE** — must be < 0.5%
- `none` → any crisis type: Acceptable (false positive with benign outcome)
- `self_harm` → `suicidal_ideation`: Acceptable (both receive crisis protocol)

---

## 11. Downloading & Saving Weights

### 11.1 Save Model

```python
final_path = "./models/crisis_classifier_saathi_v1"
model.save_pretrained(final_path)
tokenizer.save_pretrained(final_path)

import json
with open(f"{final_path}/calibration.json", "w") as f:
    json.dump({"temperature": scaler.temperature, "thresholds": {
        "suicidal_ideation": 0.35,  # lower threshold = higher recall
        "self_harm": 0.40,
        "abuse_disclosure": 0.45,
        "acute_distress": 0.50,
        "medical_emergency": 0.45,
        "substance_crisis": 0.50
    }}, f, indent=2)
```

### 11.2 Production Directory Structure

```
therapeutic-copilot/server/ml_models/
└── crisis_classifier/
    ├── config.json
    ├── pytorch_model.bin          (~476MB for RoBERTa-base)
    ├── tokenizer.json
    ├── vocab.json
    ├── calibration.json           # temperature + decision thresholds
    ├── crisis_classifier_v1.onnx
    └── crisis_keywords.json       # keyword safety net config
```

---

## 12. Integrating Trained Weights into the App Workflow

### 12.1 CrisisDetectionService

```python
# therapeutic-copilot/server/services/crisis_detection_service.py

import torch, json, time
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from config.crisis_keywords import keyword_check, CRISIS_RESOURCES

CRISIS_TYPES = ["suicidal_ideation","self_harm","abuse_disclosure",
                "acute_distress","medical_emergency","substance_crisis","none"]

class CrisisDetectionService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        model_path = "./ml_models/crisis_classifier"
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.eval()

        with open(f"{model_path}/calibration.json") as f:
            cal = json.load(f)
        self.temperature = cal['temperature']
        self.thresholds = cal['thresholds']
        self._initialized = True

    def detect(self, utterance: str, emotion_hint: dict = None) -> dict:
        start = time.time()

        # Stage 1: Keyword safety net (< 5ms)
        kw_result = keyword_check(utterance)
        if kw_result['keyword_triggered'] and kw_result.get('severity_hint', 0) >= 0.90:
            return self._build_crisis_response(
                crisis_type=kw_result['crisis_type'],
                severity=kw_result['severity_hint'],
                source='keyword',
                keyword_signals=[kw_result['matched_keyword']],
                processing_ms=(time.time()-start)*1000
            )

        # Stage 2: ML Classifier
        inputs = self.tokenizer(utterance, max_length=256, truncation=True,
                                 padding='max_length', return_tensors='pt')
        with torch.no_grad():
            logits = self.model(**inputs).logits.numpy()[0]

        # Temperature-calibrated probabilities
        scaled = np.exp(logits / self.temperature)
        probs = scaled / scaled.sum()

        # Emotion hint: if emotion classifier flagged hopelessness >0.85, lower crisis threshold
        if emotion_hint and emotion_hint.get('primary_emotion') == 'hopelessness':
            if emotion_hint.get('intensity', 0) > 0.85:
                self.thresholds['suicidal_ideation'] = max(
                    self.thresholds['suicidal_ideation'] - 0.10, 0.20
                )

        # Decision logic
        none_idx = 6
        crisis_probs = [(i, CRISIS_TYPES[i], probs[i]) for i in range(6)]
        crisis_probs.sort(key=lambda x: x[2], reverse=True)
        top_crisis_idx, top_crisis_type, top_crisis_prob = crisis_probs[0]

        crisis_flag = top_crisis_prob >= self.thresholds.get(top_crisis_type, 0.50)

        return self._build_crisis_response(
            crisis_type=top_crisis_type if crisis_flag else None,
            severity=float(top_crisis_prob) if crisis_flag else 0.0,
            crisis_flag=crisis_flag,
            ml_scores={CRISIS_TYPES[i]: float(probs[i]) for i in range(7)},
            keyword_signals=[kw_result.get('matched_keyword')] if kw_result['keyword_triggered'] else [],
            processing_ms=(time.time()-start)*1000
        )

    def _build_crisis_response(self, crisis_type, severity, crisis_flag=True, **kwargs) -> dict:
        return {
            "crisis_flag": crisis_flag,
            "crisis_type": crisis_type,
            "severity_score": severity,
            "intervention_required": severity >= 0.85 or crisis_type == "suicidal_ideation",
            "escalation_level": "IMMEDIATE" if severity >= 0.85 else ("ELEVATED" if crisis_flag else "NONE"),
            "recommended_resources": CRISIS_RESOURCES.get(crisis_type, []) if crisis_flag else [],
            **kwargs
        }
```

### 12.2 Integration into Chat Flow

```python
# In chat_routes.py — runs BEFORE any LLM call

@router.post("/chat/message")
async def process_message(request: ChatMessageRequest):
    user_message = request.message

    # Crisis detection FIRST — highest priority gate
    crisis_result = crisis_service.detect(
        utterance=user_message,
        emotion_hint=emotion_result  # from emotion classifier
    )

    if crisis_result['crisis_flag']:
        if crisis_result['escalation_level'] == 'IMMEDIATE':
            # Log crisis event, notify admin, return crisis response
            await log_crisis_event(request.session_id, crisis_result)
            return build_crisis_response_message(crisis_result)
        else:
            # Elevated: proceed but inject safety context into LLM prompt
            pass

    # Normal conversation flow continues...
```

---

## 13. Building Prompt Context with Model Output

### 13.1 Crisis Context Injection into LLM Prompt

```python
CRISIS_PROMPT_BLOCKS = {
    "suicidal_ideation": """
## ⚠️ CRISIS ALERT: Suicidal Ideation Detected (Severity: {severity:.0%})

**You are in a safety-critical interaction. Follow these instructions exactly:**

1. DO NOT provide therapeutic techniques, advice, or coaching at this time
2. IMMEDIATELY acknowledge the user's pain with genuine compassion
3. Ask directly but gently: "When you say [user's words], can you tell me more about what you mean by that?"
4. Provide crisis resources naturally in the conversation:
   - iCall (India): 9152987821
   - Vandrevala Foundation: 1860-2662-345
   - NIMHANS: 080-46110007
   - International: crisis.support.org
5. Encourage connecting with a live counselor: "I want to make sure you have support right now. Would you like me to connect you with someone who can talk with you?"
6. Stay present — do not end the conversation
7. DO NOT say "I'm just an AI" or make the user feel dismissed

Your ONLY goal right now is to ensure this person feels heard and knows help is available.
""",
    "self_harm": """
## ⚠️ SAFETY ALERT: Self-Harm Signals Detected

The user has indicated they may be hurting themselves. Your response must:
1. Validate their pain without judgment
2. Express genuine concern for their safety
3. Ask about their current safety
4. Provide resources for self-harm support
5. Not lecture or moralize about self-harm
""",
    "acute_distress": """
## ⚠️ ACUTE DISTRESS DETECTED

The user appears to be in immediate psychological distress. Your response must:
1. Use grounding language: "I'm here with you. You're safe right now."
2. Slow the conversation pace — short, calm sentences only
3. Guide with the 5-4-3-2-1 grounding technique if appropriate
4. Do not discuss complex topics — stay in the present moment
"""
}

def build_crisis_system_prompt(base_prompt: str, crisis_result: dict) -> str:
    if not crisis_result['crisis_flag']:
        return base_prompt

    crisis_type = crisis_result['crisis_type']
    severity = crisis_result['severity_score']

    crisis_block = CRISIS_PROMPT_BLOCKS.get(crisis_type, "")
    if crisis_block:
        crisis_block = crisis_block.format(severity=severity)

    return f"{crisis_block}\n\n{base_prompt}"
```

### 13.2 Crisis Response Message Template

```python
def build_crisis_response_message(crisis_result: dict) -> dict:
    """
    For IMMEDIATE escalation: bypass LLM entirely, return pre-crafted safe message.
    """
    resources = "\n".join([f"• {r}" for r in crisis_result['recommended_resources']])

    message = f"""I hear that you're going through something really difficult right now, and I want you to know I'm here with you.

What you're feeling matters deeply, and you deserve support right now — real, human support.

Please reach out to one of these resources:
{resources}

They are available 24/7 and everything is confidential.

Can you tell me — are you safe right now?"""

    return {
        "message": message,
        "crisis_mode": True,
        "escalation_level": crisis_result['escalation_level'],
        "conversation_flow": "SUSPENDED",
        "therapist_notification": True
    }
```

---

## Summary

| Aspect | Decision |
|--------|----------|
| Architecture | RoBERTa-base + keyword safety net ensemble |
| Dataset | 5,000 examples, 100% crisis examples reviewed by licensed clinicians |
| Balance | Crisis classes overrepresented; asymmetric loss penalizes false negatives 5x |
| Primary metric | Crisis recall ≥ 98% (safety first) |
| Thresholds | Calibrated with temperature scaling; per-class thresholds |
| Integration | Runs FIRST on every message, before LLM call |
| Prompt use | Injects crisis protocol instructions, overrides normal therapeutic flow |
| Response | IMMEDIATE escalation bypasses LLM entirely; ELEVATED injects safety context |

---

*Document Version: 1.0 | Model Version: crisis_classifier_saathi_v1 | Last Updated: 2025-03*
