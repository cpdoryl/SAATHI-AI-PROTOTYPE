# Saathi AI — Therapeutic Co-Pilot
## Developer Setup & Prototype Build Guide

> **For**: All developers contributing to the Saathi AI prototype
> **Goal**: Get a working local dev environment running and understand exactly how to build each prototype module
> **Reference**: See [PROTOTYPE_BUILDING_DOCUMENT.md](./PROTOTYPE_BUILDING_DOCUMENT.md) for full architecture, workflows, and investor context

---

## Table of Contents

1. [Before You Start — Read This](#1-before-you-start)
2. [Repository Structure](#2-repository-structure)
3. [Prerequisites & Tooling](#3-prerequisites--tooling)
4. [Environment Setup — Local Dev](#4-environment-setup--local-dev)
5. [Backend Setup (FastAPI)](#5-backend-setup-fastapi)
6. [Frontend Setup (React + TypeScript)](#6-frontend-setup-react--typescript)
7. [Database Setup](#7-database-setup)
8. [AI / Inference Setup](#8-ai--inference-setup)
9. [RAG Knowledge Base Setup](#9-rag-knowledge-base-setup)
10. [Running the Full Stack Locally](#10-running-the-full-stack-locally)
11. [Docker Compose (Recommended)](#11-docker-compose-recommended)
12. [Module-by-Module Build Guide](#12-module-by-module-build-guide)
13. [API Reference & Testing](#13-api-reference--testing)
14. [Environment Variables Reference](#14-environment-variables-reference)
15. [Code Standards & Workflow](#15-code-standards--workflow)
16. [Testing Guide](#16-testing-guide)
17. [Deployment to E2E Networks](#17-deployment-to-e2e-networks)
18. [Troubleshooting](#18-troubleshooting)
19. [Team Role Guide — Who Builds What](#19-team-role-guide--who-builds-what)

---

## 1. Before You Start

### What is Saathi AI?

Saathi AI is a **B2B SaaS therapeutic co-pilot** that allows mental health clinics to embed an AI-powered chat widget on their website. The AI handles:
- **Stage 1** — Lead generation: converting website visitors into booked therapy appointments
- **Stage 2** — Therapeutic co-pilot: structured AI-assisted therapeutic conversations between sessions
- **Stage 3** — Dropout re-engagement: bringing inactive patients back

The AI runs on a **self-hosted Qwen 2.5-7B** model fine-tuned with two LoRA adapters on 3,651 therapeutic conversations.

### Prototype Goal

Build a **working demo** to show investors these flows:
1. Widget embeds on any website with one `<script>` tag
2. AI conversations feel clinically appropriate
3. Crisis detection works and escalates correctly
4. Clinician dashboard shows real-time alerts and patient data
5. Booking + payment flows complete end-to-end

### Key Architectural Decisions (Do Not Change Without Discussion)
- **Backend**: FastAPI (Python 3.11) — not Node.js Express
- **AI**: Qwen 2.5-7B GGUF via llama.cpp — not OpenAI/Gemini APIs
- **DB**: PostgreSQL for production, SQLite for local dev
- **Widget**: Shadow DOM isolation — not iframes
- **Payments**: Razorpay (India-first) — Stripe is deprecated
- **Infra**: E2E Networks Mumbai (Indian data sovereignty)

---

## 2. Repository Structure

```
SAATHI-AI-CO-PILOT-B2B-SaaS-app-develop-copy/
│
├── therapeutic-copilot/            ← MAIN APPLICATION (work here)
│   ├── server/                     ← FastAPI backend
│   │   ├── main.py                 ← App entry point
│   │   ├── database.py             ← DB engine + session factory
│   │   ├── models.py               ← SQLAlchemy ORM models
│   │   ├── config.py               ← App configuration
│   │   ├── config_manager.py       ← Environment variable manager
│   │   ├── requirements.txt        ← Python dependencies
│   │   ├── api/                    ← Route handlers (thin layer)
│   │   │   ├── chat.py
│   │   │   ├── payments.py
│   │   │   ├── appointments.py
│   │   │   ├── leads.py
│   │   │   ├── tenants.py
│   │   │   └── users.py
│   │   ├── routes/                 ← Additional route modules
│   │   │   ├── chat_routes.py
│   │   │   ├── auth_routes.py
│   │   │   ├── assessment_routes.py
│   │   │   ├── crisis_routes.py
│   │   │   ├── rag_routes.py
│   │   │   ├── widget_routes.py
│   │   │   ├── payment_routes.py
│   │   │   ├── websocket_routes.py
│   │   │   └── ...
│   │   ├── services/               ← Business logic (work here most)
│   │   │   ├── therapeutic_ai_service.py   ← Core AI orchestrator
│   │   │   ├── chatbot_service.py          ← Chat state machine
│   │   │   ├── crisis_detection_service.py ← Crisis keywords engine
│   │   │   ├── assessment_service.py       ← PHQ-9, GAD-7, etc.
│   │   │   ├── rag_service.py              ← Pinecone RAG
│   │   │   ├── qwen_inference.py           ← llama.cpp wrapper
│   │   │   ├── lora_model_service.py       ← Stage 1/2 adapter switching
│   │   │   ├── payment_service.py          ← Razorpay integration
│   │   │   ├── lead_service.py             ← Stage 1 lead logic
│   │   │   ├── dropout_service.py          ← Stage 3 re-engagement
│   │   │   ├── websocket_manager.py        ← Real-time connections
│   │   │   └── embedding_service.py        ← 384-dim embeddings
│   │   ├── middleware/             ← Auth, rate limiting, validation
│   │   ├── auth/                   ← JWT token management
│   │   ├── alembic/                ← DB migration scripts
│   │   └── models/                 ← Pydantic schemas
│   │
│   ├── client/                     ← React + TypeScript frontend
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── chatbot/        ← Main chat widget UI
│   │   │   │   ├── clinician/      ← Clinician dashboard
│   │   │   │   ├── patient/        ← Patient portal
│   │   │   │   ├── analytics/      ← Charts & metrics
│   │   │   │   ├── admin/          ← Admin panel
│   │   │   │   ├── landing/        ← Landing page
│   │   │   │   ├── payment/        ← Razorpay UI
│   │   │   │   └── ui/             ← Shared UI primitives
│   │   │   ├── pages/
│   │   │   ├── hooks/
│   │   │   ├── lib/                ← API client functions
│   │   │   ├── contexts/           ← React context providers
│   │   │   └── types/
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   ├── widget/                     ← Standalone embeddable widget
│   │   ├── src/
│   │   │   ├── widget.ts           ← Entry point + Shadow DOM init
│   │   │   └── components/         ← Widget-specific components
│   │   └── vite.config.widget.ts   ← Widget build config
│   │
│   ├── ml_pipeline/                ← Training scripts & datasets
│   ├── tests/                      ← Integration tests
│   ├── scripts/                    ← Utility scripts
│   ├── docker-compose.yml          ← Local dev orchestration
│   ├── .env                        ← Your local secrets (NEVER commit)
│   └── .env.example                ← Template for .env
│
├── .env.example                    ← Root-level env template (full)
├── PROTOTYPE_BUILDING_DOCUMENT.md  ← Architecture & investor doc
├── DEVELOPER_SETUP_README.md       ← This file
└── docker-compose.prod.yml         ← Production deployment
```

> **Rule**: All application code lives inside `therapeutic-copilot/`. Root-level `.md` files are documentation only.

---

## 3. Prerequisites & Tooling

Install the following before cloning:

### Required
| Tool | Version | Install |
|------|---------|---------|
| **Python** | 3.11+ | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org/) |
| **npm** | 9+ | Comes with Node.js |
| **Git** | Latest | [git-scm.com](https://git-scm.com/) |
| **Docker Desktop** | Latest | [docker.com](https://www.docker.com/products/docker-desktop/) |
| **PostgreSQL** | 15 | [postgresql.org](https://www.postgresql.org/) — or use Docker |
| **Redis** | 7+ | [redis.io](https://redis.io/) — or use Docker |

### Verify Your Installations
```bash
python --version        # Python 3.11.x
node --version          # v18.x.x or higher
npm --version           # 9.x.x or higher
docker --version        # Docker 24.x or higher
git --version           # git 2.x.x
```

### Recommended Dev Tools
| Tool | Purpose |
|------|---------|
| **VS Code** | Primary IDE |
| **VS Code — Python extension** | IntelliSense, debugging |
| **VS Code — ESLint extension** | Frontend linting |
| **VS Code — Prettier extension** | Auto-formatting |
| **Postman or Bruno** | API testing |
| **TablePlus or DBeaver** | Database GUI |

### API Keys You Need (Get These First)

Before writing a single line of code, collect these credentials:

| Service | Where to Get | Used For |
|---------|-------------|----------|
| **Together AI** | [api.together.xyz](https://api.together.xyz/) | Qwen 2.5-7B inference (dev/fallback) |
| **Pinecone** | [app.pinecone.io](https://app.pinecone.io/) | RAG vector database |
| **Razorpay (Test)** | [dashboard.razorpay.com](https://dashboard.razorpay.com/) | Payment testing |
| **Google Cloud** | [console.cloud.google.com](https://console.cloud.google.com/) | Calendar API |
| **Sendgrid** | [sendgrid.com](https://sendgrid.com/) | Email notifications |

> **For the prototype**, use **Together AI** (cloud API) instead of self-hosted llama.cpp. Self-hosted inference is for production. Together AI gives you the same Qwen 2.5-7B model at $0.20/1M tokens — cheap enough for development and investor demos.

---

## 4. Environment Setup — Local Dev

### Step 1: Clone the Repository
```bash
git clone <repository-url> SAATHI-AI-CO-PILOT
cd SAATHI-AI-CO-PILOT
```

### Step 2: Create Your `.env` File

Copy the root-level example and the therapeutic-copilot example:
```bash
# Root level (for Docker Compose)
cp .env.example .env

# App level (for server)
cp therapeutic-copilot/.env.example therapeutic-copilot/.env
```

Edit `therapeutic-copilot/.env` and fill in your keys. At minimum you need:
```env
# === REQUIRED FOR PROTOTYPE ===

# AI — Together API (cloud inference, no setup needed)
TOGETHER_API_KEY=your_together_api_key_here
TOGETHER_MODEL=Qwen/Qwen2.5-7B-Instruct-Turbo

# RAG
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX=therapeutic-kb

# Database (SQLite for local dev — no install needed)
DATABASE_URL=sqlite:///./saathi_copilot.db

# Redis (use Docker for local dev)
REDIS_URL=redis://localhost:6379

# Auth
JWT_SECRET_KEY=your-super-secret-key-change-this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Security
ENCRYPTION_KEY=generate-with-command-below

# Payments (use test keys)
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_razorpay_test_secret

# App Config
DEBUG_MODE=true
LOG_LEVEL=DEBUG
PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

**Generate your ENCRYPTION_KEY:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Generate your JWT_SECRET_KEY:**
```bash
openssl rand -hex 32
# On Windows (PowerShell):
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 5. Backend Setup (FastAPI)

### Step 1: Create Python Virtual Environment
```bash
cd therapeutic-copilot

# Create venv
python -m venv .venv

# Activate (Linux/Mac)
source .venv/bin/activate

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Windows CMD)
.\.venv\Scripts\activate.bat
```

### Step 2: Install Python Dependencies
```bash
# Core backend dependencies
pip install -r server/requirements.txt

# RAG dependencies (Pinecone + embeddings)
pip install -r requirements-rag.txt

# Dev/test dependencies (optional but recommended)
pip install -r server/requirements-dev.txt
```

> If you get `psycopg2` install errors on Windows, use `requirements-no-psycopg2.txt` instead. SQLite will be used for local dev automatically.

### Step 3: Initialize the Database
```bash
cd server

# SQLite (default for local dev — auto-creates saathi_copilot.db)
python -c "from database import engine; from models import Base; Base.metadata.create_all(bind=engine); print('DB tables created')"

# OR run dedicated init script
python init_db.py

# Verify tables were created
python -c "from sqlalchemy import inspect; from database import engine; print(inspect(engine).get_table_names())"
```

### Step 4: Start the Backend Server
```bash
# From therapeutic-copilot/server/
uvicorn main:app --reload --port 8000

# Expected output:
# ✅ Configuration management loaded
# ✅ Security middleware available
# ✅ Database tables created (or already exist)
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 5: Verify Backend is Running
```bash
# Health check
curl http://localhost:8000/health

# API docs (auto-generated by FastAPI)
# Open in browser: http://localhost:8000/docs
# Alternate docs:  http://localhost:8000/redoc
```

---

## 6. Frontend Setup (React + TypeScript)

### Step 1: Install Dependencies
```bash
cd therapeutic-copilot/client
npm install
```

### Step 2: Configure Frontend Environment
```bash
# Create frontend .env (Vite reads VITE_ prefixed vars)
cp .env.example .env.local
```

Add to `therapeutic-copilot/client/.env.local`:
```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
VITE_ENABLE_GPT5_MINI=false
```

### Step 3: Start the Dev Server
```bash
npm run dev

# Expected output:
#   VITE v5.x.x  ready in xxx ms
#   ➜  Local:   http://localhost:5173/
#   ➜  Network: http://192.168.x.x:5173/
```

### Step 4: Build Type Check
```bash
# Check for TypeScript errors
npx tsc --noEmit

# Lint check
npm run lint
```

---

## 7. Database Setup

### Option A: SQLite (Local Dev — No Install)
- **No setup needed.** The backend auto-creates `saathi_copilot.db` in `therapeutic-copilot/server/`
- Suitable for solo development and testing
- Do **not** use for multi-developer shared environment

### Option B: PostgreSQL via Docker (Recommended for Team Dev)
```bash
# From therapeutic-copilot/
docker compose up db redis -d

# Wait 10 seconds for DB to initialize, then:
# Update .env:
DATABASE_URL=postgresql://saathi:password@localhost:5432/saathi

# Run migrations
cd server
alembic upgrade head
```

### Running Alembic Migrations
```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration after changing models.py
alembic revision --autogenerate -m "add_crisis_alerts_table"

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history --verbose
```

### Seed Test Data
```bash
# From therapeutic-copilot/server/
python scripts/seed_data.py    # Creates test clinic, clinician, patient accounts
```

Default test credentials after seeding:
```
Clinician:  clinician@test.saathi.ai / TestPass123!
Patient:    patient@test.saathi.ai  / TestPass123!
Admin:      admin@test.saathi.ai    / AdminPass123!
```

---

## 8. AI / Inference Setup

### Option A: Together AI — Cloud (Use for Prototype & Development)

This is the **simplest and recommended approach** for the prototype. No local model download needed.

1. Get your key from [api.together.xyz](https://api.together.xyz/)
2. Set in `.env`:
   ```env
   TOGETHER_API_KEY=your_key_here
   TOGETHER_MODEL=Qwen/Qwen2.5-7B-Instruct-Turbo
   ```
3. The `qwen_inference.py` service will automatically route to Together API when `MODEL_PATH` is not set

**Cost**: ~$0.20 per 1M tokens. For the prototype demo (few hundred messages), cost is negligible (<$1).

### Option B: Self-Hosted llama.cpp — Production (E2E Networks)

Use this for the deployed prototype on the investor demo server.

#### On your E2E Networks server (SSH in first):
```bash
# Step 1: Install build dependencies
sudo apt update && sudo apt install -y build-essential cmake git python3-pip

# Step 2: Install llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make -j4

# Step 3: Download the Qwen model (4.5GB)
mkdir -p /opt/saathi/models
cd /opt/saathi/models

# Download Qwen 2.5-7B GGUF (Q4_K_M quantized)
wget https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf

# Step 4: Test inference
/home/ubuntu/llama.cpp/main \
  -m /opt/saathi/models/qwen2.5-7b-instruct-q4_k_m.gguf \
  -p "You are a helpful therapeutic assistant." \
  -n 100

# Step 5: Install llama-cpp-python (Python binding)
pip install llama-cpp-python

# Step 6: Update .env on server
MODEL_PATH=/opt/saathi/models/qwen2.5-7b-instruct-q4_k_m.gguf
LLAMA_N_CTX=8192
LLAMA_N_THREADS=4
LLAMA_N_GPU_LAYERS=0
```

### Option C: LoRA Adapters (Fine-Tuned Models)

If you have the trained LoRA adapters (contact ML engineer for model files):

```bash
# Place adapter files in:
therapeutic-copilot/server/models/
├── qwen-lora-stage1/       ← Stage 1: Lead generation adapter
│   ├── adapter_config.json
│   └── adapter_model.bin
└── qwen-lora-stage2/       ← Stage 2: Therapeutic co-pilot adapter
    ├── adapter_config.json
    └── adapter_model.bin

# Update .env:
MODEL_STAGE_1_PATH=./models/qwen-lora-stage1
MODEL_STAGE_2_PATH=./models/qwen-lora-stage2
```

> **For the prototype demo**: Use Together AI (Option A). LoRA adapters improve therapeutic quality but Together AI's base Qwen 2.5-7B is sufficient to demonstrate the concept to investors.

---

## 9. RAG Knowledge Base Setup

RAG (Retrieval-Augmented Generation) lets the AI answer clinic-specific questions by fetching relevant documents before generating a response.

### Step 1: Install RAG Dependencies
```bash
pip install -r requirements-rag.txt
```

### Step 2: Run the RAG Setup Script
```bash
# From therapeutic-copilot/
python setup_rag.py
```

This script will:
- Verify your Pinecone API key
- Create the `therapeutic-kb` index (384-dim, cosine similarity)
- Test the embedding service
- Optionally ingest base knowledge documents

### Step 3: Seed the Knowledge Base
```bash
# Ingest the default knowledge base documents
python scripts/ingest_knowledge_base.py \
  --source knowledge-base.md \
  --tenant default

# Add clinic-specific documents (for multi-tenant demo)
python scripts/ingest_knowledge_base.py \
  --source /path/to/clinic-faq.pdf \
  --tenant clinic_ABC123
```

### Step 4: Test RAG Query
```bash
python -c "
from server.services.rag_service import RAGService
rag = RAGService()
results = rag.query('What therapy approaches do you use?', tenant_id='default')
print(results)
"
```

---

## 10. Running the Full Stack Locally

Run each of these in **separate terminal windows**:

### Terminal 1 — Backend API
```bash
cd therapeutic-copilot
source .venv/bin/activate      # or .\.venv\Scripts\Activate.ps1 on Windows
cd server
uvicorn main:app --reload --port 8000
```

### Terminal 2 — Frontend
```bash
cd therapeutic-copilot/client
npm run dev
```

### Terminal 3 — Redis (if not using Docker)
```bash
redis-server
# Or on Windows: use Redis for Windows or Docker
```

### Terminal 4 — Celery Worker (for background jobs)
```bash
cd therapeutic-copilot
source .venv/bin/activate
celery -A server.tasks worker --loglevel=info
```

### Access Points
| Service | URL |
|---------|-----|
| Frontend App | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |
| Widget Demo | http://localhost:5173/widget-demo |

---

## 11. Docker Compose (Recommended)

Using Docker Compose is the **easiest way** to run all services without manual terminal management.

### Start All Services
```bash
cd therapeutic-copilot
docker compose up --build
```

This starts:
- `server` — FastAPI backend on port 4000
- `client` — React frontend on port 3000
- `db` — PostgreSQL 15 on port 5432
- (Add Redis to `docker-compose.yml` if not present)

### Useful Docker Commands
```bash
# Start in background
docker compose up -d

# View logs
docker compose logs -f server
docker compose logs -f client

# Rebuild after code changes
docker compose up --build server

# Stop everything
docker compose down

# Stop and delete volumes (reset DB)
docker compose down -v

# Shell into the backend container
docker compose exec server bash

# Run migrations inside container
docker compose exec server alembic upgrade head
```

### Updating the docker-compose.yml

Add Redis support to `therapeutic-copilot/docker-compose.yml`:
```yaml
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  db_data:
  redis_data:
```

---

## 12. Module-by-Module Build Guide

This section maps each prototype feature to the **exact files you need to work in**.

---

### Module 1 — Stage 1: Lead Generation Chat

**Owner**: Backend Engineer 1 + Frontend Engineer

**Backend files**:
- [therapeutic-copilot/server/services/lead_service.py](therapeutic-copilot/server/services/lead_service.py) — Stage 1 conversation logic
- [therapeutic-copilot/server/services/chatbot_service.py](therapeutic-copilot/server/services/chatbot_service.py) — Chat state machine (which stage are we in?)
- [therapeutic-copilot/server/routes/chat_routes.py](therapeutic-copilot/server/routes/chat_routes.py) — `POST /chat` endpoint
- [therapeutic-copilot/server/services/qwen_inference.py](therapeutic-copilot/server/services/qwen_inference.py) — LLM call wrapper

**Frontend files**:
- [therapeutic-copilot/client/src/components/chatbot/ChatWidget.tsx](therapeutic-copilot/client/src/components/chatbot/ChatWidget.tsx) — Main chat UI
- [therapeutic-copilot/client/src/lib/chatApi.ts](therapeutic-copilot/client/src/lib/chatApi.ts) — API client

**Test this module**:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, I am looking for therapy help", "stage": 1, "session_id": "test123"}'
```

---

### Module 2 — Stage 2: Therapeutic Co-Pilot

**Owner**: Backend Engineer 1 + ML Engineer

**Backend files**:
- [therapeutic-copilot/server/services/therapeutic_ai_service.py](therapeutic-copilot/server/services/therapeutic_ai_service.py) — 11-step flow orchestrator
- [therapeutic-copilot/server/services/lora_model_service.py](therapeutic-copilot/server/services/lora_model_service.py) — Switch to Stage 2 LoRA adapter
- [therapeutic-copilot/server/routes/therapeutic_routes.py](therapeutic-copilot/server/routes/therapeutic_routes.py) — Therapeutic endpoints

**Key logic**: `therapeutic_ai_service.py` must track which of the 11 steps the conversation is currently in. Store step state in Redis (key: `session:{session_id}:step`).

**Test this module**:
```bash
# After a booking is confirmed (stage transitions from 1 → 2):
curl -X POST http://localhost:8000/api/therapeutic/chat \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{"message": "I have been feeling very anxious lately", "session_id": "test123"}'
```

---

### Module 3 — Clinical Assessments

**Owner**: Backend Engineer 2

**Backend files**:
- [therapeutic-copilot/server/services/assessment_service.py](therapeutic-copilot/server/services/assessment_service.py) — Assessment logic
- [therapeutic-copilot/server/services/assessment_scoring_service.py](therapeutic-copilot/server/services/assessment_scoring_service.py) — Score calculation per test
- [therapeutic-copilot/server/routes/assessment_routes.py](therapeutic-copilot/server/routes/assessment_routes.py) — Assessment endpoints

**Scoring logic for each test**:
```python
# Example: PHQ-9 scoring
# Sum all 9 items (0-3 each) → total 0-27
# 0-4:  Minimal depression
# 5-9:  Mild depression
# 10-14: Moderate depression
# 15-19: Moderately severe
# 20-27: Severe depression
```

**Test this module**:
```bash
curl -X POST http://localhost:8000/api/assessments/submit \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "test_type": "PHQ9",
    "patient_id": "patient_123",
    "responses": [2, 1, 3, 2, 1, 0, 2, 1, 1]
  }'
```

---

### Module 4 — Crisis Detection

**Owner**: Backend Engineer 1

**This is the most critical module from a safety perspective.**

**Backend files**:
- [therapeutic-copilot/server/services/crisis_detection_service.py](therapeutic-copilot/server/services/crisis_detection_service.py) — Keyword scoring engine
- [therapeutic-copilot/server/routes/crisis_routes.py](therapeutic-copilot/server/routes/crisis_routes.py) — Crisis alert endpoints
- [therapeutic-copilot/server/services/websocket_manager.py](therapeutic-copilot/server/services/websocket_manager.py) — Real-time alert push

**How it works**:
1. Every incoming message is scanned BEFORE being sent to the LLM
2. 30+ weighted keywords are checked (e.g., "suicide" = 10, "hopeless" = 4)
3. Score 7–10 → block AI response, trigger immediate escalation
4. Score 4–6 → alert clinician, include safety resources in AI response
5. Score 1–3 → log silently, monitor

**Never bypass this check.** Crisis detection must run on every single user message.

**WebSocket for real-time alerts**:
```javascript
// Frontend clinician dashboard connects to:
const ws = new WebSocket('ws://localhost:8000/ws/crisis-alerts/{clinician_id}')
ws.onmessage = (event) => {
  const alert = JSON.parse(event.data)
  // Show banner immediately
}
```

---

### Module 5 — RAG Knowledge Base

**Owner**: ML Engineer

**Backend files**:
- [therapeutic-copilot/server/services/rag_service.py](therapeutic-copilot/server/services/rag_service.py) — Query + ingest
- [therapeutic-copilot/server/services/embedding_service.py](therapeutic-copilot/server/services/embedding_service.py) — Generate 384-dim embeddings
- [therapeutic-copilot/server/routes/rag_routes.py](therapeutic-copilot/server/routes/rag_routes.py) — Upload/query endpoints

**The RAG flow**:
```
User message
    │
    ▼
Generate embedding (sentence-transformers, 384-dim)
    │
    ▼
Query Pinecone (top-K=5, cosine similarity)
    │
    ▼
Retrieved context chunks injected into prompt
    │
    ▼
Qwen generates response with clinic-specific knowledge
```

---

### Module 6 — Clinician Dashboard

**Owner**: Frontend Engineer

**Frontend files**:
- [therapeutic-copilot/client/src/components/clinician/](therapeutic-copilot/client/src/components/clinician/) — All clinician UI components
- [therapeutic-copilot/client/src/components/analytics/](therapeutic-copilot/client/src/components/analytics/) — Charts and metrics
- [therapeutic-copilot/client/src/pages/](therapeutic-copilot/client/src/pages/) — Dashboard page routes

**Key features to build**:
1. Patient list with status indicators (active/at-risk/crisis)
2. Conversation history viewer (timeline format)
3. Assessment score trends (use Recharts)
4. Crisis alert banner (connects to WebSocket)
5. Session notes editor with AI-generated summary

---

### Module 7 — B2B Embeddable Widget

**Owner**: Frontend Engineer + DevOps Engineer

**Widget files**:
- [therapeutic-copilot/widget/](therapeutic-copilot/widget/) — Standalone widget package

**Build the widget**:
```bash
cd therapeutic-copilot/widget
npm install
npm run build:widget

# Output: dist/widget.js (~50KB gzipped)
# This file gets hosted on CDN
```

**Test widget embed locally**:
```html
<!-- Open therapeutic-copilot/tidio-style-widget-demo.html in a browser -->
<!-- Or create a test.html with: -->
<!DOCTYPE html>
<html>
<body>
  <h1>Test Clinic Website</h1>
  <script
    src="http://localhost:5173/widget.js"
    data-clinic-id="DEMO_CLINIC"
    data-color="#6366f1">
  </script>
</body>
</html>
```

**Critical requirement**: Widget must work via Shadow DOM — no CSS leaking to/from the host page.

---

### Module 8 — Booking & Payment

**Owner**: Backend Engineer 2

**Backend files**:
- [therapeutic-copilot/server/services/payment_service.py](therapeutic-copilot/server/services/payment_service.py) — Razorpay integration
- [therapeutic-copilot/server/routes/payment_routes.py](therapeutic-copilot/server/routes/payment_routes.py) — Payment endpoints
- [therapeutic-copilot/server/api/appointments.py](therapeutic-copilot/server/api/appointments.py) — Calendar booking

**Razorpay payment flow**:
```
Backend creates order → Frontend opens Razorpay modal
    → Patient pays → Razorpay sends webhook to /webhooks/razorpay
    → Backend verifies signature → Books appointment → Sends confirmation
```

**Frontend files**:
- [therapeutic-copilot/client/src/components/payment/](therapeutic-copilot/client/src/components/payment/) — Payment UI

**Test payments (Razorpay test mode)**:
```
Test card: 4111 1111 1111 1111
Expiry:    Any future date
CVV:       Any 3 digits
OTP:       1234 (for UPI simulation)
```

---

## 13. API Reference & Testing

### Full API Documentation
Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Quick API Test with curl

**Register a clinician**:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "dr.test@clinic.com",
    "password": "SecurePass123!",
    "full_name": "Dr. Test Clinician",
    "role": "clinician",
    "tenant_id": "clinic_001"
  }'
```

**Login**:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "dr.test@clinic.com", "password": "SecurePass123!"}'
# Response includes: access_token
```

**Send a chat message**:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"message": "I need help with anxiety", "session_id": "sess_001"}'
```

**Submit PHQ-9 Assessment**:
```bash
curl -X POST http://localhost:8000/api/assessments/submit \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "test_type": "PHQ9",
    "responses": [2, 1, 3, 2, 1, 0, 2, 1, 1]
  }'
```

### Running the Full API Test Suite
```bash
cd therapeutic-copilot
python test_real_world_api.py
python test_conversation_complete.py
python validate_system.py
```

---

## 14. Environment Variables Reference

All environment variables with descriptions. Set these in `therapeutic-copilot/.env`:

```env
# =============================================
# AI CONFIGURATION
# =============================================
# For prototype dev: use Together AI (no local model needed)
TOGETHER_API_KEY=                    # REQUIRED: From api.together.xyz
TOGETHER_MODEL=Qwen/Qwen2.5-7B-Instruct-Turbo

# For production self-hosted:
# MODEL_PATH=/opt/saathi/models/qwen2.5-7b-instruct-q4_k_m.gguf
# MODEL_STAGE_1_PATH=./models/qwen-lora-stage1
# MODEL_STAGE_2_PATH=./models/qwen-lora-stage2
# LLAMA_N_CTX=8192
# LLAMA_N_THREADS=4
# LLAMA_N_GPU_LAYERS=0

QWEN_MAX_TOKENS=512
QWEN_TEMPERATURE=0.7
QWEN_TOP_P=0.9

# =============================================
# RAG KNOWLEDGE BASE
# =============================================
PINECONE_API_KEY=                    # REQUIRED
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX=therapeutic-kb

# =============================================
# DATABASE
# =============================================
DATABASE_URL=sqlite:///./saathi_copilot.db    # Local dev
# DATABASE_URL=postgresql://saathi:password@localhost:5432/saathi  # With Docker

# =============================================
# REDIS
# =============================================
REDIS_URL=redis://localhost:6379

# =============================================
# AUTHENTICATION
# =============================================
JWT_SECRET_KEY=                      # REQUIRED: generate with openssl rand -hex 32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# =============================================
# ENCRYPTION (for PHI data at rest)
# =============================================
ENCRYPTION_KEY=                      # REQUIRED: generate with Fernet.generate_key()

# =============================================
# PAYMENTS
# =============================================
RAZORPAY_KEY_ID=                     # REQUIRED for payment module
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=

# =============================================
# GOOGLE CALENDAR
# =============================================
GOOGLE_CALENDAR_CREDENTIALS_PATH=./credentials/google_calendar_credentials.json
GOOGLE_CALENDAR_TOKEN_PATH=./credentials/google_calendar_token.json

# =============================================
# EMAIL (SendGrid)
# =============================================
SENDGRID_API_KEY=
SMTP_FROM=noreply@saathi.ai

# =============================================
# CRISIS ALERTS
# =============================================
CRISIS_ALERT_EMAIL=crisis@yourclinic.com
CRISIS_ALERT_SMS=+919876543210

# =============================================
# APP SETTINGS
# =============================================
PORT=8000
DEBUG_MODE=true
LOG_LEVEL=DEBUG
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# =============================================
# WIDGET
# =============================================
WIDGET_ENABLED=true
WIDGET_DEFAULT_THEME=light
WIDGET_DEFAULT_POSITION=bottom-right
WIDGET_BUBBLE_COLOR=#6366F1

# =============================================
# FEATURE FLAGS
# =============================================
ENABLE_STAGE_AUTO_SWITCHING=true
ENABLE_RAG_FALLBACK=true
ENABLE_HIPAA_AUDIT_LOGGING=true
ENABLE_WIDGET_ANALYTICS=true
```

---

## 15. Code Standards & Workflow

### Git Workflow
```
main          ← Protected. Only merged via PR after review.
develop       ← Integration branch. All features merge here first.
feature/*     ← Your feature branches (e.g., feature/crisis-detection)
fix/*         ← Bug fix branches (e.g., fix/assessment-scoring)
```

**Creating a feature branch**:
```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
# ... do work ...
git push origin feature/your-feature-name
# Open PR to merge into develop
```

**Commit message format**:
```
feat: add PHQ-9 scoring algorithm
fix: resolve WebSocket reconnection issue
docs: update API endpoint reference
test: add integration tests for crisis detection
refactor: simplify LoRA adapter switching logic
```

### Python Code Standards
```bash
# Format all Python code before committing
black server/
isort server/
flake8 server/ --max-line-length=100

# Type checking
mypy server/ --ignore-missing-imports
```

### TypeScript/React Standards
```bash
# Format before committing
npm run lint
npx prettier --write src/

# Run type check
npx tsc --noEmit
```

### PR Requirements
Before opening a PR:
- [ ] All tests pass locally (`pytest` + `npm test`)
- [ ] No TypeScript errors (`npx tsc --noEmit`)
- [ ] Code formatted (`black` + `prettier`)
- [ ] Added tests for new business logic
- [ ] Updated API docs if you changed endpoints
- [ ] Environment variable changes documented in `.env.example`

---

## 16. Testing Guide

### Backend Tests (Pytest)
```bash
cd therapeutic-copilot

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=server --cov-report=html
open htmlcov/index.html    # View coverage report

# Run specific test file
pytest tests/test_crisis_detection.py -v

# Run specific test
pytest tests/test_assessments.py::test_phq9_scoring -v

# Run integration tests (requires running server)
python test_real_world_api.py
python test_pipeline_smoke.py
```

### Frontend Tests (Jest + React Testing Library)
```bash
cd therapeutic-copilot/client

# Run unit tests
npm test

# Watch mode
npm run test:watch

# End-to-end tests (requires running full stack)
npm run e2e
```

### Manual Test Checklist (Before Each Demo)

Run through these manually before any investor/stakeholder demo:

```
STAGE 1 FLOW:
[ ] Open widget on demo page → greeting appears
[ ] Have a 3-exchange conversation → AI stays on topic
[ ] Trigger booking intent → calendar slot picker appears
[ ] Complete payment → confirmation message sent

STAGE 2 FLOW:
[ ] Log in as patient → therapeutic mode activates
[ ] Complete 5 conversation turns → AI follows therapeutic structure
[ ] Crisis keyword triggered → alert appears on clinician dashboard

ASSESSMENTS:
[ ] PHQ-9 completes → score calculated correctly
[ ] GAD-7 completes → severity level shown

CLINICIAN DASHBOARD:
[ ] Patient list loads → shows active conversations
[ ] Crisis alert received in real-time (via WebSocket)
[ ] Assessment scores visible with trend chart

WIDGET:
[ ] Embed widget on test HTML page → appears correctly
[ ] Chat works through embedded widget
[ ] No CSS leaks from widget to host page
```

---

## 17. Deployment to E2E Networks

### First-Time Server Setup

```bash
# SSH into E2E Networks server
ssh ubuntu@your-e2e-server-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Nginx
sudo apt install -y nginx certbot python3-certbot-nginx

# Clone repository
git clone <repository-url> /opt/saathi
cd /opt/saathi
```

### Configure Production `.env`

```bash
cp .env.example .env
nano .env    # Fill in all production values
```

Production-specific changes:
```env
DEBUG_MODE=false
LOG_LEVEL=INFO
DATABASE_URL=postgresql://saathi:strongpassword@localhost:5432/saathi_prod
CORS_ORIGINS=https://yourdomain.com,https://demo.saathi.ai
MODEL_PATH=/opt/saathi/models/qwen2.5-7b-instruct-q4_k_m.gguf
```

### Start Production Services
```bash
# From /opt/saathi
docker compose -f docker-compose.prod.yml up -d

# Run DB migrations
docker compose -f docker-compose.prod.yml exec server alembic upgrade head

# Set up Nginx with SSL
sudo certbot --nginx -d demo.saathi.ai
```

### Nginx Config (paste to `/etc/nginx/sites-available/saathi`):
```nginx
server {
    listen 443 ssl;
    server_name demo.saathi.ai;

    # SSL managed by certbot

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
    }
}
```

### CI/CD with GitHub Actions

The `.github/workflows/` directory contains automated deploy pipelines. On every push to `main`:
1. Tests run automatically
2. Docker image builds
3. Deploys to E2E Networks server via SSH

Set these GitHub Secrets in your repo settings:
```
E2E_SERVER_IP        ← Your E2E Networks server IP
E2E_SSH_KEY          ← Private SSH key for server access
DOCKER_USERNAME       ← Docker Hub username
DOCKER_PASSWORD       ← Docker Hub password or token
```

---

## 18. Troubleshooting

### Common Issues & Fixes

**`ImportError: No module named 'psycopg2'`**
```bash
# Use SQLite for local dev (no psycopg2 needed)
DATABASE_URL=sqlite:///./saathi_copilot.db

# Or install psycopg2 binary
pip install psycopg2-binary
```

**`together` API returning errors**
```bash
# Verify key is valid
python -c "
import together
client = together.Together(api_key='your_key')
print(client.models.list())
"
```

**Port 8000 already in use**
```bash
# Find and kill the process
lsof -ti:8000 | xargs kill -9    # Mac/Linux
netstat -ano | findstr :8000      # Windows (then: taskkill /PID <pid> /F)
```

**React `VITE_API_URL` not being picked up**
```bash
# Make sure you're using VITE_ prefix and it's in client/.env.local (not .env)
# Restart the dev server after any .env changes
```

**Alembic migration conflict**
```bash
# Reset to clean state (destroys data — dev only)
alembic downgrade base
alembic upgrade head
```

**WebSocket connection failing**
```bash
# Check Nginx config has WebSocket proxy headers
# Check CORS_ORIGINS includes your frontend URL
# Confirm ws:// vs wss:// — use wss:// in production
```

**Widget not loading on external page**
```bash
# Check CORS headers on /api/widget/* routes
# Verify data-clinic-id is set on the script tag
# Open browser console for detailed error
```

**Pinecone index not found**
```bash
# Re-run setup
python setup_rag.py

# Or manually create index in Pinecone dashboard
# Name: therapeutic-kb, Dimensions: 384, Metric: cosine
```

---

## 19. Team Role Guide — Who Builds What

### Backend Engineer 1 — AI Services & Core Chat
| Task | Files | Week |
|------|-------|------|
| LLM inference wrapper (Together AI + llama.cpp) | `services/qwen_inference.py` | 1 |
| Stage 1 lead generation chat API | `services/lead_service.py`, `routes/chat_routes.py` | 1 |
| Stage 2 therapeutic 11-step flow | `services/therapeutic_ai_service.py` | 2 |
| Crisis detection engine | `services/crisis_detection_service.py` | 2 |
| NLP meta-model pattern detection | `services/therapeutic_ai_service.py` | 3 |
| Stage 3 dropout detection | `services/dropout_service.py` | 3 |
| WebSocket real-time chat | `services/websocket_manager.py` | 3 |

### Backend Engineer 2 — Integrations & Data
| Task | Files | Week |
|------|-------|------|
| Auth (JWT + role-based access) | `auth/`, `middleware/` | 1 |
| Database models + migrations | `models.py`, `alembic/` | 1 |
| 8 clinical assessments scoring | `services/assessment_service.py` | 2 |
| Razorpay payment integration | `services/payment_service.py` | 2 |
| Google Calendar booking | `api/appointments.py` | 2 |
| Email/SMS notifications | `services/communication_service.py` | 3 |
| Multi-tenant middleware | `middleware/` | 1 |

### Frontend Engineer — UI & Widget
| Task | Files | Week |
|------|-------|------|
| Chat widget UI (Stage 1 + 2) | `components/chatbot/` | 2 |
| Clinician dashboard | `components/clinician/` | 3 |
| Assessment flow UI | `components/` (assessment forms) | 2 |
| Crisis alert panel (WebSocket) | `components/clinician/` | 3 |
| Patient portal | `components/patient/` | 3 |
| Analytics charts | `components/analytics/` | 3 |
| B2B embeddable widget | `widget/src/` | 3 |
| Razorpay payment modal | `components/payment/` | 2 |

### ML/AI Engineer — Models & RAG
| Task | Files | Week |
|------|-------|------|
| Pinecone RAG setup + ingestion | `setup_rag.py`, `services/rag_service.py` | 1 |
| Embedding service | `services/embedding_service.py` | 1 |
| LoRA adapter loading + switching | `services/lora_model_service.py` | 1 |
| Prompt engineering (Stage 1, 2, 3) | `services/therapeutic_ai_service.py` | 2 |
| Model evaluation scripts | `ml_pipeline/scripts/` | 4 |
| RAG document ingestion pipeline | `scripts/ingest_knowledge_base.py` | 2 |

### DevOps Engineer — Infrastructure
| Task | Files | Week |
|------|-------|------|
| Docker Compose for dev | `docker-compose.yml` | 1 |
| E2E Networks server setup | SSH + bash scripts | 1 |
| Nginx config + SSL | `nginx.conf` | 1 |
| GitHub Actions CI/CD | `.github/workflows/` | 2 |
| llama.cpp install + model download | Server setup | 1 |
| CDN setup for widget.js | Cloudflare config | 3 |
| Monitoring (Prometheus + Grafana) | Docker Compose services | 4 |
| Production docker-compose | `docker-compose.prod.yml` | 3 |

---

## Quick Reference Card

```
START BACKEND:    cd therapeutic-copilot/server && uvicorn main:app --reload --port 8000
START FRONTEND:   cd therapeutic-copilot/client && npm run dev
START ALL:        cd therapeutic-copilot && docker compose up --build
API DOCS:         http://localhost:8000/docs
APP:              http://localhost:5173

RUN TESTS:        pytest tests/ -v
FORMAT PYTHON:    black server/ && isort server/
FORMAT JS:        cd client && npx prettier --write src/

ADD MIGRATION:    alembic revision --autogenerate -m "description"
APPLY MIGRATION:  alembic upgrade head

GENERATE JWT KEY: python -c "import secrets; print(secrets.token_hex(32))"
GENERATE ENC KEY: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

*For architecture decisions, workflow diagrams, and investor context — see [PROTOTYPE_BUILDING_DOCUMENT.md](./PROTOTYPE_BUILDING_DOCUMENT.md)*
*For questions, contact the team lead or open an issue in the repository.*
