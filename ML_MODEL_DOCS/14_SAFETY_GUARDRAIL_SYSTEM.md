# SAATHI AI — Safety Guardrail System
## Model 14 · Safety Classifier + 5-Layer Runtime Guardrail

---

## 1. Overview

The Safety Guardrail System is a **multi-layer interception pipeline** that
runs on every LLM-generated response before it is delivered to the user.
It is the final safeguard in the SAATHI AI response pipeline, designed to
medical-grade standards aligned with:

- **IEC 62304** — Software lifecycle processes for medical devices
- **FDA AI/ML SaMD Action Plan** — Software as a Medical Device guidance
- **NIMHANS Clinical Safety Guidelines** (mental health context)

The system operates in two modes:

| Mode | Component | When runs |
|------|-----------|-----------|
| **Offline training** | `safety_crisis_emergency/` scripts | Once, before deployment |
| **Runtime inference** | `server/services/safety_guardrail_service.py` | Every LLM response |

---

## 2. Architecture

```
User message
     |
     v
[Crisis Detection Service]   <-- existing fast scan (<100ms)
     |
     v
[LLM Response Generation]    <-- Stage 1 / Stage 2 / Qwen base
     |
     v
+============================+
|  SAFETY GUARDRAIL (5 layers)|
|  safety_guardrail_service  |
+============================+
     |
     v
  Layer 1: Hard Block Rules      (regex, <1ms)
     |
     v
  Layer 2: Crisis Protocol       (<2ms)
  Validator
     |
     v
  Layer 3: Hallucination         (<5ms)
  Detector
     |
     v
  Layer 4: ML Safety             (~30ms)
  Classifier
     |
     v
  Layer 5: Response Sanitizer    (always runs)
     |
     v
[Safe response delivered]
[Audit log written]
```

---

## 3. Pipeline Layers

### Layer 1 — Hard Block Rules

**Type**: Regex pattern matching
**Latency**: <1ms
**Action**: BLOCK (terminal — skips remaining layers)

Matches absolute no-output scenarios regardless of context.

| Pattern | Reason Code |
|---------|-------------|
| How to hang / overdose / cut / kill / end your life | `SELF_HARM_INSTRUCTION` |
| Step-by-step suicide / self-harm | `SELF_HARM_INSTRUCTION` |
| Take/swallow all pills/medication | `OVERDOSE_INSTRUCTION` |
| Carbon monoxide method/technique | `SELF_HARM_INSTRUCTION` |
| Deeper/effective cutting/wrist | `SELF_HARM_INSTRUCTION` |
| Best/easiest/painless way to die | `SELF_HARM_INSTRUCTION` |
| Tie/knot/noose neck | `SELF_HARM_INSTRUCTION` |
| Lethal/fatal dose of \<drug\> | `OVERDOSE_INSTRUCTION` |

When triggered: the LLM response is **completely discarded** and replaced
with a pre-approved empathic fallback containing verified crisis resources.

---

### Layer 2 — Crisis Protocol Validator

**Type**: Marker search
**Latency**: <2ms
**Action**: ESCALATE

Activates only when `crisis_active=True` (upstream crisis score ≥ 5).

Checks whether the LLM response contains at least one recognised crisis
escalation marker:

```
iCall, Vandrevala, NIMHANS, AASRA,
+91-9152987821, 1860-2662-345, 080-46110007, 9820466627,
helpline, hotline, emergency, crisis line, call <number>
```

If **no marker is found**: the original response is preserved AND a verified
resource block is appended with a soft separator.

If the marker is present: Layer 2 passes without modification.

---

### Layer 3 — Hallucination Detector

**Type**: Regex + allow-list
**Latency**: <5ms
**Action**: REDACT

Detects three categories of hallucination unique to mental-health AI:

#### A) Phone Number Hallucination

Any phone-number-like string in the response is extracted and checked
against the approved allow-list:

| Approved | Number |
|----------|--------|
| iCall | +91-9152987821 |
| Vandrevala Foundation | 1860-2662-345 |
| NIMHANS | 080-46110007 |
| AASRA | 9820466627 |
| National Emergency | 112, 100, 102, 108 |
| Generic toll-free | 1-800-* |

Any unrecognised phone number is **redacted** with `[VERIFIED RESOURCES BELOW]`
and the verified resource block is appended.

**Why this matters**: LLMs frequently hallucinate plausible-looking phone numbers.
A patient in crisis calling a wrong number could be catastrophic.

#### B) Dangerous Medication Dosage

Flags responses containing a numeric dose ≥ 100mg/mcg/ml paired with a
named psychiatric medication (sertraline, fluoxetine, quetiapine, lithium,
benzodiazepines, opioids etc.).

When triggered: response is replaced with a medication-guidance refusal
directing the user to their doctor/pharmacist.

**Why this matters**: LLMs can suggest dosages from training data that are
dangerous or fatal for individual patients.

#### C) Scope Violation

Flags phrases where the AI claims clinical authority:
- "I diagnose / I am diagnosing"
- "I prescribe / I am prescribing"
- "I recommend you take / I advise you to take \<drug\>"

When triggered: response replaced with scope-limitation fallback.

---

### Layer 4 — ML Safety Classifier

**Type**: DeBERTa-v3-small multi-label neural classifier
**Latency**: ~30ms (CPU), ~5ms (GPU)
**Action**: BLOCK / ESCALATE / REDACT

Loaded from `SAFETY_GUARDRAIL_MODEL_PATH` (see §7 Deployment).

**Labels** (6, non-exclusive):

| Label | Threshold | Action if triggered |
|-------|-----------|---------------------|
| `safe` | 0.40 | PASS |
| `harmful_content` | 0.30 (critical) | BLOCK |
| `crisis_escalation_missing` | 0.30 (critical) | ESCALATE |
| `hallucinated_fact` | 0.40 | REDACT |
| `toxic_language` | 0.40 | BLOCK |
| `scope_violation` | 0.40 | REDACT |

Lower threshold for critical labels (`harmful_content`,
`crisis_escalation_missing`) means the model errs on the side of caution —
**high recall over high precision** for safety-critical categories.

If `SAFETY_GUARDRAIL_MODEL_PATH` is not set or the model is not found, Layer 4
is **disabled** (Layers 1–3 and 5 remain fully active). This is the
graceful-degradation design: safety never depends on a single component.

---

### Layer 5 — Response Sanitizer

**Type**: Final cleanup pass
**Latency**: <0.5ms
**Action**: Applied to all responses including PASS

- Runs hard-block regex one final time as belt-and-suspenders check
- Strips leading/trailing whitespace
- Cannot add new interventions — only cleans up formatting

---

## 4. Actions

| Action | Meaning | Response to user |
|--------|---------|-----------------|
| `PASS` | Safe | Original LLM response (after L5 cleanup) |
| `REDACT` | Partially unsafe | Modified response with harmful section removed/replaced |
| `BLOCK` | Fully unsafe | Category-specific pre-approved safe fallback |
| `ESCALATE` | Crisis not handled | Original response + appended crisis resource block |

---

## 5. Safe Fallback Responses

Pre-written, clinically reviewed responses for each BLOCK category:

| Category | Fallback content |
|----------|-----------------|
| `SELF_HARM_INSTRUCTION` | Empathic statement + all 4 crisis lines |
| `OVERDOSE_INSTRUCTION` | Medication refusal + crisis lines |
| `CRISIS_MISSING_ESCALATION` | Empathic statement + crisis lines |
| `HALLUCINATED_PHONE` | Verified crisis resource block |
| `DANGEROUS_DOSAGE` | Refer to doctor/pharmacist |
| `SCOPE_VIOLATION` | AI limitations + refer to professional |
| `ML_HARMFUL` | Soft redirection |
| `ML_CRISIS_MISSING` | Empathic statement + crisis lines |
| `ML_TOXIC` | Gentle reset |

---

## 6. Audit Trail

Every non-PASS event is written to:
```
therapeutic-copilot/server/logs/safety_guardrail_audit.jsonl
```

Each entry is a single JSON line:

```json
{
  "ts":               "2026-03-18T10:23:45Z",
  "session_id":       "sess_abc123",
  "stage":            2,
  "action":           "BLOCK",
  "reason_codes":     ["SELF_HARM_INSTRUCTION"],
  "layers_triggered": ["L1_HARD_BLOCK"],
  "latency_ms":       0.42,
  "response_len":     312,
  "user_msg_snippet": "I've been thinking about..."
}
```

**What is NOT logged**: the full original LLM response or full user message
(privacy-preserving by design — only 80-char snippets of user messages).

The audit log is append-only and should be:
- Backed up daily (compliance requirement)
- Reviewed weekly by clinical safety lead
- Retained for minimum 5 years (IEC 62304 §5.8)

---

## 7. Deployment

### 7a. Train the ML classifier

```bash
cd safety_crisis_emergency

# Step 1 — Build dataset from CSVs
python 01_build_safety_dataset.py

# Step 2 — Train DeBERTa-v3-small
python 02_train_safety_classifier.py
# Runs 8 epochs, ~45 min CPU / ~8 min GPU
# Output: output/safety-classifier/

# Step 3 — Medical-grade evaluation (must pass all 5 gates)
python 03_evaluate_safety_model.py --model ./output/safety-classifier

# Step 4 — Deploy to server
python 04_deploy_safety_model.py
```

### 7b. Configure environment

Add to `therapeutic-copilot/server/.env`:

```
SAFETY_GUARDRAIL_MODEL_PATH=<absolute path to server/ml_models/safety_guardrail>
```

### 7c. Server auto-load

`safety_guardrail_service.py` uses **lazy loading** — the ML model is loaded
on first call, not at server startup. No changes needed to `main.py`.

The service is wired into `therapeutic_ai_service.py`:

```python
# In process_message(), after LLM generates response:
_guardrail = get_guardrail_service()
_gr = _guardrail.inspect(
    response=response,
    user_message=message,
    crisis_active=crisis_result["severity"] >= 5,
    session_id=session_id,
    stage=stage,
)
response = _gr.safe_response
```

---

## 8. API Response Fields

Every `process_message` response now includes:

| Field | Type | Description |
|-------|------|-------------|
| `guardrail_action` | string | PASS / REDACT / BLOCK / ESCALATE |
| `guardrail_codes` | list | Triggered reason codes (empty if PASS) |
| `guardrail_latency_ms` | float | Processing time in ms |

---

## 9. ML Classifier Training Pipeline

### Dataset (`safety_crisis_emergency/data/`)

| Split | Examples | Source |
|-------|----------|--------|
| train.jsonl | ~137 | Build script + augmentation |
| val.jsonl | ~29 | Build script |
| test.jsonl | ~30 | Build script |

**Source CSVs** (in `safety_crisis_emergency/`):

| CSV | Examples | Labels covered |
|-----|----------|---------------|
| `safety_crisis_v1.csv` | 70 | harmful_content, crisis_escalation_missing, safe |
| `facts_hallucination_v1.csv` | 50 | hallucinated_fact, scope_violation |
| `toxicity_adv_v1.csv` | 50 | toxic_language, safe |

### Model Architecture

```
microsoft/deberta-v3-small
  ↓
Linear(768 → 6)  [multi-label head]
  ↓
Sigmoid → per-label probabilities
  ↓
Threshold per label (0.30 for critical, 0.40 for others)
```

### Loss Function

Weighted Binary Cross-Entropy:

| Label | Weight | Rationale |
|-------|--------|-----------|
| safe | 1.0 | Baseline |
| harmful_content | 3.0 | Must not miss harmful outputs |
| crisis_escalation_missing | 5.0 | Highest: missing crisis = worst failure |
| hallucinated_fact | 2.5 | Medical facts are high-stakes |
| toxic_language | 2.0 | Degrades therapeutic relationship |
| scope_violation | 2.0 | Legal and ethical exposure |

### Evaluation Gates (IEC 62304 compliant)

| Gate | Metric | Threshold | Rationale |
|------|--------|-----------|-----------|
| 1 | Static harmful pattern scan | 0 violations | Absolute |
| 2 | Recall — harmful_content | ≥ 0.95 | Cannot miss harmful outputs |
| 3 | Recall — crisis_escalation_missing | ≥ 0.95 | Cannot miss crisis |
| 4 | Recall — hallucinated_fact | ≥ 0.90 | Medical facts must be caught |
| 5 | Macro F1 (all 6 labels) | ≥ 0.70 | Overall quality floor |

**All 5 gates must pass before deployment is permitted.**

---

## 10. Graceful Degradation

The system is designed to never fail silently:

| Failure | Behaviour |
|---------|-----------|
| `SAFETY_GUARDRAIL_MODEL_PATH` not set | Layers 1–3 + 5 active; L4 disabled; warning logged |
| Model files missing/corrupt | Same as above |
| Torch import error | Same as above |
| Audit log write failure | Error logged; response still delivered |
| Any unhandled exception in guardrail | Response delivered as-is; exception logged |

Layers 1–3 are pure Python (no ML dependencies) and always run.
The ML layer is an enhancement; the system is safe without it.

---

## 11. Security and Privacy

- **No full message storage**: Only 80-char snippets in audit log
- **No PII in logs**: session_id only (not patient_id)
- **Append-only audit log**: Cannot be modified (append mode open)
- **Pre-approved fallbacks**: Never generated dynamically, immune to prompt injection

---

## 12. Future Roadmap

| Priority | Enhancement |
|----------|-------------|
| P0 | Train ML classifier with full 196-example dataset |
| P1 | Expand training data to 500+ examples across all 6 labels |
| P1 | Add multilingual support (Hindi crisis resources) |
| P2 | Real-time dashboard for clinical team to review guardrail events |
| P2 | A/B testing framework for threshold calibration |
| P3 | Active learning: clinician-reviewed guardrail events fed back to training |

---

*Document version 1.0 — SAATHI AI Safety Guardrail System*
*Authored: 2026-03-18 | Next review: 2026-06-18*
