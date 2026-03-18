# SAATHI AI — Implementation Roadmap & Build Status
## RYL NEUROACADEMY PRIVATE LIMITED
### Last Audit: 2026-03-18 | Status: Active Development

---

> **Purpose of This Document**
> This is the single source of truth for the current state of the SAATHI AI prototype — what is built, what is integrated, what is working, and what remains. All future build sessions must update this document upon completion.

---

## TABLE OF CONTENTS

1. [System Architecture Summary](#1-system-architecture-summary)
2. [Full System Audit (March 2026)](#2-full-system-audit-march-2026)
3. [ML Models Master Status Table](#3-ml-models-master-status-table)
4. [Services Integration Status](#4-services-integration-status)
5. [Frontend Status](#5-frontend-status)
6. [API Routes Status](#6-api-routes-status)
7. [P0 — Critical Blockers](#7-p0--critical-blockers-must-fix-before-investor-demo)
8. [P1 — Core Functionality Polish](#8-p1--core-functionality-polish)
9. [P2 — Production Hardening](#9-p2--production-hardening)
10. [What IS Working End-to-End](#10-what-is-working-end-to-end)
11. [Environment & Deployment Checklist](#11-environment--deployment-checklist)
12. [Session Progress Log](#12-session-progress-log)

---

## 1. System Architecture Summary

```
User Message (Widget / Portal)
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 0: Crisis Scan (CrisisDetectionService)              │
│  < 100ms · keywords + ML severity · triggers escalation     │
└─────────────────────────────────────────────────────────────┘
         │ if severity < 7 → continue
         ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: Signal Classification (async parallel)            │
│  · EmotionClassifier   (DistilBERT 8-class)  ~20ms          │
│  · IntentClassifier    (DistilBERT 7-class)  ~20ms          │
│  · TopicClassifier     (DistilBERT 5-class)  ~20ms          │
│  · MetaModelDetector   (Flan-T5 LoRA)        ~50ms [Stage2] │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: RAG Context Retrieval (Pinecone)                  │
│  Tenant-scoped · top-3 relevant passages · ~50ms            │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: LLM Inference (Stage-Routed)                      │
│  Stage 1 → Qwen2.5 + LoRA r=8  (Lead Generation, 8 turns)  │
│  Stage 2 → Qwen2.5 + LoRA r=16 (Therapy, 11 steps)         │
│  Stage 3 → Qwen2.5 base        (Re-engagement)              │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4: Safety Guardrail (5 sub-layers)                   │
│  L1 Hard Block · L2 Crisis Check · L3 Hallucination         │
│  L4 DeBERTa ML Classifier · L5 Sanitizer                    │
│  Audit log written on every intervention                     │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 5: Response Delivery                                  │
│  DB persist · Redis update · WebSocket / HTTP response       │
└─────────────────────────────────────────────────────────────┘
```

**Technology Stack**

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11) |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Widget | Shadow DOM + Custom Elements |
| AI — Prod | Qwen 2.5-7B GGUF via llama.cpp (self-hosted) |
| AI — Dev | Together AI cloud API (`TOGETHER_API_KEY`) |
| Vector DB | Pinecone (per-tenant namespaces) |
| Primary DB | PostgreSQL (prod) / SQLite (local dev) |
| Cache | Redis 7 |
| Payments | Razorpay |
| Infra | E2E Networks Mumbai |

---

## 2. Full System Audit (March 2026)

**Overall Readiness**: ~75% scaffolded | ~40% integrated | ~15% production-ready

### Audit Summary by Component

| Component | Built | Trained | Deployed | Integrated | Production-Ready |
|-----------|-------|---------|----------|------------|-----------------|
| ML Classifiers (10 planned) | 10/10 | 5/10 | 5/10 | 4/10 | 4/10 |
| LoRA Models (2 planned) | 2/2 | 1/2 | 1/2 | 1/2 | 0/2 |
| Service Files (26) | 26/26 | N/A | 26/26 | 20/26 | 12/26 |
| Frontend Pages (6) | 6/6 | N/A | 6/6 | 5/6 | 5/6 |
| API Routes (9) | 9/9 | N/A | 9/9 | 8/9 | 6/9 |

---

## 3. ML Models Master Status Table

| # | Model Name | Architecture | Dataset | Trained | Deployed | In Workflow | Notes |
|---|-----------|--------------|---------|---------|----------|-------------|-------|
| 01 | Emotion Detection Classifier | DistilBERT 8-class | 8,000 | ✅ F1=0.854 | ✅ `ml_models/emotion_classifier/` | ✅ Concurrent async | Production-ready |
| 02 | Crisis Detection Classifier | RoBERTa + Keywords | 5,000 planned | ⚠️ Keywords only | ❌ No ML weights | ✅ Keyword layer only | **ML weights missing** |
| 03 | Intent Classifier | DistilBERT 7-class | 4,000 | ✅ F1=0.989 | ✅ `ml_models/intent_classifier/` | ✅ Concurrent async | Production-ready |
| 04 | Topic Classifier | DistilBERT 5-class multi-label | 2,000 | ✅ | ✅ `ml_models/topic_classifier/` | ✅ Concurrent async | Production-ready |
| 05 | Sentiment Classifier | DistilBERT 3-class | 2,000 | ✅ | ✅ `ml_models/sentiment_classifier/` | ❌ **Loaded but NOT wired into response** | **P1: wire into pipeline** |
| 06 | Meta-Model Pattern Detector | Flan-T5-large LoRA r=16 | 3,000 | ⚠️ Demo-grade (loss=3.52) | ✅ `ml_models/meta_model_detector/` (19MB) | ✅ Stage 2 only | No real validation metrics |
| 07 | LoRA Stage 1 — Lead Gen | Qwen2.5-7B LoRA r=8 | 634 conv | ❌ **NOT TRAINED** | ❌ **NO ADAPTER** | ⚠️ Falls back to mock | **P0: Train and deploy** |
| 08 | LoRA Stage 2 — Therapy | Qwen2.5-3B LoRA r=16 | 3,017 conv | ✅ | ✅ `ml_models/stage2_therapy_model/` (115MB) | ✅ Stage 2 routing | |
| 09 | Booking Intent Detector | DistilBERT Joint (Binary+NER) | 1,000 planned | ❌ | ❌ | ❌ | **P2: Build from scratch** |
| 10 | Assessment Router | RoBERTa-base 9-class | 4,000 planned | ❌ | ❌ | ⚠️ Rule-based only | **P2: Train and deploy ML** |
| 14 | Safety Guardrail | DeBERTa-v3-small 6-class | 196 | ❌ Not yet | ❌ Code rules only | ✅ Layers 1-3+5 active | **P2: Train DeBERTa layer** |

---

## 4. Services Integration Status

### Fully Implemented (Production-Ready)

| Service File | Purpose | Status |
|-------------|---------|--------|
| `crisis_detection_service.py` | 30+ keyword crisis scan + ML severity | ✅ |
| `emotion_classifier_service.py` | DistilBERT 8-class emotion | ✅ |
| `intent_classifier_service.py` | DistilBERT 7-class routing | ✅ |
| `topic_classifier_service.py` | DistilBERT 5-class multi-label | ✅ |
| `meta_model_detector_service.py` | Flan-T5 LoRA linguistic patterns | ✅ |
| `safety_guardrail_service.py` | 5-layer response safety pipeline | ✅ |
| `therapeutic_ai_service.py` | Main orchestrator (95% complete) | ⚠️ |
| `lora_stage2_service.py` | Qwen2.5 + r=16 therapy pipeline | ✅ |
| `rag_service.py` | Pinecone RAG (sync embed needs fix) | ⚠️ |
| `assessment_service.py` | 8 clinical instruments (PHQ-9, GAD-7, etc.) | ✅ |
| `assessment_router_service.py` | Rule-based signal routing | ✅ |
| `redis_session_service.py` | Session state caching | ✅ |
| `websocket_manager.py` | Real-time clinician alerts | ✅ |
| `payment_service.py` | Razorpay order + verification | ✅ |
| `analytics_service.py` | Session stats, crisis trends | ✅ |

### Partially Implemented / Stubs

| Service File | Issue | Priority |
|-------------|-------|----------|
| `therapeutic_ai_service.py` | `_detect_patient_stage()` hardcoded to `1`; `end_session()` stub | **P0** |
| `lora_stage1_service.py` | Service ready but adapter weights missing | **P0** |
| `sentiment_classifier_service.py` | Loaded but never used in response logic | **P1** |
| `auth_routes.py` → DB layer | Doesn't query clinician from DB | **P0** |
| `ml_crisis_service.py` | Service stub, weights not deployed | **P2** |
| `qwen_inference.py` | Needs actual Qwen model path or Together API key | **P1** |
| `lead_service.py` | 2-line stub, never invoked | **P1** |
| `dropout_service.py` | Scaffolded, no scheduler integration | **P2** |
| `calendar_service.py` | Needs OAuth token storage | **P2** |

---

## 5. Frontend Status

| Page / Component | File | Status | Notes |
|-----------------|------|--------|-------|
| Clinician Dashboard | `pages/ClinicianDashboard.tsx` | ✅ Full (47KB) | Real-time patient list, crisis alerts |
| Patient Portal | `pages/PatientPortal.tsx` | ✅ Full (36KB) | Session history, assessments |
| Assessment Page | `pages/AssessmentPage.tsx` | ✅ Full (60KB) | All 8 instruments, radar charts |
| Landing Page | `pages/LandingPage.tsx` | ✅ Full (18KB) | Pricing, CTAs |
| Admin Panel | `pages/AdminPanel.tsx` | ⚠️ Scaffold | Structure only |
| Booking Page | `pages/BookingPage.tsx` | ❌ Stub (174 bytes) | **P1: Build appointment booking UI** |
| Chat Widget | `components/chatbot/ChatWidget.tsx` | ✅ | Shadow DOM embed |
| Auth Components | `components/auth/` | ❌ Missing | **P0: Auth flow needs DB wiring** |
| Design System | `components/ui/index.tsx` | ✅ | Button, Badge, Card, Spinner |
| Payment Flow | `components/payment/PaymentFlow.tsx` | ✅ | Razorpay modal |

---

## 6. API Routes Status

| Route File | Endpoints | Status | Gap |
|-----------|-----------|--------|-----|
| `chat_routes.py` | POST /start, /message, /end, GET /session | ✅ | — |
| `crisis_routes.py` | POST /scan, /escalate | ✅ | — |
| `assessment_routes.py` | GET/POST /assessments | ✅ | DB persistence unverified |
| `auth_routes.py` | POST /login, /register, /refresh | ⚠️ | **DB queries incomplete** |
| `widget_routes.py` | GET /config, /bundle | ✅ | Token lookup stub |
| `payment_routes.py` | POST /order, /verify, /webhook | ✅ | Needs Razorpay test keys |
| `rag_routes.py` | POST /query, /ingest | ✅ | Needs Pinecone key |
| `websocket_routes.py` | WS /chat/{session_id} | ✅ | Frontend handler incomplete |
| `calendar_routes.py` | POST /events, /sync | ✅ | OAuth token storage missing |

---

## 7. P0 — Critical Blockers (Must Fix Before Investor Demo)

> These break core functionality. Nothing works correctly without these.

---

### P0.1 — Implement `_detect_patient_stage()`

**File**: `therapeutic-copilot/server/services/therapeutic_ai_service.py` Line 574
**Problem**: Method returns hardcoded `1` — every session starts at Lead Gen regardless of patient
**Fix**: Query `Patient` table by `patient_id`, map `PatientStage` enum to integer stage
**Impact**: Session initialization, stage-correct LLM routing, correct step tracking
**Status**: ❌ NOT DONE

```python
# Current (broken):
async def _detect_patient_stage(self, patient_id: str) -> int:
    return 1  # hardcoded

# Required: query Patient table, map PatientStage enum → 1/2/3
```

---

### P0.2 — Implement `end_session()` with LLM Summary

**File**: `therapeutic-copilot/server/services/therapeutic_ai_service.py` Line 449
**Problem**: Stub — no summary generation, no DB persistence
**Fix**: Fetch last 10 messages → build summarization prompt → call LLM → parse JSON → persist
**Impact**: Session close flow, clinician dashboard session summary display
**Status**: ❌ NOT DONE

---

### P0.3 — Train and Deploy LoRA Stage 1 Adapter

**Directory**: `fine_tune/stage1/`
**Problem**: `ml_models/stage1_sales_model/` directory exists but contains no adapter weights
**Fix**: Run training pipeline:
```bash
cd fine_tune/stage1
python 01_prepare_dataset.py
python 02_train_stage1_lora.py
python 03_evaluate_stage1.py
python 04_deploy_adapter.py
```
**Impact**: Stage 1 (lead generation) falls back to Together AI mock without real adapter
**Status**: ❌ NOT DONE — scripts exist, data not prepared, training not run

---

### P0.4 — Complete Auth Database Integration

**File**: `therapeutic-copilot/server/routes/auth_routes.py`
**Problem**: Login/register endpoints scaffolded but don't actually query Clinician from DB
**Fix**:
- `POST /login`: query Clinician by email, verify bcrypt password, return JWT
- `POST /register`: insert new Clinician record, return JWT
- `POST /refresh`: validate refresh token, issue new access token
- Widget token lookup: `widget_routes.py` → query Widget table by token
**Impact**: No user can log in; clinician dashboard cannot load; widget cannot initialise
**Status**: ❌ NOT DONE

---

## 8. P1 — Core Functionality Polish

> Complete after P0. Required for a solid demo and QA testing.

---

### P1.1 — Wire Sentiment Classifier into Response Pipeline

**File**: `therapeutic_ai_service.py`
**Problem**: `SentimentClassifierService` is imported and loads model but result is never used
**Fix**: Call `get_sentiment_service().classify(message)` in the concurrent classifier block, add `sentiment` + `sentiment_score` to `base_response`
**Status**: ❌ NOT DONE

---

### P1.2 — Fix RAG Service Async Issue

**File**: `therapeutic-copilot/server/services/rag_service.py`
**Problem**: `SentenceTransformer.encode()` is a synchronous CPU call inside an async function — blocks the event loop
**Fix**: Wrap with `await asyncio.get_event_loop().run_in_executor(None, self.embedder.encode, query)`
**Status**: ❌ NOT DONE

---

### P1.3 — Complete Booking Page UI

**File**: `therapeutic-copilot/client/src/pages/BookingPage.tsx`
**Problem**: 174-byte stub
**Fix**: Build appointment booking UI — calendar picker, clinician selector, time slot grid, confirmation
**Status**: ❌ NOT DONE

---

### P1.4 — Wire `lead_service.py` into Stage 1 Flow

**File**: `therapeutic-copilot/server/services/lead_service.py`
**Problem**: 2-line stub, never invoked from orchestrator
**Fix**: After Stage 1 response, score lead intent (booking_intent_detected signal from stage1_result), persist lead score to Patient record
**Status**: ❌ NOT DONE

---

### P1.5 — Set Up Together AI / Qwen Inference for Dev

**File**: `therapeutic-copilot/server/services/qwen_inference.py`
**Problem**: Needs actual `TOGETHER_API_KEY` in `.env` for dev mode, or `LLAMA_CPP_SERVER_URL` for local Qwen
**Fix**: Add `TOGETHER_API_KEY` to `.env`; verify together.ai endpoint is working end-to-end
**Status**: ❌ NOT VERIFIED

---

### P1.6 — Complete Frontend WebSocket Handler

**File**: `therapeutic-copilot/client/src/`
**Problem**: Backend WebSocket rooms defined; frontend subscription handlers not fully wired
**Fix**: Wire crisis alert subscription in `ClinicianDashboard.tsx` to show real-time popup on `crisis_alert` event
**Status**: ⚠️ PARTIAL

---

## 9. P2 — Production Hardening

> Required before any real patient usage. Not blocking demo.

---

### P2.1 — Train Safety Guardrail DeBERTa Classifier

**Directory**: `safety_crisis_emergency/`
**Problem**: Layer 4 (ML classifier) in safety pipeline has no weights — code-only rules for now
**Commands**:
```bash
cd safety_crisis_emergency
python 01_build_safety_dataset.py
python 02_train_safety_classifier.py   # ~45 min CPU / ~8 min GPU
python 03_evaluate_safety_model.py --model ./output/safety-classifier
python 04_deploy_safety_model.py
# Add to .env: SAFETY_GUARDRAIL_MODEL_PATH=<path>
```
**Status**: ❌ NOT DONE — all scripts ready

---

### P2.2 — Train Crisis ML Classifier (RoBERTa)

**Directory**: `Crisis detection model/` (needs to be built)
**Problem**: Crisis detection uses only 30+ keywords — no ML severity calibration
**Required**: RoBERTa-base fine-tuned on C-SSRS aligned 6-class crisis dataset
**Status**: ❌ NOT DONE — service file exists (`ml_crisis_service.py`), training pipeline not built

---

### P2.3 — Train Assessment Router (RoBERTa 9-class)

**File**: `therapeutic-copilot/server/services/assessment_router_service.py`
**Problem**: ML model slot defined; currently rule-based signal routing only
**Status**: ❌ NOT DONE — `assessment_router_service.py` has slot for RoBERTa weights

---

### P2.4 — Build Booking Intent Detector

**Architecture**: DistilBERT Joint (Binary booking intent + NER for date/time extraction)
**Status**: ❌ NOT BUILT — Model 09 in documentation, no training data or scripts

---

### P2.5 — Integrate APScheduler for Dropout Re-engagement

**File**: `therapeutic-copilot/server/services/dropout_service.py`
**Problem**: Service scaffolded but no scheduled job integration
**Fix**: APScheduler task: daily scan for patients inactive > 7 days → send re-engagement message
**Status**: ❌ NOT DONE

---

### P2.6 — Fix Session Stage in Redis Cache

**Problem**: Redis session stores stage but `start_session()` always passes hardcoded stage — cascades from P0.1
**Fix**: After P0.1, ensure Redis session is seeded with correct stage from DB
**Depends on**: P0.1 completion

---

### P2.7 — Google Calendar OAuth Token Storage

**File**: `therapeutic-copilot/server/services/calendar_service.py`
**Problem**: OAuth flow defined but token not persisted to DB
**Fix**: Store access/refresh tokens in `Clinician` DB record; refresh automatically
**Status**: ❌ NOT DONE

---

### P2.8 — Rate Limiting Middleware

**File**: `therapeutic-copilot/server/main.py`
**Problem**: Rate limiting middleware scaffolded but not fully implemented
**Fix**: Implement per-tenant request rate limiting (100 req/min per tenant)
**Status**: ⚠️ PARTIAL

---

## 10. What IS Working End-to-End

The following flow works today (with mock LLM fallback if Together AI not configured):

```
User sends message
   → Crisis scan (keyword layer, 30+ terms)
   → If severe: WebSocket alert to clinician + crisis resources returned
   → Concurrent: emotion + intent + topic classification (all 3 models loaded)
   → RAG context retrieval (Pinecone, if API key set)
   → Stage 2 LoRA therapy response (or Together AI mock if key set)
   → 5-layer safety guardrail (rules + crisis check + hallucination detector)
   → Response persisted to DB
   → Redis session updated
   → Response returned with guardrail_action + all ML signal fields
```

**What the API response looks like today**:
```json
{
  "response": "...",
  "guardrail_action": "PASS",
  "guardrail_codes": [],
  "guardrail_latency_ms": 2.1,
  "crisis_score": 0.1,
  "emotion": "anxiety",
  "emotion_intensity": 0.72,
  "intent": "seek_support",
  "intent_confidence": 0.91,
  "topics": ["workplace", "relationships"],
  "meta_model_patterns": ["hopeless_future", "catastrophising"],
  "therapeutic_step": "validation_and_empathy",
  "stage2_backend": "lora_qwen",
  "stage": 2
}
```

---

## 11. Environment & Deployment Checklist

### Required Environment Variables

```env
# LLM (at least one required)
TOGETHER_API_KEY=                        # Dev: Together AI cloud
LLAMA_CPP_SERVER_URL=http://localhost:8080  # Prod: local Qwen

# LoRA Adapter Paths
STAGE2_LORA_ADAPTER_PATH=<abs_path>/therapeutic-copilot/server/ml_models/stage2_therapy_model
STAGE1_LORA_ADAPTER_PATH=<abs_path>/therapeutic-copilot/server/ml_models/stage1_sales_model  # P0.3
SAFETY_GUARDRAIL_MODEL_PATH=<abs_path>/therapeutic-copilot/server/ml_models/safety_guardrail  # P2.1

# Database
DATABASE_URL=sqlite:///./saathi_copilot.db  # dev
# DATABASE_URL=postgresql://user:pass@localhost/saathi  # prod

# Redis
REDIS_URL=redis://localhost:6379

# Auth
JWT_SECRET_KEY=<random-256-bit-key>
JWT_ALGORITHM=HS256

# Pinecone (RAG)
PINECONE_API_KEY=
PINECONE_INDEX=therapeutic-kb

# Payments
RAZORPAY_KEY_ID=rzp_test_xxxx
RAZORPAY_KEY_SECRET=

# Email
SENDGRID_API_KEY=

# Google Calendar
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# App
DEBUG_MODE=true
LOG_LEVEL=DEBUG
PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### ML Model Artifacts Checklist

| Location | File | Size | Status |
|----------|------|------|--------|
| `server/ml_models/emotion_classifier/model.safetensors` | DistilBERT | ~268MB | ✅ Present |
| `server/ml_models/intent_classifier/model.safetensors` | DistilBERT | ~268MB | ✅ Present |
| `server/ml_models/topic_classifier/model.safetensors` | DistilBERT | ~268MB | ✅ Present |
| `server/ml_models/sentiment_classifier/model.safetensors` | DistilBERT | ~268MB | ✅ Present |
| `server/ml_models/meta_model_detector/adapter_model.safetensors` | Flan-T5 LoRA | ~19MB | ✅ Present |
| `server/ml_models/stage2_therapy_model/adapter_model.safetensors` | Qwen2.5 LoRA | ~115MB | ✅ Present |
| `server/ml_models/stage1_sales_model/adapter_model.safetensors` | Qwen2.5 LoRA | ~115MB | ❌ **MISSING** |
| `server/ml_models/safety_guardrail/model.safetensors` | DeBERTa | ~166MB | ❌ **MISSING** |
| `server/ml_models/crisis_classifier/model.safetensors` | RoBERTa | ~500MB | ❌ **MISSING** |

---

## 12. Session Progress Log

| Date | Session | What Was Built | Status |
|------|---------|---------------|--------|
| 2026-03-06 | Session 1 | Full scaffold: 87 files, 7,019 lines. Backend, frontend, widget, ML pipeline scaffold, tests. Pushed to GitHub. | ✅ |
| 2026-03-08 | Session 2 | Services refinement: payment, calendar, dropout, analytics, embedding, redis session | ✅ |
| 2026-03-11 | Session 3 | Trained and deployed: Emotion (F1=0.854), Intent (F1=0.989), Topic, Sentiment classifiers | ✅ |
| 2026-03-12 | Session 4 | Meta-Model Pattern Detector: Flan-T5 LoRA training pipeline, data conversion, deployed 19MB adapter | ✅ |
| 2026-03-18 | Session 5 | Stage 2 LoRA: training run, evaluation (6/6 gates), deploy 115MB adapter. Git push resolved rebase conflict. | ✅ |
| 2026-03-18 | Session 6 | Safety Guardrail System: 3 training CSVs (196 examples), 4 training scripts, safety_guardrail_service.py (5 layers), wired into therapeutic_ai_service.py, docs (ML_MODEL_DOCS/14). | ✅ |
| 2026-03-18 | Session 7 | Full system audit. Created this roadmap document. P0→P2 work begins. | 🔄 IN PROGRESS |

---

## P0 Work Tracking

| Task | File(s) | Status | Completed |
|------|---------|--------|-----------|
| P0.1 — `_detect_patient_stage()` DB query | `therapeutic_ai_service.py` | ❌ | — |
| P0.2 — `end_session()` LLM summary | `therapeutic_ai_service.py` | ❌ | — |
| P0.3 — LoRA Stage 1 train + deploy | `fine_tune/stage1/` | ❌ | — |
| P0.4 — Auth DB integration (login/register/token) | `auth_routes.py`, `widget_routes.py` | ❌ | — |

## P1 Work Tracking

| Task | File(s) | Status | Completed |
|------|---------|--------|-----------|
| P1.1 — Wire sentiment into response | `therapeutic_ai_service.py` | ❌ | — |
| P1.2 — Fix RAG async (run_in_executor) | `rag_service.py` | ❌ | — |
| P1.3 — Build Booking Page UI | `pages/BookingPage.tsx` | ❌ | — |
| P1.4 — Wire lead_service into Stage 1 | `lead_service.py`, `therapeutic_ai_service.py` | ❌ | — |
| P1.5 — Verify Together AI / Qwen inference | `.env`, `qwen_inference.py` | ❌ | — |
| P1.6 — Frontend WebSocket crisis handler | `ClinicianDashboard.tsx` | ⚠️ | — |

## P2 Work Tracking

| Task | File(s) | Status | Completed |
|------|---------|--------|-----------|
| P2.1 — Train Safety Guardrail DeBERTa | `safety_crisis_emergency/` | ❌ | — |
| P2.2 — Train Crisis ML Classifier | `Crisis detection model/` | ❌ | — |
| P2.3 — Train Assessment Router | `assessment_router_service.py` | ❌ | — |
| P2.4 — Build Booking Intent Detector | New model pipeline | ❌ | — |
| P2.5 — APScheduler dropout re-engagement | `dropout_service.py` | ❌ | — |
| P2.6 — Redis cache stage fix | `therapeutic_ai_service.py` | ❌ | — |
| P2.7 — Google Calendar OAuth storage | `calendar_service.py` | ❌ | — |
| P2.8 — Rate limiting middleware | `main.py` | ⚠️ | — |

---

*Document Version 1.0 — SAATHI AI Implementation Roadmap*
*Last Updated: 2026-03-18 | Owner: CTO / Lead Developer*
*Next Review: After P0 completion*
