# SAATHI AI — DEVELOPER GUIDE
## Step-by-Step Build Log & Developer Record
### RYL NEUROACADEMY PRIVATE LIMITED | Version 1.0 | Started: March 2026

---

> **Purpose of This Document**
> This guide is a **living build record** — every step taken to build the Saathi AI prototype is recorded here in chronological order. Future developers and contributors can trace exactly what was done, why decisions were made, and how to replicate each step.

---

## TABLE OF CONTENTS

1. [Project Overview](#1-project-overview)
2. [Build Session 1 — Repository Initialization](#2-build-session-1--repository-initialization)
3. [Build Session 2 — Root-Level Scaffolding](#3-build-session-2--root-level-scaffolding)
4. [Build Session 3 — Backend Server Scaffold](#4-build-session-3--backend-server-scaffold)
5. [Build Session 4 — Frontend Client Scaffold](#5-build-session-4--frontend-client-scaffold)
6. [Build Session 5 — Embeddable Widget Scaffold](#6-build-session-5--embeddable-widget-scaffold)
7. [Build Session 6 — ML Pipeline, Tests & Scripts](#7-build-session-6--ml-pipeline-tests--scripts)
8. [Architecture Decisions Log](#8-architecture-decisions-log)
9. [File-by-File Reference](#9-file-by-file-reference)
10. [How to Continue Building](#10-how-to-continue-building)
11. [Known TODOs & Next Steps](#11-known-todos--next-steps)

---

## 1. PROJECT OVERVIEW

**Saathi AI** is a B2B SaaS therapeutic co-pilot for mental health clinics.

### What Was Built
A complete folder/file scaffold representing the full production architecture, ready for feature implementation.

### Repository
- **GitHub**: https://github.com/cpdoryl/SAATHI-AI-PROTOTYPE.git
- **Local**: `c:/saath ai prototype/`

### Tech Stack (Do Not Change Without Team Discussion)
| Layer | Choice | Reason |
|-------|--------|--------|
| Backend | FastAPI (Python 3.11) | Async-native, auto docs, fastest Python framework |
| Frontend | React 18 + TypeScript + Vite | Type safety, fast dev, Tailwind CSS |
| AI Model | Qwen 2.5-7B GGUF via llama.cpp | Self-hosted, Indian data sovereignty, low cost |
| AI (dev) | Together AI cloud API | No GPU needed during development |
| Vector DB | Pinecone | Per-tenant namespaces, fast similarity search |
| Primary DB | PostgreSQL (SQLite for local) | ACID compliance, JSON columns |
| Cache | Redis 7 | Session state, rate limiting |
| Payments | Razorpay | India-first, INR native |
| Widget | Shadow DOM + Custom Elements | Zero style conflicts with host page |
| Infra (prod) | E2E Networks Mumbai | Indian data sovereignty requirement |

---

## 2. BUILD SESSION 1 — REPOSITORY INITIALIZATION

**Date**: March 6, 2026
**Developer**: Claude Sonnet 4.6 (AI Agent) + cpdoryl

### Steps Taken

#### Step 1: Check existing project directory
```bash
ls "c:/saath ai prototype"
# Found: DEVELOPER_SETUP_README.md, PROTOTYPE_BUILDING_DOCUMENT.md
# Status: 2 documentation files existed. No git repo, no code yet.
```

#### Step 2: Initialize git repository
```bash
cd "c:/saath ai prototype"
git init
# Result: Initialized empty Git repository in C:/saath ai prototype/.git/
```

#### Step 3: Add remote origin
```bash
git remote add origin https://github.com/cpdoryl/SAATHI-AI-PROTOTYPE.git
git remote -v
# Result: origin set to https://github.com/cpdoryl/SAATHI-AI-PROTOTYPE.git
```

#### Why These Decisions
- Local directory already had documentation files — kept them, added code alongside
- Used HTTPS remote (not SSH) for compatibility across dev environments

---

## 3. BUILD SESSION 2 — ROOT-LEVEL SCAFFOLDING

**Date**: March 6, 2026

### Files Created

| File | Purpose |
|------|---------|
| `.gitignore` | Exclude secrets, node_modules, Python cache, DB files, model binaries |
| `README.md` | Project overview, quick start, repo structure, tech stack |
| `.env.example` | Root-level env template (PostgreSQL + Redis for Docker Compose) |
| `docker-compose.prod.yml` | Production deployment (nginx + backend + PostgreSQL + Redis) |

### Key Decisions

**`.gitignore` coverage:**
- Python: `__pycache__`, `.venv`, `*.pyc`, `*.egg-info`
- Node: `node_modules/`, `dist/`
- Secrets: `.env` excluded, `.env.example` included
- AI models: `*.gguf`, `*.bin`, `*.safetensors` excluded (large binaries)
- Databases: `*.db`, `*.sqlite` excluded
- Docker volumes: `postgres_data/`, `redis_data/`

**`docker-compose.prod.yml` design:**
- NGINX as reverse proxy + SSL termination
- Backend as internal service (not exposed directly)
- PostgreSQL with healthcheck before backend starts
- Redis with healthcheck
- Named volumes for data persistence

---

## 4. BUILD SESSION 3 — BACKEND SERVER SCAFFOLD

**Date**: March 6, 2026
**Location**: `therapeutic-copilot/server/`

### Files Created (in order)

#### Core Application Files

**`requirements.txt`**
- FastAPI 0.111.0 + Uvicorn (ASGI server)
- SQLAlchemy 2.0 (ORM) + Alembic (migrations)
- psycopg2-binary (PostgreSQL) + aiosqlite (SQLite local dev)
- python-jose + passlib (JWT + password hashing)
- together (Together AI SDK) + openai (compatible client)
- pinecone-client + sentence-transformers (RAG)
- razorpay (payments)
- sendgrid (email) + google-api-python-client (Calendar)
- redis + aioredis (caching)
- pydantic v2 + pydantic-settings (config)
- loguru (structured logging)

**`config.py`** — Centralised settings via pydantic-settings
- All config loaded from environment variables
- `cors_origins_list` property parses comma-separated CORS string
- Defaults safe for local development

**`config_manager.py`** — Startup config validator
- Warns about missing optional keys (Pinecone, Razorpay)
- Errors on missing critical keys (AI inference)
- Warns if JWT secret is default value

**`database.py`** — Database engine + session factory
- Sync engine for Alembic migrations
- Async engine for FastAPI endpoints (asyncpg for PostgreSQL, aiosqlite for SQLite)
- `get_db()` dependency: yields session, auto-commits, rolls back on error

**`models.py`** — SQLAlchemy ORM models
- `Tenant` — B2B clinic (has `widget_token` for embed auth)
- `Clinician` — Therapist accounts per tenant
- `Patient` — Patient records with `stage` enum (lead/active/dropout/archived)
- `TherapySession` — Per session with `current_step` (0–11 for Stage 2)
- `ChatMessage` — Individual messages with crisis keyword fields
- `Assessment` — 8 clinical assessment results per patient
- `Appointment` — Booking records linked to Google Calendar + Razorpay

**`main.py`** — FastAPI app factory
- Lifespan context manager for startup/shutdown
- CORS middleware (configured from settings)
- GZip middleware (responses >1KB)
- All routers registered with versioned prefix `/api/v1/`
- WebSocket router at `/ws`

#### API Layer (`api/`)

Thin route handlers — no business logic:
- `tenants.py` — Tenant CRUD (admin only)
- `users.py` — Clinician profile management
- `leads.py` — Stage 1 lead capture/conversion
- `appointments.py` — Google Calendar + Razorpay booking
- `chat.py` — Basic chat endpoints
- `payments.py` — Razorpay order/verify/webhook

#### Routes Layer (`routes/`)

Full-featured route handlers with service delegation:
- `auth_routes.py` — JWT login/register/refresh
- `chat_routes.py` — Full 3-stage conversation flow with BackgroundTasks
- `assessment_routes.py` — 8 clinical instruments (PHQ-9, GAD-7, etc.)
- `crisis_routes.py` — Real-time crisis scan + escalation protocol
- `rag_routes.py` — Pinecone query and document ingestion
- `widget_routes.py` — Widget config + JS bundle serving
- `payment_routes.py` — Razorpay full payment cycle
- `websocket_routes.py` — WebSocket rooms for clinician alerts + chat streaming

#### Services Layer (`services/`) — Core Business Logic

| Service | What It Does |
|---------|-------------|
| `therapeutic_ai_service.py` | **Main orchestrator** — routes through crisis → RAG → LLM |
| `chatbot_service.py` | 11-step state machine, prompt construction |
| `crisis_detection_service.py` | 30+ weighted keywords, 10-point severity, <100ms |
| `assessment_service.py` | Scores PHQ-9, GAD-7 + 6 more instruments |
| `qwen_inference.py` | Together AI (dev) or llama.cpp (prod) wrapper |
| `rag_service.py` | Pinecone query + ingest per tenant namespace |
| `lora_model_service.py` | LoRA adapter switching (Stage 1 r=8, Stage 2 r=16) |
| `payment_service.py` | Razorpay order + HMAC signature verification |
| `lead_service.py` | Stage 1 lead capture + conversion to patient |
| `dropout_service.py` | Inactivity detection + personalized re-engagement |
| `websocket_manager.py` | WebSocket rooms for real-time clinician alerts |
| `embedding_service.py` | 384-dim sentence embeddings (all-MiniLM-L6-v2) |

#### Auth Layer (`auth/`)
- `jwt_handler.py` — bcrypt password hashing, JWT create/decode with python-jose

#### Middleware (`middleware/`)
- `auth_middleware.py` — JWT Bearer token verification dependency
- `rate_limit_middleware.py` — Redis-backed rate limiter scaffold

#### Schema Layer (`models/schemas.py`)
- Pydantic v2 schemas for all request/response types
- Login, Chat, Assessment, Appointment, Payment, Tenant schemas

#### Database Migrations (`alembic/`)
- `env.py` — Alembic migration environment (imports all ORM models for autogenerate)
- `versions/.gitkeep` — Placeholder for migration version files

#### Infrastructure
- `Dockerfile` — Python 3.11-slim production container

---

## 5. BUILD SESSION 4 — FRONTEND CLIENT SCAFFOLD

**Date**: March 6, 2026
**Location**: `therapeutic-copilot/client/`

### Key Technology Choices

| Choice | Reason |
|--------|--------|
| React 18 + TypeScript | Type safety, component reuse |
| Vite | Fast HMR, smaller bundles than CRA |
| Tailwind CSS | Rapid UI development, consistent design |
| Zustand | Lightweight state management (lighter than Redux) |
| TanStack Query | Server state caching and synchronisation |
| Recharts | Charts for analytics dashboard |
| Axios | HTTP client with interceptors for JWT injection |

### Files Created

**`package.json`** — All dependencies pinned with explicit versions

**`vite.config.ts`** — Dev proxy configured:
- `/api` → `http://localhost:8000` (avoids CORS in dev)
- `/ws` → `ws://localhost:8000` (WebSocket proxy)

**`src/types/index.ts`** — All TypeScript interfaces:
- `Patient`, `TherapySession`, `ChatMessage`, `AssessmentResult`
- `Appointment`, `CrisisAlert`, `Tenant`

**`src/lib/api.ts`** — Axios client:
- JWT auto-injection from localStorage
- 401 → automatic redirect to /login
- All API calls typed and organised by domain

**`src/contexts/AuthContext.tsx`** — React auth context:
- `useAuth()` hook for components
- JWT storage + clinician state

**`src/hooks/useChat.ts`** — WebSocket chat hook:
- Auto-connects to `/ws/chat/{sessionId}`
- Handles `AI_RESPONSE`, `AI_TYPING`, `CRISIS_ALERT` message types
- `sendMessage()` adds optimistic UI update

**`src/components/chatbot/ChatWidget.tsx`** — Main chat UI:
- Connection status indicator
- Message bubbles (user right, AI left)
- Typing indicator (animated dots)
- Enter-to-send form

**`src/components/clinician/ClinicianDashboard.tsx`** — Clinician hub:
- Real-time WebSocket crisis alerts
- Patient overview cards with stage badges
- Tabbed interface (patients / alerts / analytics)
- Crisis alert count badge in tab header

**`src/components/patient/PatientPortal.tsx`** — Patient-facing:
- Session history
- 8 assessment type buttons (PHQ-9, GAD-7, etc.)
- Appointment list

**`src/components/payment/PaymentFlow.tsx`** — Razorpay UI:
- Dynamic SDK loading (no static import)
- Order creation → Razorpay modal → verification flow
- `onSuccess` / `onFailure` callbacks

**`src/components/landing/LandingPage.tsx`** — Marketing page:
- Hero section with CTA buttons
- 3-tier pricing cards (Basic/Professional/Enterprise)

**`src/components/analytics/Analytics.tsx`** — Metrics dashboard

**`src/components/admin/AdminPanel.tsx`** — Super-admin panel

**`src/components/ui/index.tsx`** — Design system primitives:
- `Button` (primary/secondary/danger + sm/md/lg)
- `Badge` (colored status badges)
- `Card` (content wrapper)
- `Spinner` (loading indicator)

**`src/App.tsx`** — React Router setup:
- `/` → LandingPage
- `/dashboard` → ClinicianDashboard (protected)
- `/patient` → PatientPortal (protected)
- `/admin` → AdminPanel (protected)

**`index.html`** — Entry HTML with Razorpay SDK script tag

**`Dockerfile.dev`** — Node 18 Alpine dev container

---

## 6. BUILD SESSION 5 — EMBEDDABLE WIDGET SCAFFOLD

**Date**: March 6, 2026
**Location**: `therapeutic-copilot/widget/`

### Architecture: Shadow DOM + Custom Elements

**Why Shadow DOM?**
- Complete CSS isolation — no conflicts with host clinic's website styles
- Host page cannot accidentally override widget styles
- Industry standard for embeddable components (Tidio, Intercom use similar)

**Why Custom Elements (Web Components)?**
- Native browser API — no framework dependency for the mount mechanism
- Self-contained — widget injects itself with no host page changes needed

### How It Works

```
1. Clinic adds: <script src="bundle.js" data-token="TOKEN"></script>
2. widget.ts runs → creates <saathi-widget> custom element
3. Custom element creates Shadow DOM (isolated DOM subtree)
4. React mounts inside the Shadow DOM container
5. ChatBubble component fetches config from /api/v1/widget/config
6. Floating action button appears → user clicks → chat panel opens
7. Messages sent via REST API to Saathi AI backend
```

### Files Created

**`vite.config.widget.ts`** — Widget-specific build:
- Output format: IIFE (Immediately Invoked Function Expression)
- Single file output: `widget.bundle.js`
- Everything bundled — no external dependencies
- minified with esbuild

**`src/widget.ts`** — Entry point:
- Defines `SaathiWidget` custom element class
- Creates Shadow DOM, injects CSS reset
- Reads `data-token` from script tag
- Mounts React `ChatBubble` inside Shadow DOM
- Registers custom element once and auto-appends to `<body>`

**`src/components/ChatBubble.tsx`** — Full widget UI:
- Floating action button (position: fixed, bottom-right)
- Expandable chat panel with header/messages/input
- Fetches widget config (persona name, primary color, greeting)
- Sends messages via `/api/v1/chat/message`
- Handles crisis response passthrough
- Hover animation on FAB button
- Inline styles (no Tailwind dependency in widget)

---

## 7. BUILD SESSION 6 — ML PIPELINE, TESTS & SCRIPTS

**Date**: March 6, 2026

### ML Pipeline (`ml_pipeline/`)

**`train_lora.py`** — LoRA fine-tuning pipeline:
- Configures Stage 1 (r=8) and Stage 2 (r=16) adapters
- Uses QLoRA (4-bit quantization) for memory efficiency
- Comments show the full training pipeline for when GPU is available
- Designed for HuggingFace PEFT + Transformers

**`data/.gitkeep`** — Placeholder for training data directory
- Training JSONLs go here: `stage1_conversations.jsonl`, `stage2_conversations.jsonl`

### Tests (`tests/`)

**`conftest.py`** — Pytest configuration:
- Adds server to sys.path for imports
- Sets SQLite test database URL

**`test_chat.py`** — Chat API integration tests:
- `test_health_check` — verifies /health endpoint
- `test_start_session` — verifies session initialisation
- `test_send_message` — verifies normal AI response
- `test_crisis_detection_in_message` — verifies crisis escalation triggers

**`test_crisis_detection.py`** — Crisis detection unit tests:
- `test_non_crisis_message` — below threshold
- `test_high_severity_crisis` — "I want to kill myself" → severity ≥ 9
- `test_moderate_crisis` — moderate keywords
- `test_scan_speed` — 100 iterations, must average <100ms each
- `test_hinglish_crisis` — Hinglish crisis phrase detection
- `test_empty_message` — edge case: empty string
- `test_multiple_keywords_accumulate` — multiple keywords score higher

**`test_assessments.py`** — Assessment unit tests:
- PHQ-9 minimal (all 0s → "None–minimal")
- PHQ-9 severe (all 3s → "Severe", score=27)
- GAD-7 mild scoring
- Unknown assessment type error handling
- Question list retrieval

### Scripts (`scripts/`)

**`setup_db.py`** — One-time database setup:
```bash
python scripts/setup_db.py          # Create tables only
python scripts/setup_db.py --seed   # Create + seed demo data
```
- Creates all SQLAlchemy tables
- Seeds demo tenant (MindWell Clinic) with widget token

**`generate_widget_token.py`** — Widget token generator:
```bash
python scripts/generate_widget_token.py --tenant-name "My Clinic"
# Outputs: token + ready-to-use embed script
```

### App-level Docker Compose (`therapeutic-copilot/docker-compose.yml`)

- `backend` — FastAPI with hot-reload (volume-mounted)
- `frontend` — Vite dev server with HMR
- `db` — PostgreSQL 15 with healthcheck
- `redis` — Redis 7 with healthcheck
- Services wait for DB/Redis health before starting

---

## 8. ARCHITECTURE DECISIONS LOG

### Decision 1: Shadow DOM for Widget (NOT iframes)
- **Decision**: Use Shadow DOM + Custom Elements
- **Alternatives considered**: iframe, vanilla DOM injection
- **Reason**: iframes require cross-origin messaging, complex sizing. Shadow DOM is native, zero overhead, complete CSS isolation.
- **Precedent**: Tidio, HubSpot Chat, Intercom all use similar approaches.

### Decision 2: Together AI for Development (NOT self-hosted llama.cpp)
- **Decision**: Use Together AI cloud API for dev/demo
- **Reason**: Self-hosted llama.cpp requires GPU. Together AI gives the same Qwen 2.5-7B model at ~$0.20/1M tokens. Dev can happen without hardware setup.
- **Migration path**: `qwen_inference.py` auto-switches based on `TOGETHER_API_KEY` vs `LLAMA_CPP_SERVER_URL`

### Decision 3: SQLite Local, PostgreSQL Production
- **Decision**: `DATABASE_URL=sqlite:///./saathi_copilot.db` for local dev
- **Reason**: Zero-install setup. Developer doesn't need Docker for day-1 local dev.
- **Migration path**: Change `DATABASE_URL` to PostgreSQL string — SQLAlchemy handles both.

### Decision 4: Razorpay (NOT Stripe)
- **Decision**: Razorpay for all payment processing
- **Reason**: India-first, INR native, cheaper MDR than Stripe India, better Indian payment method support (UPI, NetBanking).

### Decision 5: Pinecone for RAG (NOT pgvector)
- **Decision**: Pinecone with per-tenant namespaces
- **Reason**: Managed service, no infra to run. Per-tenant namespaces provide data isolation. pgvector would require self-managed scaling.

### Decision 6: Pydantic v2 Settings (NOT python-decouple or dotenv directly)
- **Decision**: `pydantic-settings` for all config
- **Reason**: Type validation, IDE autocomplete on settings, automatic env loading, compatible with FastAPI's dependency system.

---

## 9. FILE-BY-FILE REFERENCE

### Root Level
```
.gitignore                          ← Comprehensive exclusion rules
README.md                           ← Project overview + quick start
.env.example                        ← Root env template (Docker Compose vars)
docker-compose.prod.yml             ← Production deployment config
DEVELOPER_SETUP_README.md           ← Pre-existing: full developer setup guide
PROTOTYPE_BUILDING_DOCUMENT.md      ← Pre-existing: architecture + investor spec
DEVELOPER_GUIDE.md                  ← This file: living build record
```

### therapeutic-copilot/server/
```
main.py                             ← FastAPI app, middleware, router registration
config.py                           ← All env vars with defaults via pydantic-settings
config_manager.py                   ← Startup config validator (logs warnings/errors)
database.py                         ← Sync + async DB engines, get_db() dependency
models.py                           ← SQLAlchemy ORM (Tenant, Clinician, Patient, etc.)
requirements.txt                    ← Python dependencies
Dockerfile                          ← Python 3.11 container
alembic/env.py                      ← Alembic migration environment
alembic/versions/                   ← Migration scripts (generated by alembic revision)
api/__init__.py
api/tenants.py                      ← Tenant CRUD
api/users.py                        ← Clinician profile
api/leads.py                        ← Stage 1 lead management
api/appointments.py                 ← Appointment booking
api/chat.py                         ← Basic chat endpoints
api/payments.py                     ← Razorpay integration
routes/__init__.py
routes/auth_routes.py               ← JWT login/register/refresh
routes/chat_routes.py               ← Full 3-stage conversation pipeline
routes/assessment_routes.py         ← 8 clinical assessments
routes/crisis_routes.py             ← Crisis scan + escalation
routes/rag_routes.py                ← Pinecone query + ingest
routes/widget_routes.py             ← Widget config + bundle serving
routes/payment_routes.py            ← Full Razorpay payment cycle
routes/websocket_routes.py          ← Real-time WebSocket rooms
services/__init__.py
services/therapeutic_ai_service.py  ← MAIN ORCHESTRATOR (start here)
services/chatbot_service.py         ← 11-step state machine
services/crisis_detection_service.py ← 30+ keywords, <100ms
services/assessment_service.py      ← PHQ-9, GAD-7, etc.
services/qwen_inference.py          ← Together AI + llama.cpp wrapper
services/rag_service.py             ← Pinecone RAG
services/lora_model_service.py      ← LoRA adapter switching
services/payment_service.py         ← Razorpay orders + verification
services/lead_service.py            ← Stage 1 lead logic
services/dropout_service.py         ← Stage 3 re-engagement
services/websocket_manager.py       ← WebSocket connection rooms
services/embedding_service.py       ← 384-dim embeddings
middleware/auth_middleware.py        ← JWT Bearer verification
middleware/rate_limit_middleware.py  ← Redis rate limiting (scaffold)
auth/jwt_handler.py                 ← bcrypt + python-jose JWT
models/schemas.py                   ← Pydantic v2 request/response schemas
```

### therapeutic-copilot/client/
```
package.json                        ← React 18 + TS + Vite + Tailwind deps
vite.config.ts                      ← Dev proxy to backend + WebSocket
tsconfig.json                       ← TypeScript strict config
index.html                          ← Entry HTML + Razorpay SDK script
Dockerfile.dev                      ← Node 18 dev container
src/main.tsx                        ← React DOM mount point
src/App.tsx                         ← Router + route protection
src/index.css                       ← Tailwind directives
src/types/index.ts                  ← All TypeScript interfaces
src/lib/api.ts                      ← Axios client + all API functions
src/contexts/AuthContext.tsx        ← JWT auth state + hooks
src/hooks/useChat.ts                ← WebSocket chat hook
src/components/chatbot/ChatWidget.tsx ← Chat UI component
src/components/clinician/ClinicianDashboard.tsx ← Main clinician hub
src/components/patient/PatientPortal.tsx ← Patient-facing portal
src/components/payment/PaymentFlow.tsx ← Razorpay checkout
src/components/landing/LandingPage.tsx ← Marketing page
src/components/analytics/Analytics.tsx ← Metrics dashboard
src/components/admin/AdminPanel.tsx ← Super-admin panel
src/components/ui/index.tsx         ← Design system (Button, Badge, Card, Spinner)
src/pages/index.tsx                 ← Page-level re-exports
```

### therapeutic-copilot/widget/
```
vite.config.widget.ts               ← IIFE bundle build (single file output)
src/widget.ts                       ← Custom element + Shadow DOM mount
src/components/ChatBubble.tsx       ← Floating chat UI (inline styles)
```

### therapeutic-copilot/
```
docker-compose.yml                  ← Local dev (backend + frontend + DB + Redis)
.env.example                        ← App-level env template (all vars documented)
requirements-rag.txt                ← RAG-specific Python deps
ml_pipeline/train_lora.py          ← LoRA fine-tuning pipeline
ml_pipeline/README.md               ← ML pipeline documentation
ml_pipeline/data/                   ← Training data directory (files NOT committed)
tests/conftest.py                   ← Pytest config + path setup
tests/test_chat.py                  ← Chat API integration tests
tests/test_crisis_detection.py      ← Crisis detection unit tests
tests/test_assessments.py           ← Assessment scoring unit tests
scripts/setup_db.py                 ← DB table creation + demo seeding
scripts/generate_widget_token.py    ← Widget token generator
```

---

## 10. HOW TO CONTINUE BUILDING

### Priority Order for Next Steps

#### P0 — Must Have for Investor Demo

1. **Complete `therapeutic_ai_service.py`**
   - Implement `_detect_patient_stage()` with DB query
   - Wire up the full pipeline (crisis → RAG → prompt → LLM)
   - Test end-to-end with Together AI key

2. **Complete `chat_routes.py`**
   - Implement streaming response via WebSocket
   - Store messages to DB via `ChatMessage` model
   - Update session `current_step` after each response

3. **Complete `crisis_detection_service.escalate()`**
   - Log crisis event to DB
   - Send WebSocket alert to clinician via `WebSocketManager`
   - Send email via SendGrid

4. **Complete auth flow**
   - `auth_routes.py` → query DB for clinician, verify bcrypt password
   - `/users/me` endpoint to return user details from JWT
   - Frontend `AuthContext` → call `/users/me` after login

5. **Complete widget config**
   - `widget_routes.py` → look up tenant by `widget_token` from DB
   - Return real persona config

#### P1 — For Demo Polish

6. **Razorpay payment flow** — end-to-end test in test mode
7. **Google Calendar integration** — OAuth token storage + event creation
8. **Clinician Dashboard** — real data from API (not empty arrays)
9. **Assessment flow** — wire frontend to backend, store results

#### P2 — Production Readiness

10. **Rate limiting** — implement Redis sliding window in `rate_limit_middleware.py`
11. **Alembic migrations** — run `alembic revision --autogenerate` to generate first migration
12. **Redis session management** — move session state from in-memory to Redis
13. **Dropout scheduler** — add APScheduler job calling `dropout_service.scan_inactive_patients()`

### Running Locally

```bash
# Option A: Docker Compose (recommended)
cd "c:/saath ai prototype/therapeutic-copilot"
cp .env.example .env
# Edit .env — add TOGETHER_API_KEY at minimum
docker compose up --build

# Option B: Manual (without Docker)
# Backend
cd server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/setup_db.py --seed
uvicorn main:app --reload --port 8000

# Frontend
cd client
npm install
npm run dev
```

### Running Tests

```bash
cd "c:/saath ai prototype/therapeutic-copilot"
pip install pytest pytest-asyncio httpx

# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_crisis_detection.py -v

# Speed check
pytest tests/test_crisis_detection.py::test_scan_speed -v
```

---

## 11. KNOWN TODOS & NEXT STEPS

These are placeholder implementations that need to be completed:

| File | TODO |
|------|------|
| `services/therapeutic_ai_service.py` | `_detect_patient_stage()` — query Patient DB |
| `services/therapeutic_ai_service.py` | Persist messages to `ChatMessage` table |
| `services/chatbot_service.py` | Load `current_step` from DB session |
| `services/crisis_detection_service.py` | `escalate()` — WebSocket alert + SendGrid email |
| `services/rag_service.py` | Fix sync `SentenceTransformer` call (should be async/threadpool) |
| `routes/auth_routes.py` | DB query for clinician login |
| `routes/widget_routes.py` | DB lookup by widget_token |
| `middleware/rate_limit_middleware.py` | Implement Redis sliding window |
| `api/tenants.py` | Admin auth guard |
| `client/src/contexts/AuthContext.tsx` | Call `/users/me` to populate user state |
| `client/src/components/clinician/ClinicianDashboard.tsx` | Load real patient data |

---

*This document is updated with every build session. Last updated: March 6, 2026.*
*Built by: Claude Sonnet 4.6 (AI Agent) + cpdoryl*
