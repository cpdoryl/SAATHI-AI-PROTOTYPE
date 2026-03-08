# SAATHI AI — Backend Blueprint
## FastAPI Server | RYL NEUROACADEMY PRIVATE LIMITED
### Version: 1.0 | Date: 2026-03-08 | Status: In Progress

---

## PURPOSE OF THIS DOCUMENT
This blueprint defines every backend requirement, design decision, implementation
target, and completion criteria for the Saathi AI FastAPI server. The autonomous
AI agent reads this before starting any backend task.

---

## 1. TECH STACK

| Component | Choice | Version |
|-----------|--------|---------|
| Framework | FastAPI | 0.111+ |
| Runtime | Python | 3.11 |
| ASGI Server | Uvicorn + Gunicorn | latest |
| ORM | SQLAlchemy (async) | 2.0 |
| Auth | python-jose (JWT) + passlib (bcrypt) | latest |
| Validation | Pydantic v2 | 2.x |
| HTTP client | httpx (async) | latest |
| Logging | Loguru | latest |
| Task queue | APScheduler | 3.x |
| Migration | Alembic | latest |

---

## 2. FOLDER STRUCTURE (target state)

```
server/
├── main.py                         # App entry, lifespan, middleware, routers
├── config.py                       # Pydantic Settings from .env
├── config_manager.py               # Startup config validator
├── database.py                     # SQLAlchemy async engine + session
├── models.py                       # All ORM models
├── auth/
│   └── jwt_handler.py              # JWT encode/decode helpers
├── middleware/
│   ├── auth_middleware.py          # JWT bearer extraction
│   └── rate_limit_middleware.py    # Redis sliding window ✓ DONE
├── routes/
│   ├── auth_routes.py              # /api/v1/auth/* ✓ DONE
│   ├── chat_routes.py              # /api/v1/chat/* PARTIAL
│   ├── assessment_routes.py        # /api/v1/assessments/* PARTIAL
│   ├── crisis_routes.py            # /api/v1/crisis/* PARTIAL
│   ├── rag_routes.py               # /api/v1/rag/* ✓ DONE
│   ├── widget_routes.py            # /api/v1/widget/* ✓ DONE
│   ├── payment_routes.py           # /api/v1/payments/* PARTIAL
│   ├── websocket_routes.py         # /ws/* ✓ DONE
│   └── calendar_routes.py          # /api/v1/calendar/* STUB
├── api/
│   ├── tenants.py                  # /api/v1/tenants CRUD
│   ├── users.py                    # /api/v1/users CRUD
│   ├── leads.py                    # /api/v1/leads CRUD
│   ├── appointments.py             # /api/v1/appointments PARTIAL
│   └── patients.py                 # /api/v1/patients ✓ DONE
├── services/
│   ├── therapeutic_ai_service.py   # MAIN ORCHESTRATOR ✓ DONE
│   ├── chatbot_service.py          # Prompt builder ✓ DONE
│   ├── crisis_detection_service.py # Keyword scanner ✓ DONE
│   ├── qwen_inference.py           # LLM inference ✓ DONE
│   ├── rag_service.py              # Pinecone RAG ✓ DONE
│   ├── lora_model_service.py       # LoRA adapter switcher PARTIAL
│   ├── assessment_service.py       # Clinical scoring ✓ DONE
│   ├── payment_service.py          # Razorpay PARTIAL
│   ├── websocket_manager.py        # WS room mgr ✓ DONE
│   ├── redis_session_service.py    # Redis session ✓ DONE
│   ├── dropout_service.py          # Stage 3 cron ✓ DONE
│   ├── calendar_service.py         # Google Calendar STUB
│   └── embedding_service.py        # Vector embedding ✓ DONE
├── tests/
│   ├── conftest.py                 # Fixtures
│   ├── test_smoke_p0.py            # P0 smoke tests ✓
│   ├── test_chat.py                # Chat API tests PARTIAL
│   ├── test_crisis_detection.py    # Crisis tests ✓
│   ├── test_assessments.py         # Assessment tests
│   ├── test_razorpay_sandbox.py    # Payment tests
│   ├── test_rag.py                 # RAG tests MISSING
│   ├── test_auth.py                # Auth tests MISSING
│   └── test_websocket.py           # WS tests MISSING
├── alembic/                        # DB migrations
├── scripts/
│   └── setup_db.py                 # DB seeding script
├── requirements.txt
└── Dockerfile
```

---

## 3. API ENDPOINTS — COMPLETE SPECIFICATION

### Auth Routes (`/api/v1/auth`)

| Method | Path | Input | Output | Status |
|--------|------|-------|--------|--------|
| POST | `/login` | `{email, password}` | `{access_token, token_type, clinician_id, tenant_id}` | ✓ DONE |
| POST | `/register` | `{email, password, full_name, tenant_id}` | `{clinician_id, message}` | ✓ DONE |
| POST | `/refresh` | Bearer token | `{access_token}` | ✓ DONE |
| POST | `/logout` | Bearer token | `{message}` | MISSING |
| GET | `/me` | Bearer token | `{id, email, full_name, tenant_id}` | MISSING |

### Chat Routes (`/api/v1/chat`)

| Method | Path | Input | Output | Status |
|--------|------|-------|--------|--------|
| POST | `/session` | `{patient_id, widget_token}` | `{session_id, stage, greeting}` | ✓ DONE |
| POST | `/session/{id}/message` | `{message, stage}` | `{response, crisis_detected, current_step}` | ✓ DONE |
| GET | `/session/{id}` | session_id | `{session, messages[]}` | PARTIAL — returns `[]` |
| POST | `/session/{id}/end` | session_id | `{summary, insights}` | PARTIAL — returns placeholder |
| GET | `/session/{id}/history` | session_id | `[ChatMessage]` | MISSING |

### Assessment Routes (`/api/v1/assessments`)

| Method | Path | Input | Output | Status |
|--------|------|-------|--------|--------|
| GET | `/types` | — | `{assessments: []}` | ✓ DONE |
| GET | `/{type}/questions` | assessment_type | `{questions: []}` | ✓ DONE |
| POST | `/{patient_id}/submit` | `{assessment_type, responses[]}` | `{score, severity}` | ✓ DONE |
| GET | `/{patient_id}/history` | patient_id | `[Assessment]` | STUB — returns `[]` |

### Crisis Routes (`/api/v1/crisis`)

| Method | Path | Input | Output | Status |
|--------|------|-------|--------|--------|
| POST | `/scan` | `{message}` | `{severity, escalate, keywords}` | ✓ DONE |
| POST | `/escalate` | `{session_id, patient_id, severity}` | `{escalated, resources}` | PARTIAL — no SendGrid |
| GET | `/resources` | — | `{helplines: []}` | ✓ DONE |

### Payment Routes (`/api/v1/payments`)

| Method | Path | Input | Output | Status |
|--------|------|-------|--------|--------|
| POST | `/create-order` | `{appointment_id, amount_inr}` | `{order_id, amount_paise, key_id}` | ✓ DONE |
| POST | `/verify` | `{order_id, payment_id, signature}` | `{verified, payment_id}` | ✓ DONE |
| POST | `/webhook` | Razorpay event body | 200 OK | PARTIAL — event handlers TODO |

### Calendar Routes (`/api/v1/calendar`)

| Method | Path | Input | Output | Status |
|--------|------|-------|--------|--------|
| GET | `/auth-url` | Bearer token | `{auth_url}` | STUB |
| GET | `/callback` | `?code=...` | redirect | STUB |
| POST | `/events` | `{clinician_id, patient_id, scheduled_at, duration}` | `{event_id, meet_link}` | STUB |
| GET | `/events` | Bearer token | `[CalendarEvent]` | STUB |

---

## 4. PENDING BACKEND TASKS (ordered by priority)

### CRITICAL

#### TASK-BE-01: Complete Chat Session Retrieval
**File**: `routes/chat_routes.py`
**Problem**: `GET /session/{id}` returns hardcoded `[]`
**Solution**:
```python
result = await db.execute(
    select(TherapySession).where(TherapySession.id == session_id)
)
session = result.scalar_one_or_none()
msgs = await db.execute(
    select(ChatMessage).where(ChatMessage.session_id == session_id)
    .order_by(ChatMessage.created_at)
)
return {"session": session, "messages": msgs.scalars().all()}
```

#### TASK-BE-02: Chat Session End with AI Summary
**File**: `services/therapeutic_ai_service.py`
**Problem**: `_end_session()` returns placeholder string
**Solution**: Fetch last 10 messages, call LLM to summarize, persist to
`TherapySession.session_summary`, update status to COMPLETED, delete Redis cache

#### TASK-BE-03: Assessment History from DB
**File**: `routes/assessment_routes.py`
**Problem**: `GET /{patient_id}/history` returns `[]`
**Solution**:
```python
result = await db.execute(
    select(Assessment).where(Assessment.patient_id == patient_id)
    .order_by(Assessment.administered_at.desc())
)
return {"patient_id": patient_id, "assessments": result.scalars().all()}
```

#### TASK-BE-04: Crisis Escalation — SendGrid Email
**File**: `services/crisis_detection_service.py`
**Problem**: `escalate()` has `# TODO: Log to DB, send WebSocket alert, notify via SendGrid`
**Solution**: Use `sendgrid` SDK to send email to clinician using
`SENDGRID_API_KEY` + `SENDGRID_FROM_EMAIL` from config

#### TASK-BE-05: Razorpay Webhook Event Handlers
**File**: `services/payment_service.py`
**Problem**: `handle_webhook()` has `# TODO: Handle payment.captured, payment.failed`
**Solution**:
- `payment.captured`: Update `Appointment.payment_status = "paid"`
- `payment.failed`: Update `Appointment.payment_status = "failed"`
- `refund.created`: Update `Appointment.payment_status = "refunded"`

#### TASK-BE-06: Auth `/me` + `/logout` Endpoints
**File**: `routes/auth_routes.py`
**Solution**: GET `/me` returns current clinician profile. POST `/logout` blacklists token in Redis.

#### TASK-BE-07: LoRA Adapter Hot-Swap API
**File**: `services/lora_model_service.py`
**Problem**: `# TODO: Call llama.cpp API to hot-swap LoRA adapter`
**Solution**: POST to `{LLAMA_CPP_SERVER_URL}/lora` with adapter path. Handle graceful fallback.

### HIGH

#### TASK-BE-08: Backend Test Coverage — Auth
**File**: `tests/test_auth.py` (create)
Tests: correct login → JWT, wrong password → 401, unknown email → 401, register → 201, refresh → new token

#### TASK-BE-09: Backend Test Coverage — RAG
**File**: `tests/test_rag.py` (create)
Tests: ingest document → Pinecone upsert, query → returns top-k chunks, wrong tenant → empty results

#### TASK-BE-10: Backend Test Coverage — WebSocket
**File**: `tests/test_websocket.py` (create)
Tests: clinician connects to room, crisis alert broadcasts to room, chat session WS streams tokens

#### TASK-BE-11: Appointments CRUD Completion
**File**: `api/appointments.py`
Currently returns placeholder. Wire to DB: create appointment → Razorpay order + Calendar event

#### TASK-BE-12: Patient Sessions List for Dashboard
**File**: `api/patients.py`
Add: `GET /api/v1/patients/{id}/sessions` → list TherapySession rows for that patient

---

## 5. ENVIRONMENT VARIABLES REQUIRED

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/saathi

# Auth
SECRET_KEY=<256-bit random>
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# AI Inference
TOGETHER_API_KEY=<from together.ai>
TOGETHER_MODEL=Qwen/Qwen2.5-7B-Instruct-Turbo
LLAMA_CPP_SERVER_URL=http://localhost:8080
LLAMA_CPP_PYTHON_MODEL_PATH=/models/qwen2.5-7b-q4.gguf

# Pinecone
PINECONE_API_KEY=<from pinecone.io>
PINECONE_INDEX=saathi-rag
PINECONE_ENVIRONMENT=gcp-starter

# Redis
REDIS_URL=redis://localhost:6379

# Payments
RAZORPAY_KEY_ID=<from razorpay>
RAZORPAY_KEY_SECRET=<from razorpay>

# Email
SENDGRID_API_KEY=<from sendgrid>
SENDGRID_FROM_EMAIL=alerts@saathi.ai

# Google Calendar
GOOGLE_CLIENT_ID=<from GCP Console>
GOOGLE_CLIENT_SECRET=<from GCP Console>
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/calendar/callback
```

---

## 6. COMPLETION CRITERIA

The backend is production-ready when ALL of the following pass:
- [ ] All endpoints return real data (no placeholders or empty arrays)
- [ ] All tests in `tests/` pass: `pytest tests/ -v`
- [ ] Server starts cleanly: `uvicorn main:app --reload` with no errors
- [ ] `/docs` auto-documentation renders all routes correctly
- [ ] Rate limiting returns 429 after threshold
- [ ] JWT auth blocks unauthenticated requests with 401
- [ ] Crisis detection responds in <100ms (test: `test_crisis_detection.py`)
