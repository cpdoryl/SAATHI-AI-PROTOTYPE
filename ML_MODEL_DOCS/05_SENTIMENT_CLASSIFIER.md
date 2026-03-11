# Model Document 05: Sentiment Classifier
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
The **Sentiment Classifier** provides a high-level, coarse-grained signal about whether the user's overall message is positive, negative, or neutral in valence. It operates as a **session-level trend tracker** alongside the per-message emotion classifier — giving the system a broader arc view of the user's emotional journey through a conversation.

### Why a Separate Sentiment Model?

**Sentiment vs. Emotion**: These answer different questions:
- **Emotion** (fine-grained): "What specific emotion is this?" → anxiety, hopelessness, shame
- **Sentiment** (coarse-grained): "Is this conversation trending positive, negative, or neutral?"

Sentiment is used for:
1. **Session progress monitoring**: Is the user feeling better as the conversation continues?
2. **Lead scoring in Stage 1 (sales)**: Positive sentiment correlates with booking likelihood
3. **Therapist handoff notes**: "Sentiment trended from negative (0.78) to positive (0.61) over 12 turns"
4. **Early warning**: Consistently negative sentiment across sessions signals persistent distress
5. **A/B testing**: Which response strategies shift sentiment toward positive?

### Scope
- **Input**: User utterance (text string)
- **Output**: `sentiment` (positive/negative/neutral), `confidence`, `valence_score` (-1.0 to +1.0)
- **Classes**: 3 classes
- **Session use**: Tracks sentiment trend across multiple turns (moving average)

---

## 2. Why We Chose This Model Architecture

### Architecture: Fine-tuned `distilbert-base-uncased` (3-class)

#### Why Not VADER or TextBlob?
- Rule-based sentiment tools are tuned for product reviews and social media
- They fail on therapeutic language: "I feel nothing" is NOT neutral — it's deeply negative in a mental health context
- They don't understand clinical negation: "I'm not doing well" requires model-level understanding
- VADER scores "I want to die" as slightly negative (-0.27) — wildly incorrect for our domain

#### Why Not a Larger Model (RoBERTa, BERT-large)?
- Sentiment is a 3-class problem — the simplest of our classification tasks
- DistilBERT fine-tuned on domain data exceeds all rule-based methods by 15–20 points
- Keeps inference cost minimal since sentiment runs on every message alongside 4+ other classifiers

#### Therapeutic Sentiment vs. Standard Sentiment
Standard sentiment models (SST-2, IMDB) are trained on reviews: "This movie is great!" (positive). Therapeutic sentiment is different:
- "I had a moment of clarity today" → positive (therapeutic progress)
- "I cried a lot but felt relieved" → mixed/positive (catharsis is positive in therapy)
- "I'm just fine" → often negative (minimization/suppression signal)
- "At least I got out of bed" → mixed/positive

This domain gap means we cannot use off-the-shelf models — fine-tuning on therapeutic text is essential.

---

## 3. Schema Design

### 3.1 Dataset Schema (CSV Format)

```csv
id,utterance,sentiment,valence_score,confidence,session_context,source,annotator_id,created_at
```

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | string | UUID | `sent_003421` |
| `utterance` | string | User text | `"I actually felt a bit lighter today"` |
| `sentiment` | enum | positive / negative / neutral | `positive` |
| `valence_score` | float (-1.0 to +1.0) | Continuous valence | `0.64` |
| `confidence` | float (0.0–1.0) | Label confidence | `0.88` |
| `session_context` | enum | Whether session context affects label | `therapeutic_progress` |
| `source` | enum | Data origin | `synthetic`, `therapy_transcripts` |
| `annotator_id` | string | Annotator ID | `ann_002` |
| `created_at` | ISO datetime | Timestamp | `2024-09-10T08:30:00Z` |

### 3.2 Sentiment Label Definitions (Therapeutic Context)

| Label | Definition | Examples |
|-------|------------|---------|
| `positive` | Message reflects progress, relief, hope, gratitude, growth, or reduced distress | "I feel better today", "I managed to go for a walk", "That actually makes sense" |
| `negative` | Message reflects worsening state, despair, frustration, suppression, or avoidance | "Nothing is working", "I give up", "I'm just fine" (minimization) |
| `neutral` | Factual, informational, or genuinely emotionally flat messages | "My appointment is on Tuesday", "Tell me about CBT" |

### 3.3 Valence Score (Continuous)

The valence score extends beyond 3-class labels to provide a continuous signal:
```
-1.0 ←——————— 0.0 ———————→ +1.0
Deeply      Neutral      Strongly
Negative                 Positive
```

Valence is regressed from the 3-class probabilities:
```python
def compute_valence(probs: dict) -> float:
    """Convert class probabilities to continuous valence score."""
    return probs['positive'] * 1.0 + probs['neutral'] * 0.0 + probs['negative'] * -1.0
    # Range: -1.0 to +1.0
```

### 3.4 Model Output Schema (JSON)

```json
{
  "sentiment": "positive",
  "valence_score": 0.62,
  "confidence": 0.84,
  "all_scores": {
    "positive": 0.81,
    "neutral": 0.14,
    "negative": 0.05
  },
  "session_trend": {
    "last_5_turns": [0.42, -0.31, -0.18, 0.15, 0.62],
    "trend_direction": "improving",
    "average_valence": 0.14
  },
  "processing_time_ms": 9
}
```

---

## 4. Data Preparation

### 4.1 Data Sources

| Source | Examples | Description |
|--------|----------|-------------|
| Synthetic (GPT-4 + clinical review) | 800 | Therapeutic conversation phrasings |
| SST-2/sentiment140 (filtered and relabeled) | 600 | Standard datasets, relabeled for therapeutic context |
| Therapy transcripts (anonymized) | 400 | Real therapeutic dialogue, expert-labeled |
| Mental health forum posts | 200 | User posts with clear sentiment signals |
| **Total** | **2,000** | |

### 4.2 Relabeling Standard Sentiment Datasets

Standard datasets like SST-2 often have labels that are wrong for our context. A relabeling pass was required:

```python
# Examples of relabeling decisions:

RELABELING_EXAMPLES = [
    # SST-2 label vs. Therapeutic label
    {"text": "I feel nothing anymore", "sst2": "negative", "therapeutic": "negative", "note": "same"},
    {"text": "I'm fine", "sst2": "positive", "therapeutic": "negative", "note": "minimization signal"},
    {"text": "I cried but it was good", "sst2": "mixed", "therapeutic": "positive", "note": "catharsis = progress"},
    {"text": "I don't know what I feel", "sst2": "neutral", "therapeutic": "negative", "note": "dissociation signal"},
    {"text": "I managed to get through the day", "sst2": "neutral", "therapeutic": "positive", "note": "small victory in therapy"},
    {"text": "I've been avoiding everything", "sst2": "negative", "therapeutic": "negative", "note": "same"},
    {"text": "At least something went okay", "sst2": "positive", "therapeutic": "positive", "note": "qualified but real progress"},
]
```

### 4.3 Special Annotation Cases

| Pattern | Standard Sentiment | Therapeutic Sentiment | Reason |
|---------|------------------|----------------------|--------|
| "I'm fine" / "I'm okay" | Positive | Negative | Minimization/avoidance in therapeutic context |
| "I cried but felt better" | Mixed/Negative | Positive | Catharsis = therapeutic progress |
| "I don't feel anything" | Neutral | Negative | Emotional numbing = concerning |
| "I got out of bed today" | Neutral | Positive | Enormous win for someone with depression |
| "I'm not as bad as yesterday" | Neutral | Positive | Relative improvement |

---

## 5. Data Balance Strategy

### 5.1 Class Distribution

| Sentiment | Count | % | Notes |
|-----------|-------|---|-------|
| negative | 900 | 45% | Therapeutic users skew negative — kept high |
| positive | 650 | 32.5% | Less common but important for tracking progress |
| neutral | 450 | 22.5% | Informational messages |
| **Total** | **2,000** | | |

### 5.2 Rationale for Keeping Negative Skew

Unlike typical sentiment datasets where balance is ideal, we intentionally maintain negative class dominance because:
1. In a mental health app, most messages are genuinely negative in nature
2. The model must be calibrated to the real-world distribution of a therapeutic conversation
3. Artificially balancing would cause the model to over-predict positive sentiment on truly negative therapeutic expressions

### 5.3 Post-Training Calibration

```python
# Apply Platt scaling to ensure sentiment probabilities are well-calibrated
from sklearn.calibration import CalibratedClassifierCV
# (Applied to validation set after initial training)
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
# Valence score distribution check
import matplotlib.pyplot as plt
import numpy as np

# Verify valence scores are properly distributed per class
for sentiment in ['positive', 'negative', 'neutral']:
    subset = df[df['sentiment'] == sentiment]['valence_score']
    print(f"{sentiment}: mean={subset.mean():.3f}, std={subset.std():.3f}")

# Expected:
# positive: mean ≈ 0.65, std ≈ 0.18
# negative: mean ≈ -0.62, std ≈ 0.20
# neutral: mean ≈ -0.03, std ≈ 0.15

# Check for mislabeled "fine/okay" examples
minimization_patterns = df[df['utterance'].str.lower().str.contains(r"\bi'?m (fine|okay|alright|ok)\b")]
# Verify these are labeled 'negative', not 'positive'
assert (minimization_patterns['sentiment'] == 'negative').mean() > 0.85, \
    "Minimization patterns not labeled correctly"
```

---

## 8. Training Strategy

### 8.1 Training Configuration

```python
training_config = {
    "model_name": "distilbert-base-uncased",
    "num_labels": 3,
    "max_seq_length": 128,
    "batch_size": 32,
    "num_train_epochs": 3,
    "learning_rate": 2e-5,
    "warmup_ratio": 0.1,
    "weight_decay": 0.01,
    "fp16": True,
    "eval_metric": "macro_f1",
    "class_weights": [1.0, 1.3, 1.5],  # negative=1.0, neutral=1.3, positive=1.5
    "seed": 42
}
```

---

## 9. Step-by-Step Training Process

### Step 1: Load Data and Model

```python
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from datasets import Dataset
from sklearn.model_selection import train_test_split

SENTIMENT_CLASSES = ["negative", "neutral", "positive"]
LABEL2ID = {"negative": 0, "neutral": 1, "positive": 2}

tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
model = AutoModelForSequenceClassification.from_pretrained(
    "distilbert-base-uncased", num_labels=3,
    id2label={0:"negative",1:"neutral",2:"positive"},
    label2id=LABEL2ID
)

df = pd.read_csv('ml_pipeline/data/sentiment_classifier_v1.csv')
df['label'] = df['sentiment'].map(LABEL2ID)

train_df, temp = train_test_split(df, test_size=0.2, stratify=df['label'], random_state=42)
val_df, test_df = train_test_split(temp, test_size=0.5, stratify=temp['label'], random_state=42)

def tokenize(examples):
    return tokenizer(examples['utterance'], max_length=128, truncation=True, padding='max_length')

train_ds = Dataset.from_pandas(train_df[['utterance','label']]).map(tokenize, batched=True)
val_ds = Dataset.from_pandas(val_df[['utterance','label']]).map(tokenize, batched=True)
test_ds = Dataset.from_pandas(test_df[['utterance','label']]).map(tokenize, batched=True)
```

### Step 2: Train

```python
import torch, numpy as np
from transformers import TrainingArguments, Trainer
from sklearn.metrics import f1_score, accuracy_score

class_weights = torch.FloatTensor([1.0, 1.3, 1.5])

class SentimentTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False):
        labels = inputs.get("labels")
        outputs = model(**inputs)
        loss = torch.nn.CrossEntropyLoss(weight=class_weights.to(self.args.device))(outputs.logits, labels)
        return (loss, outputs) if return_outputs else loss

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "macro_f1": f1_score(labels, preds, average='macro')
    }

args = TrainingArguments(
    output_dir="./models/sentiment_classifier",
    num_train_epochs=3,
    per_device_train_batch_size=32,
    per_device_eval_batch_size=64,
    learning_rate=2e-5,
    warmup_ratio=0.1,
    evaluation_strategy="epoch",
    save_strategy="best",
    load_best_model_at_end=True,
    metric_for_best_model="eval_macro_f1",
    fp16=True,
    report_to="wandb",
    run_name="sentiment-classifier-v1",
    seed=42
)

trainer = SentimentTrainer(
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
print(classification_report(test_ds['label'], preds, target_names=SENTIMENT_CLASSES))

model.save_pretrained("./models/sentiment_classifier_saathi_v1")
tokenizer.save_pretrained("./models/sentiment_classifier_saathi_v1")
```

---

## 10. Model Evaluation

| Metric | Target |
|--------|--------|
| Overall Accuracy | ≥ 85% |
| Macro F1 | ≥ 0.83 |
| Negative class F1 | ≥ 0.87 |
| Minimization detection | ≥ 80% ("I'm fine" → negative) |
| Catharsis detection | ≥ 78% ("cried but felt better" → positive) |

---

## 11. Downloading & Saving Weights

```
therapeutic-copilot/server/ml_models/
└── sentiment_classifier/
    ├── config.json
    ├── pytorch_model.bin    (~250MB)
    ├── tokenizer.json
    └── vocab.txt
```

---

## 12. Integrating Trained Weights into the App Workflow

### 12.1 SentimentClassifierService with Session Tracking

```python
# therapeutic-copilot/server/services/sentiment_classifier_service.py

import torch, time
import numpy as np
from collections import deque
from transformers import AutoTokenizer, AutoModelForSequenceClassification

SENTIMENT_CLASSES = ["negative", "neutral", "positive"]

class SentimentClassifierService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        path = "./ml_models/sentiment_classifier"
        self.tokenizer = AutoTokenizer.from_pretrained(path)
        self.model = AutoModelForSequenceClassification.from_pretrained(path)
        self.model.eval()
        self.session_history: dict = {}  # session_id → deque of valence scores
        self._initialized = True

    def classify(self, utterance: str, session_id: str = None) -> dict:
        start = time.time()
        inputs = self.tokenizer(utterance, max_length=128, truncation=True,
                                 padding='max_length', return_tensors='pt')
        with torch.no_grad():
            probs = torch.softmax(self.model(**inputs).logits, dim=-1).numpy()[0]

        # probs: [negative, neutral, positive]
        valence = probs[2] * 1.0 + probs[1] * 0.0 + probs[0] * -1.0
        sentiment = SENTIMENT_CLASSES[np.argmax(probs)]

        result = {
            "sentiment": sentiment,
            "valence_score": float(valence),
            "confidence": float(np.max(probs)),
            "all_scores": {s: float(probs[i]) for i, s in enumerate(SENTIMENT_CLASSES)},
            "processing_time_ms": round((time.time()-start)*1000, 1)
        }

        # Session trend tracking
        if session_id:
            if session_id not in self.session_history:
                self.session_history[session_id] = deque(maxlen=20)
            self.session_history[session_id].append(valence)
            history = list(self.session_history[session_id])
            if len(history) >= 3:
                trend = "improving" if history[-1] > history[0] else \
                        "declining" if history[-1] < history[0] else "stable"
                result['session_trend'] = {
                    "last_n_turns": history[-5:],
                    "trend_direction": trend,
                    "average_valence": np.mean(history)
                }

        return result
```

---

## 13. Building Prompt Context with Model Output

### 13.1 Sentiment Trend Prompt Context

```python
def build_sentiment_context_block(sentiment_result: dict) -> str:
    sentiment = sentiment_result['sentiment']
    valence = sentiment_result['valence_score']
    trend = sentiment_result.get('session_trend', {})
    trend_dir = trend.get('trend_direction', 'unknown')
    avg_valence = trend.get('average_valence', valence)

    block = f"""
## Sentiment Analysis (Session-Level)
- **Current Message Sentiment**: {sentiment} (valence: {valence:+.2f})
- **Session Trend**: {trend_dir} (session avg valence: {avg_valence:+.2f})
"""

    if sentiment == 'positive' and trend_dir == 'improving':
        block += "\n✅ **Positive Momentum**: User is showing signs of improvement. Reinforce and consolidate gains. Celebrate small wins explicitly.\n"
    elif sentiment == 'negative' and trend_dir == 'declining':
        block += "\n⚠️ **Declining Trend**: Session sentiment has been consistently declining. Consider checking in directly: 'I notice things feel heavier as we talk — is there something specific weighing on you?'\n"
    elif trend_dir == 'improving' and sentiment == 'negative':
        block += "\n📈 **Mixed Signal**: Overall session improving but current message negative. User may be processing difficult material — this is normal. Hold space, don't rush to resolution.\n"

    return block
```

### 13.2 Lead Scoring Integration (Stage 1 Sales)

```python
def compute_sentiment_adjusted_lead_score(
    base_lead_score: float,
    sentiment_result: dict,
    conversation_length: int
) -> float:
    """
    In Stage 1 (lead generation), positive sentiment increases
    booking likelihood. Integrate sentiment into lead score.
    """
    valence = sentiment_result['valence_score']
    trend = sentiment_result.get('session_trend', {}).get('trend_direction', 'stable')

    sentiment_multiplier = 1.0
    if valence > 0.5:
        sentiment_multiplier = 1.15  # positive sentiment → higher booking probability
    elif valence < -0.3:
        sentiment_multiplier = 0.85  # negative sentiment → lower booking probability

    if trend == 'improving':
        sentiment_multiplier += 0.05  # improving trend further boosts score
    elif trend == 'declining':
        sentiment_multiplier -= 0.10

    return min(100.0, base_lead_score * sentiment_multiplier)
```

---

## Summary

| Aspect | Decision |
|--------|----------|
| Architecture | DistilBERT fine-tuned, 3-class |
| Dataset | 2,000 examples, therapeutically relabeled |
| Key insight | Standard sentiment labels incorrect for therapeutic context |
| Session use | Tracks valence trend across conversation turns |
| Integration | Runs alongside other classifiers; also feeds lead scoring |
| Prompt use | Injects trend direction and reinforcement/concern instructions |

---

*Document Version: 1.0 | Model Version: sentiment_classifier_saathi_v1 | Last Updated: 2025-03*
