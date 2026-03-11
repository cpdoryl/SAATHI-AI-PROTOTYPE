# SAATHI AI — Intent Classifier
# Complete Technical Documentation
# Training, Evaluation, Integration, and Reference

**Version**: 1.0
**Date**: 2026-03-11
**Author**: SAATHI AI Engineering — RYL NEUROACADEMY PRIVATE LIMITED
**Model**: DistilBERT-base-uncased, fine-tuned, 7-class intent classifier
**Reference doc**: ML_MODEL_DOCS/03_INTENT_CLASSIFIER.md

---

## Table of Contents

1. [Overview and Clinical Purpose](#1-overview-and-clinical-purpose)
2. [Model Architecture](#2-model-architecture)
3. [Dataset: Schema, Sources, and Distribution](#3-dataset-schema-sources-and-distribution)
4. [Dataset Quality Checks and Validation](#4-dataset-quality-checks-and-validation)
5. [Data Splits: Train / Val / Test](#5-data-splits-train--val--test)
6. [Training Strategy: 2-Phase Approach](#6-training-strategy-2-phase-approach)
7. [Training Configuration](#7-training-configuration)
8. [Class Weights: Handling Imbalance and Safety Priority](#8-class-weights-handling-imbalance-and-safety-priority)
9. [Epoch-by-Epoch Training Results](#9-epoch-by-epoch-training-results)
10. [Early Stopping Logic](#10-early-stopping-logic)
11. [Test Evaluation Results](#11-test-evaluation-results)
12. [Qualification Criteria and Pass/Fail Gates](#12-qualification-criteria-and-passfail-gates)
13. [Model Artifacts and File Structure](#13-model-artifacts-and-file-structure)
14. [Integration into SAATHI AI Workflow](#14-integration-into-saathi-ai-workflow)
15. [Routing Architecture: How Intent Drives Conversation Flow](#15-routing-architecture-how-intent-drives-conversation-flow)
16. [API Reference: Intent in Chat Response](#16-api-reference-intent-in-chat-response)
17. [Intent-to-Prompt Mapping](#17-intent-to-prompt-mapping)
18. [Smoke Test Cases](#18-smoke-test-cases)
19. [Scripts Reference](#19-scripts-reference)
20. [Deployment Checklist](#20-deployment-checklist)
21. [Known Boundaries and Notes](#21-known-boundaries-and-notes)

---

## 1. Overview and Clinical Purpose

### What This Model Does

The **Intent Classifier** determines *what the user wants to accomplish* with their message
— independent of what they are feeling. It answers: **"What does the user want to do right now?"**

This is fundamentally distinct from the Emotion Classifier (which answers "how is the user feeling?").
Both run on every message and together give the LLM the complete picture:
- Emotion tells the AI *how to respond*
- Intent tells the AI *what to respond with and where to route*

The model outputs:
- `primary_intent` — the dominant intent label (one of 7 classes)
- `confidence` — probability of the primary class (0.0–1.0)
- `secondary_intent` — secondary intent if its probability >= 0.35
- `routing_action` — the downstream routing decision derived from primary intent
- `all_scores` — full probability distribution across all 7 classes

### Why It Matters for the Platform

Without intent classification, every message gets a therapeutic response — even:
- "Can I book a session for Thursday?" → wastes a booking opportunity
- "What is CBT?" → deserves a factual answer, not therapeutic reflection
- "I want to hurt myself" → must go to crisis protocol, not general chat
- "Can I do the PHQ-9?" → should launch the assessment flow

The Intent Classifier routes each message to the correct handler in under 15ms,
before the LLM is invoked.

### Position in the Inference Pipeline

```
User Message
     |
     v
[Crisis Detection]  <-- always first, <100ms
     |
     v
[Emotion + Intent]  <-- concurrent, ~30ms each (asyncio.gather)
     |
     v
[Intent Routing]    <-- decides which handler to call
     |
     v
[LLM with enriched prompt (emotion + intent context blocks)]
```

---

## 2. Model Architecture

### Base Model

| Component | Detail |
|-----------|--------|
| Base model | `distilbert-base-uncased` |
| Parameters | 66,959,624 total |
| Encoder layers | 6 transformer blocks |
| Hidden size | 768 |
| Attention heads | 12 |
| Classification head | Linear(768 → 7) with dropout(0.2) |
| Sequence length | 128 tokens (max) |

### Why DistilBERT for Intent Classification?

**Speed requirement**: Intent runs on every message before routing. Target: <15ms.

DistilBERT achieves this because it is 40% smaller than BERT-base with 97% of
BERT's performance on GLUE benchmarks. For 7-class text classification on short
utterances (average ~8 words for intent messages), DistilBERT is the optimal
size/speed tradeoff.

**Why not zero-shot** (`facebook/bart-large-mnli`)?
- Zero-shot is 200–500ms — too slow for routing
- Does not understand domain-specific intents (`booking_initiation`, `assessment_request`)
- Cannot be tuned on proprietary conversation patterns from our corpus

**Why not a rule-based system?**
- Rule-based keyword matching fails on indirect phrasings:
  - "Maybe it's time I talked to someone properly" → should be `book_appointment`
  - "I can't take this anymore" → ambiguous between `seek_support` and `crisis_emergency`
- DistilBERT handles semantic similarity across paraphrases and implicit signals

### Multi-Intent Support

Some messages simultaneously express two intents:
- "I've been feeling really down and I think I need to book something"
  → `seek_support` (primary) + `book_appointment` (secondary)

The model outputs a probability vector for all 7 classes. Secondary intent is
reported when its probability >= 0.35 (lower than primary threshold).

---

## 3. Dataset: Schema, Sources, and Distribution

### 3.1 CSV Schema

```
id, utterance, primary_intent, secondary_intent, confidence, source, annotator_id, created_at
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Sequential ID (intent_000001) |
| `utterance` | string | User message text |
| `primary_intent` | enum(7) | Main intent label |
| `secondary_intent` | enum(7) / empty | Secondary intent if applicable |
| `confidence` | float | Annotator confidence (0.85–0.99) |
| `source` | string | Always "synthetic" for this dataset |
| `annotator_id` | string | ann_001 through ann_005 |
| `created_at` | ISO datetime | Synthetic timestamp (2024–2025) |

### 3.2 Intent Taxonomy

```
intents/
├── seek_support          → user wants emotional support, mental health help
│   ├── "I've been feeling really low lately"
│   └── "I need someone to talk to"
├── book_appointment      → user wants to schedule a session with a therapist
│   ├── "Can I book a session for Thursday?"
│   └── "I'd like to schedule my first appointment"
├── crisis_emergency      → user signals imminent danger to self or others
│   ├── "I want to hurt myself"
│   └── "I don't want to be here anymore"
├── information_request   → user wants factual/educational information
│   ├── "What is CBT?"
│   └── "How does therapy work?"
├── feedback_complaint    → user giving feedback or complaining
│   ├── "This app is not working properly"
│   └── "I want a refund for my session"
├── general_chat          → casual conversation, no specific goal
│   ├── "Hello, how are you?"
│   └── "Just wanted to check in"
└── assessment_request    → user wants to take a clinical assessment
    ├── "I want to take the PHQ-9 test"
    └── "Can I do a depression assessment?"
```

### 3.3 Dataset Distribution

| Class | Count | % of Total | Pool Size |
|-------|-------|------------|-----------|
| seek_support | 300 | 20.0% | 120 unique utterances |
| book_appointment | 250 | 16.7% | 75 unique utterances |
| crisis_emergency | 250 | 16.7% | 75 unique utterances |
| information_request | 200 | 13.3% | 75 unique utterances |
| feedback_complaint | 150 | 10.0% | 55 unique utterances |
| general_chat | 150 | 10.0% | 55 unique utterances |
| assessment_request | 200 | 13.3% | 60 unique utterances |
| **Total** | **1,500** | **100%** | |

### 3.4 Utterance Design Principles

Each class pool covers:
1. **Direct statements**: "I want to book a session"
2. **Indirect phrasings**: "Maybe it's time I talked to someone properly"
3. **Question forms**: "Is there an appointment available this week?"
4. **Implicit signals**: "I've been struggling more than I let on"
5. **Hinglish variants**: "Appointment kaise lun yahan se?" (booking), "Bahut bura lag raha hai" (seek_support)
6. **Ambiguous boundary cases**: Carefully assigned to the safer/more supportive intent

### 3.5 Ambiguity Resolution Rule

When a message is genuinely ambiguous:
- "I need help" → assigned `seek_support` (not `crisis_emergency` unless crisis signal present)
- "I can't take this anymore" → assigned `seek_support` (danger signals required for `crisis_emergency`)
- "I want to hurt myself" → `crisis_emergency` (clear safety signal)

**Rule**: When ambiguous between `crisis_emergency` and any other class,
prefer `crisis_emergency`. Otherwise, prefer the more supportive intent.

---

## 4. Dataset Quality Checks and Validation

All checks run automatically in `prepare_data_splits.py`:

### Check 1: Zero Leakage Between Splits

```
Train+Val overlap   : 0 (PASS)
Train+Test overlap  : 0 (PASS)
Val+Test overlap    : 0 (PASS)
```
No utterance appears in more than one split.

### Check 2: All 7 Classes Present in All 3 Splits

```
train classes check : PASS (all 7 classes present)
val   classes check : PASS (all 7 classes present)
test  classes check : PASS (all 7 classes present)
```
Guaranteed by stratified splitting with `stratify=df['primary_intent']`.

### Check 3: Phrasing Diversity (Unique Start Words)

| Class | Unique First Words | Target |
|-------|-------------------|--------|
| seek_support | 11 | >10 |
| book_appointment | 11 | >10 |
| crisis_emergency | 6 | >10 (expected — "I" dominates crisis language) |
| information_request | 7 | >10 (expected — "What/How" dominates) |
| feedback_complaint | 11 | >10 |
| general_chat | 22 | >10 |
| assessment_request | 11 | >10 |

**Note on crisis_emergency (6 unique starts)**: Crisis utterances are
clinically realistic: they predominantly begin with "I" because crisis
expressions are intensely personal. This is not a dataset deficiency —
it reflects how users actually express crisis states. The model must
distinguish between "I feel sad" (seek_support) and "I want to hurt
myself" (crisis_emergency) based on semantic content, not surface form.

### Check 4: Secondary Intent Plausibility

Secondary intents are drawn from contextually plausible pairings:
- `seek_support` secondary: book_appointment or general_chat (exploring)
- `book_appointment` secondary: seek_support (also needs support)
- `crisis_emergency` secondary: seek_support (wants help)
- `assessment_request` secondary: seek_support or information_request

Total secondary intent count: ~529 examples (~35% of dataset)

---

## 5. Data Splits: Train / Val / Test

### Split Strategy

```
Method   : Stratified split preserving class proportions
Ratio    : 80% train / 10% val / 10% test
Seed     : 42
Split by : primary_intent
```

### Per-Class Counts

| Class | Train | Val | Test |
|-------|-------|-----|------|
| seek_support | 240 | 30 | 30 |
| book_appointment | 200 | 25 | 25 |
| crisis_emergency | 200 | 25 | 25 |
| information_request | 160 | 20 | 20 |
| feedback_complaint | 120 | 15 | 15 |
| general_chat | 120 | 15 | 15 |
| assessment_request | 160 | 20 | 20 |
| **Total** | **1,200** | **150** | **150** |

### Why Stratified?

Without stratification, small classes (feedback_complaint: 150 total) could be
underrepresented in val/test. Stratification guarantees each split has the same
proportional class distribution as the full dataset, preventing evaluation bias.

---

## 6. Training Strategy: 2-Phase Approach

### Phase 1 — Classifier Head Warmup (Encoder Frozen)

**Purpose**: Initialize the randomly-initialized classification head
(Linear 768→7) to produce meaningful probability distributions before
the encoder is touched. If we immediately unfreeze the encoder with
a random head, the gradients from the head can corrupt the pre-trained
DistilBERT representations.

| Setting | Value |
|---------|-------|
| Frozen | All encoder layers |
| Trainable | Linear(768→7) + pre-classifier only (~597K params) |
| Epochs | 2 |
| Learning rate | 1e-3 (high — only head is updated) |
| Loss | Standard CrossEntropyLoss (no class weights) |

### Phase 2 — Full Fine-tuning (All Layers Unfrozen)

**Purpose**: Adapt the full DistilBERT encoder to the mental health
conversation domain, guided by the warmed-up classification head.

| Setting | Value |
|---------|-------|
| Frozen | Nothing (all 67M parameters trainable) |
| Epochs | Up to 4 |
| Learning rate | 3e-5 (low — protects pre-trained weights) |
| Warmup | 10% of total steps (linear warmup) |
| Weight decay | 0.01 |
| Loss | CrossEntropyLoss with class weights (crisis=3.0, assessment=2.0) |
| Early stopping | patience=3 on val macro_f1 |

### Why 2-Phase Instead of Direct Fine-tuning?

Direct fine-tuning (skip Phase 1) risks **catastrophic forgetting**: the random
classification head introduces large initial gradients that propagate through
all 6 transformer layers and can corrupt the semantic representations BERT learned
during pre-training.

2-phase training:
1. Phase 1 stabilises the head with minimal data (no encoder disruption)
2. Phase 2 fine-tunes everything starting from a coherent state

Result: Faster convergence, better generalisation, especially on small datasets.

---

## 7. Training Configuration

### Full Hyperparameter Table

| Parameter | Phase 1 | Phase 2 |
|-----------|---------|---------|
| Base model | distilbert-base-uncased | distilbert-base-uncased |
| Trainable parameters | 596,744 (~0.9%) | 66,959,624 (100%) |
| Epochs | 2 | Up to 4 |
| Learning rate | 1e-3 | 3e-5 |
| Batch size | 16 | 16 |
| Max sequence length | 128 | 128 |
| Optimizer | AdamW | AdamW |
| Weight decay | — | 0.01 |
| LR schedule | Constant | Linear warmup + linear decay |
| Warmup steps | — | 10% of total steps |
| Gradient clip | — | 1.0 |
| Loss function | CrossEntropyLoss | CrossEntropyLoss (weighted) |
| Early stopping | — | patience=3 on val macro_f1 |
| Random seed | 42 | 42 |
| Device | CPU | CPU |
| Checkpoint criterion | — | Best val macro_f1 |

---

## 8. Class Weights: Handling Imbalance and Safety Priority

### Why Class Weights?

Two types of problems are addressed:

**Problem 1 — Class imbalance**: `seek_support` has 300 examples vs
`general_chat` and `feedback_complaint` with 150. Without weighting,
the model optimises for the majority class.

**Problem 2 — Safety priority**: `crisis_emergency` carries the highest
clinical risk. A false negative (failing to detect crisis intent) is
catastrophically worse than a false positive. The 3.0 weight causes
the model to be aggressively penalised for missing any crisis utterance.

### Weight Values (from spec 03_INTENT_CLASSIFIER.md)

| Class | Weight | Reason |
|-------|--------|--------|
| seek_support | 1.5 | Most common class — mild upweight |
| book_appointment | 1.2 | Important commercial intent — slight upweight |
| crisis_emergency | **3.0** | Safety-critical — maximum penalty for misses |
| information_request | 1.0 | Balanced class |
| feedback_complaint | 1.0 | Balanced class |
| general_chat | 1.0 | Balanced class |
| assessment_request | **2.0** | Smallest class — prevent neglect |

**Note**: These are fixed specification weights (not auto-computed from sklearn),
reflecting deliberate safety decisions rather than pure statistical balancing.

---

## 9. Epoch-by-Epoch Training Results

### Phase 1 Results (classifier head only)

| Epoch | Train Loss | Train Acc | Train F1 | Val Loss | Val Acc | Val F1 | Time |
|-------|-----------|-----------|----------|----------|---------|--------|------|
| 1 | 1.0907 | 63.3% | 0.6216 | 0.6169 | 79.3% | 0.7811 | 49s |
| 2 | 0.4970 | 83.4% | 0.8369 | 0.3751 | 90.0% | 0.9130 | 56s |

Phase 1 observations:
- Epoch 1: Classifier head begins to differentiate 7 classes from BERT embeddings (63% train acc)
- Epoch 2: Head finds strong decision boundaries; val F1 reaches 0.913 — already above the 0.85 gate
- Only 595,975 of 67M parameters were updated; encoder representations preserved intact

### Phase 2 Results (full fine-tuning)

Best checkpoint: **Epoch 2** (val_f1 = 0.9894). Epochs 3–4 showed no improvement (patience=3 would have triggered at Epoch 4, but all 4 epochs ran to completion).

| Epoch | Train Loss | Train Acc | Train F1 | Val Loss | Val Acc | Val F1 | Improved? |
|-------|-----------|-----------|----------|----------|---------|--------|-----------|
| 1 | 0.1809 | 93.8% | 0.9397 | 0.1155 | 97.3% | 0.9765 | YES (best) |
| 2 | 0.0177 | 99.5% | 0.9945 | 0.0684 | 98.7% | 0.9894 | YES (best) |
| 3 | 0.0032 | 99.8% | 0.9982 | 0.1798 | 98.7% | 0.9894 | No change |
| 4 | 0.0004 | 100.0% | 1.0000 | 0.1852 | 98.7% | 0.9894 | No change |

Phase 2 observations:
- Epoch 1: Unfreezing the encoder causes immediate jump to val_f1=0.977 — BERT's representations are highly separable for these 7 intent classes
- Epoch 2: Essentially perfect learning — val_f1=0.989, val accuracy=98.7%
- Epoch 3–4: Training approaches 100% but val plateaus (slight validation loss increase — minor overfitting begins)
- Best checkpoint is Epoch 2; Epochs 3–4 do not improve validation performance
- Train-val gap at Epoch 4 (1.000 vs 0.989) is minimal — model generalises well

*Full per-step metrics in `results/training_history.json`.*

---

## 10. Early Stopping Logic

Early stopping monitors **val macro_f1** (not loss or accuracy).

```
patience = 3
best_macro_f1 = 0.0
patience_counter = 0

for each Phase 2 epoch:
    if val_macro_f1 > best_macro_f1:
        best_macro_f1 = val_macro_f1
        patience_counter = 0
        save_checkpoint()       <-- model.save_pretrained(MODEL_DIR)
    else:
        patience_counter += 1
        if patience_counter >= 3:
            STOP training
```

**Why macro_f1?** Macro F1 averages F1 equally across all 7 classes —
it does not allow a model that is excellent on frequent classes
(seek_support, book_appointment) but poor on rare classes (feedback_complaint,
assessment_request) to appear better than it is.

**Why not loss?** Validation loss can improve even when per-class balance
worsens (the model can reduce loss by becoming more confident on easy classes
at the expense of harder ones).

---

## 11. Test Evaluation Results

Best checkpoint (P2 Epoch 2) evaluated on held-out test set (150 samples, never seen during training).

### Overall Metrics

| Metric | Minimum Required | Target | **Actual (Test)** | Status |
|--------|-----------------|--------|-------------------|--------|
| Overall accuracy | 88% | 92% | **100.00%** | EXCEEDED TARGET |
| Macro F1 | 0.85 | 0.90 | **1.0000** | EXCEEDED TARGET |
| Weighted F1 | — | — | **1.0000** | — |
| crisis_emergency recall | 95% | 99% | **100.00%** | EXCEEDED TARGET |
| book_appointment F1 | 0.90 | 0.95 | **1.0000** | EXCEEDED TARGET |
| assessment_request F1 | 0.80 | 0.88 | **1.0000** | EXCEEDED TARGET |

### Per-Class Test Results

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| seek_support | 1.00 | 1.00 | **1.000** | 30 |
| book_appointment | 1.00 | 1.00 | **1.000** | 25 |
| crisis_emergency | 1.00 | 1.00 | **1.000** | 25 |
| information_request | 1.00 | 1.00 | **1.000** | 20 |
| feedback_complaint | 1.00 | 1.00 | **1.000** | 15 |
| general_chat | 1.00 | 1.00 | **1.000** | 15 |
| assessment_request | 1.00 | 1.00 | **1.000** | 20 |
| **macro avg** | **1.00** | **1.00** | **1.000** | 150 |
| **weighted avg** | **1.00** | **1.00** | **1.000** | 150 |

### Key Observations

- **Perfect classification across all 7 classes**: Zero misclassifications on the 150-example test set
- **crisis_emergency recall = 1.00**: Every crisis-intent message correctly identified — safety gate fully satisfied
- **Confusion matrix**: Identity matrix (150×7 diagonal) — zero off-diagonal errors
- **Smoke tests**: 7/7 routing tests pass with confidence = 1.00 for all
- **Why such high performance?** The 7 intent classes are semantically well-separated in DistilBERT's embedding space. Intent classification is inherently less ambiguous than emotion classification (where guilt/shame overlap) — the phrases associated with "booking an appointment" vs "seeking emotional support" vs "requesting information" carry distinct vocabulary that DistilBERT learns to separate reliably.

### Note on Perfect Score

100% accuracy on a 150-example synthetic test set should be interpreted as
"the model has perfectly learned the patterns in this dataset". In production,
the model will encounter more ambiguous real-world utterances. The model's
strong generalisation (val_f1=0.989) indicates robust representations.
Monitoring on real user interactions is recommended (see Section 21).

### Confusion Matrix

No confusion errors observed. The confusion matrix is a 7×7 identity matrix.
Full data in `results/test_evaluation.json`.

---

## 12. Qualification Criteria and Pass/Fail Gates

All three gates must pass for production approval.

### Gate 1: Overall Accuracy >= 88%

```
Threshold: >= 0.88
Clinical reason: Below 88%, the model is mislabelling too many utterances
                 for routing decisions to be trustworthy.
```

### Gate 2: Macro F1 >= 0.85

```
Threshold: >= 0.85
Clinical reason: Ensures no class is systematically ignored.
                 A model that ignores feedback_complaint or assessment_request
                 is inadequate even if overall accuracy is high.
```

### Gate 3: crisis_emergency Recall >= 95%

```
Threshold: >= 0.95
Clinical reason: This is the safety-critical gate.
                 crisis_emergency recall measures: of all the messages that
                 were genuinely crisis-expressing, what fraction did the model
                 correctly identify?
                 A recall of 95% means at most 5% of crisis messages are missed.
                 This is a hard minimum, not a target.
                 Note: The Crisis Detection Classifier (Model 02) is the primary
                 safety layer. The Intent Classifier is a secondary routing layer.
                 Both must function correctly for full safety coverage.
```

### Approval Status

```
Gate 1 (Accuracy >= 88%)              : PASS  -- Actual: 100.00%
Gate 2 (Macro F1 >= 0.85)             : PASS  -- Actual: 1.0000
Gate 3 (crisis_emergency recall >= 95%): PASS  -- Actual: 1.0000 (100%)
----------------------------------------------------
OVERALL APPROVAL STATUS               : APPROVED (all gates passed)
Evaluated on                          : 2026-03-11
Best checkpoint                       : P2 Epoch 2 (models/best_model/)
Total training time                   : 11.9 minutes (CPU)
```

---

## 13. Model Artifacts and File Structure

### Training Folder

```
Intent classifier model/
├── intent_classifier_v1.csv         -- Full dataset (1,500 examples)
├── data/
│   └── splits/
│       ├── train.csv                -- 1,200 training examples
│       ├── val.csv                  -- 150 validation examples
│       ├── test.csv                 -- 150 test examples
│       └── split_info.json          -- Split metadata
├── models/
│   └── best_model/                  -- HuggingFace save_pretrained format
│       ├── model.safetensors        -- Trained weights (~255MB)
│       ├── config.json              -- Model configuration
│       ├── tokenizer.json           -- DistilBERT vocabulary
│       ├── tokenizer_config.json    -- Tokenizer settings
│       └── checkpoint_meta.json     -- Best epoch, val_f1
├── results/
│   ├── training_history.json        -- Per-epoch train/val metrics
│   ├── test_evaluation.json         -- Full test metrics + qualification gates
│   └── test_evaluation.txt          -- Human-readable summary
├── logs/
│   └── training_YYYYMMDD_HHMMSS.log -- Full training log
└── scripts/
    ├── generate_dataset.py          -- Creates intent_classifier_v1.csv
    ├── prepare_data_splits.py       -- Creates train/val/test splits
    ├── train_intent_distilbert.py   -- 2-phase training loop
    └── evaluate_model.py            -- Standalone evaluator
```

### Server Deployment Folder

```
therapeutic-copilot/server/
├── ml_models/
│   └── intent_classifier/           -- Copied by setup_intent_model.py
│       ├── model.safetensors
│       ├── config.json
│       ├── tokenizer.json
│       └── tokenizer_config.json
├── services/
│   └── intent_classifier_service.py -- Singleton service
├── config/
│   └── intent_prompt_context.py     -- Intent → prompt templates
└── scripts/
    └── setup_intent_model.py        -- Copies model from training folder
```

---

## 14. Integration into SAATHI AI Workflow

### How the Intent Classifier Plugs into `process_message()`

```python
# therapeutic_ai_service.py — process_message()

# Step 1: Crisis scan (ALWAYS FIRST)
crisis_result = self.crisis_detector.scan(message)

# Step 2: Emotion + Intent classification (concurrent, ~30ms each)
async def _classify_emotion():
    return await run_in_executor(None, get_emotion_service().classify, message)

async def _classify_intent():
    return await run_in_executor(None, get_intent_service().classify, message)

emo_result, int_result = await asyncio.gather(
    _classify_emotion(), _classify_intent()
)

# Step 3: Crisis check (if severity >= 7 → skip LLM, go to crisis protocol)
if crisis_result["severity"] >= 7:
    return await self._handle_crisis(...)

# Step 4: RAG retrieval
rag_context = await self.rag.query(...)

# Step 5: Build base prompt + append emotion + intent context blocks
prompt = self.chatbot.build_response_prompt(...)
if emotion_context_block:
    prompt = f"{prompt}\n\n{emotion_context_block}"
if intent_context_block:
    prompt = f"{prompt}\n\n{intent_context_block}"

# Step 6: LLM inference with fully enriched prompt
response = await self.llm.generate(prompt=prompt, stage=stage)
```

### asyncio.gather() for Parallel Classification

Emotion and intent classification run **concurrently** via `asyncio.gather()`.
Both are CPU-bound operations delegated to a thread pool via `run_in_executor`.
Total latency is `max(emotion_time, intent_time)` — approximately 30ms —
rather than `emotion_time + intent_time` (60ms) if run sequentially.

---

## 15. Routing Architecture: How Intent Drives Conversation Flow

### Intent → Routing → Handler

```
primary_intent           routing_action              handler
─────────────────────────────────────────────────────────────
seek_support        ──▶  THERAPEUTIC_CONVERSATION  ──▶ therapeutic_handler()
book_appointment    ──▶  BOOKING_FLOW              ──▶ booking_handler()
crisis_emergency    ──▶  CRISIS_PROTOCOL           ──▶ crisis_handler()
information_request ──▶  RAG_KNOWLEDGE_BASE        ──▶ rag_handler()
feedback_complaint  ──▶  SUPPORT_HANDLER           ──▶ support_handler()
general_chat        ──▶  CONVERSATIONAL            ──▶ therapeutic_handler()
assessment_request  ──▶  ASSESSMENT_ROUTER         ──▶ assessment_handler()
```

### Routing Priority Order

1. **Crisis Detection Classifier** (Model 02) runs first and can bypass
   the intent routing entirely if severity >= 7
2. **Intent Classifier** provides `crisis_emergency` as a second safety
   layer for borderline cases that the Crisis Classifier rated below 7
3. **Emotion Classifier** enriches the prompt but does not change routing

### crisis_emergency as Routing Backup

Even when the Crisis Classifier runs but scores < 7 (below hard threshold),
the Intent Classifier may still detect `crisis_emergency` intent. In this case:
- The `intent_context_block` includes a WARNING note in the LLM prompt
- The response is guided to elevated care mode
- The `routing_action = CRISIS_PROTOCOL` is returned in the API response

This two-layer approach ensures no borderline crisis message is completely missed.

---

## 16. API Reference: Intent in Chat Response

### Chat Endpoint Response Schema

The `/api/v1/chat/message` response now includes intent fields:

```json
{
  "response":           "I hear that you're struggling. Let's talk...",
  "crisis_score":       2,
  "stage":              2,
  "current_step":       3,
  "ml_crisis_class":    "mild_distress",
  "ml_model_phase":     "phase3",
  "detection_method":   "distilbert_ml",
  "emotion":            "sadness",
  "emotion_intensity":  0.84,
  "emotion_secondary":  null,
  "intent":             "seek_support",
  "intent_confidence":  0.92,
  "routing_action":     "THERAPEUTIC_CONVERSATION",
  "intent_secondary":   null
}
```

### IntentResult Fields

| Field | Type | Description |
|-------|------|-------------|
| `intent` | string | Primary intent class (7 values) |
| `intent_confidence` | float | Probability 0.0–1.0 |
| `routing_action` | string | Downstream routing decision |
| `intent_secondary` | string / null | Secondary intent (if prob >= 0.35) |

---

## 17. Intent-to-Prompt Mapping

The `build_intent_context_block()` function in `config/intent_prompt_context.py`
injects the following structured block into the LLM system prompt.

### Prompt Block Format

For a message classified as `seek_support (0.92)`:

```
## User Intent (Intent Classifier)
- Primary Intent  : seek_support (confidence: 92%)
- Routing Action  : THERAPEUTIC_CONVERSATION
- Mode            : therapeutic
- Instruction     : The user is seeking emotional support. Enter therapeutic
                    listening mode. Prioritize validation and empathy over
                    advice or information.
- Response Style  : empathetic, exploratory, non-directive
- Avoid           : unsolicited advice, silver linings, minimizing their pain
```

### Full Mapping Table

| Intent | Mode | Response Style | Key Instruction |
|--------|------|----------------|-----------------|
| seek_support | therapeutic | empathetic, exploratory | Validate first, no unsolicited advice |
| book_appointment | booking | helpful, action-oriented | Gather availability, guide booking warmly |
| crisis_emergency | crisis | calm, direct, safety-focused | Override all other routing; prioritize safety |
| information_request | educational | clear, educational | Answer first, then offer follow-up support |
| feedback_complaint | support | professional, empathetic | Acknowledge sincerely, offer resolution path |
| general_chat | conversational | casual, curious | Engage warmly, gently explore reason for visit |
| assessment_request | assessment | structured, warm, clinical | Confirm which assessment, then launch flow |

### crisis_emergency Special Handling

When `intent = crisis_emergency`, the context block includes an additional note:

```
CRITICAL: Intent Classifier flagged crisis_emergency.
Even if Crisis Detector did not trigger at severity >= 7,
treat this message with elevated care.
Do not normalise or redirect away.
```

### Secondary Intent Handling

When a secondary intent is detected (probability >= 0.35):

```
Note: Secondary intent (book_appointment, confidence: 38%) also detected.
  Secondary instruction: The user wants to schedule a session. Acknowledge
  their readiness warmly and guide them through the booking process.
```

---

## 18. Smoke Test Cases

These 7 test cases verify that the deployed model classifies correctly.
Run manually after `setup_intent_model.py`:

```python
import sys
sys.path.insert(0, 'therapeutic-copilot/server')
from services.intent_classifier_service import get_intent_service

svc = get_intent_service()
tests = [
    ("I've been feeling really low lately and need support",         "seek_support"),
    ("I'd like to book a session for Thursday afternoon",            "book_appointment"),
    ("I want to hurt myself and I don't know what to do",           "crisis_emergency"),
    ("What is the difference between CBT and DBT?",                 "information_request"),
    ("This app keeps crashing and I want a refund",                 "feedback_complaint"),
    ("Hi there, just wanted to check out the platform",             "general_chat"),
    ("I want to take the PHQ-9 depression assessment",              "assessment_request"),
]

for text, expected in tests:
    r = svc.classify(text)
    status = "PASS" if r.primary_intent == expected else "FAIL"
    print(f"{status} | expected={expected:<22} | got={r.primary_intent:<22} | conf={r.confidence:.2f}")
```

### Routing Validation Tests

```python
ROUTING_TESTS = [
    ("I need to book a session this week",         "BOOKING_FLOW"),
    ("I want to kill myself",                      "CRISIS_PROTOCOL"),
    ("What is CBT?",                               "RAG_KNOWLEDGE_BASE"),
    ("Can I do the depression test?",              "ASSESSMENT_ROUTER"),
    ("This app sucks",                             "SUPPORT_HANDLER"),
    ("Hello just browsing",                        "CONVERSATIONAL"),
    ("I'm struggling with my anxiety",             "THERAPEUTIC_CONVERSATION"),
]

for text, expected_route in ROUTING_TESTS:
    r = svc.classify(text)
    status = "PASS" if r.routing_action == expected_route else "FAIL"
    print(f"{status} | route={r.routing_action} | expected={expected_route}")
```

---

## 19. Scripts Reference

### generate_dataset.py

```
Purpose  : Generate intent_classifier_v1.csv (1,500 examples, 7 classes)
Input    : Hardcoded utterance pools per class in script
Output   : intent_classifier_v1.csv
Run      : python "Intent classifier model/scripts/generate_dataset.py"
```

### prepare_data_splits.py

```
Purpose  : Stratified 80/10/10 split with quality checks
Input    : intent_classifier_v1.csv
Output   : data/splits/train.csv, val.csv, test.csv, split_info.json
Run      : python "Intent classifier model/scripts/prepare_data_splits.py"
```

### train_intent_distilbert.py

```
Purpose  : 2-phase DistilBERT fine-tuning
Input    : data/splits/train.csv, val.csv, test.csv
Output   : models/best_model/ (HF format), results/*.json, logs/*.log
Run      : python "Intent classifier model/scripts/train_intent_distilbert.py"
Duration : 11.9 minutes on CPU (1,200 training examples, 6 epochs total)
```

### evaluate_model.py

```
Purpose  : Standalone evaluation of any checkpoint on any split
Args     : --model_path (default: models/best_model)
           --split (train | val | test)
Output   : results/eval_{split}.json
Run      : python scripts/evaluate_model.py
           python scripts/evaluate_model.py --split val
```

### setup_intent_model.py (server-side)

```
Purpose  : Copy trained model to server/ml_models/intent_classifier/
Input    : Intent classifier model/models/best_model/
Output   : therapeutic-copilot/server/ml_models/intent_classifier/
Run      : python therapeutic-copilot/server/scripts/setup_intent_model.py
           (from repo root)
```

---

## 20. Deployment Checklist

### One-Time Setup

```
[x] Training complete                                                 (2026-03-11, 11.9 min)
[x] results/test_evaluation.txt shows APPROVED                       (all 3 gates passed)
[x] All 3 qualification gates passed                                  (acc=100%, mF1=1.0, crisis_recall=1.0)
[x] Run setup_intent_model.py to copy model to server                 (DONE, 255.4 MB copied)
[x] Verify server/ml_models/intent_classifier/model.safetensors exists (DONE, verification PASS)
[ ] pip install torch transformers (if not already installed on server)
[ ] Start server: uvicorn main:app
[ ] Check startup logs: "Intent classifier loaded and ready (DistilBERT 7-class)."
[x] Run smoke tests (Section 18)                                      (7/7 PASS, all conf=1.00)
[ ] Verify chat response includes "intent" and "routing_action" fields
```

### Verification Command

```bash
# From repo root — verifies model loads and all 7 routing tests pass
python -c "
import sys
sys.path.insert(0, 'therapeutic-copilot/server')
from services.intent_classifier_service import get_intent_service
svc = get_intent_service()
print('Ready:', svc.is_ready)
r = svc.classify('I need to book a session')
print('intent:', r.primary_intent, '| route:', r.routing_action)
"
```

---

## 21. Known Boundaries and Notes

### 1. seek_support vs crisis_emergency Boundary

The most clinically important boundary. Utterances like "I can't take this
anymore" or "I feel like giving up" can be ambiguous. The training data
assigns these to `seek_support` unless explicit self-harm language is present.
The Crisis Detection Classifier (Model 02) is the primary safety layer;
the Intent Classifier provides secondary routing support.

### 2. Hinglish Coverage

The dataset includes representative Hinglish utterances per class.
Coverage is adequate for common phrases but may degrade on heavy code-switching
or regional dialect variations. A Hinglish-augmented dataset version is planned.

### 3. seek_support Dominance

`seek_support` is the largest class (300 examples, 20% of dataset).
The 1.5 class weight partially compensates. If seek_support precision is
high at the expense of recall for minority classes, consider increasing
crisis_emergency weight to 3.5 in the next training run.

### 4. assessment_request vs information_request Boundary

"How do I check my anxiety levels?" is genuinely ambiguous between
`information_request` and `assessment_request`. The dataset labels
such cases as `information_request` because the user is asking *how*,
not requesting to *do* the assessment. Explicit request phrasing
("I want to take/do/complete the [assessment]") maps to `assessment_request`.

### 5. general_chat has Highest Diversity

`general_chat` has 22 unique start words — the highest in the dataset.
This is correct: casual conversation has the most diverse phrasing.
The model must learn to distinguish "Hello how are you?" (general_chat)
from "I've been really struggling" (seek_support) even when both start
with non-intent-specific words.

### 6. Model Does Not Replace Crisis Detection

`crisis_emergency` in the Intent Classifier is a **routing signal**,
not a clinical safety assessment. The Crisis Detection Classifier
(DistilBERT + keyword rules, C-SSRS 6-class) is always the safety layer.
The Intent Classifier's crisis detection enables routing even for
borderline cases that score < 7 on the crisis severity scale.

---

*Document Version: 1.0 | Model Version: intent_classifier_saathi_v1*
*Training Date: 2026-03-11 | Platform: SAATHI AI Therapeutic Co-Pilot*
*Company: RYL NEUROACADEMY PRIVATE LIMITED*
