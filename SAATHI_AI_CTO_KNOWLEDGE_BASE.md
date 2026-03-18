# SAATHI AI — CTO MASTER KNOWLEDGE BASE
## Complete Technical Reference for AI Model Training
### RYL NEUROACADEMY PRIVATE LIMITED | Version 1.0 | March 2026
### Purpose: Feed this document to a local LLM to train it as an expert CTO for the Saathi AI project

---

> **INSTRUCTIONS FOR THE AI READING THIS DOCUMENT**
> You are being trained to act as the expert CTO and lead developer for an application called Saathi AI.
> You know every line of code in this codebase. You know every architectural decision, every trade-off,
> every pending TODO, and every deployment detail. When a developer asks you any question about this
> codebase, answer as if you personally wrote every line and remember every decision made.
> Your responses must be precise, actionable, and reference specific file names, function names,
> and line-level detail wherever relevant. Never say you don't know — reason through the codebase
> architecture and give the correct answer.

---

## SECTION 1 — WHAT IS SAATHI AI?

### 1.1 Business Overview

Saathi AI is a **B2B SaaS therapeutic co-pilot** built for mental health clinics, hospitals, and EAP
(Employee Assistance Programs) in India and Southeast Asia.

- **Company**: RYL NEUROACADEMY PRIVATE LIMITED
- **Product Name**: Saathi AI (literally "companion AI" in Hindi)
- **GitHub Repo**: `https://github.com/cpdoryl/SAATHI-AI-PROTOTYPE.git`
- **Local Path**: `c:/saath ai prototype/`
- **Stage**: Prototype, investor-demo ready
- **Date Started**: March 6, 2026

### 1.2 Core Problem Being Solved

Mental health clinics in India have therapists who see patients once a week. Between sessions, patients
are unsupported. They cannot always call the therapist. Many drop out after 2-3 sessions. Clinics have
no system to identify who is at risk of dropping out.

Saathi AI solves this by:
1. Acting as a 24/7 AI companion that talks to patients between sessions
2. Detecting emotional crisis in real time and alerting the human clinician
3. Guiding patients through structured CBT (Cognitive Behavioral Therapy) exercises
4. Tracking patient engagement and flagging dropout risk

### 1.3 Three-Stage Patient Journey

Every patient in the system goes through exactly three stages:

**Stage 1 — Lead Generation**
- Patient finds the clinic's website and opens the chat widget
- The AI holds an empathetic first conversation (non-clinical, rapport building)
- Goal: collect name, phone, understand presenting problem, convince them to book an appointment
- LoRA Adapter: r=8, trained on 634 lead-generation conversations

**Stage 2 — Active Therapeutic Co-pilot**
- Patient has had their first real session with the human clinician
- Now uses Saathi AI between sessions (3-5x/week)
- 11-step structured CBT protocol delivered as conversation
- Clinician watches the dashboard in real time; gets alerted for crisis
- LoRA Adapter: r=16, trained on 3,017 therapeutic conversations

**Stage 3 — Dropout Re-engagement**
- Patient has been inactive for 7, 14, or 30 days
- APScheduler cron job at 09:00 UTC daily scans for inactive patients
- Sends personalised re-engagement messages via `dropout_service.py`
- Goal: bring patient back to Stage 2

### 1.4 Revenue Model

| Plan | Price | Features |
|------|-------|----------|
| Basic | ₹2,999/month | 50 patients, core chat + crisis |
| Professional | ₹5,999/month | 200 patients + assessments + calendar |
| Enterprise | ₹9,999+/month | Unlimited + white-label + custom RAG context |

- **Infrastructure cost**: ₹798/month (E2E Networks Mumbai)
- **Payments**: Razorpay (India-first, UPI + NetBanking + Cards)

---

## SECTION 2 — TECH STACK COMPLETE REFERENCE

### 2.1 Backend

| Component | Choice | Version | Reason |
|-----------|--------|---------|--------|
| Framework | FastAPI | 0.111.0 | Async-native, OpenAPI auto-docs, fastest Python framework |
| Server | Uvicorn | 0.30.1 | ASGI server for FastAPI |
| Language | Python | 3.11 | Stable, all ML libraries support it |
| ORM | SQLAlchemy | 2.0 | Native async (select/execute), no raw SQL needed |
| Migrations | Alembic | 1.13 | Works with SQLAlchemy models, autogenerate migrations |
| DB (prod) | PostgreSQL | 15 | ACID compliance, JSON columns, production grade |
| DB (dev) | SQLite | built-in | Zero install for day-1 local dev |
| Auth | python-jose + passlib | 3.3 + 1.7 | JWT tokens + bcrypt password hashing |
| Cache | Redis | 7+ | Session state, rate limiting, pub/sub for WebSocket |
| Validation | Pydantic | v2 | Type-safe schemas, request/response validation |
| Config | pydantic-settings | 2.x | Env vars with type validation and IDE autocomplete |
| Logging | loguru | 0.7 | Structured logging, simpler than standard logging |
| HTTP client | httpx | 0.27 | Async HTTP for Together AI and llama.cpp calls |
| Scheduler | APScheduler | 3.x | Cron jobs (dropout scan at 09:00 UTC daily) |
| WebSockets | websockets | 12.0 | Real-time crisis alerts to clinician dashboard |

### 2.2 Frontend

| Component | Choice | Version | Reason |
|-----------|--------|---------|--------|
| Framework | React | 18 | Component model, hooks, concurrent features |
| Language | TypeScript | 5 | Type safety, IDE autocomplete |
| Build tool | Vite | 5 | Fast HMR, ESM-native, smaller bundles than CRA |
| Styling | Tailwind CSS | 3 | Utility-first, consistent design system |
| State (server) | TanStack Query | v5 | Caching, background refetch, loading states |
| State (client) | Zustand | 4 | Lightweight (lighter than Redux), no boilerplate |
| Routing | React Router | 6 | Declarative routing, nested routes |
| HTTP | Axios | 1.7 | Interceptors for JWT auto-injection, typed calls |
| Charts | Recharts | 2.12 | Analytics dashboard charts |
| Testing | Vitest + RTL | 1.6 + 16 | Fast unit tests, component testing |

### 2.3 AI / ML Stack

| Component | Choice | Details |
|-----------|--------|---------|
| Primary LLM (prod) | Qwen 2.5-7B GGUF Q4_K_M | Self-hosted via llama.cpp on E2E Networks Mumbai |
| Primary LLM (dev) | Together AI API | Qwen/Qwen2.5-7B-Instruct-Turbo, ~$0.20/1M tokens |
| Local dev model | Ollama qwen2.5-coder:7b | RTX 5060 8GB VRAM, 4-bit quantized |
| Vector embeddings | sentence-transformers | all-MiniLM-L6-v2, 384-dim vectors |
| Vector DB | Pinecone | Managed, per-tenant namespaces |
| LoRA Stage 1 | HuggingFace PEFT | r=8, lora_alpha=16, leads, 634 examples |
| LoRA Stage 2 | HuggingFace PEFT | r=16, lora_alpha=32, therapy, 3,017 examples |
| Crisis model | RoBERTa + Keywords | 7-class, 5,000 examples |
| Emotion model | DistilBERT | 8-class, 8,000 examples |
| Intent model | DistilBERT | 7-class, 4,000 examples |
| Topic model | DistilBERT | multi-label 5-class, 2,000 examples |
| Sentiment model | DistilBERT | 3-class, 2,000 examples |
| Meta-model | AllenNLP SRL + Flan-T5-large | NLP pattern detector |
| Booking intent | DistilBERT binary + NER | 1,000 examples |
| Assessment router | RoBERTa-base | multi-label 9-class, 4,000 examples |

### 2.4 External Services

| Service | Provider | Purpose | Config Key |
|---------|----------|---------|------------|
| Payments | Razorpay | INR payments, UPI, NetBanking | RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET |
| Email | SendGrid | Appointment reminders, crisis alerts | SENDGRID_API_KEY |
| Vector DB | Pinecone | RAG knowledge base | PINECONE_API_KEY |
| Calendar | Google Calendar API | Appointment booking | GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET |
| LLM (dev) | Together AI | Qwen inference | TOGETHER_API_KEY |
| Hosting | E2E Networks Mumbai | Indian data sovereignty | SSH access required |

### 2.5 Infrastructure

| Component | Detail |
|-----------|--------|
| Containerisation | Docker + docker-compose (dev + prod configs) |
| Reverse proxy | NGINX (SSL termination, static file serving) |
| Prod hosting | E2E Networks Mumbai |
| Monthly infra cost | ₹798/month |
| CI/CD | Not yet set up (manual deploy via git pull) |

---

## SECTION 3 — REPOSITORY STRUCTURE (EVERY FILE EXPLAINED)

```
c:/saath ai prototype/
│
├── therapeutic-copilot/                  ← MAIN APPLICATION CODE
│   ├── server/                           ← Python FastAPI backend
│   │   ├── main.py                       ← App entry point, all 16 routers
│   │   ├── config.py                     ← All env vars (pydantic-settings)
│   │   ├── config_manager.py             ← Startup config validator
│   │   ├── database.py                   ← DB engine, get_db() dependency
│   │   ├── models.py                     ← ALL SQLAlchemy ORM models
│   │   ├── requirements.txt              ← 40+ Python deps with pinned versions
│   │   ├── Dockerfile                    ← Python 3.11-slim container
│   │   ├── alembic/                      ← DB migration configs
│   │   │   ├── env.py                    ← Imports all ORM models for autogenerate
│   │   │   └── versions/                 ← Migration scripts go here
│   │   ├── api/                          ← Simple CRUD route handlers
│   │   │   ├── tenants.py                ← Tenant CRUD
│   │   │   ├── users.py                  ← Clinician profile
│   │   │   ├── leads.py                  ← Stage 1 lead management
│   │   │   ├── appointments.py           ← Appointment booking
│   │   │   ├── chat.py                   ← Basic chat endpoints
│   │   │   └── payments.py               ← Razorpay integration
│   │   ├── routes/                       ← Smart route handlers with business logic
│   │   │   ├── auth_routes.py            ← JWT login/register/refresh
│   │   │   ├── chat_routes.py            ← Full 3-stage conversation pipeline
│   │   │   ├── assessment_routes.py      ← 8 clinical assessment instruments
│   │   │   ├── crisis_routes.py          ← Crisis scan + escalation
│   │   │   ├── rag_routes.py             ← Pinecone query + ingest
│   │   │   ├── widget_routes.py          ← Widget config + bundle serving
│   │   │   ├── payment_routes.py         ← Full Razorpay payment cycle
│   │   │   ├── websocket_routes.py       ← Real-time WebSocket rooms
│   │   │   └── calendar_routes.py        ← Google Calendar OAuth + events
│   │   ├── services/                     ← ALL REAL LOGIC IS HERE
│   │   │   ├── therapeutic_ai_service.py ← MAIN ORCHESTRATOR — start every AI task here
│   │   │   ├── chatbot_service.py        ← 11-step CBT state machine
│   │   │   ├── crisis_detection_service.py ← 30+ keywords, severity 0-10, <100ms
│   │   │   ├── assessment_service.py     ← PHQ-9, GAD-7, PCL-5, etc.
│   │   │   ├── qwen_inference.py         ← LLM inference (Together AI dev / llama.cpp prod)
│   │   │   ├── rag_service.py            ← Pinecone query + ingest
│   │   │   ├── lora_model_service.py     ← LoRA adapter switching
│   │   │   ├── payment_service.py        ← Razorpay orders + HMAC verification
│   │   │   ├── lead_service.py           ← Stage 1 lead capture + conversion
│   │   │   ├── dropout_service.py        ← Inactivity detection + re-engagement
│   │   │   ├── websocket_manager.py      ← WebSocket rooms for clinician alerts
│   │   │   ├── embedding_service.py      ← 384-dim sentence embeddings
│   │   │   ├── redis_session_service.py  ← Redis session cache
│   │   │   ├── emotion_classifier_service.py ← DistilBERT 8-class
│   │   │   ├── intent_classifier_service.py  ← DistilBERT 7-class
│   │   │   ├── topic_classifier_service.py   ← DistilBERT multi-label 5-class
│   │   │   ├── sentiment_classifier_service.py ← DistilBERT 3-class
│   │   │   ├── meta_model_detector_service.py  ← AllenNLP SRL + Flan-T5
│   │   │   ├── ml_crisis_service.py      ← RoBERTa ML crisis model
│   │   │   ├── analytics_service.py      ← Metrics aggregation
│   │   │   └── calendar_service.py       ← Google Calendar OAuth
│   │   ├── middleware/
│   │   │   ├── auth_middleware.py        ← JWT Bearer dependency
│   │   │   └── rate_limit_middleware.py  ← Redis rate limiter (scaffold, not implemented)
│   │   ├── auth/
│   │   │   └── jwt_handler.py            ← bcrypt + python-jose JWT
│   │   └── models/
│   │       └── schemas.py               ← ALL Pydantic v2 request/response schemas
│   │
│   ├── client/                           ← React 18 + TypeScript frontend
│   │   ├── src/
│   │   │   ├── App.tsx                   ← Router config: /, /dashboard, /patient, /admin
│   │   │   ├── main.tsx                  ← React DOM mount
│   │   │   ├── index.css                 ← Tailwind directives
│   │   │   ├── types/index.ts            ← ALL TypeScript interfaces
│   │   │   ├── lib/api.ts                ← Axios client + all typed API calls
│   │   │   ├── contexts/AuthContext.tsx  ← JWT auth state + useAuth() hook
│   │   │   ├── hooks/useChat.ts          ← WebSocket chat hook
│   │   │   ├── pages/index.tsx           ← Page re-exports
│   │   │   └── components/
│   │   │       ├── chatbot/ChatWidget.tsx        ← Main chat UI component
│   │   │       ├── clinician/ClinicianDashboard.tsx ← Real-time clinician hub
│   │   │       ├── patient/PatientPortal.tsx     ← Patient-facing portal
│   │   │       ├── payment/PaymentFlow.tsx       ← Razorpay checkout
│   │   │       ├── landing/LandingPage.tsx       ← Marketing page
│   │   │       ├── analytics/Analytics.tsx       ← Metrics dashboard
│   │   │       ├── admin/AdminPanel.tsx          ← Super-admin panel
│   │   │       └── ui/index.tsx                  ← Design system (Button, Badge, Card, Spinner)
│   │   ├── vite.config.ts                ← Dev proxy: /api→:8000, /ws→:8000
│   │   ├── package.json                  ← All deps pinned
│   │   └── Dockerfile.dev                ← Node 18 Alpine dev container
│   │
│   ├── widget/                           ← Embeddable chat widget for clinic websites
│   │   └── src/
│   │       ├── widget.ts                 ← Custom element + Shadow DOM entry
│   │       └── components/ChatBubble.tsx ← Full widget UI (inline styles, no Tailwind)
│   │
│   ├── ml_pipeline/                      ← ML training code
│   │   ├── ML_BLUEPRINT.md               ← ML pipeline documentation
│   │   ├── train_lora.py                 ← LoRA fine-tuning (QLoRA, HuggingFace PEFT)
│   │   ├── scripts/                      ← Data prep scripts
│   │   └── data/                         ← Training data (not in git, too large)
│   │
│   ├── tests/
│   │   ├── conftest.py                   ← Pytest setup
│   │   ├── test_chat.py                  ← Chat API integration tests
│   │   ├── test_crisis_detection.py      ← Crisis unit tests (speed + accuracy)
│   │   └── test_assessments.py           ← Assessment scoring tests
│   │
│   ├── scripts/
│   │   ├── setup_db.py                   ← DB init + seed demo data
│   │   └── generate_widget_token.py      ← Widget token generator
│   │
│   └── docker-compose.yml               ← Local dev stack (all 4 services)
│
├── ML_MODEL_DOCS/                        ← Documentation for all 10 ML models
│   ├── 00_INDEX_AND_OVERVIEW.md          ← Master index (read this first)
│   ├── 01_EMOTION_DETECTION_CLASSIFIER.md
│   ├── 02_CRISIS_DETECTION_CLASSIFIER.md
│   ├── 03_INTENT_CLASSIFIER.md
│   ├── 04_TOPIC_CLASSIFIER.md
│   ├── 05_SENTIMENT_CLASSIFIER.md
│   ├── 06_META_MODEL_PATTERN_DETECTOR.md
│   ├── 07_LORA_STAGE1_LEAD_GENERATION.md
│   ├── 08_LORA_STAGE2_THERAPEUTIC_SUPPORT.md
│   ├── 09_BOOKING_INTENT_DETECTOR.md
│   └── 10_ASSESSMENT_ROUTER.md
│
├── ML_MODEL_DATASETS/                    ← Raw training datasets
│   ├── 01_emotion_detection_v1.csv       ← 8,000 rows, 8 emotions
│   ├── 03_intent_classifier_v1.csv       ← 4,000 rows, 7 intents
│   ├── 04_topic_classifier_v1.csv        ← 2,000 rows, 5 topics
│   ├── 05_sentiment_classifier_v1.csv    ← 2,000 rows, 3 sentiments
│   ├── 06_meta_model_patterns_v1.json    ← NLP patterns
│   ├── 07_stage1_sales_dataset.jsonl     ← 634 conversations (Stage 1 LoRA)
│   ├── 08_stage2_therapy_dataset.jsonl   ← 3,017 conversations (Stage 2 LoRA)
│   ├── 09_booking_intent_v1.json         ← 1,000 booking examples
│   ├── 10_assessment_router_v1.json      ← 4,000 routing examples
│   └── rag_knowledge_base.json           ← Initial RAG knowledge base
│
└── [Various training folders]            ← Individual model training folders
    ├── Emotion detection model/
    ├── Intent classifier model/
    ├── Sentiment classifier model/
    ├── Topic classifier model/
    ├── Meta model pattern detector/
    └── Crises detection models dataset, training and testing scripts model/
```

---

## SECTION 4 — BACKEND ARCHITECTURE IN DETAIL

### 4.1 Application Entry Point (`main.py`)

The FastAPI app uses a **lifespan context manager** for startup/shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP — runs in this order:
    await init_db()                          # Create tables if not exist
    await warmup_crisis_model()              # Pre-load crisis detector
    await warmup_emotion_classifier()        # Pre-load emotion DistilBERT
    await warmup_intent_classifier()         # Pre-load intent DistilBERT
    await warmup_topic_classifier()          # Pre-load topic DistilBERT
    scheduler.start()                        # APScheduler cron jobs
    yield
    # SHUTDOWN:
    scheduler.shutdown()
```

**All 16 routers mounted at `/api/v1/`**:
- auth_router (`/api/v1/auth`)
- chat_router (`/api/v1/chat`)
- assessment_router (`/api/v1/assessments`)
- crisis_router (`/api/v1/crisis`)
- rag_router (`/api/v1/rag`)
- widget_router (`/api/v1/widget`)
- payment_router (`/api/v1/payments`)
- websocket_router (`/ws`)
- calendar_router (`/api/v1/calendar`)
- tenant_router (`/api/v1/tenants`)
- user_router (`/api/v1/users`)
- leads_router (`/api/v1/leads`)
- appointments_router (`/api/v1/appointments`)
- analytics_router (`/api/v1/analytics`)
- basic_chat_router (`/api/v1/basic-chat`)
- dropout_router (`/api/v1/dropout`)

**CORS** configured from `settings.cors_origins_list` (comma-separated string → list).
**JWT middleware** verifies Bearer tokens on all protected routes.

### 4.2 Configuration (`config.py`)

All settings via `pydantic-settings` `BaseSettings` class. Loads from `.env` file automatically.

**Critical env vars (MUST be set for any functionality)**:
```bash
DATABASE_URL=sqlite:///./saathi_copilot.db     # SQLite for dev
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=your-256-bit-secret             # CRITICAL — use long random string
JWT_ALGORITHM=HS256
```

**AI inference env vars (at least one required)**:
```bash
TOGETHER_API_KEY=your-key                      # Dev/fallback — Together AI
TOGETHER_MODEL=Qwen/Qwen2.5-7B-Instruct-Turbo # Default model
LLAMA_CPP_SERVER_URL=http://localhost:8080     # Prod: llama.cpp HTTP server
LLAMA_CPP_PYTHON_MODEL_PATH=/models/qwen.gguf  # Prod: native llama-cpp-python (FASTEST)
```

**Important**: `LLAMA_CPP_PYTHON_MODEL_PATH` takes priority over everything else. If set,
the app uses in-process llama-cpp-python (no HTTP round-trip). This is the fastest production option.

**Optional services (app runs without them, features degraded)**:
```bash
PINECONE_API_KEY=...        # RAG disabled without this
RAZORPAY_KEY_ID=...         # Payments disabled
RAZORPAY_KEY_SECRET=...
SENDGRID_API_KEY=...        # Email notifications disabled
GOOGLE_CLIENT_ID=...        # Calendar booking disabled
GOOGLE_CLIENT_SECRET=...
```

### 4.3 Database Models (`models.py`)

**All tables use string UUIDs as primary keys (NOT integer serial)**. Multi-tenant: every table
(except `tenants`) has a `tenant_id` FK. Soft deletes via `is_active` boolean.

**Complete table list**:

**`tenants`** — The B2B customer (a clinic or hospital)
- `id` (UUID string PK), `name`, `domain` (unique), `widget_token` (unique)
- `plan` (basic/professional/enterprise), `is_active`, `pinecone_namespace`
- `razorpay_account_id`, `created_at`

**`clinicians`** — The therapists who log in to the dashboard
- `id` (UUID PK), `tenant_id` (FK → tenants), `email` (unique)
- `hashed_password` (bcrypt), `full_name`, `specialization`
- `google_calendar_token` (encrypted OAuth token), `is_active`, `created_at`

**`patients`** — The end users of the therapy
- `id` (UUID PK), `tenant_id` (FK → tenants), `clinician_id` (FK → clinicians, nullable)
- `full_name`, `phone`, `email`, `stage` (LEAD/ACTIVE/DROPOUT/ARCHIVED)
- `language` (default "en"), `cultural_context`, `last_active`
- `dropout_risk_score` (float 0.0–1.0), `created_at`

**`therapy_sessions`** — Each AI conversation session
- `id` (UUID PK), `patient_id` (FK → patients)
- `stage` (integer 1/2/3), `current_step` (0–11 for Stage 2 CBT protocol)
- `status` (PENDING/IN_PROGRESS/COMPLETED/CRISIS_ESCALATED)
- `crisis_score` (float), `session_summary` (Text), `ai_insights` (JSON)
- `started_at`, `ended_at`

**`chat_messages`** — Individual messages in a session
- `id` (UUID PK), `session_id` (FK → therapy_sessions)
- `role` (user/assistant/system), `content` (Text)
- `emotion_label`, `intent_label`, `crisis_score`
- `metadata` (JSON — all classifier outputs stored here), `created_at`

**`assessments`** — Clinical assessment results
- `id` (UUID PK), `patient_id` (FK → patients), `clinician_id` (FK → clinicians)
- `assessment_type` (PHQ-9, GAD-7, PCL-5, DASS-21, PSQ, ISI, BAI, MDQ)
- `score` (float), `severity_label` (string), `answers` (JSON array)
- `administered_at`, `notes` (Text)

**`appointments`** — Therapy appointment bookings
- `id` (UUID PK), `patient_id`, `clinician_id`, `tenant_id`
- `scheduled_at` (DateTime), `duration_minutes` (default 50)
- `status` (SCHEDULED/CONFIRMED/COMPLETED/CANCELLED/NO_SHOW)
- `google_event_id` (from Google Calendar), `notes`

**Missing tables (TODO — need to be created)**:
- `audit_logs` — for HIPAA compliance
- `widget_sessions` — for anonymous widget visitors before they register

### 4.4 AI Orchestration Pipeline (`therapeutic_ai_service.py`)

This is the most important service in the entire backend. All AI logic flows through here.

**`process_message(session_id, message, stage)` — Full Pipeline**:

```
Step 1: Load session from Redis cache (fast path) OR database (slow path)
        ↓
Step 2: Crisis detection — ALWAYS RUNS FIRST, NEVER SKIP
        crisis_detector.scan(message)
        → Returns: {score: float, is_crisis: bool, keywords_matched: list}
        → If is_crisis: trigger escalation (WebSocket alert to clinician, email)
        ↓
Step 3: Parallel classifier calls (asyncio.gather):
        - emotion_classifier.classify(message) → {label, confidence}
        - intent_classifier.classify(message) → {label, confidence}
        - topic_classifier.classify(message) → {labels: list, confidences: list}
        ↓
Step 4: Build context blocks from classifier outputs:
        - build_emotion_context_block(emotion_result)
        - build_intent_context_block(intent_result)
        - build_topic_context_block(topic_result)
        ↓
Step 5: RAG retrieval
        rag.query(message, tenant_id, namespace)
        → Returns: list of relevant knowledge chunks
        ↓
Step 6: Build system prompt
        chatbot.build_system_prompt(stage, current_step, emotion_block, intent_block, topic_block, rag_context)
        ↓
Step 7: LLM inference
        llm.generate(prompt, stage, max_tokens=512)
        → Together AI (dev) or llama.cpp (prod)
        ↓
Step 8: Persist messages to database
        ChatMessage(role="user", content=message, ...)
        ChatMessage(role="assistant", content=response, ...)
        ↓
Step 9: Advance CBT step (Stage 2 only)
        session.current_step = min(session.current_step + 1, 11)
        ↓
Step 10: Return response + metadata to WebSocket/HTTP client
```

### 4.5 Crisis Detection (`crisis_detection_service.py`)

**Design principles**:
- RULE-BASED FIRST (fast, reliable, transparent): 30+ weighted keywords
- ML-backed second: RoBERTa model for nuanced cases
- Must complete in <100ms (verified by unit test)
- 7 severity classes (0 = none, 6 = immediate danger)
- Also detects Hinglish (Hindi-English mixed language)

**Severity scoring algorithm**:
- Each keyword has a weight (1–5)
- Multiple keywords accumulate (sum, not max)
- Score capped at 10
- Threshold for alert: score ≥ 7 (configurable in settings)

**Action on crisis detected**:
1. Store `crisis_score` in `ChatMessage.metadata`
2. Update `TherapySession.status` → `CRISIS_ESCALATED`
3. WebSocket push to clinician room: `{type: "CRISIS_ALERT", patient_id, score, message_preview}`
4. SendGrid email to clinician (TODO: not yet fully implemented)

### 4.6 CBT State Machine (`chatbot_service.py`)

11-step CBT protocol for Stage 2 patients. `current_step` stored in `TherapySession.current_step`.

| Step | Protocol Phase |
|------|---------------|
| 0 | Session opening + mood check-in |
| 1 | Rapport building |
| 2 | Problem identification |
| 3 | Thought monitoring (automatic thoughts) |
| 4 | Cognitive restructuring |
| 5 | Behavioral activation homework |
| 6 | Relaxation techniques (breathing, grounding) |
| 7 | Problem-solving skills |
| 8 | Interpersonal effectiveness |
| 9 | Mindfulness introduction |
| 10 | Relapse prevention planning |
| 11 | Session closure + next steps |

**`build_system_prompt(stage, step, emotion_block, intent_block, topic_block, rag_context)`**:
- Injects all classifier outputs into system prompt
- Tells the LLM exactly what emotion/intent the user is showing
- Gives the LLM the current CBT step context
- Injects relevant RAG knowledge chunks
- Applies cultural context (Indian patient, possible Hinglish, family dynamics)

### 4.7 LLM Inference (`qwen_inference.py`)

Three inference modes (auto-selected at startup based on env vars):

**Mode 1: llama-cpp-python native (FASTEST — prod)**
- `LLAMA_CPP_PYTHON_MODEL_PATH` must be set
- Model loaded once into memory at `_get_llama_native_model()` singleton
- All requests run in-process, no HTTP overhead
- Parameters: `n_ctx=4096`, `n_gpu_layers=-1` (all layers on GPU), `temperature=0.7`, `top_p=0.9`

**Mode 2: Together AI API (dev/fallback)**
- `TOGETHER_API_KEY` must be set
- HTTP call to `https://api.together.xyz/v1/chat/completions`
- Model: `Qwen/Qwen2.5-7B-Instruct-Turbo`
- `timeout=30.0` seconds

**Mode 3: llama.cpp HTTP server**
- Neither above is set
- HTTP call to `LLAMA_CPP_SERVER_URL/completion`
- For running llama.cpp as a separate process on the same host

### 4.8 RAG Service (`rag_service.py`)

**Pinecone configuration**:
- Index: one shared index with per-tenant namespaces
- Namespace: `tenant.pinecone_namespace` (stored in DB)
- Vector dimension: 384 (matching all-MiniLM-L6-v2)
- Distance metric: cosine similarity
- Default top_k: 5 chunks returned per query

**How it works**:
1. Query text → embedding via `embedding_service.embed(text)` (384-dim vector)
2. Pinecone query with `namespace=tenant_namespace, top_k=5`
3. Returns list of matching knowledge chunks with scores
4. Chunks formatted and injected into system prompt

**Known issue (TODO)**: `rag_service.py` calls `SentenceTransformer` synchronously inside an async
function. This blocks the event loop. Fix: wrap in `asyncio.get_event_loop().run_in_executor(None, ...)`.

### 4.9 Payment Service (`payment_service.py`)

**Razorpay payment flow**:
1. `create_order(amount_inr, tenant_id)` → Razorpay order object with `order_id`
2. Frontend loads Razorpay JS SDK (from CDN), renders payment modal
3. User completes payment (UPI/card/NetBanking)
4. Razorpay webhooks backend at `/api/v1/payments/webhook`
5. Backend verifies HMAC signature: `HMAC-SHA256(order_id + "|" + payment_id, KEY_SECRET)`
6. On success: update tenant plan in DB, send confirmation email

### 4.10 WebSocket Architecture (`websocket_manager.py`)

**Room-based design**:
- Each clinician gets their own WebSocket room keyed by `clinician_id`
- When crisis detected, `ws_manager.broadcast_to_clinician(clinician_id, payload)` is called
- Clinician dashboard frontend connects to `/ws/clinician/{clinician_id}` on load

**Message types**:
- `CRISIS_ALERT` — patient in crisis, contains score and preview
- `AI_RESPONSE` — streaming AI response to patient
- `AI_TYPING` — typing indicator
- `SESSION_UPDATE` — patient session status changed

### 4.11 Assessment Service (`assessment_service.py`)

**8 clinical instruments implemented**:

| Instrument | Full Name | Score Range | Severity Labels |
|------------|-----------|-------------|-----------------|
| PHQ-9 | Patient Health Questionnaire | 0–27 | None, Mild, Moderate, Mod-Severe, Severe |
| GAD-7 | Generalised Anxiety Disorder | 0–21 | None, Mild, Moderate, Severe |
| PCL-5 | PTSD Checklist (DSM-5) | 0–80 | Symptoms absent/present |
| DASS-21 | Depression Anxiety Stress | 0–63 | Normal/Mild/Mod/Severe/Extreme |
| PSQ | Perceived Stress Questionnaire | 0–1 (normalised) | Low/Medium/High stress |
| ISI | Insomnia Severity Index | 0–28 | None/Subthreshold/Mod/Severe |
| BAI | Beck Anxiety Inventory | 0–63 | Minimal/Mild/Mod/Severe |
| MDQ | Mood Disorder Questionnaire | Criteria-based | Positive/Negative screen |

---

## SECTION 5 — FRONTEND ARCHITECTURE IN DETAIL

### 5.1 Route Structure (`App.tsx`)

```
/ (public)          → LandingPage.tsx
/dashboard          → ClinicianDashboard.tsx  [PROTECTED — requires JWT]
/patient            → PatientPortal.tsx        [PROTECTED — requires JWT]
/admin              → AdminPanel.tsx           [PROTECTED — requires admin role]
```

All protected routes check `useAuth()` hook. If not authenticated, redirect to `/`.

### 5.2 Authentication Flow

1. Clinician goes to `/`, clicks "Login"
2. `POST /api/v1/auth/login` with `{email, password}` → returns `{access_token, token_type}`
3. `AuthContext` stores token in `localStorage.getItem("saathi_token")`
4. Axios client in `lib/api.ts` auto-injects `Authorization: Bearer <token>` via interceptor
5. **TODO**: `AuthContext` needs to call `GET /users/me` after login to populate user state

### 5.3 WebSocket Chat Hook (`hooks/useChat.ts`)

```typescript
const { messages, sendMessage, isConnected, isTyping } = useChat(sessionId);
```

- Connects to `ws://localhost:8000/ws/chat/{sessionId}`
- Handles three message types: `AI_RESPONSE`, `AI_TYPING`, `CRISIS_ALERT`
- Optimistic add: user's message shown immediately before server confirms
- On `CRISIS_ALERT`: triggers alert banner in UI

### 5.4 API Client (`lib/api.ts`)

All API calls are typed and organised by domain:
```typescript
// Auth
api.auth.login(email, password) → Promise<{access_token: string}>
api.auth.register(data) → Promise<Clinician>

// Chat
api.chat.startSession(patientId, widgetToken) → Promise<{session_id, greeting}>
api.chat.sendMessage(sessionId, message) → Promise<{response, crisis_score}>

// Assessments
api.assessments.getQuestions(type) → Promise<Question[]>
api.assessments.submit(patientId, type, answers) → Promise<AssessmentResult>

// Payments
api.payments.createOrder(amount) → Promise<{order_id, amount}>
api.payments.verify(orderId, paymentId, signature) → Promise<{success: bool}>
```

### 5.5 Design System (`components/ui/index.tsx`)

Four primitive components used throughout:

- `<Button variant="primary|secondary|danger" size="sm|md|lg">`
- `<Badge color="green|yellow|red|blue">{label}</Badge>`
- `<Card className="...">{children}</Card>`
- `<Spinner size="sm|md|lg" />`

**Tailwind conventions in this codebase**:
- Primary color: indigo-600 / indigo-700
- Danger: red-500 / red-600
- Success: green-500
- Neutral: gray-100/200/300 for backgrounds, gray-700/800 for text
- All interactive elements have `hover:` and `focus:` states
- Rounded corners: `rounded-lg` (standard), `rounded-full` (pills/avatars)

---

## SECTION 6 — WIDGET ARCHITECTURE

### 6.1 How the Widget Works

The embeddable widget is a completely separate build from the main React app. It uses:
- **Shadow DOM** for complete CSS isolation (no conflicts with host site styles)
- **Custom Elements API** for the mount mechanism
- **IIFE bundle** (single JavaScript file, no npm install needed by clinic)

**Clinic installation**:
```html
<script src="https://cdn.saathiai.com/widget.bundle.js" 
        data-token="CLINIC_WIDGET_TOKEN">
</script>
```

**What happens**:
1. `widget.ts` runs → reads `data-token` from script tag
2. Creates `<saathi-widget>` Custom Element, appends to `<body>`
3. Custom Element creates Shadow DOM with CSS reset
4. React mounts `<ChatBubble token={token} />` inside Shadow DOM
5. `ChatBubble` calls `GET /api/v1/widget/config?token=...` → gets persona config
6. Renders floating circle button (bottom-right, fixed position)
7. User clicks → chat panel opens, `POST /api/v1/chat/message` for each turn

### 6.2 Widget Build (`vite.config.widget.ts`)

```javascript
// Output is a single self-contained IIFE bundle
build: {
  lib: { entry: 'src/widget.ts', formats: ['iife'], name: 'SaathiWidget' },
  rollupOptions: { output: { entryFileNames: 'widget.bundle.js' } }
}
```

---

## SECTION 7 — ML/AI MODELS COMPLETE REFERENCE

### 7.1 Five-Layer ML Pipeline (runs on every patient message)

```
Layer 1: SAFETY (ALWAYS FIRST — never skip, never delay)
  └── Crisis Detection: rule-based keywords + RoBERTa ML (<100ms)
      → If crisis detected: STOP, escalate immediately

Layer 2: SIGNAL CLASSIFICATION (parallel, ~30ms each)
  ├── Emotion Classification: DistilBERT 8-class
  ├── Intent Classification: DistilBERT 7-class
  └── Sentiment Analysis: DistilBERT 3-class

Layer 3: DOMAIN ENRICHMENT
  ├── Topic Classification: DistilBERT multi-label 5-class
  ├── Booking Intent: DistilBERT binary + NER
  └── Assessment Router: RoBERTa-base multi-label 9-class

Layer 4: NLP ANALYSIS (Stage 2 therapeutic mode only)
  └── Meta-Model Pattern Detector: AllenNLP SRL + Flan-T5-large LoRA

Layer 5: LLM GENERATION
  └── Qwen 2.5-7B with LoRA adapter (Stage 1 r=8 or Stage 2 r=16)
      System prompt = all classifier outputs + RAG context + CBT step
```

### 7.2 Model 1 — Crisis Detection Classifier

- **Architecture**: RoBERTa + 30+ weighted keywords
- **Classes (7)**: `safe`, `ideation_passive`, `ideation_active`, `plan_forming`,
  `plan_with_means`, `attempt_history`, `immediate_danger`
- **Training data**: 5,000 examples
- **Dataset location**: `ML_MODEL_DATASETS/` + `Crises detection models dataset, training and testing scripts model/`
- **Speed requirement**: <100ms (enforced by unit test)
- **Priority**: IF crisis score ≥ threshold, ALL other processing stops

### 7.3 Model 2 — Emotion Detection Classifier

- **Architecture**: DistilBERT fine-tuned
- **Classes (8)**: `neutral`, `happy`, `sad`, `anxious`, `angry`, `fearful`, `disgusted`, `surprised`
- **Training data**: 8,000 examples, CSV format
- **Dataset**: `ML_MODEL_DATASETS/01_emotion_detection_v1.csv`
- **Output used for**: Tailor LLM system prompt with emotional context
- **Service**: `emotion_classifier_service.py` → `get_emotion_service()` singleton

### 7.4 Model 3 — Intent Classifier

- **Architecture**: DistilBERT fine-tuned
- **Classes (7)**: `seeking_support`, `sharing_experience`, `asking_question`,
  `expressing_gratitude`, `showing_resistance`, `booking_intent`, `crisis_signal`
- **Training data**: 4,000 examples
- **Dataset**: `ML_MODEL_DATASETS/03_intent_classifier_v1.csv`
- **Service**: `intent_classifier_service.py` → `get_intent_service()` singleton

### 7.5 Model 4 — Topic Classifier

- **Architecture**: DistilBERT fine-tuned, MULTI-LABEL
- **Labels (5)**: `depression`, `anxiety`, `relationship`, `work_stress`, `family`
- **Training data**: 2,000 examples
- **Dataset**: `ML_MODEL_DATASETS/04_topic_classifier_v1.csv`
- **Multi-label**: A single message can have multiple topics (e.g., `depression + work_stress`)
- **Service**: `topic_classifier_service.py` → `get_topic_service()` singleton

### 7.6 Model 5 — Sentiment Classifier

- **Architecture**: DistilBERT fine-tuned
- **Classes (3)**: `positive`, `neutral`, `negative`
- **Training data**: 2,000 examples
- **Dataset**: `ML_MODEL_DATASETS/05_sentiment_classifier_v1.csv`
- **Service**: `sentiment_classifier_service.py`

### 7.7 Model 6 — Meta-Model Pattern Detector

- **Architecture**: AllenNLP SRL (Semantic Role Labelling) + Flan-T5-large LoRA
- **Purpose**: Detects linguistic patterns in patient speech that indicate cognitive distortions
  (e.g., catastrophizing, black-and-white thinking, mind reading)
- **Training data**: Meta-model patterns reference (`meta_model_patterns_v1_reference.csv`)
- **Location**: `Meta model pattern detector/` folder with full documentation
- **Service**: `meta_model_detector_service.py`
- **Only used in Stage 2** (therapeutic mode, not Stage 1 lead gen)

### 7.8 Model 7 — LoRA Stage 1 (Lead Generation)

- **Base model**: Qwen/Qwen2.5-7B-Instruct
- **LoRA config**: `r=8`, `lora_alpha=16`, target: `q_proj`, `v_proj`, `k_proj`, `o_proj`
- **Training data**: 634 conversations
- **Dataset**: `ML_MODEL_DATASETS/07_stage1_sales_dataset.jsonl`
- **Conversation style**: Empathetic first contact, non-clinical, rapport building
- **Goal**: Convert LEAD patient to book an appointment
- **Cultural context**: Indian patients, family pressures, work stress, Hinglish

### 7.9 Model 8 — LoRA Stage 2 (Therapeutic Support)

- **Base model**: Qwen/Qwen2.5-7B-Instruct
- **LoRA config**: `r=16`, `lora_alpha=32`, target: all projection layers including
  `gate_proj`, `up_proj`, `down_proj` (more parameters = deeper adaptation)
- **Training data**: 3,017 conversations
- **Dataset**: `ML_MODEL_DATASETS/08_stage2_therapy_dataset.jsonl`
- **Conversation style**: CBT-aligned, therapeutic, structured 11-step protocol
- **Goal**: Support ACTIVE patients between human therapy sessions

### 7.10 Model 9 — Booking Intent Detector

- **Architecture**: DistilBERT binary + NER (Named Entity Recognition)
- **Classes**: `wants_to_book` (binary yes/no)
- **NER extraction**: Extracts preferred date/time from natural language
- **Training data**: 1,000 examples
- **Dataset**: `ML_MODEL_DATASETS/09_booking_intent_v1.json`

### 7.11 Model 10 — Assessment Router

- **Architecture**: RoBERTa-base multi-label
- **Classes (9)**: `PHQ-9`, `GAD-7`, `PCL-5`, `DASS-21`, `PSQ`, `ISI`, `BAI`, `MDQ`, `none`
- **Purpose**: Automatically detects which clinical assessment the patient's message suggests
- **Training data**: 4,000 examples
- **Dataset**: `ML_MODEL_DATASETS/10_assessment_router_v1.json`
- **Trigger**: If assessment router detects `PHQ-9` signal in conversation, proactively ask
  "It sounds like you've been struggling with your mood — would you like to take a quick 9-question
   check-in to better understand how you're feeling?"

---

## SECTION 8 — API ENDPOINTS COMPLETE REFERENCE

### Authentication (`/api/v1/auth/`)
```
POST /api/v1/auth/register         → Create new clinician account
POST /api/v1/auth/login            → Returns JWT access_token
POST /api/v1/auth/refresh          → Refresh expired token
GET  /api/v1/auth/me               → Get current user info from JWT
```

### Chat (`/api/v1/chat/`)
```
POST /api/v1/chat/sessions         → Start new therapy session (returns session_id + greeting)
POST /api/v1/chat/message          → Send message, get AI response (full pipeline)
GET  /api/v1/chat/sessions/{id}    → Get session details + message history
GET  /api/v1/chat/sessions         → List all sessions for a patient
```

### Assessments (`/api/v1/assessments/`)
```
GET  /api/v1/assessments/types            → List all 8 assessment types
GET  /api/v1/assessments/{type}/questions → Get questions for an instrument
POST /api/v1/assessments/submit           → Submit answers, get score + severity
GET  /api/v1/assessments/patient/{id}     → Get all assessments for a patient
```

### Crisis (`/api/v1/crisis/`)
```
POST /api/v1/crisis/scan           → Standalone crisis scan (not tied to session)
GET  /api/v1/crisis/alerts         → List crisis events for clinician
POST /api/v1/crisis/resolve/{id}   → Mark crisis as handled
```

### RAG (`/api/v1/rag/`)
```
POST /api/v1/rag/ingest            → Add knowledge chunk to Pinecone namespace
POST /api/v1/rag/query             → Query knowledge base
DELETE /api/v1/rag/{chunk_id}      → Remove a knowledge chunk
GET  /api/v1/rag/list              → List all chunks for a tenant
```

### Widget (`/api/v1/widget/`)
```
GET  /api/v1/widget/config?token=  → Get widget display config (persona, colors)
POST /api/v1/widget/message        → Send message from embedded widget
GET  /api/v1/widget/bundle.js      → Serve the widget JavaScript bundle
```

### Payments (`/api/v1/payments/`)
```
POST /api/v1/payments/create-order → Create Razorpay order
POST /api/v1/payments/verify       → Verify HMAC signature after payment
POST /api/v1/payments/webhook      → Razorpay webhook receiver
GET  /api/v1/payments/history      → Payment history for tenant
```

### WebSocket (`/ws/`)
```
WS  /ws/chat/{session_id}          → Patient chat (receives AI responses)
WS  /ws/clinician/{clinician_id}   → Clinician dashboard real-time feed
```

### Tenants / Users / Leads / Appointments
```
GET/POST  /api/v1/tenants          → List/create tenants (admin only)
GET/PUT   /api/v1/tenants/{id}     → Get/update tenant
GET/POST  /api/v1/leads            → List/create Stage 1 leads
PATCH     /api/v1/leads/{id}/convert → Convert lead to active patient
GET/POST  /api/v1/appointments     → List/create appointments
PATCH     /api/v1/appointments/{id}/status → Update status
GET       /api/v1/analytics/dashboard → Clinic metrics summary
```

---

## SECTION 9 — DOCKER AND DEPLOYMENT

### 9.1 Local Development (`therapeutic-copilot/docker-compose.yml`)

```yaml
# Start everything with one command:
# cd therapeutic-copilot && docker compose up --build

services:
  backend:
    build: ./server
    ports: ["8000:8000"]
    env_file: .env
    volumes: ["./server:/app"]   # Hot reload
    depends_on: [db, redis]

  frontend:
    build: ./client/Dockerfile.dev
    ports: ["5173:5173"]
    volumes: ["./client:/app"]   # HMR

  db:
    image: postgres:15
    environment: {POSTGRES_DB: saathi, POSTGRES_USER: saathi, POSTGRES_PASSWORD: saathi}
    healthcheck: {test: ["CMD", "pg_isready", "-U", "saathi"]}

  redis:
    image: redis:7
    healthcheck: {test: ["CMD", "redis-cli", "ping"]}
```

### 9.2 Production (`docker-compose.prod.yml` at root)

```yaml
# Production deployment on E2E Networks Mumbai
# nginx → backend (internal only) + PostgreSQL + Redis

services:
  nginx:
    image: nginx:latest
    ports: ["80:80", "443:443"]
    volumes: ["./nginx.conf:/etc/nginx/nginx.conf", "./ssl:/etc/ssl"]
    depends_on: [backend]

  backend:
    build: ./therapeutic-copilot/server
    environment: [DATABASE_URL, REDIS_URL, JWT_SECRET_KEY, TOGETHER_API_KEY, ...]
    # NOT exposed to internet — only accessible via nginx

  db:
    image: postgres:15
    volumes: ["postgres_data:/var/lib/postgresql/data"]

  redis:
    image: redis:7
    volumes: ["redis_data:/data"]
```

### 9.3 Running Without Docker (development)

```powershell
# Backend (Windows PowerShell)
cd "c:\saath ai prototype\therapeutic-copilot\server"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/setup_db.py --seed     # Creates tables + demo data
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd "c:\saath ai prototype\therapeutic-copilot\client"
npm install
npm run dev                            # Runs on port 5173, proxies /api to :8000
```

---

## SECTION 10 — CODING PATTERNS AND CONVENTIONS

### 10.1 Backend Patterns

**Dependency injection in routes**:
```python
@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),           # DB session injected
    current_user: Clinician = Depends(get_current_user)  # JWT auth injected
):
```

**Async-first**: All DB calls use `await db.execute(select(...))`. Never use sync SQLAlchemy
in async context. If you need to call a sync function (like a Transformer model), use:
```python
result = await asyncio.get_event_loop().run_in_executor(None, sync_function, argument)
```

**Error handling convention**:
```python
from fastapi import HTTPException
raise HTTPException(status_code=404, detail="Patient not found")
raise HTTPException(status_code=403, detail="Access denied — different tenant")
```

**Logging convention** (loguru):
```python
logger.info(f"Starting session for patient {patient_id} at stage {stage}")
logger.warning(f"Crisis score {score} for patient {patient_id}")
logger.error(f"LLM inference failed: {exc}")
```

**Multi-tenant data isolation**: EVERY DB query that returns patient/session data must include
a `tenant_id` filter. Never return cross-tenant data. Example:
```python
result = await db.execute(
    select(Patient)
    .where(Patient.tenant_id == current_user.tenant_id)  # ALWAYS include this
    .where(Patient.id == patient_id)
)
```

### 10.2 Frontend Patterns

**API call with TanStack Query**:
```typescript
const { data: patients, isLoading, error } = useQuery({
  queryKey: ['patients', tenantId],
  queryFn: () => api.patients.list(tenantId),
  staleTime: 30_000,  // 30 seconds before refetch
});
```

**Form state with Zustand**:
```typescript
const useFormStore = create<FormState>((set) => ({
  values: { email: '', password: '' },
  setField: (field, value) => set((s) => ({ values: { ...s.values, [field]: value } })),
}));
```

**Protected routes pattern**:
```typescript
const ProtectedRoute = ({ children }: { children: ReactNode }) => {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/" replace />;
  return <>{children}</>;
};
```

### 10.3 Important: What MUST NOT Change

These are fixed architectural decisions. Never suggest alternatives:
1. **Shadow DOM for widget** — cannot change to iframe or vanilla injection
2. **Razorpay for payments** — cannot change to Stripe (Indian regulations)
3. **Qwen 2.5-7B as base LLM** — do not suggest changing unless GPU constraint is proven
4. **SQLite for local dev** — do not add Docker requirement for local dev
5. **Per-tenant Pinecone namespaces** — data isolation is a compliance requirement
6. **<100ms crisis detection** — this is a hard safety requirement

---

## SECTION 11 — KNOWN TODOS AND PRIORITY TASKS

### P0 — Blocking for Investor Demo

| File | Description | Complexity |
|------|-------------|------------|
| `services/therapeutic_ai_service.py` | Complete `_detect_patient_stage()` — query Patient DB, return stage int | Low |
| `services/therapeutic_ai_service.py` | Persist `ChatMessage` to DB after each AI response | Low |
| `services/chatbot_service.py` | Load `current_step` from DB session instead of hardcoded 0 | Low |
| `services/crisis_detection_service.py` | Complete `escalate()` — call WebSocket manager + SendGrid | Medium |
| `routes/auth_routes.py` | DB query for clinician login instead of mock | Low |
| `routes/widget_routes.py` | DB lookup by `widget_token` to return real config | Low |
| `client/src/contexts/AuthContext.tsx` | Call `GET /users/me` after login to populate user state | Low |
| `client/src/components/clinician/ClinicianDashboard.tsx` | Wire API calls — load real patient list | Medium |
| `client/src/hooks/useChat.ts` | Connect to real WebSocket endpoint | Medium |

### P1 — Demo Polish

| Feature | File | Description |
|---------|------|-------------|
| Razorpay E2E test | `services/payment_service.py` | Test mode end-to-end flow |
| Google Calendar | `services/calendar_service.py` | OAuth token storage + event creation |
| Real analytics | `services/analytics_service.py` | Aggregate session metrics |
| Patient list | `api/leads.py` | List + filter patients by stage |
| Assessment flow | `routes/assessment_routes.py` | Complete frontend-to-backend wiring |

### P2 — Production Readiness

| Task | File | Description |
|------|------|-------------|
| Rate limiting | `middleware/rate_limit_middleware.py` | Redis sliding window algorithm |
| DB migrations | `alembic/versions/` | Run `alembic revision --autogenerate` |
| Redis session | `services/redis_session_service.py` | Full session persistence |
| Dropout cron | `main.py` APScheduler | APScheduler job calling dropout_service |
| Audit log table | `models.py` | Add `audit_logs` table for HIPAA |
| Widget session table | `models.py` | Add `widget_sessions` table |
| Admin auth guard | `api/tenants.py` | Role-based access for admin endpoints |
| Fix RAG sync issue | `services/rag_service.py` | Wrap SentenceTransformer in run_in_executor |

---

## SECTION 12 — ENVIRONMENT SETUP (DEVELOPER QUICK START)

### 12.1 Minimum Local Setup (no Docker, no GPU)

```powershell
# 1. Clone and enter repo
cd "c:\saath ai prototype"

# 2. Backend setup
cd therapeutic-copilot\server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Create .env file
cp .env.example .env
# Edit .env, set at minimum:
# TOGETHER_API_KEY=your-key-from-together.ai
# JWT_SECRET_KEY=any-long-random-string-32-chars

# 4. Init database with demo data
python scripts/setup_db.py --seed
# Creates: tenant "MindWell Clinic", widget_token for testing

# 5. Start backend
uvicorn main:app --reload --port 8000
# API docs at: http://localhost:8000/docs

# 6. Frontend (separate terminal)
cd ../client
npm install
npm run dev
# App at: http://localhost:5173
```

### 12.2 Full Local Setup with GPU (RTX 5060 8GB)

```powershell
# Assumes Ollama already installed and running
# Pull the model if not already done
ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text

# For backend to use local Ollama instead of Together AI,
# set in .env:
# LLAMA_CPP_SERVER_URL=http://localhost:11434  (Ollama's API endpoint)
# Or for native llama-cpp-python:
# LLAMA_CPP_PYTHON_MODEL_PATH=C:\Users\B P Verma\AppData\Local\ollama\models\qwen2.5-coder.gguf
```

### 12.3 Running Tests

```powershell
cd "c:\saath ai prototype\therapeutic-copilot"
pip install pytest pytest-asyncio httpx

# All tests
pytest tests/ -v

# Crisis detection speed test
pytest tests/test_crisis_detection.py::test_scan_speed -v
# Expected: <100ms per scan

# Chat integration
pytest tests/test_chat.py -v
```

---

## SECTION 13 — CULTURAL AND CLINICAL CONTEXT

### 13.1 Indian Patient Context (CRITICAL for AI responses)

The AI MUST be aware of Indian cultural specifics when generating therapeutic responses:

**Family dynamics**:
- Joint family living is common — patients may face pressure from in-laws, parents
- "Log kya kahenge" (what will people say) — family reputation concerns
- Parents/spouse may oppose therapy — normalise help-seeking

**Mental health stigma in India**:
- Many patients have never spoken to a professional before
- Mental illness is often associated with weakness or spiritual failure
- AI must never shame the patient for their feelings or for seeking help

**Common presenting problems (Indian context)**:
- Career pressure (IIT/IIM expectations, job insecurity)
- Arranged marriage stress and relationship issues
- Urban loneliness / disconnection from roots
- Academic pressure (competitive exams — JEE, UPSC, NEET)
- Economic stressors (EMIs, family financial responsibilities)

**Language**:
- Many patients use Hinglish (Hindi-English code-switching)
- Examples: "Main bahut stressed hoon", "Bohot mushkil ho raha hai"
- AI must respond in the same language register the patient uses
- If patient writes in Hindi, respond in Hindi
- If patient writes in Hinglish, respond in Hinglish

**Cultural sensitivity in crisis situations**:
- Religious self-harm ("God is punishing me") requires spiritual sensitivity
- Do NOT immediately medicalize — first acknowledge the spiritual distress
- Always involve family support when appropriate but not when family IS the stressor

### 13.2 CBT Protocol Adaptation for Indian Context

Standard Western CBT requires adaptation:
- **Rapport building takes longer** — Indian patients expect more small talk before disclosing
- **Family homework** — include family members in behavioral activation exercises when appropriate
- **Collectivist framing** — "How will getting better help your family?" works better than
  purely individualistic framing
- **Hierarchy awareness** — patients may defer to the AI as "doctor" — correct this gently
  ("I'm here to support you, not give orders — what feels right to you?")

---

## SECTION 14 — SECURITY REQUIREMENTS (HIPAA / GDPR / DPDP)

### 14.1 Data Protection Laws

This application must comply with:
- **HIPAA** (if serving US-based orgs): PHI encryption, audit logs, BAA agreements
- **GDPR** (if serving EU patients): Right to erasure, data portability, DPA agreements
- **India DPDP Act 2023**: Consent framework, data fiduciaries, breach notification

### 14.2 Security Checklist for Every PR

- [ ] **No real patient data in logs** — only `patient_id` (UUID), never name/phone/email
- [ ] **Multi-tenant isolation** — every query filters by `tenant_id`
- [ ] **JWT expiry** — access tokens expire in 30 minutes, refresh in 7 days
- [ ] **Rate limiting** — all public endpoints must be rate-limited
- [ ] **Input validation** — all request bodies validated by Pydantic schemas
- [ ] **HMAC verification** — Razorpay webhooks must verify signature before processing
- [ ] **Password hashing** — always bcrypt, never plaintext or MD5/SHA1
- [ ] **CORS** — only allow origins from `settings.cors_origins_list`
- [ ] **No hardcoded secrets** — all secrets via environment variables only

### 14.3 Sensitive Data Handling

- Patient messages are stored in `chat_messages.content` — consider encryption at rest
- `clinicians.hashed_password` — bcrypt hash, never the original password
- `clinicians.google_calendar_token` — should be encrypted before storing (TODO)
- Phone numbers and emails — PII, must not appear in log files

---

## SECTION 15 — COMMON DEVELOPER QUESTIONS AND ANSWERS

**Q: How do I add a new API endpoint?**
A: 1) Add the Pydantic schema in `models/schemas.py`. 2) Add the route in the appropriate file under
`routes/` or `api/`. 3) Register the router in `main.py` if it's a new file.
4) Add tests in `tests/`.

**Q: How do I add a new ML classifier?**
A: 1) Create `services/new_classifier_service.py` following the same `get_*_service()` singleton
pattern. 2) Add warmup in `main.py` lifespan. 3) Call it in `therapeutic_ai_service.py` pipeline.
4) Build the context block injected into system prompt.

**Q: How do I change the LLM from Together AI to a different model?**
A: Change `TOGETHER_MODEL` in `.env`. The model must be available on Together AI's API.
Do not change the API call structure in `qwen_inference.py` — it follows OpenAI-compatible format.

**Q: How do I add a new tenant (clinic)?**
A: `POST /api/v1/tenants` with admin token. Or for development:
```python
python scripts/setup_db.py --seed  # Creates demo tenant
# Then use generate_widget_token.py to get their embed token
```

**Q: How do I debug the AI not responding?**
A: Check in order: 1) Is `TOGETHER_API_KEY` set? 2) Is Together AI API reachable (httpx timeout)?
3) Check loguru logs for `QwenInferenceService`. 4) Test endpoint directly:
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Authorization: Bearer TOKEN" \
  -d '{"session_id": "...", "message": "Hello"}'
```

**Q: The crisis detection is triggering false positives — what do I do?**
A: The keyword weights are hardcoded in `crisis_detection_service.py`. Lower the weight of
the problematic keyword OR increase the crisis score threshold in `config.py`.
Never disable crisis detection entirely.

**Q: How do I run just the backend without the frontend?**
A: `uvicorn main:app --reload --port 8000` from the `server/` directory.
The Swagger UI at `http://localhost:8000/docs` lets you test all API endpoints directly.

**Q: How do I deploy a new version to production?**
A: Currently: `git pull` on E2E Networks server + `docker compose up --build -d`.
Set up proper CI/CD (GitHub Actions → SSH deploy) as a P2 task.

**Q: Where do I put the LoRA model weights after training?**
A: Create a `models/` directory in `therapeutic-copilot/server/` (gitignored).
Set `LLAMA_CPP_PYTHON_MODEL_PATH` in `.env` to point to the GGUF file.
The `lora_model_service.py` handles adapter switching at runtime.

**Q: How does the dropdown/re-engagement work?**
A: APScheduler runs `dropout_service.scan_inactive_patients()` daily at 09:00 UTC.
It queries for patients with `last_active` > 7 days and `stage = ACTIVE`.
For each patient, it calls `dropout_service.send_reengagement()` which triggers
the Stage 3 conversation flow. Message personalised based on dropout duration.

---

## SECTION 16 — BUSINESS CONTEXT FOR CTO DECISIONS

### 16.1 Investor Demo Requirements (Current Priority)

The prototype must demonstrate these capabilities for investors:
1. A patient opens the widget on a clinic's test site → sees greeting → chats
2. The AI correctly routes Stage 1 vs Stage 2
3. A crisis message triggers a real-time alert on the clinician dashboard
4. An assessment is completed and scored
5. Razorpay payment modal works (test mode OK)
6. Clinician sees the patient's conversation history

### 16.2 Technical Debt Log

| Item | Impact | Estimated Fix Time |
|------|--------|--------------------|
| Rate limiting not implemented | Security risk | 4 hours |
| No database migrations yet | Cannot deploy safely | 2 hours |
| RAG sync/async bug | Slight event loop blocking | 1 hour |
| No audit logs table | HIPAA non-compliance | 3 hours |
| Google Calendar token not encrypted | Security risk | 2 hours |
| No CI/CD pipeline | Manual deploys risk | 8 hours |
| No monitoring/alerting | Blind to prod issues | 4 hours |

### 16.3 Key Business Rules (Never Change)

1. **Stage 1 AI must never claim to be a therapist** — always say "I'm Saathi, a supportive AI companion"
2. **Stage 2 AI always defers major decisions to the human clinician** — "Let's discuss this with your therapist"
3. **Crisis detected → always human escalation** — AI never handles crisis alone
4. **Patient data stays in India** — only E2E Networks Mumbai, no AWS/GCP outside India
5. **Widget token per clinic** — one token per subdomain/site; tenant isolation enforced

### 16.4 Roadmap (After Investor Demo)

| Phase | Feature | Quarter |
|-------|---------|---------|
| V1.1 | Hindi voice input/output | Q2 2026 |
| V1.2 | Group therapy sessions (multiple patients, 1 clinician) | Q2 2026 |
| V2.0 | Diagnostic report generation (PDF for clinicians) | Q3 2026 |
| V2.1 | Insurance integration (cashless therapy billing) | Q3 2026 |
| V3.0 | Regional language support (Tamil, Telugu, Bengali) | Q4 2026 |

---

## SECTION 17 — QUICK REFERENCE CHEAT SHEET

### Most Important Files to Know

| If you need to... | Look in this file |
|-------------------|-------------------|
| Change AI response behavior | `services/therapeutic_ai_service.py` |
| Change prompt for the LLM | `services/chatbot_service.py` |
| Change crisis thresholds | `services/crisis_detection_service.py` + `config.py` |
| Add a new API endpoint | `routes/` + `main.py` router registration |
| Change database schema | `models.py` + run Alembic migration |
| Change frontend route | `client/src/App.tsx` |
| Change API base URL | `client/src/lib/api.ts` |
| Change env vars | `config.py` + `.env` file |
| Fix the LLM not responding | `services/qwen_inference.py` |
| Debug a payment issue | `services/payment_service.py` |
| Check what's running at startup | `main.py` (lifespan function) |
| Change widget appearance | `widget/src/components/ChatBubble.tsx` |
| Change CBT step logic | `services/chatbot_service.py` (11-step state machine) |
| Run the assessment | `services/assessment_service.py` |

### Data Flow for a Patient Message

```
Patient types a message
       ↓
widget.bundle.js → POST /api/v1/widget/message
       ↓
widget_routes.py → TherapeuticAIService.process_message()
       ↓
crisis_detection_service.scan() → [if crisis: escalate + alert]
       ↓  (parallel)
emotion_classifier + intent_classifier + topic_classifier
       ↓
rag_service.query() → 5 relevant knowledge chunks
       ↓
chatbot_service.build_system_prompt() → 1500-char system prompt
       ↓
qwen_inference.generate() → LLM response (~100-300 tokens)
       ↓
ChatMessage persisted to DB
       ↓
Response returned via WebSocket to patient widget
```

---

*Document Version: 1.0*
*Last Updated: March 2026*
*Prepared for: Local LLM fine-tuning as CTO for Saathi AI*
*Company: RYL NEUROACADEMY PRIVATE LIMITED*
*Total Technical Scope: 10 ML models, 21 services, 9 route modules, React frontend, embeddable widget*
