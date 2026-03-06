# SAATHI AI — THERAPEUTIC CO-PILOT
## Prototype Building Document for Investor Validation
### Version 1.0 | March 2026 | RYL NEUROACADEMY PRIVATE LIMITED

---

> **Document Purpose**: This document defines the complete technical specification, workflow diagrams, and tech stack requirements for building a working prototype of Saathi AI — a B2B SaaS AI-powered therapeutic co-pilot platform — to demonstrate to investors and pilot customers.

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement & Market Opportunity](#2-problem-statement--market-opportunity)
3. [Prototype Scope — What We Are Building](#3-prototype-scope)
4. [System Architecture Overview](#4-system-architecture-overview)
5. [End-to-End Workflow Diagram](#5-end-to-end-workflow-diagram)
6. [Core Feature Modules](#6-core-feature-modules)
7. [Tech Stack — Complete Requirements](#7-tech-stack--complete-requirements)
8. [Infrastructure & Deployment Architecture](#8-infrastructure--deployment-architecture)
9. [AI/ML Pipeline](#9-aiml-pipeline)
10. [Database Schema Overview](#10-database-schema-overview)
11. [API Architecture](#11-api-architecture)
12. [Frontend Architecture](#12-frontend-architecture)
13. [B2B Widget Architecture](#13-b2b-widget-architecture)
14. [Security & Compliance](#14-security--compliance)
15. [4-Week Build Timeline](#15-4-week-build-timeline)
16. [Team & Resource Requirements](#16-team--resource-requirements)
17. [Cost Projections](#17-cost-projections)
18. [Investor Demo Checklist](#18-investor-demo-checklist)

---

## 1. EXECUTIVE SUMMARY

**Saathi AI — Therapeutic Co-Pilot** is a HIPAA/GDPR/DPDP-compliant **B2B SaaS super-application** that revolutionizes mental healthcare delivery for psychologists, clinics, hospitals, and corporate EAPs (Employee Assistance Programs).

### What It Does
- Automates **patient acquisition** via AI-powered chat across all channels (web, WhatsApp, Instagram, email, SMS)
- Delivers a structured **11-step therapeutic co-pilot** experience between sessions
- Screens patients using **8 validated clinical assessments** (PHQ-9, GAD-7, PCL-5, etc.)
- Detects **crisis situations** in real-time with escalation protocols
- Provides clinicians a **comprehensive dashboard** with AI-generated session insights
- Deploys as a **one-script embeddable widget** on any client website (Tidio-style)

### Business Model
| Tier | Target | Monthly Price |
|------|--------|--------------|
| Basic | Solo practitioner | ₹2,999/month |
| Professional | 2–5 clinicians | ₹9,999/month |
| Enterprise | 5+ clinicians | Custom |

### Key Differentiators
- **Self-hosted AI** — 93% cost reduction vs API-based competitors (₹798/month vs ₹15,000/month)
- **Indian data sovereignty** — 100% data stays in India on E2E Networks Mumbai
- **Multi-stage fine-tuned LLM** — Qwen 2.5-7B trained on 3,651 therapeutic conversations
- **One-script B2B widget** — deploys on any website in 30 seconds

---

## 2. PROBLEM STATEMENT & MARKET OPPORTUNITY

### Pain Points in Mental Healthcare

| Pain Point | Current Reality | Saathi AI Solution |
|-----------|-----------------|-------------------|
| Patient acquisition | Manual follow-ups, 70% drop-off | AI-powered 24/7 engagement across all channels |
| Assessment overload | Clinician spends 30–45 min on intake | Automated 8-test clinical battery pre-session |
| Between-session gaps | No support between weekly sessions | AI co-pilot available 24/7 |
| Crisis detection | Zero real-time monitoring | 30+ keyword detection with instant escalation |
| Data & insights | Fragmented notes, no AI analysis | Structured AI-generated session summaries |
| Integration | Clinics need new platforms | One `<script>` tag on existing website |

### Market Size (India + SE Asia)
- **TAM**: $4.5B mental healthcare SaaS market (2025)
- **SAM**: 150,000+ registered mental health practitioners in India
- **SOM (Year 1)**: 500 clinics × ₹9,999/month = **₹6 Cr ARR target**

---

## 3. PROTOTYPE SCOPE

### What the Prototype Must Demonstrate

The prototype is scoped to validate **3 core investor hypotheses**:

1. **AI Quality** — The fine-tuned Qwen 2.5-7B delivers clinically appropriate therapeutic conversations
2. **B2B Integration** — The embeddable widget deploys instantly on any website
3. **Clinical Workflow** — The 3-stage patient journey (lead → therapy → re-engagement) works end-to-end

### Prototype Feature Checklist

| # | Feature | Priority | Status |
|---|---------|----------|--------|
| 1 | Stage 1: AI lead generation + booking chat | P0 | 95% complete |
| 2 | Stage 2: Therapeutic co-pilot (11-step flow) | P0 | 90% complete |
| 3 | Stage 3: Dropout re-engagement | P1 | 75% complete |
| 4 | Embeddable chat widget (Tidio-style) | P0 | 60% complete |
| 5 | 8 clinical assessments (PHQ-9 to WHO-5) | P0 | 90% complete |
| 6 | Crisis detection + escalation | P0 | 90% complete |
| 7 | Clinician dashboard | P0 | 85% complete |
| 8 | Patient portal | P1 | 80% complete |
| 9 | Razorpay payment integration | P1 | 85% complete |
| 10 | Google Calendar booking | P1 | 80% complete |
| 11 | RAG knowledge base (per-tenant) | P1 | 85% complete |
| 12 | NLP meta-model detection | P2 | 85% complete |

---

## 4. SYSTEM ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SAATHI AI — SYSTEM ARCHITECTURE                   │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  CLIENT CHANNELS (Entry Points)                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │ Website  │  │WhatsApp  │  │Instagram │  │  Email / SMS Bots    │ │
│  │  Widget  │  │  Bot     │  │  DM Bot  │  │  (Twilio/SendGrid)   │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘ │
└───────┼─────────────┼─────────────┼────────────────────┼─────────────┘
        │             │             │                    │
        └─────────────┴─────────────┴────────────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │         NGINX Reverse Proxy    │
                    │   (SSL Termination + Routing)  │
                    └───────────────┬───────────────┘
                                    │
        ┌───────────────────────────▼────────────────────────────┐
        │              FASTAPI BACKEND (Python 3.11)              │
        │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
        │  │ Stage 1 │  │ Stage 2  │  │ Stage 3  │  │ Widget  │ │
        │  │ Router  │  │ Router   │  │ Router   │  │ Router  │ │
        │  └────┬────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
        │       │            │              │              │      │
        │  ┌────▼────────────▼──────────────▼──────────────▼────┐ │
        │  │              SERVICE LAYER                           │ │
        │  │  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │ │
        │  │  │ Qwen LLM   │  │   Crisis   │  │  Assessment  │  │ │
        │  │  │ Service    │  │ Detection  │  │   Service    │  │ │
        │  │  └────────────┘  └────────────┘  └──────────────┘  │ │
        │  │  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │ │
        │  │  │ RAG Service│  │  Booking   │  │   Payment    │  │ │
        │  │  │(Pinecone)  │  │  Service   │  │   Service    │  │ │
        │  │  └────────────┘  └────────────┘  └──────────────┘  │ │
        │  └─────────────────────────────────────────────────────┘ │
        └───────────────────┬────────────────────────────────────┘
                            │
        ┌───────────────────┴────────────────────────────────────┐
        │                  DATA LAYER                              │
        │  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐   │
        │  │ PostgreSQL  │  │  Pinecone   │  │  Redis Cache  │   │
        │  │(Primary DB) │  │(Vector DB)  │  │(Session/Rate) │   │
        │  └─────────────┘  └─────────────┘  └───────────────┘   │
        └───────────────────┬────────────────────────────────────┘
                            │
        ┌───────────────────┴────────────────────────────────────┐
        │            AI INFERENCE LAYER (Self-Hosted)             │
        │  ┌──────────────────────────────────────────────────┐  │
        │  │  E2E Networks Mumbai Server (2vCPU / 4GB RAM)    │  │
        │  │  Qwen 2.5-7B-Instruct GGUF Q4_K_M               │  │
        │  │  llama.cpp inference engine                       │  │
        │  │  LoRA Adapters: Stage 1 (r=8) + Stage 2 (r=16)  │  │
        │  └──────────────────────────────────────────────────┘  │
        └────────────────────────────────────────────────────────┘

        ┌────────────────────────────────────────────────────────┐
        │         FRONTEND CLIENTS                                │
        │  ┌──────────────┐        ┌──────────────────────────┐  │
        │  │ Clinician    │        │ Patient Portal           │  │
        │  │ Dashboard    │        │ (React SPA)              │  │
        │  │ (React+TS)   │        └──────────────────────────┘  │
        │  └──────────────┘        ┌──────────────────────────┐  │
        │                          │ B2B Embeddable Widget    │  │
        │                          │ (Shadow DOM, ~50KB)      │  │
        │                          └──────────────────────────┘  │
        └────────────────────────────────────────────────────────┘
```

---

## 5. END-TO-END WORKFLOW DIAGRAM

### Patient Journey — 3-Stage Flow

```
┌───────────────────────────────────────────────────────────────────┐
│                  STAGE 1: LEAD GENERATION & SALES                  │
│                    (LoRA Adapter: r=8, 634 examples)               │
└───────────────────────────────────────────────────────────────────┘

Patient Discovers Platform
        │
        ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Website      │     │  Social Media │     │  Email / SMS  │
│  Chat Widget  │ OR  │  DM Bot       │ OR  │  Campaign     │
└───────┬───────┘     └───────┬───────┘     └───────┬───────┘
        └───────────────┬──────┘                     │
                        ▼                             │
                ┌───────────────────────────────────────────┐
                │      SAATHI AI GREETING (Qwen 2.5-7B)      │
                │  → Gratitude Expression                     │
                │  → Warm Connection Building                 │
                │  → Deep Discovery Questions                 │
                │  → Values & Motivations Mapping             │
                │  → Platform Education                       │
                │  → Therapist Credentials Sharing            │
                │  → FAQ & Objection Handling (via RAG)       │
                └──────────────────┬────────────────────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  Booking Intent?     │
                        └──────────┬──────────┘
                                   │ YES
                        ┌──────────▼──────────────────┐
                        │  Google Calendar Integration │
                        │  + Razorpay Payment Flow     │
                        │  + Confirmation Notification │
                        └──────────┬──────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────┐
│                  STAGE 2: THERAPEUTIC CO-PILOT                     │
│                    (LoRA Adapter: r=16, 3,017 examples)            │
└───────────────────────────────────────────────────────────────────┘
                                   │
                        ┌──────────▼──────────────────┐
                        │   Mode Switch: S1 → S2       │
                        │   Consent & Privacy Agreement│
                        │   Cultural Context Detection │
                        └──────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │        11-STEP THERAPEUTIC FLOW      │
                    │                                      │
                    │  Step 1:  Rapport Building           │ ←─── Crisis Detection Active
                    │  Step 2:  Challenge Context          │      (30+ weighted keywords)
                    │  Step 3:  Empathetic Connection      │      (10-point severity scale)
                    │  Step 4:  Challenge Prioritization   │      (<100ms response time)
                    │  Step 5:  Exploration Consent        │
                    │  Step 6:  VAK Narrative Collection   │ ←─── 128K context window
                    │  Step 7:  Meta-Model Clarification   │      (Distortions/Deletions/
                    │  Step 8:  Third-Person Perspective   │       Generalizations)
                    │  Step 9:  Pattern Mapping            │
                    │  Step 10: Feedback Collection        │
                    │  Step 11: Session Summary (RAG+AI)   │
                    └──────────────┬──────────────────────┘
                                   │
                        ┌──────────▼──────────────────┐
                        │  8 CLINICAL ASSESSMENTS      │
                        │  PHQ-9  | GAD-7  | PCL-5    │
                        │  ISI    | OCI-R  | SPIN      │
                        │  PSS    | WHO-5              │
                        └──────────┬──────────────────┘
                                   │
                        ┌──────────▼──────────────────┐
                        │   AI-Generated Insights      │
                        │   Therapy Recommendations    │
                        │   (CBT/DBT/ACT/Psychodynamic)│
                        │   Clinician Dashboard Update │
                        └──────────┬──────────────────┘
                                   │
         ┌─────────────────────────▼─────────────────────────┐
         │                 CRISIS DETECTED?                    │
         │     YES ──► Emergency Escalation Protocol          │
         │             → Alert Clinician (real-time)          │
         │             → Emergency Resource Links             │
         │             → Crisis Line Connection               │
         └─────────────────────────┬─────────────────────────┘
                                   │ NO (continue)
                                   ▼
┌───────────────────────────────────────────────────────────────────┐
│              STAGE 3: DROPOUT RE-ENGAGEMENT                        │
│                    (Stage 2 continuity model)                      │
└───────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  Dropout Detection Engine           │
                    │  → Inactivity monitoring (7/14/30d) │
                    │  → Sentiment trend analysis         │
                    │  → Re-engagement message generation │
                    │  → Personalized follow-up           │
                    └──────────────┬──────────────────────┘
                                   │
                        ┌──────────▼──────────────────┐
                        │   Re-book session?           │
                        │   YES ──► Back to Stage 1    │
                        │   NO  ──► Archive + Report   │
                        └─────────────────────────────┘


╔═══════════════════════════════════════════════════════════════════╗
║                    CRISIS ESCALATION FLOW                         ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  Patient Message ──► NLP Crisis Scan (30+ keywords)               ║
║       │                                                            ║
║       ▼                                                            ║
║  Severity Score (0-10)                                             ║
║       │                                                            ║
║  Score 1-3 ──► Monitor + Gentle Check-in                          ║
║  Score 4-6 ──► Clinician Alert + Safety Resources                 ║
║  Score 7-10 ──► IMMEDIATE: Call Clinician + Emergency Services    ║
║                 Block AI responses + Human takeover               ║
╚═══════════════════════════════════════════════════════════════════╝


╔═══════════════════════════════════════════════════════════════════╗
║                B2B WIDGET INTEGRATION FLOW                        ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  Client Website (any)                                             ║
║       │                                                            ║
║       │  Add 1-line script tag:                                   ║
║       │  <script src="https://cdn.saathi.ai/widget.js"           ║
║       │    data-clinic-id="ABC123"></script>                      ║
║       │                                                            ║
║       ▼                                                            ║
║  Widget Loader ──► Shadow DOM ──► Floating Bubble                 ║
║       │                                                            ║
║       ▼                                                            ║
║  Patient clicks bubble ──► Chat opens ──► Full Stage 1 flow       ║
║       │                                                            ║
║       ▼                                                            ║
║  All data routes to clinic's isolated tenant in DB                ║
║  Clinic sees all leads/conversations in their dashboard           ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## 6. CORE FEATURE MODULES

### Module 1 — AI Chat Engine (Stage 1: Lead Generation)
- **Purpose**: Convert website visitors to booked therapy sessions
- **AI**: Qwen 2.5-7B + Stage 1 LoRA adapter (r=8)
- **Key Behaviors**: Warm greeting → discovery → education → booking intent
- **RAG Integration**: Platform FAQs, therapist credentials, pricing
- **Output**: Booked appointment + patient profile created

### Module 2 — Therapeutic Co-Pilot (Stage 2)
- **Purpose**: AI-assisted structured therapeutic conversations
- **AI**: Qwen 2.5-7B + Stage 2 LoRA adapter (r=16)
- **NLP Features**: Meta-model pattern detection (Deletion/Generalization/Distortion)
- **Context Window**: 128K tokens — full conversation history maintained
- **Output**: Session summary, insights, assessment recommendations

### Module 3 — Clinical Assessment Engine
- **8 Standardized Tests**:

| Test | Condition Screened | Score Range |
|------|--------------------|-------------|
| PHQ-9 | Depression | 0–27 |
| GAD-7 | Generalized Anxiety | 0–21 |
| PCL-5 | PTSD | 0–80 |
| ISI | Insomnia | 0–28 |
| OCI-R | OCD | 0–72 |
| SPIN | Social Phobia | 0–68 |
| PSS | Perceived Stress | 0–40 |
| WHO-5 | Well-being | 0–25 |

- **AI Layer**: Qwen analysis of responses → therapy type recommendation

### Module 4 — Crisis Detection System
- **Detection**: 30+ weighted keywords, 10-point severity scale
- **Response Time**: <100ms
- **Escalation**: Automatic clinician SMS/email + emergency resources
- **Override**: AI conversation blocked; human takeover mode activated

### Module 5 — RAG Knowledge Base
- **Per-Tenant**: Each clinic gets isolated vector store
- **Ingestion**: PDF, URL, video transcript support
- **Vector Store**: Pinecone/Weaviate (384-dimension embeddings)
- **Retrieval**: Semantic search <1s, top-K context injection

### Module 6 — Clinician Dashboard
- Patient queue + conversation history
- Assessment score tracking (trend graphs)
- Crisis alert center
- Session notes + AI-generated summaries
- Appointment management

### Module 7 — B2B Embeddable Widget
- One `<script>` tag deployment
- Shadow DOM isolation (zero CSS conflict)
- White-label branding (colors, logo, clinic name)
- ~50KB bundle size
- WordPress plugin (1-click install)

### Module 8 — Booking & Payment
- **Calendar**: Google Calendar API — real-time slot availability
- **Payments**: Razorpay — UPI, Cards, Wallets, Net Banking
- **Webhooks**: Server-side payment verification
- **Notifications**: Email + WhatsApp confirmation

---

## 7. TECH STACK — COMPLETE REQUIREMENTS

### 7.1 Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Web Framework** | FastAPI | 0.104+ | REST API + WebSocket server |
| **Language** | Python | 3.11 | Primary backend language |
| **ORM** | SQLAlchemy | 2.0 | Database models + queries |
| **Migrations** | Alembic | 1.12+ | Schema versioning |
| **Async** | asyncio + uvicorn | — | Async request handling |
| **Auth** | JWT (python-jose) | — | Token-based auth |
| **Encryption** | cryptography | — | PHI field-level encryption |
| **Task Queue** | Celery + Redis | — | Background jobs (emails, reports) |
| **WebSockets** | FastAPI WebSocket | — | Real-time chat, crisis alerts |
| **Rate Limiting** | slowapi | — | API protection |
| **Validation** | Pydantic v2 | — | Request/response schemas |
| **HTTP Client** | httpx | — | External API calls |
| **Payment SDK** | razorpay-python | — | Razorpay integration |
| **Calendar SDK** | google-api-python-client | — | Google Calendar |

### 7.2 Frontend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | React | 18+ | Component-based UI |
| **Language** | TypeScript | 5+ | Type-safe development |
| **Build Tool** | Vite | 5+ | Dev server + bundler |
| **Styling** | Tailwind CSS | 3.4+ | Utility-first CSS |
| **UI Components** | shadcn/ui | — | Accessible component library |
| **State Management** | React Query + Zustand | — | Server state + client state |
| **Routing** | React Router v6 | — | SPA navigation |
| **Charts** | Recharts | — | Assessment score visualizations |
| **Forms** | React Hook Form + Zod | — | Validated form handling |
| **WebSocket** | Native browser WS | — | Real-time chat UI |
| **HTTP Client** | Axios | — | API communication |
| **Animation** | Framer Motion | — | UI animations |

### 7.3 AI / ML Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Base LLM** | Qwen 2.5-7B-Instruct GGUF Q4_K_M | Core conversation AI |
| **Inference Engine** | llama.cpp | CPU-based local inference |
| **Fine-tuning Framework** | PEFT (Hugging Face) | LoRA/QLoRA training |
| **LoRA Stage 1** | r=8, alpha=16, 634 examples | Lead generation adapter |
| **LoRA Stage 2** | r=16, alpha=32, 3,017 examples | Therapeutic co-pilot adapter |
| **Quantization** | QLoRA 4-bit | Memory: 28GB → 4.5GB |
| **Embeddings** | sentence-transformers | 384-dim RAG embeddings |
| **Vector Store** | Pinecone / Weaviate | Knowledge base retrieval |
| **RAG Framework** | LangChain | Document chunking + retrieval |
| **Tokenization** | Hugging Face Transformers | Model tokenization |
| **Training Data** | 3,651 ChatML-format examples | Custom dataset |
| **Evaluation** | Custom evaluation scripts | Therapeutic accuracy (96.8%) |

### 7.4 Database

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Primary DB** | PostgreSQL 15 | All relational data |
| **Vector DB** | Pinecone / Weaviate | Knowledge base vectors |
| **Cache** | Redis | Sessions, rate limits, task queue |
| **Search** | PostgreSQL FTS / pgvector | Full-text + vector search |
| **Backup** | Automated daily to S3/B2 | Disaster recovery |

**Key Tables**:
- `tenants` — B2B clients (clinics, hospitals)
- `users` — Clinicians + patients
- `conversations` — Full chat history (encrypted)
- `messages` — Individual messages with metadata
- `assessments` — Clinical test responses + scores
- `crisis_alerts` — Flagged events + resolution status
- `appointments` — Booking calendar entries
- `payments` — Transaction records
- `rag_documents` — Per-tenant knowledge base metadata
- `audit_logs` — HIPAA-compliant access logs

### 7.5 Infrastructure & DevOps

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Cloud Provider** | E2E Networks Mumbai | AI inference server |
| **Server Spec** | 2 vCPU / 4GB RAM | Qwen 2.5-7B inference |
| **OS** | Ubuntu 22.04 LTS | Server OS |
| **Container** | Docker + Docker Compose | App containerization |
| **Reverse Proxy** | Nginx | SSL, load balancing, routing |
| **SSL** | Let's Encrypt (Certbot) | HTTPS certificates |
| **CI/CD** | GitHub Actions | Automated deploy pipeline |
| **Monitoring** | Prometheus + Grafana | Performance metrics |
| **Logging** | ELK Stack (or Loki) | Centralized log management |
| **CDN** | Cloudflare (or AWS CloudFront) | Widget JS delivery |
| **Object Storage** | AWS S3 / Backblaze B2 | File uploads, model storage |

### 7.6 Third-Party Integrations

| Service | SDK/API | Purpose |
|---------|---------|---------|
| **Razorpay** | razorpay-python + Razorpay.js | Payment processing |
| **Google Calendar** | google-api-python-client | Appointment booking |
| **WhatsApp** | Twilio / Meta Business API | Channel integration |
| **Email** | SendGrid / AWS SES | Notifications, confirmations |
| **SMS** | Twilio / MSG91 | OTP + reminders |
| **Instagram** | Meta Graph API | DM bot |

### 7.7 Development Tools

| Tool | Purpose |
|------|---------|
| **Package Manager (Python)** | UV (fast pip replacement) |
| **Package Manager (Node)** | NPM |
| **Code Quality** | Prettier + ESLint + Black + Ruff |
| **Testing (Backend)** | Pytest + httpx |
| **Testing (Frontend)** | Vitest + React Testing Library |
| **API Documentation** | FastAPI auto-generated Swagger/ReDoc |
| **Version Control** | Git + GitHub |
| **IDE** | VS Code |
| **Environment Config** | python-dotenv + .env files |

---

## 8. INFRASTRUCTURE & DEPLOYMENT ARCHITECTURE

```
┌────────────────────────────────────────────────────────────┐
│                DEPLOYMENT ARCHITECTURE                      │
└────────────────────────────────────────────────────────────┘

                         Internet
                            │
                    ┌───────▼───────┐
                    │  Cloudflare   │
                    │  CDN + DDoS   │
                    └───────┬───────┘
                            │
              ┌─────────────┼──────────────┐
              │                            │
    ┌─────────▼──────────┐    ┌────────────▼──────────┐
    │  E2E Networks      │    │  Widget CDN            │
    │  Mumbai Server     │    │  (saathi-widget.js)    │
    │  2vCPU / 4GB RAM   │    │  ~50KB, globally cached│
    │  ₹699/month        │    └───────────────────────┘
    │                    │
    │  ┌──────────────┐  │
    │  │ Nginx        │  │
    │  │ (Port 80/443)│  │
    │  └──────┬───────┘  │
    │         │           │
    │  ┌──────▼───────┐  │
    │  │ FastAPI      │  │
    │  │ (Port 8000)  │  │
    │  └──────┬───────┘  │
    │         │           │
    │  ┌──────▼───────┐  │
    │  │ React Build  │  │
    │  │ (Port 3000)  │  │
    │  └──────┬───────┘  │
    │         │           │
    │  ┌──────▼───────┐  │
    │  │ PostgreSQL   │  │
    │  │ (Port 5432)  │  │
    │  └──────┬───────┘  │
    │         │           │
    │  ┌──────▼───────┐  │
    │  │ Redis        │  │
    │  │ (Port 6379)  │  │
    │  └──────┬───────┘  │
    │         │           │
    │  ┌──────▼───────┐  │
    │  │ llama.cpp    │  │    ← Qwen 2.5-7B-GGUF
    │  │ (Port 8080)  │  │      Q4_K_M quantized
    │  └──────────────┘  │      4.5GB memory usage
    └────────────────────┘

  Monthly Cost:
  ├── E2E Networks server:  ₹699
  ├── E2E bandwidth:        ₹99
  ├── Pinecone (starter):   Free → ₹1,500
  ├── Domain + SSL:         ₹800/year
  └── TOTAL:                ~₹798–2,400/month
```

---

## 9. AI/ML PIPELINE

### 9.1 Training Pipeline

```
RAW THERAPEUTIC DATA
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  DATA PREPARATION                                            │
│  • 3,651 examples in ChatML format                          │
│  • Stage 1: 634 examples (lead generation conversations)    │
│  • Stage 2: 3,017 examples (therapeutic sessions)          │
│  • Categories: Depression, Anxiety, PTSD, OCD, Stress,     │
│    Social Phobia, Trauma                                    │
│  • Bilingual: Hindi + English                               │
└───────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1 LoRA TRAINING                                       │
│  • Base: Qwen 2.5-7B-Instruct                               │
│  • LoRA: r=8, alpha=16, dropout=0.05                        │
│  • Epochs: 3, Batch: 2, LR: 2e-4                           │
│  • Hardware: 6–8 GB VRAM, ~1–2 hours                        │
│  • Output: stage1_lora_adapter/                             │
└───────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 2 LoRA TRAINING                                       │
│  • Base: Qwen 2.5-7B-Instruct                               │
│  • LoRA: r=16, alpha=32, dropout=0.05                       │
│  • Epochs: 3, Batch: 2, LR: 2e-4                           │
│  • Hardware: 6–8 GB VRAM, ~3–5 hours                        │
│  • Output: stage2_lora_adapter/                             │
└───────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  MODEL QUANTIZATION & PACKAGING                              │
│  • Convert LoRA merged model to GGUF Q4_K_M                 │
│  • Memory: ~4.5GB (from 28GB full precision)                │
│  • Upload to E2E Networks server                            │
│  • Path: /opt/saathi/models/qwen2.5-7b-q4_k_m.gguf         │
└───────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
                    PRODUCTION INFERENCE
                    (llama.cpp, <2s latency)
```

### 9.2 Inference Request Flow

```
User Message
     │
     ▼
Stage Detector  ──► Which LoRA adapter? (Stage 1 or 2)
     │
     ▼
RAG Context Injector  ──► Retrieve top-K relevant documents
     │
     ▼
Crisis Scanner  ──► Check 30+ keywords before sending to LLM
     │
     ├─► CRISIS DETECTED ──► Emergency escalation (skip LLM)
     │
     ▼
Prompt Builder
  [System prompt] + [RAG context] + [Conversation history] + [User message]
     │
     ▼
llama.cpp Inference  (Qwen 2.5-7B Q4_K_M, ~1–2s)
     │
     ▼
Response Post-Processor
  → Safety filter
  → NLP meta-model pattern extraction
  → Stage transition detection
     │
     ▼
Streamed Response to Client (via WebSocket or HTTP)
```

---

## 10. DATABASE SCHEMA OVERVIEW

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   tenants    │◄───────┤    users     ├────────►│conversations │
│──────────────│  1:N   │──────────────│  1:N   │──────────────│
│ id (PK)      │         │ id (PK)      │         │ id (PK)      │
│ name         │         │ tenant_id(FK)│         │ patient_id   │
│ domain       │         │ email        │         │ stage (1/2/3)│
│ plan_tier    │         │ role         │         │ started_at   │
│ config_json  │         │ encrypted_phi│         │ ended_at     │
│ created_at   │         │ created_at   │         │ summary_ai   │
└──────────────┘         └──────┬───────┘         └──────┬───────┘
                                │                        │
                         ┌──────▼───────┐         ┌──────▼───────┐
                         │ appointments │         │   messages   │
                         │──────────────│         │──────────────│
                         │ id (PK)      │         │ id (PK)      │
                         │ patient_id   │         │ conv_id (FK) │
                         │ clinician_id │         │ role (user/ai│
                         │ gcal_event_id│         │ content      │
                         │ razorpay_id  │         │ metadata     │
                         │ status       │         │ created_at   │
                         └──────────────┘         └──────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│ assessments  │         │ crisis_alerts│         │  audit_logs  │
│──────────────│         │──────────────│         │──────────────│
│ id (PK)      │         │ id (PK)      │         │ id (PK)      │
│ patient_id   │         │ patient_id   │         │ user_id      │
│ test_type    │         │ severity(0-10│         │ action       │
│ responses    │         │ keywords_hit │         │ resource     │
│ score        │         │ status       │         │ ip_address   │
│ risk_level   │         │ resolved_by  │         │ timestamp    │
│ created_at   │         │ created_at   │         │ phi_accessed │
└──────────────┘         └──────────────┘         └──────────────┘
```

---

## 11. API ARCHITECTURE

### Core API Endpoints

```
BASE URL: https://api.saathi.ai/v1

AUTH
├── POST   /auth/register          Register clinician or patient
├── POST   /auth/login             Get JWT token
├── POST   /auth/refresh           Refresh access token
└── POST   /auth/logout            Invalidate token

STAGE 1 — LEAD GENERATION
├── POST   /stage1/chat            Send message, get AI response
├── POST   /stage1/booking-intent  Trigger booking flow
└── GET    /stage1/sessions/{id}   Get session history

STAGE 2 — THERAPEUTIC
├── POST   /stage2/chat            Therapeutic conversation
├── GET    /stage2/sessions/{id}   Full conversation with AI summary
└── POST   /stage2/complete        Mark session complete, generate report

STAGE 3 — RE-ENGAGEMENT
├── GET    /stage3/at-risk         Get patients flagged for dropout
└── POST   /stage3/message/{id}    Send re-engagement message

ASSESSMENTS
├── GET    /assessments/types      List available tests
├── POST   /assessments/submit     Submit test responses
└── GET    /assessments/{id}       Get scored results

CRISIS
├── GET    /crisis/alerts          Active crisis alerts (real-time)
├── POST   /crisis/resolve/{id}    Mark crisis resolved
└── WS     /crisis/ws              WebSocket for real-time alerts

CLINICIAN DASHBOARD
├── GET    /dashboard/patients     Patient list with stats
├── GET    /dashboard/patient/{id} Full patient profile
└── GET    /dashboard/analytics    Aggregate metrics

WIDGET (B2B)
├── POST   /widget/init            Initialize widget session
├── POST   /widget/chat            Widget chat endpoint
└── GET    /widget/config/{tenant} Get tenant widget config

PAYMENTS
├── POST   /payments/create-order  Create Razorpay order
├── POST   /payments/verify        Verify payment signature
└── GET    /payments/history       Payment records

RAG
├── POST   /rag/upload             Upload document to knowledge base
├── POST   /rag/query              Query knowledge base
└── DELETE /rag/document/{id}      Remove document
```

---

## 12. FRONTEND ARCHITECTURE

```
therapeutic-copilot/client/src/
├── components/
│   ├── auth/
│   │   ├── LoginForm.tsx
│   │   └── RegisterForm.tsx
│   ├── chatbot/
│   │   ├── ChatWidget.tsx         ← Main chat interface
│   │   ├── MessageBubble.tsx
│   │   ├── TypingIndicator.tsx
│   │   └── AssessmentModal.tsx
│   ├── dashboard/
│   │   ├── PatientList.tsx
│   │   ├── PatientProfile.tsx
│   │   ├── AssessmentCharts.tsx
│   │   └── CrisisAlertBanner.tsx
│   ├── assessment/
│   │   ├── PHQ9Form.tsx
│   │   ├── GAD7Form.tsx
│   │   └── AssessmentResults.tsx
│   └── booking/
│       ├── CalendarPicker.tsx
│       └── PaymentModal.tsx
├── pages/
│   ├── LandingPage.tsx
│   ├── ClinicianDashboard.tsx
│   ├── PatientPortal.tsx
│   ├── AssessmentPage.tsx
│   └── BookingPage.tsx
├── hooks/
│   ├── useChat.ts
│   ├── useWebSocket.ts
│   └── useAssessments.ts
├── lib/
│   ├── chatApi.ts
│   ├── authApi.ts
│   └── assessmentApi.ts
└── types/
    └── index.ts
```

---

## 13. B2B WIDGET ARCHITECTURE

```
Client Website (any domain)
        │
        │  <script src="https://cdn.saathi.ai/widget.js"
        │    data-clinic-id="CLINIC_123"
        │    data-color="#6366f1"
        │    data-position="bottom-right">
        │  </script>
        │
        ▼
widget/
├── loader.js          ← Async loader (1KB)
│   └── Creates <div> + Shadow Root
├── widget.js          ← Full bundle (~50KB, gzipped)
│   ├── Floating bubble (ChatBubble.tsx)
│   ├── Chat window (ChatWindow.tsx)
│   ├── Message list (MessageList.tsx)
│   ├── Input box (InputBox.tsx)
│   ├── Welcome screen (WelcomeScreen.tsx)
│   ├── Booking modal (BookingModal.tsx)
│   └── Payment modal (PaymentModal.tsx)
│
Shadow DOM
├── Isolated CSS (no host website conflicts)
├── localStorage for session persistence
└── WebSocket to Saathi AI backend

Integration Options:
├── HTML Script Tag  (any website)
├── WordPress Plugin  (1-click install, 40% of web)
├── Shopify App  (future)
└── React Component  (for React apps)
```

---

## 14. SECURITY & COMPLIANCE

| Requirement | Implementation |
|------------|----------------|
| **HIPAA** | PHI field-level AES-256 encryption, audit logs, access controls |
| **GDPR** | Consent management, data export, right to deletion |
| **DPDP Act** | Indian data residency (E2E Mumbai), privacy notices |
| **Authentication** | JWT with refresh tokens, bcrypt password hashing |
| **Authorization** | Role-based (admin/clinician/patient), tenant isolation |
| **Transport** | TLS 1.3 for all API communication |
| **Data at Rest** | AES-256 encryption for sensitive fields |
| **Rate Limiting** | Per-IP + per-tenant API rate limiting |
| **Input Validation** | Pydantic schemas, SQL injection prevention |
| **Audit Logging** | All PHI access logged with user + timestamp |
| **Crisis Safety** | Real-time crisis detection, human escalation protocol |

---

## 15. 4-WEEK BUILD TIMELINE

```
WEEK 1 (Days 1–7): INFRASTRUCTURE & AI CORE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Day 1:  Provision E2E Networks server, install Docker + Nginx
Day 2:  Install llama.cpp, download Qwen 2.5-7B GGUF model
Day 3:  Build self-hosted inference service (FastAPI wrapper)
Day 4:  Load LoRA Stage 1 + Stage 2 adapters, test inference
Day 5:  Set up PostgreSQL + Redis, run Alembic migrations
Day 6:  Set up Pinecone vector store, seed RAG with base docs
Day 7:  Stage 1 chat API functional end-to-end

✅ Milestone: AI inference live, Stage 1 chat working


WEEK 2 (Days 8–14): CORE FEATURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Day 8:  Stage 2 therapeutic flow API (11-step workflow)
Day 9:  Crisis detection service + WebSocket real-time alerts
Day 10: 8 clinical assessments scoring engine
Day 11: Razorpay payment integration + webhooks
Day 12: Google Calendar booking integration
Day 13: JWT auth + multi-tenant middleware
Day 14: React frontend — chat interface + Stage 1 flow

✅ Milestone: Core therapeutic flow functional


WEEK 3 (Days 15–21): DASHBOARD & WIDGET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Day 15: Clinician dashboard UI (patient list, chat history)
Day 16: Assessment results dashboard + charts
Day 17: Crisis alert center (real-time)
Day 18: B2B Widget development (Shadow DOM + bubble)
Day 19: Widget: chat integration + tenant config
Day 20: Stage 3 dropout detection service
Day 21: WordPress plugin packaging

✅ Milestone: Clinician dashboard + widget working


WEEK 4 (Days 22–28): TESTING & DEMO PREP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Day 22: Integration testing (all 3 stages)
Day 23: Security audit + HIPAA checklist
Day 24: Performance testing (load, latency)
Day 25: Bug fixes + UI polish
Day 26: Investor demo script + walkthrough preparation
Day 27: Onboard 2–3 pilot clinics (beta testers)
Day 28: PROTOTYPE LAUNCH ✅

🎯 Target: Production-ready POC in 28 days
```

---

## 16. TEAM & RESOURCE REQUIREMENTS

### Minimum Viable Team (5 Engineers)

| Role | Skills Required | Focus Area |
|------|----------------|------------|
| **Backend Engineer 1** | Python, FastAPI, PostgreSQL, LLM APIs | AI services, Stage 1/2/3 APIs |
| **Backend Engineer 2** | Python, FastAPI, Redis, Razorpay, Google Calendar | Payments, bookings, auth |
| **Frontend Engineer** | React, TypeScript, Tailwind, WebSocket | Dashboard, chat UI, widget |
| **ML/AI Engineer** | PyTorch, PEFT, llama.cpp, RAG | Model training, inference optimization |
| **DevOps Engineer** | Docker, Nginx, GitHub Actions, Linux | Deployment, CI/CD, monitoring |

### Hardware Requirements

| Purpose | Spec | Cost |
|---------|------|------|
| **AI Inference Server** | E2E Networks: 2vCPU/4GB RAM | ₹698/month |
| **ML Training (one-time)** | Colab Pro or RunPod: 8GB VRAM GPU | ~₹2,000–5,000 |
| **Development Machines** | Standard laptops (developers) | Existing |

---

## 17. COST PROJECTIONS

### Prototype Build Costs

| Item | One-Time | Monthly |
|------|----------|---------|
| E2E Networks Server | — | ₹798 |
| Pinecone Vector DB | — | Free (starter) |
| Domain + SSL | ₹800/year | — |
| Razorpay (per transaction) | — | 2% per txn |
| Google Calendar API | — | Free |
| Development hours (5 eng × 4 weeks) | ₹3,00,000 est. | — |
| **Total Prototype Cost** | **~₹3,10,000** | **~₹800** |

### Unit Economics at Scale

| Phase | Monthly Users | AI Cost (Self-Hosted) | Revenue Potential |
|-------|--------------|----------------------|------------------|
| Prototype | 50–100 | ₹798 | ₹0 (pilot) |
| MVP | 1,000 | ₹79,600 | ₹29.99L |
| Growth | 10,000 | ₹1,50,000 | ₹2.99Cr |
| Scale | 50,000 | ₹3,50,000 | ₹14.99Cr |

**Cost Advantage**: Self-hosted Qwen 2.5-7B costs **93% less** than API-based competitors (₹798/month vs ₹15,000/month at prototype scale).

---

## 18. INVESTOR DEMO CHECKLIST

The prototype must demonstrate these **10 investor-critical flows**:

| # | Demo Flow | What It Proves |
|---|-----------|---------------|
| 1 | **Widget embed** on demo website | B2B integration simplicity (30-second deploy) |
| 2 | **Stage 1 conversation** from cold visitor to booked appointment | Lead generation AI capability |
| 3 | **Razorpay payment** completion in-chat | Monetization readiness |
| 4 | **Stage 2 therapeutic session** (2–3 exchanges) | Core AI quality + NLP depth |
| 5 | **PHQ-9 assessment** flow in-chat | Clinical tool integration |
| 6 | **Crisis trigger** → escalation alert on clinician dashboard | Safety system (critical differentiator) |
| 7 | **Clinician dashboard** — patient queue, conversation history | B2B value for buyers |
| 8 | **RAG query** — AI answers clinic-specific question (their docs) | Customization capability |
| 9 | **Stage 3 re-engagement** message to inactive patient | Retention feature |
| 10 | **Cost comparison** slide: ₹798/month vs ₹15,000/month competitor | Investment story |

### Key Metrics to Show

| Metric | Target |
|--------|--------|
| AI response latency | < 2 seconds |
| Crisis detection accuracy | ≥ 95% sensitivity |
| Assessment completion rate | > 80% |
| Therapeutic accuracy score | 96.8% |
| Widget bundle size | < 50KB |
| API uptime | 99.9% |
| Self-hosted cost | ₹798/month |

---

## APPENDIX: REFERENCE DOCUMENTS

All reference documents exist in the repository:

| Document | Path |
|----------|------|
| Comprehensive Product Document | `COMPREHENSIVE_PRODUCT_DEVELOPMENT_DOCUMENT.md` |
| Patient Journey Diagrams | `PATIENT_JOURNEY_MERMAID_DIAGRAM (1).md` |
| Architecture Summary | `ARCHITECTURE_UPDATE_SUMMARY.md` |
| POC Deployment Roadmap | `POC_PROTOTYPE_DEPLOYMENT_ROADMAP.md` |
| Folder Structure | `FOLDER_ARCHITECTURE_v2.0.md` |
| ML/NLP Analysis | `ML_NLP_ALIGNMENT_ANALYSIS.md` |
| Qwen Migration Summary | `QWEN_LLM_ARCHITECTURE_MIGRATION_SUMMARY.md` |
| 4-Week Roadmap | `4_WEEK_IMPLEMENTATION_ROADMAP.md` |
| Widget Architecture | `TIDIO_STYLE_WIDGET_ARCHITECTURE.md` |
| API Architecture | `API_ARCHITECTURE_UPDATE_NOV_23.md` |
| Clinical Assessments | `CLINICAL_ASSESSMENTS_GUIDE.md` |
| Crisis Detection | `CRISIS_IMPLEMENTATION_COMPLETE_GUIDE.md` |
| Backend Guide | `BACKEND_IMPLEMENTATION_GUIDE.md` |
| Frontend Guide | `FRONTEND_IMPLEMENTATION_GUIDE.md` |
| Go-to-Market Strategy | `COMPREHENSIVE_GO_TO_MARKET_STRATEGY.pdf` |

---

*Document prepared from existing repository architecture and documentation.*
*RYL NEUROACADEMY PRIVATE LIMITED — Saathi AI Therapeutic Co-Pilot*
