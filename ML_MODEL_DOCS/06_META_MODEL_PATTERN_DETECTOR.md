# Model Document 06: Meta-Model Pattern Detector (NLP)
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
The **Meta-Model Pattern Detector** is Saathi's most unique and therapeutically sophisticated classifier. It is based on Richard Bandler and John Grinder's **Linguistic Meta-Model** from Neuro-Linguistic Programming (NLP) — a framework that identifies how people systematically distort, delete, and generalize their experience through language. By detecting these patterns, the therapeutic AI can ask precision recovery questions that help users access their own deeper understanding and resources.

### The Meta-Model Framework

The linguistic Meta-Model identifies how surface-level language conceals the deeper structure of a person's internal experience. Three main violation categories exist:

#### 1. Deletions
The speaker omits information from their surface structure that is present in their deeper structure:
- **Unspecified referential index**: "They make me feel worthless" → Who specifically is "they"?
- **Unspecified verb**: "He upset me" → How exactly did he upset you?
- **Comparative deletion**: "I'm better off alone" → Better off than whom? Compared to what?

#### 2. Generalizations
The speaker treats a specific experience as a universal rule:
- **Universal quantifiers**: "Nobody ever listens to me" → Nobody? Ever?
- **Modal operators of necessity**: "I must be perfect" → What would happen if you weren't?
- **Modal operators of possibility**: "I can't talk about this" → What stops you?

#### 3. Distortions
The speaker misrepresents reality in their linguistic structure:
- **Mind reading**: "She thinks I'm a failure" → How do you know what she thinks?
- **Cause and effect**: "You make me angry" → How exactly does their behavior cause your anger?
- **Complex equivalence**: "He doesn't talk to me, so he hates me" → How does not talking mean he hates you?
- **Presupposition**: "When things get worse..." → What makes you think things will get worse?
- **Nominalization**: "I'm in a deep depression" → Depression as a noun (static state) vs. "I'm depressing myself" (process that can change)

### Why It Matters for Therapy
These linguistic patterns are not just grammatical curiosities — they reveal **limiting beliefs and cognitive distortions** that a therapist needs to challenge. By automatically detecting these patterns, the AI can generate the exact type of recovery question that an NLP practitioner or CBT therapist would ask, at the right moment in the conversation.

### Scope
- **Input**: User utterance (text string)
- **Output**: Detected patterns list, each with `pattern_type`, `pattern_subtype`, `matched_text`, `confidence`, `recovery_questions`
- **Classes**: 11 pattern subtypes across 3 categories

---

## 2. Why We Chose This Model Architecture

### Architecture: Hybrid — AllenNLP SRL + Fine-tuned Flan-T5-large (Seq2Seq)

This is a **two-component system**:

#### Component 1: AllenNLP Semantic Role Labeling (SRL)
**What it does**: Identifies syntactic structure — who is doing what to whom (predicate-argument structure). This provides the structural foundation for detecting generalizations and deletions.

```python
# AllenNLP SRL identifies sentence structure:
# "Nobody ever listens to me"
# → ARG0: Nobody, VERB: listens, ARGM-TMP: ever, ARG2: to me
# Pattern detected: universal_quantifier ("nobody"), temporal_quantifier ("ever")
```

**Why AllenNLP SRL?**
- State-of-the-art semantic role labeling with structured output
- Provides predicate-argument structure needed to identify missing arguments (deletions)
- Well-maintained, production-ready model
- Works on short therapeutic utterances effectively

#### Component 2: Fine-tuned Flan-T5-large (Seq2Seq Classification)
**What it does**: Given the SRL output + original text, classifies which specific meta-model pattern(s) are present.

**Why Flan-T5 (Seq2Seq) instead of DistilBERT (classification)?**
- Meta-model detection requires **reasoning about semantic structure**, not just pattern matching
- Flan-T5 is instruction-tuned — it understands task descriptions (e.g., "Identify if this is a universal quantifier or mind-reading pattern")
- The task requires **multi-label detection across 11 subtypes** with contextual reasoning
- Seq2Seq allows the model to output structured text labels with explanation
- Flan-T5-large (770M params) is much smaller than GPT-4 but has strong reasoning from instruction tuning

**Why NOT GPT-4 for this?**
- Cost: This runs on every therapeutic message (after intent = seek_support routing)
- Latency: GPT-4 takes 500ms+ vs. Flan-T5 at ~80ms
- Domain specificity: Fine-tuned Flan-T5 on our therapeutic data outperforms zero-shot GPT-4 on our specific 11-class taxonomy

---

## 3. Schema Design

### 3.1 Dataset Schema (JSON Format)

```json
{
  "id": "meta_001234",
  "utterance": "Nobody ever listens to me and I always end up alone",
  "patterns": [
    {
      "pattern_category": "generalization",
      "pattern_subtype": "universal_quantifiers",
      "matched_text": "Nobody ever",
      "confidence": 0.94,
      "recovery_questions": [
        "Nobody ever? Is there anyone in your life who has listened to you, even once?",
        "What would it mean if someone did listen?"
      ]
    },
    {
      "pattern_category": "generalization",
      "pattern_subtype": "universal_quantifiers",
      "matched_text": "always end up",
      "confidence": 0.89,
      "recovery_questions": [
        "Always? Have there been times when you haven't ended up alone?",
        "What would need to be different for 'always' to become 'sometimes'?"
      ]
    }
  ],
  "srl_output": {
    "verbs": [
      {"verb": "listens", "description": "ARG0: Nobody | TMP: ever | ARG2: to me"},
      {"verb": "end up", "description": "ARG0: I | TMP: always | ARG2: alone"}
    ]
  },
  "source": "synthetic",
  "annotator_id": "ann_nlp_003",
  "clinical_reviewer_id": "clin_001",
  "created_at": "2024-11-01T10:00:00Z"
}
```

### 3.2 Full Pattern Taxonomy

```
meta_model_patterns/
├── deletion/
│   ├── unspecified_referential_index   → "They upset me" (who is 'they'?)
│   ├── unspecified_verb                → "He did it again" (did what?)
│   └── comparative_deletion            → "I'm better off alone" (better than whom/what?)
│
├── generalization/
│   ├── universal_quantifiers           → "always", "never", "nobody", "everyone", "all"
│   ├── modal_operators_necessity       → "must", "should", "have to", "need to"
│   └── modal_operators_possibility     → "can't", "won't", "impossible", "unable to"
│
└── distortion/
    ├── nominalization                  → abstract nouns from verbs: "depression", "confusion", "failure"
    ├── mind_reading                    → "She thinks I'm worthless"
    ├── cause_and_effect                → "You make me feel this way"
    ├── complex_equivalence             → "Not calling = doesn't care"
    └── presupposition                  → "When I fail again..." (presupposes future failure)
```

### 3.3 Model Output Schema (JSON)

```json
{
  "patterns_detected": [
    {
      "pattern_category": "distortion",
      "pattern_subtype": "mind_reading",
      "matched_text": "She thinks I'm a failure",
      "confidence": 0.92,
      "severity": "moderate",
      "recovery_questions": [
        "How do you know what she thinks?",
        "Has she said this to you directly, or is this something you're sensing?",
        "What evidence would change your belief about what she thinks?"
      ],
      "therapeutic_note": "Mind reading creates unnecessary suffering. Challenge gently."
    }
  ],
  "pattern_count": 1,
  "dominant_category": "distortion",
  "processing_time_ms": 78,
  "srl_used": true
}
```

---

## 4. Data Preparation

### 4.1 Data Sources

| Source | Examples | Description |
|--------|----------|-------------|
| Synthetic (GPT-4 + NLP practitioner review) | 1,500 | Expert-crafted examples for each of 11 pattern subtypes |
| Real therapy transcripts (annotated) | 800 | Clinical transcripts annotated by NLP-trained therapists |
| NLP training manuals and books | 500 | Examples from Bandler & Grinder texts, adapted |
| Negative examples (no patterns) | 200 | Well-formed language without meta-model violations |
| **Total** | **3,000** | |

### 4.2 Expert Annotation Requirements

This dataset requires highly specialized annotation:
- **Primary annotators**: Must have completed NLP Practitioner training (minimum 7-day certified course)
- **Clinical reviewer**: Licensed psychotherapist familiar with CBT and NLP frameworks
- All examples with `mind_reading` and `cause_and_effect` patterns reviewed by clinical reviewer (therapeutic implications)

### 4.3 Flan-T5 Training Data Format

```python
# Seq2Seq format for Flan-T5 training
# Input: Instruction + utterance
# Output: Structured pattern label(s)

TRAINING_EXAMPLE = {
    "input": """Identify all meta-model language patterns in the following utterance.
Output each pattern as: CATEGORY|SUBTYPE|MATCHED_TEXT

Utterance: She never listens to anything I say and I can't talk to her about this.

Patterns:""",

    "output": """GENERALIZATION|universal_quantifiers|never
GENERALIZATION|modal_operators_possibility|can't talk to her about this"""
}
```

### 4.4 Recovery Question Templates

```python
# For each pattern, pre-defined recovery question templates
RECOVERY_QUESTION_TEMPLATES = {
    "universal_quantifiers": [
        "Always? / Never? Is there any time when {opposite}?",
        "What would it mean if there were an exception to {quantifier}?",
        "Has there ever been a time when things were different?"
    ],
    "mind_reading": [
        "How do you know that {inferred_thought}?",
        "Has {person} said this to you directly?",
        "What other explanation might there be for their behavior?"
    ],
    "cause_and_effect": [
        "How exactly does {cause} lead to {effect}?",
        "Is there always a direct link between {cause} and {effect}?",
        "What would need to be true for {cause} not to produce {effect}?"
    ],
    "unspecified_referential_index": [
        "Who specifically is '{pronoun}'?",
        "When you say '{pronoun}', who are you referring to?",
    ],
    "nominalization": [
        "If '{nominalization}' were a verb — what would '{verb_form}' look like for you?",
        "How are you '{verb_form}ing' yourself right now?",
        "When did this '{nominalization}' begin?"
    ],
    "modal_operators_possibility": [
        "What stops you from {action}?",
        "What would happen if you {action}?",
        "What would you need to believe differently to {action}?"
    ],
    "modal_operators_necessity": [
        "What would happen if you didn't {action}?",
        "Who says you must {action}?",
        "Is this a rule you chose, or one that was given to you?"
    ]
}
```

---

## 5. Data Balance Strategy

### 5.1 Pattern Subtype Distribution

| Pattern Subtype | Count | Target | Strategy |
|----------------|-------|--------|----------|
| unspecified_referential_index | 380 | 350 | Minor downsample |
| unspecified_verb | 320 | 300 | Minor downsample |
| comparative_deletion | 200 | 200 | Keep |
| universal_quantifiers | 420 | 350 | Downsample |
| modal_operators_necessity | 280 | 280 | Keep |
| modal_operators_possibility | 300 | 280 | Minor downsample |
| nominalization | 220 | 250 | Upsample |
| mind_reading | 300 | 280 | Minor downsample |
| cause_and_effect | 240 | 260 | Minor upsample |
| complex_equivalence | 180 | 220 | Upsample |
| presupposition | 160 | 230 | Significant upsample |
| **Total** | **3,000** | **3,000** | |

### 5.2 Multi-Label Augmentation

Since utterances often contain multiple patterns, augmentation must preserve co-occurrence realism:

```python
# Combine pattern examples to create multi-pattern utterances
def combine_patterns(example_a: str, example_b: str, connector: str = " and ") -> str:
    """
    Create multi-pattern utterances by combining single-pattern examples.
    Manual review required before adding to dataset.
    """
    return f"{example_a.rstrip('.')}{connector}{example_b}"

# Example:
a = "Nobody cares about me"         # universal_quantifier
b = "I can't say anything right"   # modal_operators_possibility
combined = combine_patterns(a, b, " and ")
# → "Nobody cares about me and I can't say anything right"
# Labels: [universal_quantifiers, modal_operators_possibility]
```

---

## 6. Dataset Splits

```
Full Dataset: 3,000 examples
├── Training:   2,100 examples (70%)
├── Validation:   450 examples (15%)
└── Test:         450 examples (15%)
```

Larger validation/test sets needed due to multi-label complexity and 11 fine-grained classes.

---

## 7. Dataset Evaluation & Quality Checks

```python
# Validate that recovery questions are clinically appropriate
import random

# Sample 50 random examples for human review
sample = df.sample(50, random_state=42)
for _, row in sample.iterrows():
    patterns = row['patterns']
    for pattern in patterns:
        # Each recovery question must:
        # 1. Be a genuine question (ends with ?)
        # 2. Not be accusatory
        # 3. Be open-ended (not yes/no)
        for rq in pattern['recovery_questions']:
            assert rq.endswith('?'), f"Not a question: {rq}"
            assert not rq.startswith("Did you"), "Avoid yes/no questions"

# Inter-annotator agreement on pattern subtypes
from sklearn.metrics import cohen_kappa_score
# Expected kappa > 0.70 for all pattern subtypes
```

---

## 8. Training Strategy

### 8.1 Overall Pipeline

```
Input utterance
     │
     ▼
AllenNLP SRL Model (pre-trained, not fine-tuned)
  → Extracts predicate-argument structure
  → Identifies verbs, arguments, modifiers
     │
     ▼
Flan-T5-large (fine-tuned on meta-model dataset)
  → Input: instruction + utterance + SRL output
  → Output: structured pattern labels
     │
     ▼
Post-processing:
  → Parse output labels
  → Generate recovery questions from templates
  → Build PatternDetectionResult
```

### 8.2 LoRA Configuration for Flan-T5

```python
from peft import get_peft_model, LoraConfig, TaskType

lora_config = LoraConfig(
    task_type=TaskType.SEQ_2_SEQ_LM,
    r=16,                            # LoRA rank
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q", "v"],       # T5 attention projection matrices
    bias="none"
)

model = get_peft_model(flan_t5_large, lora_config)
model.print_trainable_parameters()
# trainable params: ~4.7M out of 770M = 0.61%
```

### 8.3 Training Configuration

```python
training_config = {
    "base_model": "google/flan-t5-large",
    "lora_rank": 16,
    "lora_alpha": 32,
    "max_input_length": 512,    # instruction + utterance + SRL
    "max_target_length": 256,   # pattern labels output
    "batch_size": 8,
    "gradient_accumulation_steps": 4,
    "num_train_epochs": 5,
    "learning_rate": 3e-4,
    "warmup_ratio": 0.1,
    "fp16": True,
    "eval_metric": "exact_match_f1",
    "seed": 42
}
```

---

## 9. Step-by-Step Training Process

### Step 1: Install Dependencies

```bash
pip install transformers datasets peft allennlp allennlp-models torch
pip install pandas numpy wandb scikit-learn
```

### Step 2: Load AllenNLP SRL Model (Pre-trained)

```python
from allennlp.predictors.predictor import Predictor

srl_predictor = Predictor.from_path(
    "https://storage.googleapis.com/allennlp-public-models/structured-prediction-srl-bert.2020.12.15.tar.gz"
)

def get_srl_output(utterance: str) -> str:
    """Extract SRL structure as a formatted string for Flan-T5 input."""
    result = srl_predictor.predict(sentence=utterance)
    srl_str = ""
    for verb_info in result.get('verbs', []):
        srl_str += f"VERB:{verb_info['verb']} → {verb_info['description']}\n"
    return srl_str.strip()

# Example:
srl = get_srl_output("Nobody ever listens to me")
# VERB:listens → ARG0: Nobody | ARGM-TMP: ever | ARG2: to me
```

### Step 3: Prepare Flan-T5 Training Data

```python
from transformers import T5Tokenizer, T5ForConditionalGeneration
import json

tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-large")

def format_input(utterance: str, srl_output: str) -> str:
    return f"""Identify all linguistic meta-model patterns in the utterance below.
Output format: CATEGORY|SUBTYPE|MATCHED_TEXT (one per line)
Categories: deletion, generalization, distortion
Subtypes: unspecified_referential_index, unspecified_verb, comparative_deletion,
          universal_quantifiers, modal_operators_necessity, modal_operators_possibility,
          nominalization, mind_reading, cause_and_effect, complex_equivalence, presupposition

SRL Structure:
{srl_output}

Utterance: {utterance}

Patterns:"""

def format_output(patterns: list) -> str:
    if not patterns:
        return "NONE"
    return "\n".join([
        f"{p['pattern_category'].upper()}|{p['pattern_subtype']}|{p['matched_text']}"
        for p in patterns
    ])

# Tokenize
def tokenize_function(example):
    srl = get_srl_output(example['utterance'])
    input_text = format_input(example['utterance'], srl)
    output_text = format_output(example['patterns'])

    model_input = tokenizer(input_text, max_length=512, truncation=True, padding='max_length')
    target = tokenizer(output_text, max_length=256, truncation=True, padding='max_length')
    model_input['labels'] = target['input_ids']
    return model_input
```

### Step 4: Apply LoRA and Train

```python
from peft import get_peft_model, LoraConfig, TaskType
from transformers import Seq2SeqTrainingArguments, Seq2SeqTrainer

base_model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-large")
lora_config = LoraConfig(
    task_type=TaskType.SEQ_2_SEQ_LM, r=16, lora_alpha=32,
    lora_dropout=0.05, target_modules=["q", "v"]
)
model = get_peft_model(base_model, lora_config)

args = Seq2SeqTrainingArguments(
    output_dir="./models/meta_model_detector",
    num_train_epochs=5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=16,
    gradient_accumulation_steps=4,
    learning_rate=3e-4,
    warmup_ratio=0.1,
    evaluation_strategy="epoch",
    save_strategy="best",
    load_best_model_at_end=True,
    predict_with_generate=True,
    generation_max_length=256,
    fp16=True,
    report_to="wandb",
    run_name="meta-model-detector-flan-t5-lora",
    seed=42
)

trainer = Seq2SeqTrainer(
    model=model, args=args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    tokenizer=tokenizer,
    compute_metrics=compute_metrics_seq2seq
)
trainer.train()
```

### Step 5: Define Seq2Seq Metrics

```python
import numpy as np
from sklearn.metrics import f1_score

def compute_metrics_seq2seq(eval_preds):
    predictions, labels = eval_preds
    decoded_preds = tokenizer.batch_decode(predictions, skip_special_tokens=True)
    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)

    # Parse output into pattern labels
    def parse_patterns(text):
        lines = [l.strip() for l in text.strip().split('\n') if '|' in l]
        return set(lines)

    exact_matches = sum(
        parse_patterns(pred) == parse_patterns(label)
        for pred, label in zip(decoded_preds, decoded_labels)
    )
    return {"exact_match": exact_matches / len(decoded_preds)}
```

### Step 6: Merge LoRA Weights and Save

```python
from peft import PeftModel

# Merge LoRA into base model for production inference
merged_model = model.merge_and_unload()
merged_model.save_pretrained("./models/meta_model_detector_merged")
tokenizer.save_pretrained("./models/meta_model_detector_merged")

# Save LoRA adapter separately (smaller file)
model.save_pretrained("./models/meta_model_detector_lora_adapter")
```

---

## 10. Model Evaluation

| Metric | Target |
|--------|--------|
| Exact match (full pattern set) | ≥ 72% |
| Pattern category F1 (deletion/gen/distortion) | ≥ 0.85 |
| Pattern subtype F1 (11 classes) | ≥ 0.75 |
| False positive rate (no pattern detected as pattern) | < 15% |
| Recovery question quality (human eval) | ≥ 4.0/5.0 |

### Human Evaluation of Recovery Questions

```python
# Recovery questions evaluated by NLP practitioners on 5-point scale:
# 1=Inappropriate, 2=Poor, 3=Adequate, 4=Good, 5=Excellent
# Criteria:
# - Relevance to detected pattern
# - Clinical appropriateness
# - Non-accusatory tone
# - Opens exploration (vs. closes it)
# - Fits natural conversation flow
```

---

## 11. Downloading & Saving Weights

```
therapeutic-copilot/server/ml_models/
└── meta_model_detector/
    ├── config.json                          # Flan-T5 config
    ├── pytorch_model.bin                   # Merged weights (~3GB)
    ├── tokenizer.json
    ├── lora_adapter/                        # Lightweight LoRA adapter only
    │   ├── adapter_config.json
    │   └── adapter_model.bin               (~38MB)
    └── recovery_questions.json             # Template questions per pattern
```

---

## 12. Integrating Trained Weights into the App Workflow

### 12.1 MetaModelDetectorService (References Existing Detector)

The existing [detector.py](therapeutic-copilot/ml_pipeline/src/pattern_detection/detector.py) implements the `MetaModelDetector` class. The production service wraps this:

```python
# therapeutic-copilot/server/services/meta_model_detector_service.py

import torch, time
from transformers import T5Tokenizer, T5ForConditionalGeneration
from allennlp.predictors.predictor import Predictor
import json

PATTERN_CATEGORIES = {
    "unspecified_referential_index": "deletion",
    "unspecified_verb": "deletion",
    "comparative_deletion": "deletion",
    "universal_quantifiers": "generalization",
    "modal_operators_necessity": "generalization",
    "modal_operators_possibility": "generalization",
    "nominalization": "distortion",
    "mind_reading": "distortion",
    "cause_and_effect": "distortion",
    "complex_equivalence": "distortion",
    "presupposition": "distortion"
}

class MetaModelDetectorService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        # Load Flan-T5 model
        model_path = "./ml_models/meta_model_detector"
        self.tokenizer = T5Tokenizer.from_pretrained(model_path)
        self.model = T5ForConditionalGeneration.from_pretrained(model_path)
        self.model.eval()

        # Load AllenNLP SRL
        self.srl_predictor = Predictor.from_path(
            "https://storage.googleapis.com/allennlp-public-models/"
            "structured-prediction-srl-bert.2020.12.15.tar.gz"
        )

        with open(f"{model_path}/recovery_questions.json") as f:
            self.recovery_questions = json.load(f)

        self._initialized = True

    def detect(self, utterance: str) -> dict:
        start = time.time()

        # Get SRL structure
        srl_result = self.srl_predictor.predict(sentence=utterance)
        srl_str = self._format_srl(srl_result)

        # Generate pattern predictions with Flan-T5
        input_text = self._format_input(utterance, srl_str)
        inputs = self.tokenizer(input_text, return_tensors='pt', max_length=512, truncation=True)
        with torch.no_grad():
            outputs = self.model.generate(
                inputs['input_ids'],
                max_length=256,
                num_beams=4,
                early_stopping=True
            )
        output_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Parse output
        patterns = self._parse_output(output_text, utterance)

        return {
            "patterns_detected": patterns,
            "pattern_count": len(patterns),
            "dominant_category": self._get_dominant_category(patterns),
            "srl_output": srl_str,
            "processing_time_ms": round((time.time()-start)*1000, 1)
        }

    def _format_input(self, utterance: str, srl_str: str) -> str:
        return f"""Identify meta-model patterns.
SRL: {srl_str}
Utterance: {utterance}
Patterns:"""

    def _format_srl(self, srl_result: dict) -> str:
        return " | ".join([v['description'] for v in srl_result.get('verbs', [])])

    def _parse_output(self, output_text: str, utterance: str) -> list:
        patterns = []
        for line in output_text.strip().split('\n'):
            parts = line.strip().split('|')
            if len(parts) == 3:
                category, subtype, matched = parts
                recovery_qs = self.recovery_questions.get(subtype.strip(), [])[:3]
                patterns.append({
                    "pattern_category": category.strip().lower(),
                    "pattern_subtype": subtype.strip(),
                    "matched_text": matched.strip(),
                    "confidence": 0.85,  # fixed for now; extend with beam scores
                    "recovery_questions": recovery_qs
                })
        return patterns

    def _get_dominant_category(self, patterns: list) -> str:
        if not patterns:
            return "none"
        cats = [p['pattern_category'] for p in patterns]
        return max(set(cats), key=cats.count)
```

### 12.2 Integration into Therapeutic Conversation Flow

```python
# In chat_routes.py — runs ONLY when intent = seek_support (therapeutic mode)

if intent_result['routing_action'] == "THERAPEUTIC_CONVERSATION":
    # Run meta-model detection (takes ~80ms — run in parallel with LLM)
    meta_result = meta_model_service.detect(user_message)

    # Feed into LLM prompt
    response = await therapeutic_ai.generate(
        message=user_message,
        emotion_context=emotion_result,
        meta_model_context=meta_result,
        therapeutic_step=session['current_step']
    )
```

---

## 13. Building Prompt Context with Model Output

### 13.1 Meta-Model Context Block

```python
def build_meta_model_context_block(meta_result: dict) -> str:
    patterns = meta_result.get('patterns_detected', [])
    if not patterns:
        return ""

    block = "## Meta-Model Patterns Detected (NLP Analysis)\n\n"

    for i, pattern in enumerate(patterns[:3]):  # Max 3 patterns in prompt
        block += f"""### Pattern {i+1}: {pattern['pattern_subtype'].replace('_',' ').title()}
- **Category**: {pattern['pattern_category'].title()}
- **Matched Text**: "{pattern['matched_text']}"
- **Suggested Recovery Questions**:
"""
        for rq in pattern['recovery_questions'][:2]:
            block += f"  - {rq}\n"

    block += """
**Instructions for this turn**:
- You MAY choose ONE recovery question to ask naturally in your response
- Do NOT ask all questions at once — this is not an interrogation
- Frame the question with empathy: "I'm curious..." or "I wonder..." or "I notice..."
- Only use a recovery question when it feels natural and the user seems ready to explore
- If the pattern suggests significant cognitive distortion (mind reading, cause-effect), address the underlying belief gently
"""
    return block
```

### 13.2 Example Assembled Prompt with Meta-Model Context

**User says**: "My partner always makes me feel like I'm not good enough and I can never do anything right."

**Meta-Model patterns detected**:
- `universal_quantifiers`: "always" and "never"
- `cause_and_effect`: "makes me feel" (external locus of causation)

**Injected into system prompt**:

```
## Meta-Model Patterns Detected (NLP Analysis)

### Pattern 1: Universal Quantifiers
- Category: Generalization
- Matched Text: "always makes me feel"
- Suggested Recovery Questions:
  - Always? Are there times when they don't make you feel this way?
  - What would it mean if this happened "sometimes" instead of "always"?

### Pattern 2: Cause And Effect
- Category: Distortion
- Matched Text: "makes me feel like I'm not good enough"
- Suggested Recovery Questions:
  - How exactly does their behavior lead to that feeling in you?
  - Is there a part of you that also has some doubts about your worth, independent of your partner?

Instructions for this turn:
- You MAY choose ONE recovery question to ask naturally in your response
- Do NOT ask all questions at once...
```

**Resulting AI Response** (example):

> "That sounds really painful — feeling like whatever you do isn't good enough. I want to make sure I understand fully. When you say your partner 'always' makes you feel this way — is that truly every interaction, or are there moments that feel different?"

The recovery question challenges the `universal_quantifier` ("always") gently and naturally — exactly what an NLP practitioner would do.

---

## Summary

| Aspect | Decision |
|--------|----------|
| Architecture | AllenNLP SRL + Flan-T5-large with LoRA (Seq2Seq) |
| Framework | NLP Linguistic Meta-Model (Bandler & Grinder) |
| Dataset | 3,000 examples, annotated by certified NLP practitioners |
| Classes | 11 pattern subtypes across 3 categories (multi-label) |
| Training | Seq2Seq format; LoRA rank=16 on Flan-T5 attention layers |
| Output | Structured pattern labels + recovery questions |
| Integration | Runs in therapeutic conversation mode only |
| Prompt use | Injects detected patterns + recovery questions for therapist-quality questioning |

---

*Document Version: 1.0 | Model Version: meta_model_detector_saathi_v1 | Last Updated: 2025-03*
