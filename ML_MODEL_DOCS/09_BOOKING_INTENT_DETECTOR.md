# Model Document 09: Booking Intent Detector
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
The **Booking Intent Detector** is a specialized binary classifier that identifies whether a user's message contains a **booking signal** — any indication that they want to schedule a therapy session, whether explicit ("I want to book") or implicit ("I think I'm ready to talk to someone"). It also extracts any date/time/preference entities mentioned to pre-populate the booking form.

### Why a Dedicated Model Instead of Using the Intent Classifier?

The Intent Classifier (Model 03) has `book_appointment` as one of its 7 classes. However, the Booking Intent Detector serves a **different, more fine-grained purpose**:

| Feature | Intent Classifier | Booking Intent Detector |
|---------|------------------|------------------------|
| Scope | All 7 intents | Booking only (binary) |
| Threshold | Standard classification | Lower threshold — more sensitive to weak signals |
| Entity extraction | No | Yes (date, time, therapist preference, format preference) |
| Context awareness | Single utterance | Can analyze across last 3 turns for cumulative signal |
| Use case | Routing decisions | CRM lead qualification + booking flow trigger |

### Business Importance
In the B2B SaaS model, detecting booking intent as early as possible allows the system to:
1. Trigger a booking flow at exactly the right moment (too early = pushback; too late = lost opportunity)
2. Pass detected entities (date, time, format) to the booking system to reduce friction
3. Update the lead score in real-time
4. Notify the human intake team if the AI should hand off

### Scope
- **Input**: User utterance (and optionally last 3 utterances for context)
- **Output**: `booking_intent` (bool), `confidence`, `intent_strength` (explicit/implicit/weak), extracted entities
- **Classes**: Binary (booking intent present / absent)
- **Dataset Size**: 1,000 examples

---

## 2. Why We Chose This Model Architecture

### Architecture: Fine-tuned `distilbert-base-uncased` + NER Head (Joint Model)

#### Two Tasks in One Model

```
Input: User utterance
     │
     ▼
DistilBERT Encoder (shared)
     │
     ├── [CLS] token → Binary Booking Intent Classification Head
     │
     └── Token-level outputs → Named Entity Recognition (NER) Head
                               → Extracts: DATE, TIME, PREFERENCE entities
```

**Why joint training?**
- Booking intent and entity extraction are related tasks — training them together with shared representations improves both
- Single model call instead of two sequential calls (lower latency)
- Entity extraction is only needed when booking intent is detected — joint model naturally learns this dependency

#### Why DistilBERT?
- Fast (<12ms), consistent with platform infrastructure
- Binary classification + token-level NER are both well within DistilBERT's capability
- The task is primarily lexical (booking vocabulary is distinctive)

---

## 3. Schema Design

### 3.1 Dataset Schema (JSON)

```json
{
  "id": "book_intent_001234",
  "utterance": "I think I'm ready to try a session, maybe next Tuesday morning?",
  "booking_intent": true,
  "intent_strength": "explicit",
  "confidence": 0.95,
  "entities": {
    "date_mention": "next Tuesday",
    "time_mention": "morning",
    "therapist_preference": null,
    "format_preference": null,
    "duration_preference": null
  },
  "source": "synthetic",
  "annotator_id": "ann_004",
  "created_at": "2024-10-05T14:30:00Z"
}
```

### 3.2 Intent Strength Taxonomy

```
intent_strength/
├── explicit      → "I want to book a session" (clear, direct statement)
├── implicit      → "I think I need to talk to someone" (clear intention, indirect phrasing)
├── weak          → "Maybe someday I'll try therapy" (possible future interest, no immediate action)
└── none          → "How does therapy work?" (information-seeking only)
```

### 3.3 Entity Types

| Entity | Examples | Notes |
|--------|---------|-------|
| `date_mention` | "next Tuesday", "this week", "March 15th" | Relative or absolute dates |
| `time_mention` | "morning", "after 5pm", "11am" | Time preferences |
| `therapist_preference` | "female therapist", "someone who speaks Hindi" | Demographic/language preferences |
| `format_preference` | "online", "video call", "in-person" | Session format |
| `duration_preference` | "short session", "one hour" | Duration preference |

### 3.4 Model Output Schema (JSON)

```json
{
  "booking_intent": true,
  "intent_strength": "implicit",
  "confidence": 0.81,
  "entities": {
    "date_mention": "this week",
    "time_mention": "evening",
    "therapist_preference": "female therapist",
    "format_preference": "video call",
    "duration_preference": null
  },
  "trigger_booking_flow": true,
  "pre_fill_available": true,
  "processing_time_ms": 13
}
```

---

## 4. Data Preparation

### 4.1 Data Sources

| Source | Examples | Booking Intent |
|--------|----------|---------------|
| Synthetic (GPT-4 + sales expert) | 600 | 300 positive, 300 negative |
| Real intake conversation logs | 300 | 150 positive, 150 negative |
| Booking workflow conversation dataset | 100 | 80 positive, 20 negative |
| **Total** | **1,000** | 530 positive, 470 negative |

### 4.2 Implicit Booking Signal Examples (Challenging Cases)

These require the model to understand context and subtext:

```python
IMPLICIT_BOOKING_EXAMPLES = [
    # Positive (booking_intent = True)
    "I think I've been putting this off for too long",          # readiness signal
    "My manager recommended I talk to someone",                 # external motivation
    "I keep coming back to this chat, maybe it's time",        # behavioral signal
    "Fine, let's do it. What do I need to do?",                # conversion moment
    "I just feel like I need more than this chat",             # service escalation
    "Can I meet an actual therapist?",                         # explicit enough

    # Negative (booking_intent = False)
    "I wonder what therapy is actually like",                  # curiosity, no intent
    "Some of my friends have tried therapy",                   # social reference
    "What does a session cost?",                               # information seeking
    "I'm not sure I'm ready for that yet",                     # explicit non-readiness
    "Tell me more about what therapy involves",                # pre-consideration
]
```

### 4.3 NER Annotation for Entity Extraction

```python
# BIO tagging for entity extraction
# B = Beginning of entity
# I = Inside entity
# O = Outside entity

ENTITY_EXAMPLE = {
    "tokens": ["Can", "we", "schedule", "something", "next", "Tuesday", "at", "3pm", "online"],
    "ner_tags": ["O", "O", "O", "O", "B-DATE", "I-DATE", "O", "B-TIME", "B-FORMAT"]
}

# Label mapping
NER_LABELS = {
    "O": 0,
    "B-DATE": 1, "I-DATE": 2,
    "B-TIME": 3, "I-TIME": 4,
    "B-THERAPIST_PREF": 5, "I-THERAPIST_PREF": 6,
    "B-FORMAT": 7, "I-FORMAT": 8,
    "B-DURATION": 9, "I-DURATION": 10
}
```

---

## 5. Data Balance Strategy

### 5.1 Binary Balance

```
Booking Intent = True:  530 examples (53%)
Booking Intent = False: 470 examples (47%)
```

The dataset is nearly balanced, reflecting the real deployment context: during Stage 1, roughly 50% of all messages will eventually show booking signals (at different strengths) as the conversation progresses.

### 5.2 Intent Strength Distribution

| Strength | Count | % |
|----------|-------|---|
| explicit | 180 | 34% (of positive) |
| implicit | 220 | 42% (of positive) |
| weak | 130 | 24% (of positive) |

Implicit signals intentionally have the highest count — this is the hardest to detect and most valuable (explicit signals are caught by simple rules).

---

## 6. Dataset Splits

```
Full Dataset: 1,000 examples
├── Training:   800 examples (80%)
├── Validation: 100 examples (10%)
└── Test:       100 examples (10%)
```

---

## 7. Dataset Evaluation & Quality Checks

```python
# Verify entity annotation consistency
def validate_bio_tags(tokens: list, tags: list) -> bool:
    """Ensure BIO tags are valid (I- must follow B- of same type)."""
    for i, (token, tag) in enumerate(zip(tokens, tags)):
        if tag.startswith('I-'):
            entity_type = tag.split('-')[1]
            if i == 0 or not tags[i-1].endswith(entity_type):
                return False
    return True

# Check intent strength alignment with labels
for item in dataset:
    if item['booking_intent'] == False:
        assert item['intent_strength'] == 'none', f"Mismatch: {item['id']}"
    if item['intent_strength'] == 'explicit':
        assert item['booking_intent'] == True, f"Explicit must be True: {item['id']}"
```

---

## 8. Training Strategy

### 8.1 Joint Model Architecture

```python
import torch
import torch.nn as nn
from transformers import DistilBertModel

class BookingIntentNERModel(nn.Module):
    def __init__(self, n_ner_labels: int = 11, dropout: float = 0.3):
        super().__init__()
        self.bert = DistilBertModel.from_pretrained('distilbert-base-uncased')

        # Classification head (binary booking intent)
        self.intent_classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(768, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 2)  # binary: intent / no intent
        )

        # NER head (per-token entity labels)
        self.ner_classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(768, n_ner_labels)
        )

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        sequence_output = outputs.last_hidden_state  # (batch, seq_len, 768)
        cls_output = sequence_output[:, 0, :]       # [CLS] for classification

        intent_logits = self.intent_classifier(cls_output)   # (batch, 2)
        ner_logits = self.ner_classifier(sequence_output)   # (batch, seq_len, 11)

        return intent_logits, ner_logits
```

### 8.2 Joint Loss Function

```python
def compute_joint_loss(
    intent_logits, ner_logits,
    intent_labels, ner_labels,
    attention_mask,
    intent_weight=0.6,
    ner_weight=0.4
):
    # Binary cross-entropy for intent
    intent_loss = nn.CrossEntropyLoss()(intent_logits, intent_labels)

    # NER loss (ignore padding tokens where attention_mask=0)
    active_loss = attention_mask.view(-1) == 1
    active_logits = ner_logits.view(-1, 11)[active_loss]
    active_labels = ner_labels.view(-1)[active_loss]
    ner_loss = nn.CrossEntropyLoss(ignore_index=-100)(active_logits, active_labels)

    return intent_weight * intent_loss + ner_weight * ner_loss
```

### 8.3 Training Configuration

```python
training_config = {
    "model_name": "distilbert-base-uncased",
    "batch_size": 32,
    "num_epochs": 5,
    "learning_rate": 2e-5,
    "warmup_ratio": 0.1,
    "weight_decay": 0.01,
    "fp16": True,
    "intent_loss_weight": 0.6,
    "ner_loss_weight": 0.4,
    "intent_class_weights": [1.0, 1.3],  # [no_intent, intent] — boost intent class
    "eval_metric": "intent_f1",
    "seed": 42
}
```

---

## 9. Step-by-Step Training Process

### Step 1: Prepare Tokenized Dataset with NER Labels

```python
import torch
from torch.utils.data import Dataset

class BookingIntentDataset(Dataset):
    def __init__(self, data: list, tokenizer, max_length: int = 128):
        self.tokenizer = tokenizer
        self.data = data
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        encoding = self.tokenizer(
            item['utterance'],
            max_length=self.max_length,
            truncation=True,
            padding='max_length',
            return_offsets_mapping=True
        )

        # Align NER labels to tokenized input
        ner_labels = self._align_ner_labels(item, encoding)

        return {
            'input_ids': torch.tensor(encoding['input_ids']),
            'attention_mask': torch.tensor(encoding['attention_mask']),
            'intent_label': torch.tensor(int(item['booking_intent'])),
            'ner_labels': torch.tensor(ner_labels)
        }

    def _align_ner_labels(self, item: dict, encoding) -> list:
        """Align word-level NER tags to sub-word token level."""
        labels = [-100] * self.max_length  # -100 = ignore in loss
        # Map token offset → original token → BIO tag
        word_ids = encoding.word_ids()
        prev_word_id = None
        for i, word_id in enumerate(word_ids):
            if word_id is None:
                labels[i] = -100
            elif word_id != prev_word_id:
                labels[i] = item.get('token_ner_tags', [0]*100)[word_id]
            else:
                # Sub-word continuation: use I- version if B- before
                labels[i] = -100  # or handle B→I conversion
            prev_word_id = word_id
        return labels
```

### Step 2: Training Loop

```python
import torch
from torch.optim import AdamW
from transformers import get_linear_schedule_with_warmup

model = BookingIntentNERModel()
optimizer = AdamW(model.parameters(), lr=2e-5, weight_decay=0.01)
scheduler = get_linear_schedule_with_warmup(
    optimizer,
    num_warmup_steps=int(0.1 * len(train_loader) * 5),
    num_training_steps=len(train_loader) * 5
)

for epoch in range(5):
    model.train()
    for batch in train_loader:
        optimizer.zero_grad()

        intent_logits, ner_logits = model(
            batch['input_ids'], batch['attention_mask']
        )

        loss = compute_joint_loss(
            intent_logits, ner_logits,
            batch['intent_label'], batch['ner_labels'],
            batch['attention_mask']
        )

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()
```

### Step 3: Evaluate and Save

```python
from sklearn.metrics import f1_score, classification_report

# Evaluate on test set
model.eval()
all_intent_preds, all_intent_labels = [], []
all_ner_preds, all_ner_labels = [], []

with torch.no_grad():
    for batch in test_loader:
        intent_logits, ner_logits = model(batch['input_ids'], batch['attention_mask'])
        intent_preds = torch.argmax(intent_logits, dim=-1)
        all_intent_preds.extend(intent_preds.tolist())
        all_intent_labels.extend(batch['intent_label'].tolist())

print("Booking Intent Classification:")
print(classification_report(all_intent_labels, all_intent_preds, target_names=['no_intent', 'intent']))

# Save model
torch.save(model.state_dict(), './models/booking_intent_detector/model.pt')
tokenizer.save_pretrained('./models/booking_intent_detector')
```

---

## 10. Model Evaluation

| Metric | Target |
|--------|--------|
| Booking intent F1 | ≥ 0.88 |
| Implicit intent recall | ≥ 0.80 |
| Entity extraction F1 (DATE) | ≥ 0.85 |
| Entity extraction F1 (TIME) | ≥ 0.82 |
| False positive rate | < 15% |
| Inference latency | < 15ms |

---

## 11. Downloading & Saving Weights

```
therapeutic-copilot/server/ml_models/
└── booking_intent_detector/
    ├── model.pt             # PyTorch model weights
    ├── tokenizer.json
    └── config.json
```

---

## 12. Integrating Trained Weights into the App Workflow

### 12.1 BookingIntentService

```python
# therapeutic-copilot/server/services/booking_intent_service.py

import torch, time
from transformers import AutoTokenizer

class BookingIntentService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        path = "./ml_models/booking_intent_detector"
        self.tokenizer = AutoTokenizer.from_pretrained(path)
        self.model = BookingIntentNERModel()
        self.model.load_state_dict(torch.load(f"{path}/model.pt"))
        self.model.eval()
        self._initialized = True

    def detect(self, utterance: str, context_history: list = None) -> dict:
        """Detect booking intent and extract entities."""
        start = time.time()

        # Optionally prepend last 2 user turns for context
        if context_history:
            context = " [SEP] ".join([m['content'] for m in context_history[-4:]
                                       if m['role'] == 'user'][-2:])
            input_text = f"{context} [SEP] {utterance}"
        else:
            input_text = utterance

        encoding = self.tokenizer(input_text, max_length=128, truncation=True,
                                   padding='max_length', return_tensors='pt')

        with torch.no_grad():
            intent_logits, ner_logits = self.model(
                encoding['input_ids'], encoding['attention_mask']
            )

        intent_probs = torch.softmax(intent_logits, dim=-1)[0]
        booking_intent = bool(intent_probs[1] > 0.55)  # threshold

        entities = self._extract_entities(encoding, ner_logits)

        intent_strength = "explicit" if intent_probs[1] > 0.85 else \
                          "implicit" if intent_probs[1] > 0.65 else \
                          "weak" if intent_probs[1] > 0.55 else "none"

        return {
            "booking_intent": booking_intent,
            "intent_strength": intent_strength,
            "confidence": float(intent_probs[1]),
            "entities": entities,
            "trigger_booking_flow": booking_intent and intent_strength in ["explicit", "implicit"],
            "pre_fill_available": any(v is not None for v in entities.values()),
            "processing_time_ms": round((time.time()-start)*1000, 1)
        }

    def _extract_entities(self, encoding, ner_logits) -> dict:
        ner_preds = torch.argmax(ner_logits, dim=-1)[0].tolist()
        tokens = self.tokenizer.convert_ids_to_tokens(encoding['input_ids'][0])

        entities = {"date_mention": None, "time_mention": None,
                    "therapist_preference": None, "format_preference": None,
                    "duration_preference": None}

        NER_LABEL_MAP = {1:"DATE", 2:"DATE", 3:"TIME", 4:"TIME",
                         5:"THERAPIST_PREF", 6:"THERAPIST_PREF",
                         7:"FORMAT", 8:"FORMAT", 9:"DURATION", 10:"DURATION"}
        ENTITY_KEY_MAP = {"DATE": "date_mention", "TIME": "time_mention",
                          "THERAPIST_PREF": "therapist_preference",
                          "FORMAT": "format_preference", "DURATION": "duration_preference"}

        current_entity, current_tokens = None, []
        for token, label_id in zip(tokens, ner_preds):
            if token in ['[CLS]', '[SEP]', '[PAD]']:
                continue
            entity_type = NER_LABEL_MAP.get(label_id)
            if entity_type:
                if entity_type != current_entity:
                    if current_entity and current_tokens:
                        key = ENTITY_KEY_MAP[current_entity]
                        entities[key] = ' '.join(current_tokens).replace(' ##', '')
                    current_entity = entity_type
                    current_tokens = [token.replace('##', '')]
                else:
                    current_tokens.append(token.replace('##', ''))
            else:
                if current_entity and current_tokens:
                    key = ENTITY_KEY_MAP[current_entity]
                    entities[key] = ' '.join(current_tokens).replace(' ##', '')
                current_entity, current_tokens = None, []

        return entities
```

### 12.2 Integration into Chat Flow

```python
# In chat_routes.py — runs during Stage 1 conversations

if intent_result['routing_action'] in ["THERAPEUTIC_CONVERSATION", "CONVERSATIONAL"]:
    booking_result = booking_intent_service.detect(
        utterance=user_message,
        context_history=session.get_last_n_turns(4)
    )

    if booking_result['trigger_booking_flow']:
        # Update lead score
        lead_score = update_lead_score(lead_score, booking_result)

        # If high confidence, trigger booking handoff
        if booking_result['confidence'] > 0.80:
            return await initiate_booking_flow(
                session_id=request.session_id,
                pre_fill_data=booking_result['entities'],
                booking_result=booking_result
            )
```

---

## 13. Building Prompt Context with Model Output

### 13.1 Booking Intent Context in System Prompt

```python
def build_booking_intent_context(booking_result: dict) -> str:
    if not booking_result['booking_intent']:
        return ""

    entities = booking_result['entities']
    entity_summary = []
    if entities.get('date_mention'):
        entity_summary.append(f"Preferred date: {entities['date_mention']}")
    if entities.get('time_mention'):
        entity_summary.append(f"Preferred time: {entities['time_mention']}")
    if entities.get('format_preference'):
        entity_summary.append(f"Format: {entities['format_preference']}")
    if entities.get('therapist_preference'):
        entity_summary.append(f"Therapist preference: {entities['therapist_preference']}")

    block = f"""
## Booking Signal Detected
- Intent Strength: {booking_result['intent_strength']} (confidence: {booking_result['confidence']:.0%})
- Detected Preferences: {', '.join(entity_summary) if entity_summary else 'None explicitly stated'}

**Your Next Action**: The user is showing {booking_result['intent_strength']} booking interest.
"""
    if booking_result['intent_strength'] == 'explicit':
        block += "→ Immediately facilitate booking. Offer available slots or next steps.\n"
    elif booking_result['intent_strength'] == 'implicit':
        block += "→ Gently reflect their readiness and offer to help them take the next step.\n"
    elif booking_result['intent_strength'] == 'weak':
        block += "→ Acknowledge their openness. Don't push yet — one more turn of rapport building.\n"

    return block
```

---

## Summary

| Aspect | Decision |
|--------|----------|
| Architecture | DistilBERT joint model: binary intent + NER |
| Dataset | 1,000 examples (530 positive, 470 negative) |
| Key challenge | Detecting implicit booking signals |
| Entity extraction | 5 entity types (date, time, format, therapist, duration) |
| Integration | Runs during Stage 1 on every user message |
| Prompt use | Injects booking readiness level and next-action instruction into LLM system prompt |

---

*Document Version: 1.0 | Model Version: booking_intent_detector_saathi_v1 | Last Updated: 2025-03*
