# ML Model Documentation — Master Index
## Saathi AI Therapeutic Co-Pilot Platform

---

## Overview

This directory contains detailed engineering and clinical documentation for **every machine learning classifier model** used in the Saathi AI platform. Each document covers the complete lifecycle of one model: from architectural rationale through training, evaluation, weight management, application integration, and prompt context building.

---

## Document Index

| # | Document | Model | Architecture | Dataset | Purpose |
|---|----------|-------|-------------|---------|---------|
| 01 | [Emotion Detection Classifier](./01_EMOTION_DETECTION_CLASSIFIER.md) | `emotion_classifier_saathi_v1` | DistilBERT (8-class) | 8,000 examples | Detects primary/secondary emotion + intensity on every user message |
| 02 | [Crisis Detection Classifier](./02_CRISIS_DETECTION_CLASSIFIER.md) | `crisis_classifier_saathi_v1` | RoBERTa + Keywords (7-class) | 5,000 examples | Safety-critical crisis detection; highest priority model |
| 03 | [Intent Classifier](./03_INTENT_CLASSIFIER.md) | `intent_classifier_saathi_v1` | DistilBERT (7-class) | 4,000 examples | Routes user message to correct handler |
| 04 | [Topic Classifier](./04_TOPIC_CLASSIFIER.md) | `topic_classifier_saathi_v1` | DistilBERT (multi-label, 5-class) | 2,000 examples | Identifies life domain (workplace/relationships/academic/health/financial) |
| 05 | [Sentiment Classifier](./05_SENTIMENT_CLASSIFIER.md) | `sentiment_classifier_saathi_v1` | DistilBERT (3-class) | 2,000 examples | Session-level valence tracking; lead score influence |
| 06 | [Meta-Model Pattern Detector](./06_META_MODEL_PATTERN_DETECTOR.md) | `meta_model_detector_saathi_v1` | AllenNLP SRL + Flan-T5-large LoRA | 3,000 examples | NLP linguistic pattern detection for therapeutic recovery questions |
| 07 | [LoRA Stage 1 — Lead Generation](./07_LORA_STAGE1_LEAD_GENERATION.md) | `qwen-lora-stage1` | Qwen2.5-7B + LoRA r=8 | 634 conversations | 8-step sales/onboarding conversation model |
| 08 | [LoRA Stage 2 — Therapeutic Support](./08_LORA_STAGE2_THERAPEUTIC_SUPPORT.md) | `qwen-lora-stage2` | Qwen2.5-7B + LoRA r=16 | 3,017 conversations | 11-step evidence-based therapeutic conversation model |
| 09 | [Booking Intent Detector](./09_BOOKING_INTENT_DETECTOR.md) | `booking_intent_detector_saathi_v1` | DistilBERT Joint (Binary + NER) | 1,000 examples | Detects booking readiness + extracts scheduling entities |
| 10 | [Assessment Router](./10_ASSESSMENT_ROUTER.md) | `assessment_router_saathi_v1` | RoBERTa-base (multi-label, 9-class) | 4,000 examples | Routes to appropriate clinical assessment (PHQ-9, GAD-7, DASS-21, etc.) |
| 14 | [Safety Guardrail System](./14_SAFETY_GUARDRAIL_SYSTEM.md) | `saathi-safety-classifier-v1` | DeBERTa-v3-small (multi-label, 6-class) + 5-layer runtime pipeline | 196 examples | Post-LLM response guardrail: hard-block rules, crisis validator, hallucination detector, ML classifier, sanitizer |

---

## System Architecture: How Models Work Together

```
User Message
     │
     ▼
┌────────────────────────────────────────────────────────────────┐
│  SAFETY LAYER (runs first on EVERY message, < 100ms)           │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Model 02: Crisis Detection                              │  │
│  │  RoBERTa + Keywords → crisis_flag, severity, type        │  │
│  └──────────────────────────────────────────────────────────┘  │
│       │                                                        │
│       ├─ IMMEDIATE crisis → CRISIS PROTOCOL (bypass LLM)      │
│       └─ ELEVATED crisis → flag, continue to classifiers      │
└────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────┐
│  SIGNAL CLASSIFICATION LAYER (runs in parallel, < 25ms each)  │
│                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────┐  │
│  │ Model 01    │  │ Model 03    │  │ Model 05               │  │
│  │ Emotion     │  │ Intent      │  │ Sentiment              │  │
│  │ Detector    │  │ Classifier  │  │ Classifier             │  │
│  └─────────────┘  └─────────────┘  └────────────────────────┘  │
│                         │                                       │
│                         ▼ Routing Decision                     │
└────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────┐
│  DOMAIN ENRICHMENT LAYER (route-specific, < 20ms each)        │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │ Model 04     │  │ Model 09     │  │ Model 10             │  │
│  │ Topic        │  │ Booking      │  │ Assessment           │  │
│  │ Classifier   │  │ Intent       │  │ Router               │  │
│  └──────────────┘  └──────────────┘  └─────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────┐
│  NLP ANALYSIS LAYER (therapeutic mode only, < 80ms)           │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Model 06: Meta-Model Pattern Detector                   │  │
│  │  AllenNLP SRL + Flan-T5-large → linguistic patterns      │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────┐
│  LLM GENERATION LAYER                                          │
│                                                                │
│  ┌──────────────────────────────┐  ┌────────────────────────┐  │
│  │  Model 07: LoRA Stage 1      │  │  Model 08: LoRA Stage 2 │  │
│  │  Qwen2.5-7B r=8             │  │  Qwen2.5-7B r=16       │  │
│  │  Lead Generation             │  │  Therapeutic Support   │  │
│  └──────────────────────────────┘  └────────────────────────┘  │
│       │                                    │                   │
│       └── System prompt enriched with all ML classifier outputs │
└────────────────────────────────────────────────────────────────┘
     │
     ▼
  AI Response delivered to user
```

---

## Prompt Context Assembly Pipeline

All classifier outputs flow into the LLM system prompt through a structured assembly:

```python
def assemble_complete_system_prompt(
    base_prompt: str,
    crisis_result: dict,       # Model 02
    emotion_result: dict,      # Model 01
    intent_result: dict,       # Model 03
    topic_result: dict,        # Model 04
    sentiment_result: dict,    # Model 05
    meta_model_result: dict,   # Model 06
    booking_result: dict,      # Model 09
    assessment_result: dict,   # Model 10
    therapeutic_step: str,
    session_info: dict
) -> str:
    blocks = [base_prompt]

    # Crisis block (if any flag)
    if crisis_result.get('crisis_flag'):
        blocks.append(build_crisis_system_prompt("", crisis_result))

    # Emotion context
    blocks.append(build_emotion_aware_system_prompt("", emotion_result, therapeutic_step, {}))

    # Intent and mode
    blocks.append(build_intent_context_block(intent_result))

    # Topic/domain
    blocks.append(build_topic_context_block(topic_result))

    # Sentiment trend
    blocks.append(build_sentiment_context_block(sentiment_result))

    # Meta-model patterns (therapeutic mode only)
    if meta_model_result.get('patterns_detected'):
        blocks.append(build_meta_model_context_block(meta_model_result))

    # Booking signals (Stage 1 only)
    if booking_result and booking_result.get('booking_intent'):
        blocks.append(build_booking_intent_context(booking_result))

    # Assessment routing (if recommended)
    if assessment_result and not assessment_result.get('no_assessment_needed'):
        blocks.append(build_assessment_context_block(assessment_result))

    return "\n\n".join(filter(None, blocks))
```

---

## Total Dataset Summary

| Model | Dataset Name | Size | Format |
|-------|-------------|------|--------|
| Emotion Classifier | `emotion_detection_v1` | 8,000 | CSV |
| Crisis Detector | `safety_crisis_v1` | 5,000 | CSV |
| Intent Classifier | `intent_classifier_v1` | 4,000 | CSV |
| Topic Classifier | `topic_classifier_v1` | 2,000 | CSV |
| Sentiment Classifier | `sentiment_classifier_v1` | 2,000 | CSV |
| Meta-Model Detector | `meta_model_patterns_v1` + subtypes | 3,000 | JSON |
| Stage 1 LoRA | `stage1_sales_dataset` | 634 | JSONL (ChatML) |
| Stage 2 LoRA | `stage2_therapy_dataset` | 3,017 | JSONL (ChatML) |
| Booking Intent | `booking_intent_detector_v1` | 1,000 | JSON |
| Assessment Router | `assessment_router_v1` | 4,000 | JSON |
| **TOTAL** | | **32,651** | |

---

## Model Production Locations

```
therapeutic-copilot/server/ml_models/
├── emotion_classifier/          # Model 01 (~250MB)
├── crisis_classifier/           # Model 02 (~476MB + keywords)
├── intent_classifier/           # Model 03 (~250MB)
├── topic_classifier/            # Model 04 (~250MB)
├── sentiment_classifier/        # Model 05 (~250MB)
├── meta_model_detector/         # Model 06 (~3GB or ~38MB LoRA adapter)
├── stage1_sales_model/          # Model 07 (~17MB LoRA adapter)
├── stage2_therapy_model/        # Model 08 (~38MB LoRA adapter)
├── booking_intent_detector/     # Model 09 (~250MB)
└── assessment_router/           # Model 10 (~476MB)

# Base model (shared by Models 07 and 08):
~/.cache/huggingface/hub/Qwen2.5-7B-Instruct/  # ~15GB FP16 or ~4GB 4-bit
```

---

## Priority Order for Production Deployment

1. **Model 02** (Crisis Detection) — Highest priority. Safety-critical.
2. **Model 01** (Emotion Detection) — Runs on every message.
3. **Model 03** (Intent Classifier) — Routing decisions.
4. **Model 07/08** (LoRA Stage 1/2) — Core conversational AI.
5. **Model 05** (Sentiment) — Session monitoring.
6. **Model 04** (Topic) — Domain enrichment.
7. **Model 09** (Booking Intent) — Commercial optimization.
8. **Model 10** (Assessment Router) — Clinical enrichment.
9. **Model 06** (Meta-Model Detector) — Advanced therapeutic depth.

---

*Documentation Version: 1.0 | Platform: Saathi AI Therapeutic Co-Pilot | Last Updated: 2025-03*
