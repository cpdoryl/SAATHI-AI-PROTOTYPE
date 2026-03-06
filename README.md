# SAATHI AI — Therapeutic Co-Pilot

> **B2B SaaS AI-powered therapeutic co-pilot platform**
> Built by **RYL NEUROACADEMY PRIVATE LIMITED** | Version 1.0 | March 2026

---

## What Is Saathi AI?

Saathi AI is a HIPAA/GDPR/DPDP-compliant B2B SaaS super-application that transforms mental healthcare delivery for psychologists, clinics, hospitals, and corporate EAPs.

**3-Stage Patient Journey:**
1. **Stage 1** — AI lead generation + appointment booking
2. **Stage 2** — 11-step therapeutic co-pilot between sessions
3. **Stage 3** — Dropout re-engagement engine

**Key Differentiators:**
- Self-hosted Qwen 2.5-7B (fine-tuned on 3,651 therapeutic conversations)
- Indian data sovereignty — 100% data on E2E Networks Mumbai
- One-script embeddable widget (`<script>` tag deployment)
- ₹798/month infrastructure cost vs ₹15,000/month competitor APIs

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/cpdoryl/SAATHI-AI-PROTOTYPE.git
cd SAATHI-AI-PROTOTYPE

# Set up environment
cp .env.example .env
cp therapeutic-copilot/.env.example therapeutic-copilot/.env
# Edit therapeutic-copilot/.env with your API keys

# Run with Docker (recommended)
cd therapeutic-copilot
docker compose up --build
```

Frontend → http://localhost:5173
Backend API → http://localhost:8000
API Docs → http://localhost:8000/docs

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [DEVELOPER_SETUP_README.md](./DEVELOPER_SETUP_README.md) | Full developer setup & module build guide |
| [PROTOTYPE_BUILDING_DOCUMENT.md](./PROTOTYPE_BUILDING_DOCUMENT.md) | Architecture, investor spec, tech stack |
| [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) | Step-by-step build log (past records) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11) |
| Frontend | React 18 + TypeScript + Vite |
| AI Model | Qwen 2.5-7B GGUF via llama.cpp |
| Vector DB | Pinecone (RAG) |
| Primary DB | PostgreSQL (SQLite for local dev) |
| Cache | Redis 7+ |
| Payments | Razorpay (India-first) |
| Infra | E2E Networks Mumbai |
| Widget | Shadow DOM isolated embed |

---

## Repository Structure

```
SAATHI-AI-PROTOTYPE/
├── therapeutic-copilot/       ← Main application (work here)
│   ├── server/                ← FastAPI backend
│   ├── client/                ← React + TypeScript frontend
│   ├── widget/                ← Embeddable chat widget
│   ├── ml_pipeline/           ← Training scripts & datasets
│   ├── tests/                 ← Integration tests
│   ├── scripts/               ← Utility scripts
│   └── docker-compose.yml     ← Local dev orchestration
├── DEVELOPER_GUIDE.md         ← Step-by-step build log
├── DEVELOPER_SETUP_README.md  ← Developer setup guide
├── PROTOTYPE_BUILDING_DOCUMENT.md ← Full architecture spec
└── docker-compose.prod.yml    ← Production deployment
```

---

## License

Proprietary — RYL NEUROACADEMY PRIVATE LIMITED. All rights reserved.
