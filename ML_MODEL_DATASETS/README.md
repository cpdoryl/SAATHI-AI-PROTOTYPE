# ML Model Datasets — Saathi AI Therapeutic Co-Pilot

Complete training datasets for all 10 ML classifier models and the RAG knowledge base.
All datasets are formatted for direct use — copy any file to another project.

---

## Dataset Index

| File | Format | Rows/Entries | Model | Purpose |
|------|--------|-------------|-------|---------|
| [01_emotion_detection_v1.csv](01_emotion_detection_v1.csv) | CSV | 120 rows | DistilBERT 8-class | Emotion detection fine-tuning |
| [02_crisis_detection_v1.csv](02_crisis_detection_v1.csv) | CSV | 160 rows | RoBERTa crisis classifier | Crisis detection fine-tuning |
| [03_intent_classifier_v1.csv](03_intent_classifier_v1.csv) | CSV | 95 rows | DistilBERT 7-class | Intent classification fine-tuning |
| [04_topic_classifier_v1.csv](04_topic_classifier_v1.csv) | CSV | 80 rows | DistilBERT multi-label | Topic classification fine-tuning |
| [05_sentiment_classifier_v1.csv](05_sentiment_classifier_v1.csv) | CSV | 80 rows | DistilBERT 3-class | Therapeutic sentiment fine-tuning |
| [06_meta_model_patterns_v1.json](06_meta_model_patterns_v1.json) | JSON | 40 objects | Flan-T5-large LoRA | Meta-model pattern detection |
| [07_stage1_sales_dataset.jsonl](07_stage1_sales_dataset.jsonl) | JSONL | 8 conversations | Qwen2.5-7B LoRA r=8 | Stage 1 lead generation fine-tuning |
| [08_stage2_therapy_dataset.jsonl](08_stage2_therapy_dataset.jsonl) | JSONL | 7 conversations | Qwen2.5-7B LoRA r=16 | Stage 2 therapy fine-tuning |
| [09_booking_intent_v1.json](09_booking_intent_v1.json) | JSON | 40 objects | DistilBERT + NER | Booking intent + entity extraction |
| [10_assessment_router_v1.json](10_assessment_router_v1.json) | JSON | 20 objects | RoBERTa multi-label | Assessment routing |
| [rag_knowledge_base.json](rag_knowledge_base.json) | JSON | 20 entries | Pinecone + MiniLM-L6 | RAG retrieval knowledge base |

---

## File Schemas

### CSV Files (01–05)

**01_emotion_detection_v1.csv**
```
text, primary_emotion, secondary_emotion, intensity
```
- `primary_emotion`: anxiety | sadness | anger | fear | hopelessness | guilt | shame | neutral
- `secondary_emotion`: same classes or "none"
- `intensity`: low | medium | high

**02_crisis_detection_v1.csv**
```
text, crisis_label, severity_score, c_ssrs_level
```
- `crisis_label`: suicidal_ideation | self_harm | abuse_disclosure | acute_distress | medical_emergency | substance_crisis | none
- `severity_score`: 0.0–1.0
- `c_ssrs_level`: passive_ideation | active_ideation | ideation_with_plan | ideation_with_intent | none

**03_intent_classifier_v1.csv**
```
text, intent, confidence_tier
```
- `intent`: seek_support | book_appointment | crisis_emergency | information_request | feedback_complaint | general_chat | assessment_request
- `confidence_tier`: high | medium | low

**04_topic_classifier_v1.csv**
```
text, topic_labels, primary_topic
```
- `topic_labels`: pipe-separated multi-label (e.g., "workplace_stress|relationship_issues")
- `primary_topic`: workplace_stress | relationship_issues | academic_stress | health_concerns | financial_stress

**05_sentiment_classifier_v1.csv**
```
text, sentiment_label, valence_score, therapeutic_relabeled, session_turn
```
- `sentiment_label`: positive | negative | neutral
- `valence_score`: -1.0 to +1.0
- `therapeutic_relabeled`: true (surface positive, clinically negative) | false
- `session_turn`: early | middle | late

---

### JSON Files (06, 09, 10)

**06_meta_model_patterns_v1.json** — Array of NLP pattern objects
```json
{
  "id": "mm_001",
  "text": "I always mess everything up.",
  "srl_annotations": {"predicate": "...", "agent": "...", "theme": "..."},
  "patterns_detected": [{
    "category": "deletion|generalization|distortion",
    "subtype": "universal_quantifier|mind_reading|...",
    "pattern_text": "always mess everything up",
    "recovery_question": "Always? Can you think of one time you didn't?",
    "severity": "low|medium|high"
  }],
  "multi_pattern": false
}
```

**09_booking_intent_v1.json** — Array of booking intent objects
```json
{
  "id": "bi_001",
  "text": "Book me a session for Saturday morning online.",
  "context_turns": ["..."],
  "booking_intent": true,
  "booking_confidence": 0.97,
  "entities": {
    "date": "Saturday", "time": "morning", "format": "online",
    "therapist_pref": null, "duration": null, "urgency": null
  },
  "trigger_booking_flow": true,
  "entity_count": 3
}
```

**10_assessment_router_v1.json** — Array of routing decision objects
```json
{
  "id": "ar_001",
  "conversation_context": [{"turn": 1, "speaker": "user", "text": "..."}],
  "recommended_assessments": ["PHQ-9", "DASS-21"],
  "primary_assessment": "PHQ-9",
  "routing_confidence": 0.95,
  "routing_reason": "Classic depression indicators...",
  "no_assessment_needed": false,
  "proactive_trigger": true
}
```

---

### JSONL Files (07, 08)

Each line is a complete multi-turn conversation in ChatML format:
```json
{
  "messages": [
    {"role": "system", "content": "System prompt..."},
    {"role": "user", "content": "User message..."},
    {"role": "assistant", "content": "Saathi response..."}
  ],
  "conversation_type": "A",
  "outcome": "booking_triggered|assessment_offered|crisis_escalated|skill_practiced|insight_gained",
  "turns": 8
}
```

**Stage 1 conversation types:**
- A: Stressed IT professional, receptive
- B: Skeptical user, resists therapy
- C: Crisis detected mid-conversation
- D: Ready to book immediately
- E: Privacy/cost questions
- F: Indian family/relationship context

**Stage 2 therapy modalities:**
- CBT (cognitive restructuring, thought records)
- DBT (TIPP, DEAR MAN, Radical Acceptance)
- ACT (values clarification, defusion)
- Behavioural Activation (depression)
- Motivational Interviewing (ambivalence)
- Grief support

---

### RAG Knowledge Base (rag_knowledge_base.json)

```json
{
  "id": "rag_001",
  "title": "Cognitive Restructuring — The Thought Record Technique",
  "content": "200–400 word clinical content...",
  "category": "cbt_techniques|dbt_skills|mindfulness|psychoeducation|crisis_resources|workplace_wellness|...",
  "tags": ["CBT", "thought_record", "depression"],
  "source": "clinical_guidelines|research_paper|psychoeducation|india_specific",
  "evidence_level": "A|B|C",
  "last_updated": "2025-01"
}
```

---

## How to Use in Training

### For CSV classifiers (DistilBERT/RoBERTa):
```python
import pandas as pd
from datasets import Dataset

df = pd.read_csv("01_emotion_detection_v1.csv")
dataset = Dataset.from_pandas(df)
# Use with HuggingFace Trainer or custom PyTorch training loop
```

### For JSONL LoRA fine-tuning (Qwen):
```python
from datasets import load_dataset

dataset = load_dataset("json", data_files="07_stage1_sales_dataset.jsonl")
# Use with TRL SFTTrainer
```

### For RAG vectorisation (Pinecone):
```python
import json
from sentence_transformers import SentenceTransformer

with open("rag_knowledge_base.json") as f:
    entries = json.load(f)

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
for entry in entries:
    embedding = model.encode(entry["content"])
    # upsert to Pinecone with id=entry["id"], metadata=entry
```

---

## Expanding the Datasets

These seed datasets are designed for schema validation and initial fine-tuning experiments.
For production-quality models, expand to:

| Model | Seed Examples | Production Target |
|-------|--------------|-------------------|
| Emotion detection | 120 | 8,000 |
| Crisis detection | 160 | 5,000 |
| Intent classifier | 95 | 4,000 |
| Topic classifier | 80 | 2,000 |
| Sentiment classifier | 80 | 2,000 |
| Meta-model patterns | 40 | 3,000 |
| Stage 1 LoRA | 8 conversations | 634 conversations |
| Stage 2 LoRA | 7 conversations | 3,017 conversations |
| Booking intent | 40 | 1,000 |
| Assessment router | 20 | 4,000 |
| RAG knowledge base | 20 entries | 500+ entries |

---

## Clinical Disclaimer

These datasets are intended for training AI support tools only. All clinical data used for training should be:
1. Reviewed by a licensed mental health professional before use
2. Expanded with real-world de-identified data from clinical settings
3. Validated for cultural appropriateness in the target population
4. Audited for bias and representation before production deployment

Crisis detection datasets in particular must be validated by clinical supervisors before training models deployed in production safety-critical systems.
