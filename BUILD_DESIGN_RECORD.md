# SAATHI AI — Complete Build & Design Record
## RYL NEUROACADEMY PRIVATE LIMITED
### Autonomous AI-Driven Development Log | March 2026

---

> **Purpose**: This document captures every design decision, architectural choice, code
> implementation, and technical rationale made during the autonomous AI-driven build of
> the SAATHI AI Therapeutic Co-Pilot prototype. It serves as a reference for investors,
> developers, and technical reviewers.

---

## TABLE OF CONTENTS

1. [Product Identity](#1-product-identity)
2. [Tech Stack — Full Decisions Log](#2-tech-stack--full-decisions-log)
3. [Database Design](#3-database-design)
4. [Session 1 — 2026-03-06 — Full Scaffold (87 files)](#4-session-1--2026-03-06--full-scaffold)
5. [Session 2 — 2026-03-07 — P0 Core Pipeline](#5-session-2--2026-03-07--p0-core-pipeline)
6. [Session 3 — 2026-03-07 — P1 Demo Polish](#6-session-3--2026-03-07--p1-demo-polish)
7. [Session 4 — 2026-03-07 — Watcher Fixes](#7-session-4--2026-03-07--watcher-fixes)
8. [Session 5 — 2026-03-08 — P2 Production Readiness](#8-session-5--2026-03-08--p2-production-readiness)
9. [AI Pipeline Architecture](#9-ai-pipeline-architecture)
10. [API Surface Map](#10-api-surface-map)
11. [Security Design](#11-security-design)
12. [Autonomous Coding Workflow](#12-autonomous-coding-workflow)

---

## 1. PRODUCT IDENTITY

| Field | Value |
|-------|-------|
| Product | SAATHI AI — Therapeutic Co-Pilot |
| Company | RYL NEUROACADEMY PRIVATE LIMITED |
| Model | B2B SaaS — sold to mental health clinics |
| GitHub | https://github.com/cpdoryl/SAATHI-AI-PROTOTYPE |
| Local Path | `c:/saath ai prototype/` |
| Branch | `main` |
| Started | March 6, 2026 |
| Build Method | Autonomous AI agent (Claude Sonnet 4.6) via GitHub command board |

### What It Does
Saathi AI is an embeddable chat widget that sits on a clinic's website. Patients chat with
an AI therapeutic co-pilot. Clinicians get a real-time dashboard showing patient stage,
crisis alerts, and session history. The AI routes conversations through 3 therapeutic stages.

---

## 2. TECH STACK — FULL DECISIONS LOG

### Backend
| Choice | Technology | Why This, Not Alternatives |
|--------|-----------|---------------------------|
| Framework | **FastAPI (Python 3.11)** | Native async (`async/await`) for WebSocket + SSE. Auto-generates OpenAPI docs at `/docs`. 3x faster than Django REST for IO-bound workloads. Pydantic v2 for request validation |
| ASGI Server | **Uvicorn** | Production-grade ASGI server. Works with Gunicorn workers for multi-process prod deployment |
| ORM | **SQLAlchemy 2.0 (async)** | `AsyncSession` + `async with` context managers. No sync DB calls blocking the event loop |
| Auth | **python-jose (JWT) + bcrypt** | JWT for stateless auth (scales across instances). bcrypt for password hashing (cost factor 12, not MD5/SHA) |

### Frontend
| Choice | Technology | Why |
|--------|-----------|-----|
| Framework | **React 18** | Concurrent rendering, Suspense. Industry standard |
| Language | **TypeScript** | Type safety prevents runtime bugs in patient-facing UI |
| Build Tool | **Vite** | 10x faster HMR than CRA. ES modules native |
| Styling | **Tailwind CSS** | Utility-first, no CSS file bloat, easy theming per clinic |
| State | **React Context** | Simple enough for this scale; no Redux overhead |

### AI Model
| Choice | Technology | Why |
|--------|-----------|-----|
| Production model | **Qwen 2.5-7B GGUF via llama.cpp** | Self-hosted on E2E Networks Mumbai. Indian data sovereignty — patient data never leaves India. 7B parameters fits 16GB VRAM. GGUF quantization (Q4_K_M) reduces VRAM to ~5GB |
| Dev/staging model | **Together AI cloud API** | No GPU needed during development. Same Qwen 2.5-7B model. `TOGETHER_API_KEY` in `.env` |
| Inference routing | Priority: native llama-cpp-python → Together AI → llama.cpp HTTP | Automatic failover. Production uses native bindings (no HTTP overhead). Dev uses cloud |
| Therapeutic fine-tuning | **LoRA adapters** | Stage 1: r=8, 634 examples (lead generation). Stage 2: r=16, 3,017 examples (therapy). Low GPU memory vs full fine-tune |

### Data Layer
| Choice | Technology | Why |
|--------|-----------|-----|
| Primary DB (prod) | **PostgreSQL** | ACID compliance. JSON columns for flexible AI insights. Mature ecosystem |
| Primary DB (dev) | **SQLite** | Zero-config local development |
| Cache | **Redis 7** | Session state (4h TTL), rate limiting (sorted sets), pub/sub for WebSocket events |
| Vector DB | **Pinecone** | Per-tenant namespaces for RAG. 384-dim embeddings (all-MiniLM-L6-v2). SaaS — no infra to manage |

### Integrations
| Service | Purpose | Why |
|---------|---------|-----|
| **Razorpay** | Appointment payments | India-first, INR native, UPI support. NOT Stripe (no INR, high fees in India) |
| **Google Calendar** | Appointment booking | Clinicians already use Google Calendar. OAuth 2.0 token stored encrypted in DB |
| **SendGrid** | Crisis emails | Transactional email for crisis escalation alerts to clinicians |
| **Pinecone** | RAG knowledge base | Per-tenant clinic knowledge (CBT protocols, clinic policies) |

### Infrastructure
| Layer | Choice | Why |
|-------|--------|-----|
| Cloud | **E2E Networks Mumbai** | Indian data sovereignty requirement. HIPAA-adjacent compliance for health data |
| Widget delivery | **Shadow DOM + Custom Elements** | Zero style conflicts with any host website CSS. Embeds with one `<script>` tag |
| Migrations | **Alembic** | SQLAlchemy-native. Version-controlled schema changes |
| Job scheduling | **APScheduler** | Async-compatible. No separate Celery/Redis worker needed for daily cron |

---

## 3. DATABASE DESIGN

**7 tables, designed for multi-tenant B2B SaaS.**

### Entity Relationship Summary
```
Tenant (clinic)
  ├── Clinician (doctor/therapist) [M]
  └── Patient [M]
        ├── TherapySession [M]
        │     └── ChatMessage [M]
        ├── Assessment [M]
        └── Appointment [M]
                └── Clinician (FK)
```

### Table Designs

#### `tenants` — One row per clinic
```python
id              String (UUID)   PK
name            String(255)     Clinic name
domain          String(255)     UNIQUE — e.g. "apollo.saathai.in"
widget_token    String(255)     UNIQUE — used to authenticate widget embeds
plan            String(50)      "basic" | "professional" | "enterprise"
pinecone_namespace String       Per-tenant RAG namespace in Pinecone
razorpay_account_id String      For payment splits (future)
```
**Decision**: `widget_token` is separate from user auth tokens. Each clinic gets one
unique token embedded in their `<script>` tag. Validated on every widget request.

#### `clinicians` — Therapists/doctors
```python
id                  String (UUID)   PK
tenant_id           FK → tenants
email               String UNIQUE
hashed_password     String          bcrypt hash, cost=12
google_calendar_token Text          Encrypted OAuth2 token JSON
```
**Decision**: `google_calendar_token` stored as encrypted Text column (not separate table)
for simplicity at this stage. In production, move to a dedicated `oauth_tokens` table.

#### `patients` — The end-users
```python
stage               Enum: LEAD | ACTIVE | DROPOUT | ARCHIVED
language            String(10)      "en" | "hi" | "ta" etc.
cultural_context    String(50)      For culturally-aware AI responses
dropout_risk_score  Float           0.0–1.0, computed daily by APScheduler
last_active         DateTime        Updated on every chat message
```
**Decision**: `stage` drives which AI LoRA adapter is used. LEAD → Stage 1 adapter.
ACTIVE → Stage 2 adapter. DROPOUT → Stage 3 re-engagement.

#### `therapy_sessions`
```python
stage           Integer     1, 2, or 3 (maps to AI adapter)
current_step    Integer     0–11 for Stage 2 (11-step structured protocol)
crisis_score    Float       Max crisis severity seen in this session
status          Enum: PENDING | IN_PROGRESS | COMPLETED | CRISIS_ESCALATED
```
**Decision**: `current_step` tracks position in the Stage 2 CBT protocol. The AI prompt
changes at each step (e.g., step 0 = rapport building, step 5 = cognitive restructuring).

#### `chat_messages`
```python
role                    String(20)  "user" | "assistant"
crisis_keywords_detected JSON       List of detected keywords + weights
```
**Decision**: Crisis keywords stored per-message for audit trail. Required for clinical
compliance and post-incident review.

#### `assessments`
```python
assessment_type String(20)  "PHQ-9" | "GAD-7" | "PCL-5" | "ISI" | etc.
responses       JSON        Raw answer array
score           Float       Computed score
severity        String(50)  "minimal" | "mild" | "moderate" | "severe"
```
**Supported**: PHQ-9, GAD-7, PCL-5, ISI, OCI-R, SPIN, PSS, WHO-5

---

## 4. SESSION 1 — 2026-03-06 — FULL SCAFFOLD

**Timestamp**: 2026-03-06
**Commits**: Initial commits (multiple)
**Method**: Claude Sonnet 4.6 interactive session
**Output**: 87 files, 7,019 lines of code

### What Was Built

#### Folder Structure Created
```
c:/saath ai prototype/
├── therapeutic-copilot/
│   ├── server/                     # FastAPI backend
│   │   ├── main.py                 # App entry, middleware, routers
│   │   ├── config.py               # Pydantic settings from .env
│   │   ├── database.py             # SQLAlchemy async engine + session
│   │   ├── models.py               # All 7 ORM models
│   │   ├── routes/                 # HTTP route handlers
│   │   │   ├── auth_routes.py      # /api/v1/auth/*
│   │   │   ├── chat_routes.py      # /api/v1/chat/*
│   │   │   ├── assessment_routes.py
│   │   │   ├── crisis_routes.py
│   │   │   ├── rag_routes.py
│   │   │   ├── widget_routes.py
│   │   │   ├── payment_routes.py
│   │   │   ├── websocket_routes.py
│   │   │   └── calendar_routes.py
│   │   ├── api/                    # Resource CRUD endpoints
│   │   │   ├── tenants.py
│   │   │   ├── users.py
│   │   │   ├── leads.py
│   │   │   ├── appointments.py
│   │   │   └── patients.py
│   │   ├── services/               # Business logic layer
│   │   │   ├── therapeutic_ai_service.py   # MAIN ORCHESTRATOR
│   │   │   ├── crisis_detection_service.py
│   │   │   ├── rag_service.py
│   │   │   ├── qwen_inference.py
│   │   │   ├── chatbot_service.py
│   │   │   ├── payment_service.py
│   │   │   ├── assessment_service.py
│   │   │   ├── websocket_manager.py
│   │   │   ├── redis_session_service.py
│   │   │   └── dropout_service.py
│   │   ├── middleware/
│   │   │   └── rate_limit_middleware.py
│   │   └── tests/
│   │       ├── test_chat.py
│   │       ├── test_crisis.py
│   │       └── test_assessments.py
│   ├── client/                     # React frontend
│   │   └── src/
│   │       ├── components/
│   │       │   ├── clinician/ClinicianDashboard.tsx
│   │       │   ├── patient/PatientPortal.tsx
│   │       │   ├── chatbot/ChatWidget.tsx
│   │       │   ├── payment/PaymentFlow.tsx
│   │       │   ├── landing/LandingPage.tsx
│   │       │   └── admin/AdminPanel.tsx
│   │       ├── contexts/AuthContext.tsx
│   │       ├── hooks/useChat.ts
│   │       └── lib/api.ts
│   └── widget/                     # Embeddable Shadow DOM widget
│       └── src/
│           ├── widget.ts           # Custom Element + Shadow DOM
│           └── components/ChatBubble.tsx
├── github_watcher.py               # Autonomous task runner
├── start_watcher.bat               # Windows launcher
├── TASKS.md                        # GitHub command board
├── DEVELOPER_GUIDE.md              # Living build log
├── CLAUDE_REMOTE.md                # Watcher workflow guide
└── RESULTS.md                      # Smoke test results
```

### Key Design Decision: Service Layer Architecture
All business logic lives in `services/`, not in route handlers.
Routes are thin: validate input → call service → return response.
This makes services independently testable without HTTP.

---

## 5. SESSION 2 — 2026-03-07 — P0 CORE PIPELINE

**Timestamp**: 2026-03-07
**Trigger**: GitHub TASKS.md edits → autonomous watcher
**Commits**: 9 commits pushed automatically

### P0.1 — `_detect_patient_stage()`
**File**: `therapeutic-copilot/server/services/therapeutic_ai_service.py`
**Problem**: Was returning a hardcoded `PatientStage.LEAD` placeholder.
**Solution**: Real async SQLAlchemy query against `patients` table.

```python
async def _detect_patient_stage(self, patient_id: str) -> int:
    result = await self.db.execute(
        select(Patient).where(Patient.id == patient_id)
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        return 1  # Default: Stage 1 (lead generation)
    stage_map = {
        PatientStage.LEAD: 1,
        PatientStage.ACTIVE: 2,
        PatientStage.DROPOUT: 3,
    }
    return stage_map.get(patient.stage, 1)
```
**Decision**: Unknown patients default to Stage 1 (safest — non-therapeutic lead mode).

---

### P0.2 — TherapySession Persistence
**File**: `therapeutic-copilot/server/services/therapeutic_ai_service.py`
**Problem**: Session was created in memory only, never saved to DB.
**Solution**: `db.add(session)` → `await db.commit()` → `await db.refresh(session)`

**Pattern used**: SQLAlchemy async unit-of-work pattern.
`db.refresh(session)` re-reads from DB after commit to populate server-generated fields (timestamps, etc).

---

### P0.3 — Auth /login Route
**File**: `therapeutic-copilot/server/routes/auth_routes.py`
**Problem**: Route was returning a placeholder JWT.
**Solution**: Real DB lookup + bcrypt verify + JWT generation.

```python
# Query clinician by email
result = await db.execute(select(Clinician).where(Clinician.email == payload.email))
clinician = result.scalar_one_or_none()
if not clinician:
    raise HTTPException(401, "Invalid credentials")

# bcrypt verify (timing-safe)
if not bcrypt.checkpw(payload.password.encode(), clinician.hashed_password.encode()):
    raise HTTPException(401, "Invalid credentials")

# JWT with 24h expiry
token = jose.jwt.encode(
    {"sub": clinician.id, "tenant_id": clinician.tenant_id, "exp": ...},
    settings.SECRET_KEY, algorithm="HS256"
)
```
**Decision**: Same error message for "user not found" and "wrong password" — prevents
user enumeration attacks.

---

### P0.4 — ChatMessage Persistence
**File**: `therapeutic-copilot/server/services/therapeutic_ai_service.py`
**Solution**: Both user and assistant messages persisted in `process_message()`:

```python
user_msg = ChatMessage(session_id=session_id, role="user", content=message,
                       crisis_keywords_detected=crisis_result.get("detected_keywords", []))
self.db.add(user_msg)
# ... AI generates response ...
ai_msg = ChatMessage(session_id=session_id, role="assistant", content=response)
self.db.add(ai_msg)
await self.db.commit()
```
**Decision**: Crisis keywords stored with each user message for clinical audit trail.

---

### P0.5 — Crisis Escalation
**File**: `therapeutic-copilot/server/services/crisis_detection_service.py`
**Algorithm**: Weighted keyword scan, `<100ms` target.

```
severity = max_keyword_weight + min(2.0, cumulative_weight * 0.1)
```

**30+ keywords** across 3 tiers:
- Immediate danger (weight 9–10): "kill myself", "suicide", "hang myself"
- High risk (weight 6–8): "no reason to live", "better off dead"
- Moderate (weight 3–5): "can't cope", "overwhelmed"
- **Multilingual/Hinglish**: "mar jaana chahta", "jeena nahi chahta", "zindagi khatam"

**Escalation** (severity ≥ 7.0): Session status → `CRISIS_ESCALATED`, WebSocket alert
to clinician room, emergency helplines returned to patient:
- iCall: +91-9152987821
- Vandrevala Foundation: 1860-2662-345
- NIMHANS: 080-46110007

---

### P0.6 — Widget Token Validation
**File**: `therapeutic-copilot/server/routes/widget_routes.py`
**Solution**: Real DB lookup against `tenants.widget_token` column.

```python
result = await db.execute(
    select(Tenant).where(Tenant.widget_token == token, Tenant.is_active == True)
)
tenant = result.scalar_one_or_none()
```

---

### P0.7 — Smoke Test (10/10 PASS)
**File**: `RESULTS.md` (auto-generated)
**Method**: pytest + direct async service calls
**Result**: All 7 P0 items verified working in isolation.

---

## 6. SESSION 3 — 2026-03-07 — P1 DEMO POLISH

**Timestamp**: 2026-03-07
**Commits**: 5 commits

### P1.1 — Razorpay Sandbox Test (4/4 PASS)
**Files**: `payment_service.py`, `payment_routes.py`, `client/index.html`
**Tests**:
1. Order creation returns `order_id`, `amount_paise`, `key_id`
2. HMAC-SHA256 signature verification (fixed `hmac.new` → `hmac.HMAC`)
3. Tamper detection (modified signature fails)
4. End-to-end API: POST `/api/v1/payments/create-order` → verify response

**Decision**: Amounts stored in **paise** (1 INR = 100 paise) — Razorpay's required unit.
HMAC computed as: `RAZORPAY_ORDER_ID|RAZORPAY_PAYMENT_ID` signed with `RAZORPAY_KEY_SECRET`.

---

### P1.2 — Google Calendar OAuth
**Files**: `services/calendar_service.py`, `routes/calendar_routes.py`
**Flow**:
1. Clinician hits `GET /api/v1/calendar/auth-url` → gets Google OAuth URL
2. Google redirects to `GET /api/v1/calendar/callback?code=...`
3. Token exchanged, stored encrypted in `clinicians.google_calendar_token`
4. `POST /api/v1/calendar/events` creates event via Google Calendar API

**Decision**: Token stored in `Clinician` model (not separate table) for MVP.
Encrypt at rest using `CALENDAR_TOKEN_SECRET` from `.env`.

---

### P1.3 — ClinicianDashboard Real API
**Files**: `client/src/components/clinician/ClinicianDashboard.tsx`, `api/patients.py`
**Problem**: Dashboard showed empty arrays `[]` hardcoded.
**Solution**: `useEffect` on mount → `GET /api/v1/patients` → renders patient list with
name, stage, `last_active`, and `dropout_risk_score` badge.

**New endpoint created**: `GET /api/v1/patients` returns all patients for the
authenticated clinician's tenant.

---

### P1.4 — Assessment Flow Frontend
**Files**: `client/src/components/patient/PatientPortal.tsx`, `server/routes/assessment_routes.py`
**Flow**:
1. `GET /api/v1/assessments/types` → list PHQ-9, GAD-7, etc.
2. `GET /api/v1/assessments/{type}/questions` → render question form
3. `POST /api/v1/assessments/{patient_id}/submit` → returns `score` + `severity`
4. Display result: "PHQ-9 Score: 14 — Moderate Depression"

**Supported instruments**: PHQ-9, GAD-7, PCL-5, ISI, OCI-R, SPIN, PSS, WHO-5

---

### P1.5 — Real Token Streaming (SSE)
**File**: `services/qwen_inference.py`
**Problem**: Previous implementation split response string by spaces — fake streaming.
**Solution**: True Server-Sent Events from Together AI:

```python
async with client.stream("POST", together_url, json={..., "stream": True}) as resp:
    async for line in resp.aiter_lines():
        if line.startswith("data: "):
            chunk = json.loads(line[6:])
            token = chunk["choices"][0]["delta"].get("content", "")
            if token:
                yield token
```

3-path routing implemented:
- `LLAMA_CPP_PYTHON_MODEL_PATH` set → native llama-cpp-python (production)
- `TOGETHER_API_KEY` set → Together AI SSE (development)
- Neither → llama.cpp HTTP server

---

## 7. SESSION 4 — 2026-03-07 — WATCHER FIXES

**Timestamp**: 2026-03-07
**Type**: Infrastructure (autonomous workflow fixes)

### Fix 1 — Claude CLI Path
**File**: `github_watcher.py`
**Problem**: `subprocess.run(["claude", ...])` fails on Windows — Python subprocess
doesn't search `PATH` the same way as PowerShell.
**Solution**: Hardcoded full path:
```python
claude_cmd = r"C:\Users\B P Verma\AppData\Roaming\npm\claude.cmd"
```

### Fix 2 — Flag Name Change
**Problem**: `--dangerouslySkipPermissions` (camelCase) rejected by Claude Code v2.1.71.
**Solution**: Correct flag is `--dangerously-skip-permissions` (kebab-case).

### Fix 3 — Prompt via stdin
**Problem**: Large multi-line prompt passed as CLI argument was getting dropped on Windows
(Windows cmd.exe has 8191-char command line limit).
**Solution**: Pass prompt via stdin using `input=prompt` in `subprocess.run`:
```python
result = subprocess.run(
    [claude_cmd, "--dangerously-skip-permissions", "--print", ...],
    input=prompt,   # stdin instead of CLI arg
    text=True,
    timeout=3600,
)
```

### Fix 4 — P2 Task Filter
**Problem**: Watcher was hardcoded to stop at `## P2` section.
**Solution**: Watcher now reads P0, P1, and P2 sections. Stops at `## STANDING INSTRUCTIONS`.

---

## 8. SESSION 5 — 2026-03-08 — P2 PRODUCTION READINESS

**Timestamp**: 2026-03-08
**Commits**: 6 commits (all autonomous)

### P2.1 — Redis Sliding-Window Rate Limiter
**File**: `therapeutic-copilot/server/middleware/rate_limit_middleware.py`
**Algorithm**: Redis sorted-set sliding window (not token bucket — more accurate).

**How it works**:
```
Key: ratelimit:{client_ip}:{route_prefix}
1. ZREMRANGEBYSCORE key 0 (now - window_seconds)  → remove old entries
2. ZCARD key                                        → count current window
3. If count >= limit → HTTP 429 Too Many Requests
4. ZADD key {timestamp: timestamp}                 → record this request
5. EXPIRE key window_seconds                        → auto-cleanup
```

**3 tiers**:
```python
("/api/v1/chat", 10, 60)   # 10 req/min — AI is expensive
("/api/v1/auth", 20, 60)   # 20 req/min — brute force guard
("",             60, 60)   # 60 req/min — default
```

**Fail-open design**: If Redis is unreachable, requests are allowed through.
Decision: Patient care continuity > strict rate limiting.

**Response headers added**:
```
X-RateLimit-Limit: 10
X-RateLimit-Window: 60
Retry-After: 60  (on 429)
```

---

### P2.2 — Alembic Database Migration
**Files**: `therapeutic-copilot/server/alembic.ini`, `alembic/env.py`, `alembic/versions/`
**Command run**:
```bash
alembic revision --autogenerate -m "initial"
```
**Result**: Migration file generated for all 7 tables:
- `tenants`, `clinicians`, `patients`, `therapy_sessions`,
  `chat_messages`, `assessments`, `appointments`

**Decision**: Alembic used instead of `Base.metadata.create_all()` for production.
`create_all()` left in `main.py` lifespan for local dev convenience only.

---

### P2.3 — Redis Session State Management
**File**: `therapeutic-copilot/server/services/redis_session_service.py`
**Problem**: Session state (stage, current_step) was stored in a Python in-memory dict.
This fails when running multiple Uvicorn workers (each worker has its own dict).

**Solution**: `RedisSessionService` singleton with SETEX (SET + EXpire):
```python
await client.setex(
    f"session:{session_id}",
    SESSION_TTL,           # 4 hours
    json.dumps(state),     # {"patient_id", "tenant_id", "stage", "current_step", "status"}
)
```

**4 operations**:
- `set_session(id, state)` — create/overwrite with TTL
- `get_session(id)` → `dict | None` — read from cache
- `update_step(id, new_step)` — atomic step increment
- `refresh_ttl(id)` — extend TTL on every message

**Decision**: TTL = 4 hours. Therapy sessions rarely exceed 90 minutes.
Expired sessions fall back to DB query gracefully.

---

### P2.4 — APScheduler Dropout Re-engagement Cron
**Files**: `therapeutic-copilot/server/main.py`, `services/dropout_service.py`
**Schedule**: Daily at 09:00 UTC (14:30 IST — morning working hours)

**Registered in `lifespan` (startup)**:
```python
scheduler.add_job(
    _dropout_scan_job,
    trigger=CronTrigger(hour=9, minute=0),
    id="dropout_scan",
    replace_existing=True,
)
```

**`scan_inactive_patients()` logic**:
```python
# Real SQLAlchemy async query
result = await db.execute(
    select(Patient).where(
        Patient.stage == PatientStage.ACTIVE,
        Patient.last_active <= (now - timedelta(days=7)),
    )
)
```

**3-tier inactivity scoring**:
```
7 days inactive  → "warning",  risk_score = days/14, capped 0.5
14 days inactive → "at_risk",  risk_score = days/30, capped 0.9
30 days inactive → "dropout",  stage = DROPOUT, risk_score = 1.0
```

---

### P2.5 — SentenceTransformer Singleton
**File**: `therapeutic-copilot/server/services/rag_service.py`
**Problem**: `SentenceTransformer("all-MiniLM-L6-v2")` was called inside `_embed()`,
which is called on every RAG query. Each call reloads the 80MB model: ~2s overhead.

**Solution**: Module-level lazy singleton:
```python
_sentence_transformer_model = None

def _get_embedding_model():
    global _sentence_transformer_model
    if _sentence_transformer_model is None:
        from sentence_transformers import SentenceTransformer
        _sentence_transformer_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _sentence_transformer_model
```

**Impact**: First RAG call: ~2s (model load). All subsequent: <50ms.
**Decision**: Module-level (not class-level) so singleton is shared across all
`RAGService` instances created in different requests.

---

### P2.6 — llama-cpp-python Native Token Streaming
**File**: `therapeutic-copilot/server/services/qwen_inference.py`

**3-tier routing priority**:
```
1. LLAMA_CPP_PYTHON_MODEL_PATH set → llama-cpp-python native (prod, fastest)
2. TOGETHER_API_KEY set            → Together AI SSE (dev)
3. Neither                         → llama.cpp HTTP server (self-hosted)
```

**Native singleton**:
```python
_llama_native_model = None

def _get_llama_native_model():
    global _llama_native_model
    if _llama_native_model is None:
        from llama_cpp import Llama
        _llama_native_model = Llama(
            model_path=settings.LLAMA_CPP_PYTHON_MODEL_PATH,
            n_ctx=4096,
            n_gpu_layers=-1,   # offload ALL layers to GPU
            verbose=False,
        )
    return _llama_native_model
```

**Async bridge** (sync llama_cpp → async event loop):
```python
loop = asyncio.get_event_loop()
gen = await loop.run_in_executor(None, _sync_stream)
for chunk in gen:
    token = chunk["choices"][0].get("text", "")
    if token:
        yield token
```
**Decision**: `run_in_executor(None, ...)` uses the default thread pool. This prevents
the synchronous llama_cpp generator from blocking FastAPI's async event loop.

---

## 9. AI PIPELINE ARCHITECTURE

Every patient message travels through this pipeline:

```
Patient types message
        │
        ▼
[1] Crisis Detection (<100ms)
    crisis_detection_service.py
    30+ weighted keywords → severity 0-10
    Severity >= 7 → ESCALATE (skip steps 2-6)
        │
        ▼ (severity < 7)
[2] Persist user ChatMessage to DB
    crisis_keywords stored per message
        │
        ▼
[3] Resolve tenant_id for RAG
    Check Redis cache → fallback to DB Patient query
        │
        ▼
[4] RAG retrieval (Pinecone)
    rag_service.py
    SentenceTransformer embeds query (384-dim)
    Top-3 chunks from tenant's Pinecone namespace
        │
        ▼
[5] Build system prompt
    chatbot_service.py
    Stage 1/2/3 prompt template + RAG context + current_step
        │
        ▼
[6] LLM Inference
    qwen_inference.py
    Routing: llama-cpp-python → Together AI → llama.cpp HTTP
        │
        ▼
[7] Stream tokens via WebSocket
    Each token yielded by async generator → ws_manager.send()
        │
        ▼
[8] Persist assistant ChatMessage
[9] Advance Stage 2 current_step (capped at 10)
[10] Update Redis session cache
```

**Crisis escalation path**:
```
Severity >= 7
    → TherapySession.status = CRISIS_ESCALATED
    → ws_manager.broadcast to clinician's room
    → Return emergency helplines to patient
    → (Planned: SendGrid email to clinician)
```

---

## 10. API SURFACE MAP

All routes registered in `main.py`:

| Prefix | Router File | Key Endpoints |
|--------|------------|---------------|
| `/api/v1/auth` | `auth_routes.py` | `POST /login`, `POST /register`, `POST /refresh` |
| `/api/v1/chat` | `chat_routes.py` | `POST /session`, `POST /session/{id}/message`, `GET /session/{id}/history` |
| `/api/v1/assessments` | `assessment_routes.py` | `GET /types`, `GET /{type}/questions`, `POST /{patient_id}/submit`, `GET /{patient_id}/history` |
| `/api/v1/crisis` | `crisis_routes.py` | `POST /scan`, `POST /escalate` |
| `/api/v1/rag` | `rag_routes.py` | `POST /query`, `POST /ingest` |
| `/api/v1/widget` | `widget_routes.py` | `GET /validate-token`, `POST /session` |
| `/api/v1/payments` | `payment_routes.py` | `POST /create-order`, `POST /verify`, `POST /webhook` |
| `/ws` | `websocket_routes.py` | `WS /chat/{session_id}`, `WS /clinician/{clinician_id}` |
| `/api/v1/calendar` | `calendar_routes.py` | `GET /auth-url`, `GET /callback`, `POST /events` |
| `/api/v1/tenants` | `api/tenants.py` | CRUD for clinic onboarding |
| `/api/v1/patients` | `api/patients.py` | `GET /` (clinician's patients) |
| `/api/v1/leads` | `api/leads.py` | Lead management |
| `/api/v1/appointments` | `api/appointments.py` | Booking, cancel, list |

---

## 11. SECURITY DESIGN

| Threat | Mitigation |
|--------|-----------|
| Brute force login | Rate limit: 20 req/min on `/api/v1/auth` via Redis sliding window |
| User enumeration | Same error message for "user not found" and "wrong password" |
| Password storage | bcrypt hash, cost factor 12 (not MD5/SHA) |
| JWT tampering | HS256 signed with `SECRET_KEY` from `.env`, 24h expiry |
| Widget abuse | Per-tenant `widget_token` validated against DB on every request |
| XSS via widget | Shadow DOM isolates widget from host page JS/CSS |
| SQL injection | SQLAlchemy ORM + parameterized queries — no raw SQL |
| Data sovereignty | E2E Networks Mumbai — patient data never leaves India |
| Rate limiting | Redis sorted-set sliding window, fail-open for availability |

---

## 12. AUTONOMOUS CODING WORKFLOW

### How Tasks Were Executed

All code after Session 1 was written autonomously by Claude Sonnet 4.6 without
human typing a single line of code.

```
Human edits TASKS.md on GitHub (web browser, any device)
            │
            │ git push to main
            ▼
    github_watcher.py polls every 5 minutes
    Detects TASKS.md hash changed
            │
            │ git pull
            │ parse [ ] tasks
            ▼
    subprocess: claude.cmd --dangerously-skip-permissions
                            --print
                stdin: full task prompt with file context
            │
            │ Claude reads files, writes code, runs git
            ▼
    git commit + git push to main
            │
            ▼
    Human reviews commits on GitHub
    Marks tasks [x] or adds follow-up [ ] tasks
```

### Watcher Key Config
**File**: `github_watcher.py`
```python
REPO_DIR  = Path("c:/saath ai prototype")
BRANCH    = "main"
POLL_SECS = 300  # 5 minutes
claude_cmd = r"C:\Users\B P Verma\AppData\Roaming\npm\claude.cmd"
```

### Lessons Learned (Watcher Fixes)
| Issue | Root Cause | Fix Applied |
|-------|-----------|-------------|
| `WinError 2` | Python subprocess can't find `claude` in PATH | Hardcode full `.cmd` path |
| `unknown option --dangerouslySkipPermissions` | Flag renamed in v2.1.71 | Use `--dangerously-skip-permissions` |
| `Ready. What are we building today?` | Prompt dropped due to Windows CLI arg-length limit | Pass via `stdin` using `input=prompt` |
| `No pending tasks found` | Watcher stopped at `## P2` by design | Updated filter to include P2 section |

---

## SESSION 6 — 2026-03-08 — CHATWIDGET WEBSOCKET TOKEN STREAMING

### Task Completed
Complete ChatWidget WebSocket token streaming — connect to `/ws/chat/{session_id}`, receive
tokens, append to message bubble in real time. Includes crisis banner and session end modal.

### Files Changed
| File | Change |
|------|--------|
| `therapeutic-copilot/client/src/hooks/useChat.ts` | Full rewrite — streaming protocol, crisis state, endSession |
| `therapeutic-copilot/client/src/components/chatbot/ChatWidget.tsx` | Full rewrite — streaming bubble, crisis banner, summary modal |

### Design Decisions

**1. Dual-protocol WebSocket handler**
The backend may send either the new streaming protocol (`token` / `done` / `crisis` events)
or the legacy protocol (`AI_TYPING` / `AI_RESPONSE` / `CRISIS_ALERT`). The hook handles both
transparently so no backend change is required for the demo to work.

**2. Streaming placeholder pattern**
When `sendMessage()` is called, a placeholder `ChatMessage` with `content: ""` and a stable
`streamId` is inserted into the messages array immediately. Incoming `token` events find this
message by `streamId` via `streamingIdRef` and append each token in place. This avoids a
full array re-render per token — only the targeted message object changes.

**3. Blinking cursor vs animated dots**
- Content is empty (waiting for first token): show 3 bouncing dots (standard chat UX).
- Content is non-empty and streaming: show a blinking `|` cursor appended to the last char.
- Stream done: cursor disappears, message is finalized.

**4. Dynamic WebSocket URL**
`getWsBase()` reads `VITE_WS_URL` env var first, then falls back to
`ws(s)://window.location.host`. This means the widget works in dev (localhost:8000),
staging, and production without code changes.

**5. Crisis banner UX**
The crisis banner renders as an `absolute inset-0 z-50` overlay inside the widget container
so it cannot be accidentally missed. Default Indian helplines (iCALL, Vandrevala, AASRA)
are shown if the backend provides no `resources` array. The user must click "I'm safe —
continue" to dismiss it.

**6. Session end modal**
The "End session" button in the header calls `POST /api/v1/sessions/{id}/summary` via the
`endSession()` hook function (also sends `END_SESSION` over WebSocket). The modal shows
a loading spinner, then summary text + key insights + crisis score.

---

## SUMMARY — TOTAL BUILD OUTPUT

| Phase | Date | Tasks | Commits | Files Changed |
|-------|------|-------|---------|--------------|
| Session 1 — Scaffold | 2026-03-06 | 1 | ~8 | 87 new files, 7,019 lines |
| Session 2 — P0 Core | 2026-03-07 | 8 | 9 | auth, chat, crisis, widget |
| Session 3 — P1 Polish | 2026-03-07 | 5 | 5 | payments, calendar, dashboard, assessment, inference |
| Session 4 — Watcher | 2026-03-07 | 4 fixes | 4 | github_watcher.py |
| Session 5 — P2 Prod | 2026-03-08 | 6 | 6 | middleware, session, scheduler, rag, inference |
| Session 6 — ChatWidget streaming | 2026-03-08 | 3 | 2 | useChat.ts, ChatWidget.tsx |
| Session 7 — Chat session retrieval | 2026-03-08 | 1 | 1 | chat_routes.py |
| **Total** | | **28** | **~35** | **~52 files modified** |

---

## SESSION 7 — 2026-03-08 — CHAT SESSION RETRIEVAL FIX

### Task Completed
Fix `GET /api/v1/chat/session/{id}` which previously returned a hardcoded empty `[]`.
Now queries `TherapySession` and `ChatMessage` tables from DB using SQLAlchemy async ORM.

### Files Changed
| File | Change |
|------|--------|
| `therapeutic-copilot/server/routes/chat_routes.py` | Added real DB query for TherapySession + ChatMessage ordered by created_at; 404 on missing session |

### Design Decisions

**Pattern**: Query session first, 404 if not found, then query messages ordered by `created_at`.
Matches blueprint TASK-BE-01 exactly. Uses `scalar_one_or_none()` for session (single row)
and `scalars().all()` for messages (list). Loguru logs retrieval count for observability.

**Error handling**: Returns HTTP 404 with `"Session not found"` detail rather than empty dict
— prevents frontend from silently treating missing sessions as sessions with no messages.

**No raw SQL**: All queries use `sqlalchemy.future.select` + `.where()` + `.order_by()` per
project ORM-only rule.

### Algorithm
```
GET /api/v1/chat/session/{session_id}
  1. SELECT * FROM therapy_sessions WHERE id = session_id → scalar_one_or_none()
  2. If None → raise HTTPException 404
  3. SELECT * FROM chat_messages WHERE session_id = session_id ORDER BY created_at → scalars().all()
  4. Return {"session": session, "messages": messages}
```

---

## SESSION 8 — 2026-03-08 — CHAT SESSION END WITH AI SUMMARY

### Task Completed
Complete `POST /api/v1/chat/session/{id}/end` — was returning a hardcoded placeholder string.
Now fetches the last 10 messages, calls the LLM for a structured clinical summary + insights,
persists both fields to the DB, marks session COMPLETED, and deletes the Redis cache entry.

### Files Changed
| File | Change |
|------|--------|
| `therapeutic-copilot/server/services/therapeutic_ai_service.py` | Added `end_session()` method with full LLM summarisation pipeline |
| `therapeutic-copilot/server/routes/chat_routes.py` | Replaced placeholder return with `service.end_session()` call |

### Design Decisions

**Idempotency**: If `session.status == COMPLETED` and `session_summary` is already set,
`end_session()` returns the cached summary immediately without a second LLM call.
This prevents double-billing API tokens if the endpoint is called twice.

**Message fetch order**: Fetched with `ORDER BY created_at DESC LIMIT 10` then reversed
in Python — one DB round-trip, chronological order for the LLM prompt.

**Structured LLM prompt**: The prompt requests a strict JSON response with two keys:
`"summary"` (2-4 sentence narrative) and `"insights"` (object with `primary_concerns`,
`therapeutic_techniques_used`, `patient_engagement`, `recommended_followup`).
This maps directly to `TherapySession.session_summary` (Text) and `ai_insights` (JSON column).

**JSON parse fallback**: If the LLM response cannot be parsed as JSON (model hallucination,
network truncation), the raw text is stored as `session_summary` and `ai_insights` is set
to `{}`. Session is still marked COMPLETED — no exception is raised to the caller.

**Markdown fence stripping**: Before JSON parsing, a regex strips ` ```json ... ``` ` or
` ``` ... ``` ` wrappers that some LLM backends add. Ensures compatibility with Together AI
and llama.cpp which sometimes wrap JSON in code fences.

**Redis cleanup**: `redis_session_store.delete_session(session_id)` is called after DB commit.
Failures in Redis deletion are logged as warnings but do not fail the request — the session
is already COMPLETED in DB (source of truth).

**Error surface**: `ValueError` from the service (session not found) → HTTP 404.
Any other exception → HTTP 500. Both are logged with Loguru before raising.

### Algorithm
```
POST /api/v1/chat/session/{session_id}/end
  1. SELECT * FROM therapy_sessions WHERE id = session_id → scalar_one_or_none()
  2. If None → raise ValueError → HTTP 404
  3. If status == COMPLETED and session_summary → return cached {summary, insights}
  4. SELECT * FROM chat_messages WHERE session_id ORDER BY created_at DESC LIMIT 10
  5. Reverse list for chronological order
  6. Build summarisation prompt: transcript + structured JSON instruction
  7. llm.generate(prompt, stage, max_tokens=1024)
  8. Strip markdown code fences; json.loads(); extract summary + insights
  9. On JSONDecodeError: store raw response as summary, insights = {}
 10. session.session_summary = summary_text
     session.ai_insights = ai_insights
     session.status = SessionStatus.COMPLETED
     session.ended_at = datetime.utcnow()
 11. db.commit()
 12. redis_session_store.delete_session(session_id)
 13. Return {"summary": summary_text, "insights": ai_insights}
```

---

## SESSION 9 — 2026-03-08 — ASSESSMENT HISTORY FROM DB

### Task Completed
Complete `GET /api/v1/assessments/{patient_id}/history` — was returning a stub empty list `[]`.
Now queries the `assessments` table by `patient_id`, ordered by `administered_at DESC`, returning
all past assessment records for a patient.

### Files Changed
| File | Change |
|------|--------|
| `therapeutic-copilot/server/routes/assessment_routes.py` | Replaced stub return with real AsyncSession query; added imports for `select`, `HTTPException`, `logger`, `Assessment` |

### Design Decisions

**ORM-only**: Used SQLAlchemy async `select(Assessment).where(...).order_by(...)` — no raw SQL.
Follows the same pattern as `GET /api/v1/chat/session/{id}` in `chat_routes.py`.

**DESC ordering**: `administered_at.desc()` surfaces the most recent assessment first — the natural
UI expectation for a history timeline displayed newest-to-oldest.

**Error handling**: Any unexpected DB exception is caught, logged with Loguru at ERROR level, and
returned as HTTP 500 (detail: "Failed to retrieve assessment history"). The `patient_id` is
included in the log line for fast debugging.

**Empty result is valid**: If no assessments exist for a patient, `scalars().all()` returns `[]`
and the endpoint responds `{"patient_id": ..., "assessments": []}` with HTTP 200 — not 404.
An empty history is a valid state for a new patient.

### Algorithm
```
GET /api/v1/assessments/{patient_id}/history
  1. AsyncSession.execute(
       SELECT * FROM assessments
       WHERE patient_id = patient_id
       ORDER BY administered_at DESC
     )
  2. result.scalars().all() → list[Assessment]
  3. logger.info(count)
  4. Return {"patient_id": patient_id, "assessments": list}
  5. On exception: logger.error + raise HTTPException 500
```

---

---

## SESSION 10 — 2026-03-08 — CRISIS ESCALATION SENDGRID EMAIL

### Task Completed
Complete crisis escalation SendGrid email — when severity >= 7, send email to clinician.

### File Changed
- `therapeutic-copilot/server/services/crisis_detection_service.py`

### Problem Solved
`escalate()` was a stub returning hardcoded data with a `# TODO` comment. No DB write, no
WebSocket alert, no email was actually being sent.

### Implementation Pattern

Four sequential, individually fault-tolerant steps:

1. **DB persistence** — fetch `TherapySession` by `session_id`, update
   `status = CRISIS_ESCALATED` and `crisis_score = severity_score`, then `await db.commit()`.

2. **Clinician resolution** — query `Patient` by `patient_id` to get `clinician_id`, then
   query `Clinician` to get `email` and `full_name`. Both queries wrapped in try/except so a
   missing patient never blocks email sending.

3. **WebSocket alert** — call `ws_manager.send_crisis_alert(clinician_id, alert_data)` which
   broadcasts `{"type": "CRISIS_ALERT", ...}` to the `clinician:{id}` room. Silently continues
   if no clinician is connected.

4. **SendGrid email** (only when `severity >= 7.0`) — construct an HTML alert email using
   `sendgrid.helpers.mail.Mail`, send via `SendGridAPIClient(settings.SENDGRID_API_KEY)`.
   From-address is `settings.EMAIL_FROM`. Status codes 200/202 are treated as success.

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| Each step in its own try/except | Partial failure (e.g. DB timeout) must never prevent the email from going out |
| SendGrid SDK not httpx | `sendgrid==6.11.0` already in requirements.txt; SDK handles auth + retry internally |
| `settings.EMAIL_FROM` not hardcoded | Follows existing config.py pattern; env-configurable per deployment |
| `email_sent` flag in response | Caller (route) can log or alert ops if email delivery fails |
| Severity threshold 7.0 matches scan() | Consistent with `escalate: severity >= 7.0` in the scan response |

### Response Shape (after this change)
```json
{
  "escalated": true,
  "session_id": "...",
  "patient_id": "...",
  "severity": 9.0,
  "clinician_notified": true,
  "email_sent": true,
  "resources": {"iCall": "+91-9152987821", ...}
}
```

---

## SESSION 11 — 2026-03-08 — RAZORPAY WEBHOOK HANDLERS

### Task Completed
Complete `PaymentService.handle_webhook()` to process three Razorpay events:
`payment.captured`, `payment.failed`, `refund.created` — each updating
`Appointment.payment_status` via AsyncSession.

### Files Changed
| File | Change |
|------|--------|
| `therapeutic-copilot/server/services/payment_service.py` | Full webhook implementation — HMAC verification, event routing, DB update helper |
| `therapeutic-copilot/server/routes/payment_routes.py` | Pass `db: AsyncSession` dependency into `handle_webhook()` |
| `therapeutic-copilot/server/config.py` | Added `RAZORPAY_WEBHOOK_SECRET` setting |

### Algorithm

1. **Signature verification** (`_verify_webhook_signature`): HMAC-SHA256 of raw
   request body using `RAZORPAY_WEBHOOK_SECRET`. If secret is not set (dev mode),
   verification is skipped with a `logger.warning`. In production, the secret is
   configured in Razorpay Dashboard → Webhooks.

2. **payment.captured / payment.failed**: Extract `payload.payment.entity.order_id`
   from the event JSON. Call `_update_appointment_payment_status(db, order_id, status)`.

3. **refund.created**: Extract `payload.refund.entity.payment_id`. Since `Appointment`
   has `razorpay_order_id` but not `razorpay_payment_id`, we call
   `razorpay_client.payment.fetch(payment_id)` to resolve the `order_id`, then
   update the Appointment.

4. **`_update_appointment_payment_status`**: Single-responsibility helper that
   queries `Appointment` by `razorpay_order_id`, updates `payment_status`, commits.
   Logs a warning if the appointment is not found (idempotent — no error raised so
   Razorpay does not retry unnecessarily).

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| Separate `_verify_webhook_signature` method | Testable in isolation; dev vs prod behaviour controlled by env var |
| Dev-mode skip with warning not error | Allows local testing without webhook secret; explicit log prevents silent security gap |
| `_update_appointment_payment_status` helper | Avoids duplicating select+commit logic across three event branches |
| Razorpay API call for refund order_id | Appointment model stores `razorpay_order_id` (not payment_id); API fetch is the correct resolution strategy |
| Exception catch around API fetch | Razorpay API may timeout; catching prevents webhook 500 response which would cause Razorpay to retry indefinitely |
| `logger.warning` on missing appointment | Idempotent behaviour — webhook may arrive before appointment row exists in race condition; warn and continue |

---

## SESSION 12 — 2026-03-08 — AUTH /me AND /logout ENDPOINTS

### Task Completed
Add `GET /api/v1/auth/me` and `POST /api/v1/auth/logout` to complete the
authentication surface defined in the backend blueprint (TASK-BE-06).

### Files Changed
| File | Change |
|------|--------|
| `therapeutic-copilot/server/routes/auth_routes.py` | Added `GET /me`, `POST /logout`, Redis helper functions; imported `decode_token` directly at module level |

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| Token blacklisting via Redis `blacklist:{token}` key | Stateless JWTs cannot be invalidated server-side without a denylist; Redis with exact TTL ensures the key auto-expires precisely when the token would have expired, keeping memory bounded |
| TTL computed from `exp` claim, not configured lifetime | A token issued 20 minutes ago with a 30-minute lifetime should only be blacklisted for 10 more minutes. Using the remaining time is correct and avoids over-retention |
| `_get_redis()` returns `None` on failure (graceful degrade) | If Redis is down, `/me` skips blacklist check and still serves the profile; logout logs a warning but does not 503 the user. Availability > perfect security for non-critical Redis outage |
| Separate `_is_blacklisted()` helper | Reusable check that can be called from other protected routes or the `verify_jwt` middleware in the future |
| `/me` checks blacklist before `decode_token()` | Ordering: if the token is in the blacklist, skip decode entirely — avoid unnecessary crypto work |
| `/logout` returns 200 even for already-expired tokens | Idempotent — calling logout on an expired token is a no-op; returning 200 prevents unnecessary client errors |
| `HTTPBearer` dependency on `_bearer` instance | Consistent with how other protected routes use bearer extraction; returns 403 automatically for requests without Authorization header |

### Algorithm

```
GET /api/v1/auth/me
  1. Extract Bearer token via HTTPBearer dependency
  2. Check Redis blacklist:{token} → 401 if found
  3. decode_token(token) → 401 if invalid/expired
  4. SELECT * FROM clinicians WHERE id = payload["sub"]
  5. 404 if not found, 403 if is_active=False
  6. Return {id, email, full_name, tenant_id, specialization, is_active}

POST /api/v1/auth/logout
  1. Extract Bearer token via HTTPBearer dependency
  2. decode_token(token) → if invalid, return {"message": "Logged out"} (already expired)
  3. Compute remaining_ttl = payload["exp"] - now()
  4. If remaining_ttl <= 0 → return success (already expired)
  5. Redis.setex("blacklist:{token}", remaining_ttl, "1")
  6. Return {"message": "Logged out successfully"}
```

---

*Document generated: 2026-03-08*
*Build agent: Claude Sonnet 4.6 (claude-sonnet-4-6)*
*Company: RYL NEUROACADEMY PRIVATE LIMITED*
