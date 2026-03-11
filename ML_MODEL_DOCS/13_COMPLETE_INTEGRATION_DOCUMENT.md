# Document 13: Complete System Integration Guide
## Saathi AI Therapeutic Co-Pilot — B2B SaaS Platform
## Full Tech Stack Integration for Production Execution

---

## Table of Contents
1. [System Overview & Architecture Diagram](#1-system-overview--architecture-diagram)
2. [Tech Stack Master Reference](#2-tech-stack-master-reference)
3. [Frontend Integration](#3-frontend-integration)
4. [Backend API Integration](#4-backend-api-integration)
5. [Database Integration](#5-database-integration)
6. [ML Classifier Pipeline Integration](#6-ml-classifier-pipeline-integration)
7. [LoRA Fine-Tuned Qwen LLM Integration](#7-lora-fine-tuned-qwen-llm-integration)
8. [RAG (Retrieval-Augmented Generation) Integration](#8-rag-retrieval-augmented-generation-integration)
9. [Clinical Assessment Integration](#9-clinical-assessment-integration)
10. [Crisis Containment System Integration](#10-crisis-containment-system-integration)
11. [Safety & Hallucination Control Integration](#11-safety--hallucination-control-integration)
12. [Chat System Integration](#12-chat-system-integration)
13. [Report Generation & Recommendation Engine](#13-report-generation--recommendation-engine)
14. [Analytics & Dashboards Integration](#14-analytics--dashboards-integration)
15. [Authentication & Multi-Tenancy Integration](#15-authentication--multi-tenancy-integration)
16. [Real-Time Communication Layer](#16-real-time-communication-layer)
17. [Notification & Alerting System](#17-notification--alerting-system)
18. [Deployment & Infrastructure Integration](#18-deployment--infrastructure-integration)
19. [Environment Configuration Reference](#19-environment-configuration-reference)
20. [Integration Test Checklist](#20-integration-test-checklist)
21. [Missing Tech Additions & Recommendations](#21-missing-tech-additions--recommendations)

---

## 1. System Overview & Architecture Diagram

### 1.1 Full System Architecture

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                        SAATHI AI PLATFORM — FULL ARCHITECTURE               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────┐    ║
║  │                        CLIENT LAYER                                  │    ║
║  │   React 18 + TypeScript  │  Tailwind CSS  │  shadcn/ui              │    ║
║  │   Widget (iframe)  │  Web App  │  WhatsApp  │  SMS  │  Email        │    ║
║  └───────────────────────────────┬─────────────────────────────────────┘    ║
║                                  │ HTTPS / WSS                               ║
║  ┌───────────────────────────────▼─────────────────────────────────────┐    ║
║  │                     API GATEWAY LAYER                                │    ║
║  │          FastAPI (Python 3.11)  │  Nginx  │  SSL Termination        │    ║
║  │          Rate Limiting  │  JWT Auth  │  CORS  │  WebSocket          │    ║
║  └──┬─────────────┬────────────────┬──────────────┬───────────────────┘    ║
║     │             │                │              │                          ║
║  ┌──▼───┐   ┌────▼──────┐   ┌─────▼────┐   ┌────▼──────────────────┐      ║
║  │CHAT  │   │ASSESSMENT │   │ANALYTICS │   │ADMIN / THERAPIST      │      ║
║  │ROUTER│   │ROUTES     │   │ROUTES    │   │DASHBOARD ROUTES       │      ║
║  └──┬───┘   └────┬──────┘   └─────┬────┘   └────┬──────────────────┘      ║
║     │             │                │              │                          ║
║  ┌──▼─────────────▼────────────────▼──────────────▼──────────────────┐     ║
║  │                     SERVICE ORCHESTRATION LAYER                     │     ║
║  │                                                                      │     ║
║  │  ┌────────────┐  ┌──────────────┐  ┌──────────────┐               │     ║
║  │  │ CRISIS     │  │ CLASSIFIER   │  │ LLM          │               │     ║
║  │  │ CONTAINMENT│  │ PIPELINE     │  │ ORCHESTRATOR │               │     ║
║  │  └────────────┘  └──────────────┘  └──────────────┘               │     ║
║  │                                                                      │     ║
║  │  ┌────────────┐  ┌──────────────┐  ┌──────────────┐               │     ║
║  │  │ RAG        │  │ ASSESSMENT   │  │ REPORT       │               │     ║
║  │  │ SERVICE    │  │ SCORING      │  │ GENERATOR    │               │     ║
║  │  └────────────┘  └──────────────┘  └──────────────┘               │     ║
║  └──────────────────────────────────────────────────────────────────┘      ║
║                                                                              ║
║  ┌───────────────────────────────────────────────────────────────────┐      ║
║  │                      ML MODEL LAYER                                │      ║
║  │  Emotion│Crisis│Intent│Topic│Sentiment│Meta-Model│Booking│Router  │      ║
║  │  DistilBERT×5  │  RoBERTa×2  │  Flan-T5-large (LoRA)            │      ║
║  │  Qwen2.5-7B + LoRA Stage1 + LoRA Stage2                          │      ║
║  └───────────────────────────────────────────────────────────────────┘      ║
║                                                                              ║
║  ┌──────────────────────┐  ┌───────────────────┐  ┌──────────────────┐     ║
║  │   PRIMARY DATABASE   │  │  VECTOR DATABASE   │  │   CACHE LAYER    │     ║
║  │  PostgreSQL + pgvec  │  │  Pinecone (cloud)  │  │  Redis 7         │     ║
║  │  (Supabase managed)  │  │  1536-dim / 384-dim│  │  Session + Queue │     ║
║  └──────────────────────┘  └───────────────────┘  └──────────────────┘     ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### 1.2 Data Flow — Single Message Request

```
User types message in Chat Widget
        │
        ▼
1. WebSocket / HTTP POST to /api/chat/message
        │
        ▼
2. FastAPI Chat Route
   ├── Validate JWT token
   ├── Validate session
   └── Pass to ChatOrchestrator
        │
        ▼
3. CrisisContainmentService (MANDATORY FIRST — <100ms)
   ├── Keyword check (<5ms)
   ├── RoBERTa crisis classifier (<30ms)
   └── → If EMERGENCY: return pre-crafted response; send alerts; STOP
        │
        ▼
4. Parallel ML Classifiers (run simultaneously — <25ms each)
   ├── EmotionClassifierService    (DistilBERT)
   ├── IntentClassifierService     (DistilBERT)
   └── SentimentClassifierService  (DistilBERT)
        │
        ▼
5. Routing Decision (based on intent)
   ├── crisis_emergency  → CrisisProtocol
   ├── book_appointment  → BookingIntentDetector + BookingFlow
   ├── information_request → RAGService
   ├── assessment_request → AssessmentRouter → AssessmentAdmin
   └── seek_support      → continue below
        │
        ▼
6. Domain Enrichment Classifiers (parallel — <20ms each)
   ├── TopicClassifierService      (DistilBERT multi-label)
   ├── BookingIntentService        (DistilBERT joint)
   └── AssessmentRouterService     (RoBERTa multi-label)
        │
        ▼
7. MetaModelDetectorService (therapeutic mode only — <80ms)
   ├── AllenNLP SRL
   └── Flan-T5-large LoRA
        │
        ▼
8. RAGService.augment_prompt() (if relevant context available)
   └── Pinecone semantic search + top-k retrieval
        │
        ▼
9. Prompt Assembly (assemble_complete_system_prompt)
   └── All classifier outputs → structured system prompt
        │
        ▼
10. LLM Generation (LoRA Qwen2.5-7B)
    ├── Stage 1 (lead gen): qwen-lora-stage1 adapter
    └── Stage 2 (therapy):  qwen-lora-stage2 adapter
        │
        ▼
11. Safety & Hallucination Checks (post-generation)
    ├── Harmful content filter
    ├── Factual claim validator
    └── Therapeutic boundary enforcer
        │
        ▼
12. Response delivered to user via WebSocket / HTTP
    └── Session state updated; event logged to DB
```

---

## 2. Tech Stack Master Reference

### 2.1 Complete Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Frontend** | React | 18.x | UI framework |
| **Frontend** | TypeScript | 5.x | Type safety |
| **Frontend** | Vite | 5.x | Build tool & dev server |
| **Frontend** | Tailwind CSS | 3.x | Utility-first styling |
| **Frontend** | shadcn/ui | Latest | Component library |
| **Frontend** | Zustand | 4.x | Global state management |
| **Frontend** | React Query (TanStack) | 5.x | Server state, caching, sync |
| **Frontend** | Socket.io-client | 4.x | WebSocket real-time chat |
| **Frontend** | Recharts | 2.x | Analytics dashboards |
| **Frontend** | React Hook Form + Zod | Latest | Form validation |
| **Frontend** | Framer Motion | 11.x | Animations |
| **Backend** | Python | 3.11 | Runtime |
| **Backend** | FastAPI | 0.104+ | REST API + WebSocket |
| **Backend** | Uvicorn | 0.24+ | ASGI server |
| **Backend** | Pydantic v2 | 2.x | Data validation/serialization |
| **Backend** | SQLAlchemy | 2.x | ORM |
| **Backend** | Alembic | Latest | DB migrations |
| **Backend** | Celery | 5.x | Async task queue |
| **Backend** | python-jose | Latest | JWT token handling |
| **Backend** | passlib (bcrypt) | Latest | Password hashing |
| **Database** | PostgreSQL | 15+ | Primary relational DB |
| **Database** | Supabase | Cloud | Managed Postgres + Auth |
| **Database** | Redis | 7.x | Cache + session + Celery broker |
| **Database** | Pinecone | Cloud | Vector database for RAG |
| **ML** | PyTorch | 2.1 | ML framework |
| **ML** | HuggingFace Transformers | 4.36+ | Model loading & inference |
| **ML** | PEFT | 0.7+ | LoRA fine-tuning |
| **ML** | TRL | 0.7+ | SFT training |
| **ML** | sentence-transformers | 2.2+ | Embeddings (384-dim) |
| **ML** | scikit-learn | 1.3+ | Classical ML utilities |
| **ML** | AllenNLP | Latest | SRL for meta-model detection |
| **ML** | bitsandbytes | Latest | 4-bit quantization |
| **LLM** | Qwen2.5-7B-Instruct | HF | Base LLM |
| **LLM** | Together AI API | Cloud | Qwen inference (cloud option) |
| **LLM** | OpenAI API | Cloud | GPT-4o fallback |
| **Monitoring** | Weights & Biases (wandb) | Cloud | ML training tracking |
| **Monitoring** | Sentry | Cloud | Error tracking |
| **Monitoring** | Prometheus + Grafana | Self-hosted | Metrics & dashboards |
| **Communication** | Socket.io | 4.x | Real-time WebSocket |
| **Communication** | Twilio | Cloud | WhatsApp + SMS |
| **Communication** | SendGrid | Cloud | Email notifications |
| **Infrastructure** | Docker | 24+ | Containerization |
| **Infrastructure** | Docker Compose | 2.x | Local orchestration |
| **Infrastructure** | Nginx | 1.24+ | Reverse proxy + SSL |
| **Infrastructure** | AWS / GCP | Cloud | Cloud hosting |
| **Infrastructure** | GitHub Actions | CI/CD | Automated deployment |

---

## 3. Frontend Integration

### 3.1 Project Structure

```
therapeutic-copilot/client/
├── public/
│   └── widget.js                  # Embeddable chat widget script
├── src/
│   ├── components/
│   │   ├── chatbot/
│   │   │   ├── ChatWidget.tsx      # Main chat interface
│   │   │   ├── ChatMessage.tsx     # Individual message component
│   │   │   ├── AssessmentForm.tsx  # In-chat assessment form
│   │   │   └── CrisisOverlay.tsx   # Emergency crisis UI
│   │   ├── dashboard/
│   │   │   ├── AdminDashboard.tsx  # HR/Admin view
│   │   │   ├── TherapistDashboard.tsx
│   │   │   ├── AnalyticsCharts.tsx
│   │   │   └── UserProgressCard.tsx
│   │   ├── assessments/
│   │   │   ├── PHQ9Form.tsx
│   │   │   ├── GAD7Form.tsx
│   │   │   └── AssessmentResults.tsx
│   │   └── ui/                    # shadcn/ui components
│   ├── lib/
│   │   ├── chatApi.ts             # Chat API client
│   │   ├── assessmentApi.ts       # Assessment API client
│   │   ├── analyticsApi.ts        # Analytics API client
│   │   └── socket.ts              # Socket.io client setup
│   ├── store/
│   │   ├── chatStore.ts           # Zustand chat state
│   │   ├── sessionStore.ts        # Session management
│   │   └── authStore.ts           # Auth state
│   ├── hooks/
│   │   ├── useChat.ts             # Chat logic hook
│   │   ├── useWebSocket.ts        # WebSocket hook
│   │   └── useAssessment.ts       # Assessment flow hook
│   ├── pages/
│   │   ├── ChatPage.tsx
│   │   ├── DashboardPage.tsx
│   │   └── ReportsPage.tsx
│   └── main.tsx
├── package.json
└── vite.config.ts
```

### 3.2 Environment Variables (Frontend)

```env
# therapeutic-copilot/client/.env
VITE_API_BASE_URL=https://api.saathi.ai
VITE_WS_URL=wss://api.saathi.ai
VITE_SUPABASE_URL=https://yourproject.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
VITE_SENTRY_DSN=https://xxx@sentry.io/xxx
```

### 3.3 Chat API Client Integration

```typescript
// src/lib/chatApi.ts
const API_BASE = import.meta.env.VITE_API_BASE_URL;

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: {
    emotion?: string;
    intent?: string;
    crisis_level?: string;
    stage?: string;
    assessment_suggested?: string;
  };
}

export interface ChatResponse {
  message: string;
  session_id: string;
  stage: string;
  emotion_detected?: string;
  crisis_level?: string;
  assessment_suggested?: string;
  booking_intent?: boolean;
  tokens_used?: number;
}

export async function sendMessage(
  message: string,
  sessionId: string,
  token: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`Chat API error: ${res.status}`);
  return res.json();
}
```

### 3.4 WebSocket Integration

```typescript
// src/lib/socket.ts
import { io, Socket } from 'socket.io-client';

let socket: Socket | null = null;

export function initSocket(token: string): Socket {
  socket = io(import.meta.env.VITE_WS_URL, {
    auth: { token },
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
  });

  socket.on('connect', () => console.log('Socket connected'));
  socket.on('disconnect', (reason) => console.warn('Socket disconnected:', reason));
  socket.on('connect_error', (err) => console.error('Socket error:', err));

  return socket;
}

// Events emitted by server:
// 'chat_response'   → { message, emotion, stage, crisis_level }
// 'typing_start'    → AI is generating
// 'typing_end'      → AI done
// 'crisis_alert'    → Crisis detected (for admin dashboard)
// 'assessment_start'→ Start assessment flow
```

### 3.5 React Query Setup for Data Fetching

```typescript
// src/main.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,   // 5 minutes
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

// Hooks using React Query
export function useSessionHistory(sessionId: string) {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => fetchSessionHistory(sessionId),
    enabled: !!sessionId,
  });
}

export function useAssessmentScores(userId: string) {
  return useQuery({
    queryKey: ['assessments', userId],
    queryFn: () => fetchAssessmentHistory(userId),
  });
}
```

---

## 4. Backend API Integration

### 4.1 FastAPI Application Structure

```
therapeutic-copilot/server/
├── main.py                    # FastAPI app entry point
├── config/
│   ├── settings.py            # Pydantic Settings (env vars)
│   ├── stage_prompts.py       # Stage-specific LLM prompts
│   ├── crisis_keywords.py     # Crisis keyword dictionaries
│   └── emotion_prompt_context.py
├── routes/
│   ├── chat_routes.py         # /api/chat/* endpoints
│   ├── assessment_routes.py   # /api/assessments/* endpoints
│   ├── auth_routes.py         # /api/auth/* endpoints
│   ├── analytics_routes.py    # /api/analytics/* endpoints
│   ├── admin_routes.py        # /api/admin/* endpoints
│   └── report_routes.py       # /api/reports/* endpoints
├── services/
│   ├── ai_service.py                    # Sales AI (Stage 1)
│   ├── therapeutic_ai_service.py        # Therapy AI (Stage 2)
│   ├── lora_model_service.py            # Qwen LoRA loading
│   ├── chatbot_service.py               # Multi-channel chat
│   ├── qwen_inference.py                # Together API inference
│   ├── crisis_containment_service.py    # Crisis pipeline
│   ├── crisis_detection_service.py      # Model 02
│   ├── emotion_classifier_service.py    # Model 01
│   ├── intent_classifier_service.py     # Model 03
│   ├── topic_classifier_service.py      # Model 04
│   ├── sentiment_classifier_service.py  # Model 05
│   ├── meta_model_detector_service.py   # Model 06
│   ├── booking_intent_service.py        # Model 09
│   ├── assessment_router_service.py     # Model 10
│   ├── assessment_scoring_service.py    # All 8 assessments
│   ├── assessment_admin_service.py      # Assessment conversation admin
│   ├── rag_service.py                   # RAG pipeline
│   ├── embedding_service.py             # Sentence-transformers
│   ├── report_service.py                # Report generation
│   ├── safety_service.py                # Hallucination + boundary checks
│   ├── notification_service.py          # Alerts + emails
│   └── analytics_service.py             # Analytics aggregation
├── models/
│   ├── database.py            # SQLAlchemy engine + session
│   ├── user.py                # User ORM model
│   ├── session.py             # Chat session ORM model
│   ├── message.py             # Message ORM model
│   ├── assessment.py          # Assessment ORM model
│   ├── crisis_event.py        # Crisis log ORM model
│   └── company.py             # B2B company/tenant ORM model
├── middleware/
│   ├── auth_middleware.py     # JWT verification
│   ├── rate_limit_middleware.py
│   └── logging_middleware.py
├── utils/
│   ├── prompt_assembler.py    # Central prompt assembly function
│   ├── response_validator.py  # Post-generation safety checks
│   └── audit_logger.py        # Clinical audit trail
└── requirements.txt
```

### 4.2 FastAPI Application Entry Point

```python
# therapeutic-copilot/server/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk

# Import all routes
from routes.chat_routes import router as chat_router
from routes.assessment_routes import router as assessment_router
from routes.auth_routes import router as auth_router
from routes.analytics_routes import router as analytics_router
from routes.admin_routes import router as admin_router
from routes.report_routes import router as report_router

# Import all services for preloading
from services.emotion_classifier_service import EmotionClassifierService
from services.crisis_detection_service import CrisisDetectionService
from services.intent_classifier_service import IntentClassifierService
from services.topic_classifier_service import TopicClassifierService
from services.sentiment_classifier_service import SentimentClassifierService
from services.booking_intent_service import BookingIntentService
from services.assessment_router_service import AssessmentRouterService
from services.meta_model_detector_service import MetaModelDetectorService
from services.lora_model_service import LoraModelService
from services.rag_service import RAGService
from services.embedding_service import EmbeddingService

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all ML models at startup — once, into memory."""
    print("🚀 Loading ML models...")

    # Safety-critical models first
    app.state.crisis_service = CrisisDetectionService()        # Singleton
    print("  ✅ Crisis Detection Classifier loaded")

    # Core classifiers (parallel loading possible)
    app.state.emotion_service = EmotionClassifierService()
    app.state.intent_service = IntentClassifierService()
    app.state.sentiment_service = SentimentClassifierService()
    app.state.topic_service = TopicClassifierService()
    app.state.booking_service = BookingIntentService()
    app.state.assessment_router = AssessmentRouterService()
    print("  ✅ All classifier models loaded")

    # NLP Meta-model detector
    app.state.meta_model_service = MetaModelDetectorService()
    print("  ✅ Meta-Model Detector loaded")

    # LLM — largest, load last
    app.state.lora_service = LoraModelService()
    app.state.lora_service.load_stage1_model()
    print("  ✅ LoRA Stage 1 (Sales) loaded")
    app.state.lora_service.load_stage2_model()
    print("  ✅ LoRA Stage 2 (Therapy) loaded")

    # RAG
    app.state.rag_service = RAGService()
    app.state.embedding_service = EmbeddingService()
    print("  ✅ RAG + Embeddings loaded")

    print("🟢 All systems ready. Saathi is live.")
    yield  # Application runs

    # Shutdown cleanup
    print("🔴 Shutting down Saathi services...")

# Initialize Sentry error tracking
sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    traces_sample_rate=0.1,
    environment=settings.ENVIRONMENT
)

app = FastAPI(
    title="Saathi AI Therapeutic Co-Pilot API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS — restrict to known origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # ["https://app.saathi.ai", "https://widget.saathi.ai"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Mount routes
app.include_router(auth_router,       prefix="/api/auth",        tags=["Authentication"])
app.include_router(chat_router,       prefix="/api/chat",        tags=["Chat"])
app.include_router(assessment_router, prefix="/api/assessments", tags=["Assessments"])
app.include_router(analytics_router,  prefix="/api/analytics",   tags=["Analytics"])
app.include_router(admin_router,      prefix="/api/admin",       tags=["Admin"])
app.include_router(report_router,     prefix="/api/reports",     tags=["Reports"])
```

### 4.3 Core API Endpoints Reference

```
POST   /api/auth/login                    → JWT token
POST   /api/auth/register                 → New user
POST   /api/auth/refresh                  → Refresh token
GET    /api/auth/me                       → Current user profile

POST   /api/chat/message                  → Send message, get AI response
GET    /api/chat/session/{session_id}     → Session history
POST   /api/chat/session/new              → Start new session
GET    /api/chat/sessions                 → All user sessions

POST   /api/assessments/start/{type}      → Start PHQ-9, GAD-7, etc.
POST   /api/assessments/answer            → Submit answer
GET    /api/assessments/score/{id}        → Get scored result
GET    /api/assessments/history/{user_id} → All past assessments
GET    /api/assessments/progress/{type}   → Longitudinal progress

GET    /api/analytics/overview             → Platform KPIs
GET    /api/analytics/engagement           → User engagement metrics
GET    /api/analytics/sentiment-trend      → Session sentiment over time
GET    /api/analytics/crisis-events        → Crisis event analytics
GET    /api/analytics/assessment-outcomes  → Assessment score distributions

GET    /api/admin/users                    → All users (admin)
GET    /api/admin/crisis-dashboard         → Live crisis monitoring
POST   /api/admin/therapist/assign         → Assign therapist to user
GET    /api/admin/companies                → B2B company list (super-admin)

GET    /api/reports/user/{user_id}         → Individual user report
POST   /api/reports/generate               → Generate PDF report
GET    /api/reports/batch/{company_id}     → Company-level report
```

---

## 5. Database Integration

### 5.1 PostgreSQL Schema (Core Tables)

```sql
-- Multi-tenant: every table has company_id for B2B isolation

-- Companies (B2B tenants)
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE,           -- @company.com for SSO
    plan_type VARCHAR(50) DEFAULT 'basic', -- basic, pro, enterprise
    max_users INTEGER,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'employee',  -- employee, therapist, admin, super_admin
    sso_provider VARCHAR(50),             -- google, microsoft, okta
    sso_subject VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    onboarded BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ
);

-- Chat Sessions
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    company_id UUID REFERENCES companies(id),
    stage VARCHAR(50) DEFAULT 'stage1',   -- stage1 (sales), stage2 (therapy)
    mode VARCHAR(50) DEFAULT 'sales',     -- sales, therapeutic
    channel VARCHAR(50) DEFAULT 'widget', -- widget, whatsapp, sms, email
    current_therapeutic_step VARCHAR(100),
    conversation_history JSONB DEFAULT '[]',
    lead_score FLOAT DEFAULT 0,
    booking_completed BOOLEAN DEFAULT false,
    session_summary TEXT,                  -- SOAP note from therapeutic AI
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true
);

-- Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id),
    user_id UUID REFERENCES users(id),
    role VARCHAR(20) NOT NULL,             -- user, assistant, system
    content TEXT NOT NULL,
    emotion_detected VARCHAR(100),
    emotion_intensity FLOAT,
    intent_detected VARCHAR(100),
    topic_detected VARCHAR(100),
    sentiment VARCHAR(20),
    valence_score FLOAT,
    crisis_level VARCHAR(20) DEFAULT 'NONE',
    meta_model_patterns JSONB,
    tokens_used INTEGER,
    processing_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Assessment Sessions
CREATE TABLE assessment_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    company_id UUID REFERENCES companies(id),
    chat_session_id UUID REFERENCES chat_sessions(id),
    assessment_type VARCHAR(50) NOT NULL,  -- PHQ-9, GAD-7, etc.
    responses JSONB NOT NULL,
    total_score INTEGER,
    severity_level VARCHAR(50),
    crisis_indicators JSONB DEFAULT '[]',
    requires_intervention BOOLEAN DEFAULT false,
    referral_suggested BOOLEAN DEFAULT false,
    recommendations TEXT,
    therapist_notes TEXT,
    therapist_reviewed_at TIMESTAMPTZ,
    administered_at TIMESTAMPTZ DEFAULT NOW()
);

-- Crisis Events (7-year retention for EMERGENCY)
CREATE TABLE crisis_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id),
    user_id UUID REFERENCES users(id),
    company_id UUID REFERENCES companies(id),
    escalation_level VARCHAR(20) NOT NULL,  -- WATCH, ELEVATED, HIGH, EMERGENCY
    crisis_type VARCHAR(100),
    severity_score FLOAT,
    c_ssrs_category VARCHAR(200),
    trigger_signals JSONB,
    ai_response_mode VARCHAR(50),
    resources_provided JSONB,
    human_notified BOOLEAN DEFAULT false,
    human_response_time_minutes FLOAT,
    safety_plan_completed BOOLEAN DEFAULT false,
    outcome VARCHAR(100),
    clinical_reviewed_at TIMESTAMPTZ,
    occurred_at TIMESTAMPTZ DEFAULT NOW(),
    retention_until TIMESTAMPTZ          -- computed based on level
);

-- Therapist Assignments
CREATE TABLE therapist_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    therapist_id UUID REFERENCES users(id),
    company_id UUID REFERENCES companies(id),
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Booking Appointments
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    therapist_id UUID REFERENCES users(id),
    company_id UUID REFERENCES companies(id),
    session_id UUID REFERENCES chat_sessions(id),
    scheduled_at TIMESTAMPTZ,
    duration_minutes INTEGER DEFAULT 50,
    format VARCHAR(50) DEFAULT 'video',   -- video, phone, in-person
    status VARCHAR(50) DEFAULT 'pending', -- pending, confirmed, completed, cancelled
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.2 SQLAlchemy Setup

```python
# therapeutic-copilot/server/models/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config.settings import settings

engine = create_async_engine(
    settings.DATABASE_URL,          # postgresql+asyncpg://user:pass@host:5432/saathi
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,             # verify connections before use
    echo=settings.DEBUG
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

# Dependency injection for routes
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### 5.3 Redis Integration

```python
# Caching, session store, and Celery broker

import redis.asyncio as redis
from config.settings import settings

redis_client = redis.from_url(
    settings.REDIS_URL,       # redis://localhost:6379/0
    encoding="utf-8",
    decode_responses=True
)

# Usage patterns:
# Session state:   redis.setex(f"session:{session_id}", 3600, json.dumps(state))
# Lead score:      redis.set(f"lead:{session_id}", score, ex=86400)
# Rate limiting:   redis.incr(f"rate:{user_id}:{endpoint}")
# ML model cache:  redis.setex(f"emotion:{utterance_hash}", 300, json.dumps(result))
```

---

## 6. ML Classifier Pipeline Integration

### 6.1 Classifier Orchestrator

```python
# therapeutic-copilot/server/services/classifier_orchestrator.py

import asyncio
from fastapi import Request

class ClassifierOrchestrator:
    """Runs all classifiers in the correct order for a single message."""

    def __init__(self, request: Request):
        app = request.app
        self.crisis_service      = app.state.crisis_service
        self.emotion_service     = app.state.emotion_service
        self.intent_service      = app.state.intent_service
        self.sentiment_service   = app.state.sentiment_service
        self.topic_service       = app.state.topic_service
        self.booking_service     = app.state.booking_service
        self.assessment_router   = app.state.assessment_router
        self.meta_model_service  = app.state.meta_model_service

    async def classify_message(
        self,
        utterance: str,
        session_id: str,
        conversation_history: list,
        assessment_score: dict = None
    ) -> dict:
        """
        Complete classifier pipeline.
        Returns structured context dict for LLM prompt assembly.
        """

        # ── LAYER 1: Crisis (must be synchronous + first) ──────────────────
        crisis_result = self.crisis_service.detect(utterance)

        # ── LAYER 2: Core classifiers (run in parallel) ────────────────────
        emotion_task   = asyncio.to_thread(self.emotion_service.classify,   utterance)
        intent_task    = asyncio.to_thread(self.intent_service.classify,    utterance)
        sentiment_task = asyncio.to_thread(self.sentiment_service.classify, utterance, session_id)

        emotion_result, intent_result, sentiment_result = await asyncio.gather(
            emotion_task, intent_task, sentiment_task
        )

        # Re-assess crisis with emotion hint (hopelessness flag)
        if crisis_result['crisis_flag'] is False and \
           emotion_result.get('primary_emotion') == 'hopelessness' and \
           emotion_result.get('intensity', 0) > 0.85:
            crisis_result = self.crisis_service.detect(utterance, emotion_hint=emotion_result)

        # ── LAYER 3: Domain enrichment (only if not EMERGENCY) ─────────────
        topic_result = booking_result = assessment_result = {}
        if crisis_result.get('escalation_level') != 'EMERGENCY':
            topic_task    = asyncio.to_thread(self.topic_service.classify,    utterance)
            booking_task  = asyncio.to_thread(self.booking_service.detect,    utterance, conversation_history[-4:])
            topic_result, booking_result = await asyncio.gather(topic_task, booking_task)

            # Assessment routing uses full context window
            assessment_result = await asyncio.to_thread(
                self.assessment_router.route, conversation_history
            )

        # ── LAYER 4: Meta-model (therapeutic mode only) ────────────────────
        meta_model_result = {}
        if intent_result.get('routing_action') == 'THERAPEUTIC_CONVERSATION':
            meta_model_result = await asyncio.to_thread(
                self.meta_model_service.detect, utterance
            )

        return {
            "crisis":      crisis_result,
            "emotion":     emotion_result,
            "intent":      intent_result,
            "sentiment":   sentiment_result,
            "topic":       topic_result,
            "booking":     booking_result,
            "assessment":  assessment_result,
            "meta_model":  meta_model_result
        }
```

### 6.2 Model Loading Configuration

```python
# config/settings.py

class Settings(BaseSettings):
    # Model paths
    ML_MODELS_PATH: str = "./ml_models"
    EMOTION_MODEL_PATH: str = f"{ML_MODELS_PATH}/emotion_classifier"
    CRISIS_MODEL_PATH: str = f"{ML_MODELS_PATH}/crisis_classifier"
    INTENT_MODEL_PATH: str = f"{ML_MODELS_PATH}/intent_classifier"
    TOPIC_MODEL_PATH: str = f"{ML_MODELS_PATH}/topic_classifier"
    SENTIMENT_MODEL_PATH: str = f"{ML_MODELS_PATH}/sentiment_classifier"
    META_MODEL_PATH: str = f"{ML_MODELS_PATH}/meta_model_detector"
    BOOKING_MODEL_PATH: str = f"{ML_MODELS_PATH}/booking_intent_detector"
    ASSESSMENT_ROUTER_PATH: str = f"{ML_MODELS_PATH}/assessment_router"

    # Qwen LoRA paths
    QWEN_BASE_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"
    STAGE1_LORA_PATH: str = f"{ML_MODELS_PATH}/stage1_sales_model"
    STAGE2_LORA_PATH: str = f"{ML_MODELS_PATH}/stage2_therapy_model"

    # Inference settings
    USE_GPU: bool = True
    USE_4BIT_QUANTIZATION: bool = True
    MAX_BATCH_SIZE: int = 4

    class Config:
        env_file = ".env"
```

---

## 7. LoRA Fine-Tuned Qwen LLM Integration

### 7.1 Model Service with Adapter Switching

```python
# therapeutic-copilot/server/services/lora_model_service.py

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

class LoraModelService:
    """Manages Qwen2.5-7B base model with Stage 1 and Stage 2 LoRA adapters."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )

        self.tokenizer = AutoTokenizer.from_pretrained(
            settings.QWEN_BASE_MODEL, trust_remote_code=True
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token

        self.base_model = AutoModelForCausalLM.from_pretrained(
            settings.QWEN_BASE_MODEL,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True
        )

        self.stage1_model = None
        self.stage2_model = None
        self._initialized = True

    def load_stage1_model(self):
        self.stage1_model = PeftModel.from_pretrained(
            self.base_model, settings.STAGE1_LORA_PATH
        )
        self.stage1_model.eval()

    def load_stage2_model(self):
        self.stage2_model = PeftModel.from_pretrained(
            self.base_model, settings.STAGE2_LORA_PATH
        )
        self.stage2_model.eval()

    def generate(
        self,
        conversation_history: list,
        system_prompt: str,
        stage: int = 1,
        max_new_tokens: int = 350,
        temperature: float = 0.8,
    ) -> dict:
        model = self.stage1_model if stage == 1 else self.stage2_model
        messages = [{"role": "system", "content": system_prompt}] + conversation_history
        prompt = self._format_chatml(messages)

        inputs = self.tokenizer(prompt, return_tensors='pt').to(model.device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=0.92,
                top_k=50,
                repetition_penalty=1.1,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        response = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        ).strip()

        return {
            "response": response,
            "tokens_generated": len(outputs[0]) - inputs['input_ids'].shape[1],
            "model_stage": stage
        }

    def _format_chatml(self, messages: list) -> str:
        chatml = ""
        for msg in messages:
            chatml += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
        chatml += "<|im_start|>assistant\n"
        return chatml
```

---

## 8. RAG (Retrieval-Augmented Generation) Integration

### 8.1 RAG Service Integration

```python
# therapeutic-copilot/server/services/rag_service.py

from pinecone import Pinecone
from services.embedding_service import EmbeddingService

class RAGService:
    def __init__(self):
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index = pc.Index(settings.PINECONE_INDEX_NAME)  # "saathi-knowledge-base"
        self.embedding_service = EmbeddingService()
        self.similarity_threshold = 0.70

    def query_knowledge_base(self, query: str, top_k: int = 3, category: str = None) -> list:
        """Retrieve relevant knowledge base documents."""
        embedding = self.embedding_service.generate_embedding(query)
        filter_dict = {"category": {"$eq": category}} if category else None

        results = self.index.query(
            vector=embedding.tolist(),
            top_k=top_k,
            filter=filter_dict,
            include_metadata=True
        )

        documents = [
            {
                "text": match.metadata.get("text", ""),
                "score": match.score,
                "source": match.metadata.get("source", ""),
                "category": match.metadata.get("category", "")
            }
            for match in results.matches
            if match.score >= self.similarity_threshold
        ]
        return documents

    def augment_prompt(self, base_prompt: str, query: str, category: str = None) -> str:
        """Add RAG context to an existing prompt."""
        docs = self.query_knowledge_base(query, top_k=3, category=category)
        if not docs:
            return base_prompt

        rag_block = "\n## Relevant Knowledge Base Context\n"
        for i, doc in enumerate(docs, 1):
            rag_block += f"\n[Source {i}: {doc['source']} | Relevance: {doc['score']:.2f}]\n{doc['text']}\n"
        rag_block += "\nUse the above context to inform your response where relevant. Do not directly quote — synthesise naturally.\n"

        return base_prompt + rag_block
```

### 8.2 Knowledge Base Categories in Pinecone

```python
KNOWLEDGE_BASE_CATEGORIES = {
    "disorders":       "Mental health conditions, symptoms, prevalence",
    "techniques":      "Therapeutic techniques: CBT, DBT, ACT, mindfulness",
    "crisis_protocols":"Crisis response protocols, safety resources",
    "modalities":      "Therapy modalities and what they treat",
    "medications":     "Psychotropic medications (psychoeducation only, not prescription)",
    "assessments":     "Assessment tools and their interpretation",
    "india_resources": "India-specific mental health resources and contacts",
    "workplace":       "Occupational mental health, EAP information"
}

# RAG is used in these scenarios:
RAG_TRIGGER_INTENTS = [
    "information_request",     # User asks factual question
    "psychoeducation_step",    # Therapeutic step 5 — explain a concept
    "assessment_explanation",  # Explain what an assessment measures
    "resource_request"         # User asks for resources/help
]
```

---

## 9. Clinical Assessment Integration

### 9.1 Assessment Route Handler

```python
# therapeutic-copilot/server/routes/assessment_routes.py

from fastapi import APIRouter, Depends, HTTPException
from services.assessment_scoring_service import AssessmentScoringService
from services.crisis_containment_service import CrisisContainmentService
from models.database import get_db

router = APIRouter()

@router.post("/start/{assessment_type}")
async def start_assessment(
    assessment_type: str,
    session_id: str,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Initialize an assessment session and return first question."""
    valid_types = ["PHQ-9","GAD-7","DASS-21","PSS-10","WEMWBS","PCL-5","AUDIT","CAGE-AID"]
    if assessment_type.upper().replace("-","") not in [t.replace("-","") for t in valid_types]:
        raise HTTPException(400, f"Unknown assessment: {assessment_type}")

    # Create assessment session in DB
    session = AssessmentSession(
        user_id=current_user.id,
        assessment_type=assessment_type,
        chat_session_id=session_id,
        responses={}
    )
    db.add(session)
    await db.commit()

    return {
        "assessment_session_id": str(session.id),
        "assessment_type": assessment_type,
        "first_question": get_first_question(assessment_type),
        "total_questions": get_question_count(assessment_type),
        "instructions": get_instructions(assessment_type)
    }

@router.post("/score/{assessment_session_id}")
async def score_assessment(
    assessment_session_id: str,
    responses: dict,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Score completed assessment and check for crisis flags."""
    assessment = await db.get(AssessmentSession, assessment_session_id)
    if not assessment:
        raise HTTPException(404, "Assessment session not found")

    # Score
    result = AssessmentScoringService.score_assessment(
        assessment.assessment_type, responses
    )

    # Crisis check on assessment result
    if result.get('crisis_indicators'):
        await CrisisContainmentService().flag_assessment_crisis(
            user_id=current_user.id,
            assessment_type=assessment.assessment_type,
            indicators=result['crisis_indicators'],
            score=result
        )

    # Persist result
    assessment.responses = responses
    assessment.total_score = result['total_score']
    assessment.severity_level = result['severity_level']
    assessment.crisis_indicators = result.get('crisis_indicators', [])
    assessment.requires_intervention = result.get('requires_intervention', False)
    await db.commit()

    return result
```

---

## 10. Crisis Containment System Integration

### 10.1 Crisis Alert Service

```python
# therapeutic-copilot/server/services/notification_service.py

from twilio.rest import Client as TwilioClient
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

class NotificationService:
    def __init__(self):
        self.twilio = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.sendgrid = SendGridAPIClient(settings.SENDGRID_API_KEY)

    async def send_crisis_sms(self, to_phone: str, crisis_summary: str):
        """Send SMS alert for EMERGENCY crisis events."""
        self.twilio.messages.create(
            body=f"🚨 SAATHI CRISIS ALERT\n{crisis_summary}\nReply ACKNOWLEDGED to confirm.",
            from_=settings.TWILIO_PHONE,
            to=to_phone
        )

    async def send_crisis_email(self, to_email: str, crisis_data: dict):
        """Send email alert with full crisis handoff package."""
        message = Mail(
            from_email=settings.FROM_EMAIL,
            to_emails=to_email,
            subject=f"🚨 [{crisis_data['escalation_level']}] Saathi Crisis Alert — Action Required",
            html_content=self._build_crisis_email_html(crisis_data)
        )
        self.sendgrid.send(message)

    async def notify_admin_dashboard(self, crisis_event: dict):
        """Push real-time crisis event to admin Socket.io channel."""
        from socket_manager import sio
        await sio.emit('crisis_alert', crisis_event, room=f"company_{crisis_event['company_id']}")
```

---

## 11. Safety & Hallucination Control Integration

### 11.1 Safety Service (Post-Generation Checks)

```python
# therapeutic-copilot/server/services/safety_service.py

import re
from typing import Optional

class SafetyService:
    """Post-generation safety and hallucination checks on LLM output."""

    # Patterns that MUST NOT appear in AI responses
    HARMFUL_PATTERNS = [
        r"you should (kill|harm|hurt) yourself",
        r"(methods|ways) (of|to) (commit|die by) suicide",
        r"guarantee.*(cure|recovery|better)",
        r"(diagnos|prescri)(e|ing)\b",           # AI must not diagnose or prescribe
        r"you (have|definitely have|clearly have) (depression|anxiety|PTSD|bipolar)",
        r"stop (taking|using) your medication",
        r"(illegal|better) (drug|substance)",
    ]

    # Clinical boundary violations
    BOUNDARY_VIOLATIONS = [
        r"as your (therapist|doctor|psychiatrist)",  # AI is not a licensed clinician
        r"I (diagnose|diagnos[ei])",
        r"you need (medication|drugs|antidepressants)",
        r"(definitely|certainly|100%) (have|are)",  # absolute clinical statements
    ]

    # Factual claims that need RAG verification
    FACTUAL_CLAIM_PATTERNS = [
        r"\d+% of people",     # statistics
        r"studies (show|prove)",
        r"research (shows|proves|found)",
        r"(medication|drug) .{0,30} (works|treats|cures)",
    ]

    def check_response(self, response: str) -> dict:
        """Run all safety checks on generated response."""
        violations = []

        for pattern in self.HARMFUL_PATTERNS:
            if re.search(pattern, response.lower()):
                violations.append({"type": "harmful_content", "pattern": pattern})

        for pattern in self.BOUNDARY_VIOLATIONS:
            if re.search(pattern, response.lower()):
                violations.append({"type": "boundary_violation", "pattern": pattern})

        factual_claims = []
        for pattern in self.FACTUAL_CLAIM_PATTERNS:
            if re.search(pattern, response.lower()):
                factual_claims.append(pattern)

        return {
            "safe": len(violations) == 0,
            "violations": violations,
            "factual_claims_present": len(factual_claims) > 0,
            "factual_claims": factual_claims,
            "requires_rag_verification": len(factual_claims) > 0
        }

    def get_safe_fallback(self, emotion_result: dict) -> str:
        """Return a clinically safe fallback response when violations detected."""
        emotion = emotion_result.get('primary_emotion', 'neutral')
        fallbacks = {
            "hopelessness": "I hear how difficult things feel right now. I want to make sure you're supported. Would it be okay if we took a step back and just talked about what's been happening?",
            "anxiety": "It sounds like you're carrying a lot right now. Let's take this one moment at a time. What feels most pressing for you right now?",
            "sadness": "I can hear how much pain you're in. I'm here with you. Take your time — there's no rush.",
        }
        return fallbacks.get(emotion, "I want to make sure I'm supporting you well. Could you tell me a little more about what you're experiencing?")

    def verify_factual_claim(self, claim: str, rag_service) -> Optional[str]:
        """Verify a factual claim against the knowledge base."""
        docs = rag_service.query_knowledge_base(claim, top_k=2)
        if not docs:
            return None  # Cannot verify — remove claim or soften
        return docs[0]['text'] if docs else None
```

### 11.2 Hallucination Prevention Strategy

```python
HALLUCINATION_PREVENTION = {
    "temperature_settings": {
        "stage1_sales": 0.80,     # Higher creativity acceptable in sales
        "stage2_therapy": 0.70,   # Lower for clinical precision
        "crisis_response": 0.0,   # Deterministic — pre-crafted only
        "assessment_debrief": 0.65
    },
    "repetition_penalty": 1.1,    # Prevent repetitive affirmations
    "factual_augmentation": "rag", # Factual claims use RAG to ground them
    "clinical_claim_rules": [
        "Never state a diagnosis",
        "Always qualify statistics with 'research suggests'",
        "Never promise specific outcomes",
        "Use hedging: 'many people find', 'some research indicates'"
    ],
    "post_generation_checks": [
        "SafetyService.check_response()",
        "CrisisContainmentService.scan_ai_response()",  # AI response can also be crisis-checked
        "BoundaryEnforcer.check()"
    ]
}
```

---

## 12. Chat System Integration

### 12.1 Complete Chat Route Handler

```python
# therapeutic-copilot/server/routes/chat_routes.py

from fastapi import APIRouter, Depends, Request
from utils.prompt_assembler import assemble_complete_system_prompt
from services.safety_service import SafetyService

router = APIRouter()
safety_service = SafetyService()

@router.post("/message")
async def process_message(
    request_body: ChatMessageRequest,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    message = request_body.message
    session_id = request_body.session_id

    # Load session from DB
    session = await get_or_create_session(session_id, current_user.id, db)

    # ── 1. CRISIS ASSESSMENT (mandatory, first) ─────────────────────────────
    crisis_result = request.app.state.crisis_service.detect(
        utterance=message,
        emotion_hint=None,
        session_id=session_id
    )
    if crisis_result.get('escalation_level') == 'EMERGENCY':
        await log_crisis(crisis_result, session_id, current_user.id, db)
        await request.app.state.notification_service.send_crisis_alerts(crisis_result, session)
        return build_emergency_response(crisis_result)

    # ── 2. ALL CLASSIFIERS ───────────────────────────────────────────────────
    orchestrator = ClassifierOrchestrator(request)
    ctx = await orchestrator.classify_message(
        utterance=message,
        session_id=session_id,
        conversation_history=session.conversation_history
    )

    # ── 3. RAG AUGMENTATION ──────────────────────────────────────────────────
    rag_context = ""
    if ctx['intent'].get('routing_action') == 'RAG_KNOWLEDGE_BASE' or \
       ctx['assessment'].get('primary_assessment'):
        rag_docs = request.app.state.rag_service.query_knowledge_base(message)
        rag_context = format_rag_context(rag_docs)

    # ── 4. PROMPT ASSEMBLY ───────────────────────────────────────────────────
    stage = session.stage  # "stage1" or "stage2"
    base_prompt = get_base_prompt(stage, session, current_user)
    system_prompt = assemble_complete_system_prompt(
        base_prompt=base_prompt,
        crisis_context=ctx['crisis'],
        emotion_context=ctx['emotion'],
        intent_context=ctx['intent'],
        topic_context=ctx['topic'],
        sentiment_context=ctx['sentiment'],
        meta_model_context=ctx['meta_model'],
        booking_context=ctx['booking'],
        assessment_context=ctx['assessment'],
        rag_context=rag_context,
        therapeutic_step=session.current_therapeutic_step,
        session_number=session.session_number
    )

    # ── 5. LLM GENERATION ────────────────────────────────────────────────────
    stage_num = 1 if stage == "stage1" else 2
    llm_result = request.app.state.lora_service.generate(
        conversation_history=session.conversation_history,
        system_prompt=system_prompt,
        stage=stage_num,
        temperature=0.75 if stage_num == 2 else 0.80
    )
    ai_response = llm_result['response']

    # ── 6. SAFETY CHECK ──────────────────────────────────────────────────────
    safety_check = safety_service.check_response(ai_response)
    if not safety_check['safe']:
        ai_response = safety_service.get_safe_fallback(ctx['emotion'])

    # ── 7. PERSIST & RETURN ──────────────────────────────────────────────────
    await save_message(session_id, 'user', message, ctx, db)
    await save_message(session_id, 'assistant', ai_response, {}, db)
    await update_session_state(session_id, ctx, db)

    return {
        "message": ai_response,
        "session_id": session_id,
        "stage": stage,
        "emotion_detected": ctx['emotion'].get('primary_emotion'),
        "crisis_level": ctx['crisis'].get('escalation_level', 'NONE'),
        "assessment_suggested": ctx['assessment'].get('primary_assessment'),
        "booking_intent": ctx['booking'].get('booking_intent', False),
        "tokens_used": llm_result.get('tokens_generated', 0)
    }
```

---

## 13. Report Generation & Recommendation Engine

### 13.1 Report Service

```python
# therapeutic-copilot/server/services/report_service.py

from weasyprint import HTML               # PDF generation
from jinja2 import Environment, FileSystemLoader

class ReportService:
    """Generates clinical reports for users, therapists, and HR admins."""

    def __init__(self):
        self.jinja_env = Environment(loader=FileSystemLoader("templates/reports"))

    async def generate_user_report(self, user_id: str, db) -> bytes:
        """Individual user progress report (PDF)."""
        # Gather data
        user = await db.get(User, user_id)
        sessions = await get_user_sessions(user_id, db)
        assessments = await get_assessment_history(user_id, db)
        crisis_events = await get_crisis_events(user_id, db)

        # Generate recommendations via LLM
        recommendations = await self._generate_recommendations(user, assessments, sessions)

        # Render HTML template
        template = self.jinja_env.get_template("user_report.html")
        html_content = template.render(
            user=user,
            sessions=sessions,
            assessments=assessments,
            crisis_events=[e for e in crisis_events if e.escalation_level != 'WATCH'],
            recommendations=recommendations,
            generated_at=datetime.utcnow(),
            disclaimer=CLINICAL_DISCLAIMER
        )

        # Convert to PDF
        return HTML(string=html_content).write_pdf()

    async def _generate_recommendations(
        self,
        user,
        assessments: list,
        sessions: list
    ) -> dict:
        """Use LLM to generate personalised recommendations based on progress."""
        # Build context from data
        assessment_summary = format_assessment_summary(assessments)
        session_summary = format_session_summary(sessions)

        prompt = f"""You are a clinical report generator for Saathi, an AI therapeutic co-pilot.
Based on the following client data, generate:
1. A brief clinical summary (2-3 sentences)
2. Key progress observed (bullet points)
3. Areas still needing attention (bullet points)
4. Recommended next steps (3-5 concrete recommendations)

Assessment History:
{assessment_summary}

Session Summary:
{session_summary}

Output as structured JSON only.
"""
        response = await call_openai_for_report(prompt)  # Use GPT-4 for reports (higher accuracy)
        return parse_report_json(response)

    async def generate_company_report(self, company_id: str, date_range: dict, db) -> bytes:
        """Anonymised aggregate report for HR/Wellness admin."""
        # All data anonymised — no PII
        stats = await get_company_aggregate_stats(company_id, date_range, db)
        template = self.jinja_env.get_template("company_report.html")
        html = template.render(stats=stats, generated_at=datetime.utcnow())
        return HTML(string=html).write_pdf()
```

---

## 14. Analytics & Dashboards Integration

### 14.1 Analytics Service

```python
# therapeutic-copilot/server/services/analytics_service.py

class AnalyticsService:

    async def get_platform_overview(self, company_id: str, db) -> dict:
        """KPI dashboard for admin."""
        return {
            "total_users": await count_users(company_id, db),
            "active_users_30d": await count_active_users(company_id, 30, db),
            "total_sessions": await count_sessions(company_id, db),
            "avg_sessions_per_user": await avg_sessions(company_id, db),
            "booking_conversion_rate": await calc_booking_conversion(company_id, db),
            "assessments_completed": await count_assessments(company_id, db),
            "crisis_events_30d": await count_crisis_events(company_id, 30, db),
            "avg_phq9_score": await avg_score("PHQ-9", company_id, db),
            "avg_gad7_score": await avg_score("GAD-7", company_id, db),
            "sentiment_trend": await get_sentiment_trend(company_id, db),
            "top_topics": await get_topic_distribution(company_id, db)
        }

    async def get_sentiment_trend(self, company_id: str, days: int = 30, db = None) -> list:
        """Platform-wide sentiment trend over time (anonymised)."""
        # Returns: [{date, avg_valence, positive_pct, negative_pct}]
        pass

    async def get_assessment_outcomes_distribution(self, company_id: str, db) -> dict:
        """Distribution of assessment scores across company (anonymised, aggregated)."""
        # Returns severity level distributions for each assessment type
        pass
```

### 14.2 Analytics Frontend (Recharts)

```typescript
// src/components/dashboard/SentimentTrendChart.tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export function SentimentTrendChart({ data }: { data: SentimentDataPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <XAxis dataKey="date" />
        <YAxis domain={[-1, 1]} />
        <Tooltip formatter={(val) => `${(Number(val) * 100).toFixed(0)}%`} />
        <Line type="monotone" dataKey="avg_valence"
              stroke="#6366f1" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

// src/components/dashboard/AssessmentProgressCard.tsx
// Shows PHQ-9/GAD-7 scores over time with severity color coding
// src/components/dashboard/CrisisDashboard.tsx
// Real-time crisis event monitoring (admin only)
```

---

## 15. Authentication & Multi-Tenancy Integration

### 15.1 Authentication Strategy

```python
# JWT + Supabase Auth + SSO (SAML/OAuth for enterprise)

from jose import JWTError, jwt
from supabase import create_client

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Supported auth methods:
# 1. Email + password (hashed with bcrypt)
# 2. Google OAuth
# 3. Microsoft OAuth (for corporate B2B)
# 4. Okta SAML (enterprise SSO)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    return user
```

### 15.2 Multi-Tenancy Row-Level Security (PostgreSQL)

```sql
-- Enable RLS on all tables
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Company isolation policy
CREATE POLICY company_isolation ON messages
    USING (company_id = current_setting('app.current_company_id')::UUID);

-- Applied to: messages, chat_sessions, assessment_sessions,
--             crisis_events, appointments, users
```

---

## 16. Real-Time Communication Layer

### 16.1 Socket.io Server Integration

```python
# therapeutic-copilot/server/socket_manager.py

import socketio
from fastapi import FastAPI

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=settings.ALLOWED_ORIGINS,
    logger=False
)

@sio.event
async def connect(sid, environ, auth):
    """Authenticate WebSocket connection."""
    token = auth.get('token')
    user = await verify_ws_token(token)
    if not user:
        raise ConnectionRefusedError("Invalid token")
    await sio.save_session(sid, {'user_id': user.id, 'company_id': user.company_id})
    # Join company room (for broadcast events)
    await sio.enter_room(sid, f"company_{user.company_id}")
    # Join admin room if admin
    if user.role in ['admin', 'therapist']:
        await sio.enter_room(sid, f"admin_{user.company_id}")

@sio.event
async def chat_message(sid, data):
    """Handle incoming chat message via WebSocket."""
    session = await sio.get_session(sid)
    # Emit typing indicator
    await sio.emit('typing_start', room=sid)
    # Process message (same pipeline as HTTP route)
    response = await process_chat_message(
        message=data['message'],
        session_id=data['session_id'],
        user_id=session['user_id']
    )
    await sio.emit('typing_end', room=sid)
    await sio.emit('chat_response', response, room=sid)
```

---

## 17. Notification & Alerting System

### 17.1 Multi-Channel Notification Configuration

```python
NOTIFICATION_CONFIG = {
    "crisis_EMERGENCY": {
        "channels": ["sms", "email", "dashboard_push", "admin_dashboard"],
        "recipients": ["on_call_counselor", "clinical_director", "company_admin"],
        "sla_minutes": 5,
        "retry_attempts": 3
    },
    "crisis_HIGH": {
        "channels": ["email", "dashboard_push"],
        "recipients": ["intake_team", "assigned_therapist"],
        "sla_minutes": 15
    },
    "booking_confirmed": {
        "channels": ["email", "sms"],
        "recipients": ["user", "therapist"],
        "sla_minutes": None
    },
    "assessment_completed": {
        "channels": ["email"],
        "recipients": ["assigned_therapist"],
        "sla_minutes": None
    },
    "weekly_report": {
        "channels": ["email"],
        "recipients": ["company_admin"],
        "sla_minutes": None,
        "schedule": "every Monday 9am"
    }
}
```

### 17.2 WhatsApp Integration (Twilio)

```python
# Multi-channel chat via WhatsApp
@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Handle incoming WhatsApp messages via Twilio webhook."""
    form_data = await request.form()
    from_number = form_data.get('From')   # whatsapp:+91XXXXXXXXXX
    message_body = form_data.get('Body')

    # Route through same pipeline with channel='whatsapp'
    response = await process_chat_message(
        message=message_body,
        session_id=get_or_create_whatsapp_session(from_number),
        channel='whatsapp'
    )

    # Format for WhatsApp (brief, no markdown)
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{response['message'][:1600]}</Message>
</Response>"""
    return Response(content=twiml_response, media_type="application/xml")
```

---

## 18. Deployment & Infrastructure Integration

### 18.1 Docker Compose (Development)

```yaml
# docker-compose.yml
version: '3.9'

services:
  api:
    build: ./therapeutic-copilot/server
    ports:
      - "8000:8000"
    volumes:
      - ./therapeutic-copilot/server:/app
      - ./ml_models:/app/ml_models    # mount pre-downloaded model weights
    environment:
      - DATABASE_URL=postgresql+asyncpg://saathi:password@db:5432/saathi
      - REDIS_URL=redis://redis:6379/0
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - TOGETHER_API_KEY=${TOGETHER_API_KEY}
    depends_on:
      - db
      - redis
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]   # GPU for Qwen inference

  client:
    build: ./therapeutic-copilot/client
    ports:
      - "3000:3000"
    environment:
      - VITE_API_BASE_URL=http://localhost:8000

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: saathi
      POSTGRES_USER: saathi
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  celery_worker:
    build: ./therapeutic-copilot/server
    command: celery -A tasks worker --loglevel=info
    depends_on:
      - redis
      - api

  nginx:
    image: nginx:1.24
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
      - client

volumes:
  postgres_data:
  redis_data:
```

### 18.2 Production Infrastructure (AWS)

```
Production Architecture (AWS):
├── Route 53          → DNS
├── CloudFront CDN    → Static assets (React build)
├── ALB               → Load balancer for API
├── ECS (Fargate)     → API containers (auto-scaling)
├── EC2 g4dn.xlarge  → GPU instance for Qwen inference (dedicated)
├── RDS PostgreSQL    → Managed database (Multi-AZ)
├── ElastiCache Redis → Managed Redis
├── S3                → Reports, model weights, static assets
├── Pinecone          → Vector DB (managed cloud)
├── CloudWatch        → Logs, metrics, alarms
├── Secrets Manager   → All API keys and credentials
└── WAF               → Web Application Firewall
```

---

## 19. Environment Configuration Reference

### 19.1 Complete .env Reference

```env
# therapeutic-copilot/server/.env

# ── Application ──────────────────────────────────────────────────────────────
ENVIRONMENT=production              # development | staging | production
DEBUG=false
SECRET_KEY=your_secret_key_here
ALLOWED_ORIGINS=https://app.saathi.ai,https://widget.saathi.ai

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/saathi
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_SERVICE_KEY=your_service_key

# ── Redis ────────────────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── Auth ─────────────────────────────────────────────────────────────────────
JWT_SECRET=your_jwt_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ── LLM APIs ─────────────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-...              # GPT-4o for reports + fallback
TOGETHER_API_KEY=...               # Qwen cloud inference (optional)
ANTHROPIC_API_KEY=...              # Optional fallback

# ── ML Models ────────────────────────────────────────────────────────────────
ML_MODELS_PATH=./ml_models
QWEN_BASE_MODEL=Qwen/Qwen2.5-7B-Instruct
USE_GPU=true
USE_4BIT_QUANTIZATION=true

# ── Vector DB ────────────────────────────────────────────────────────────────
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=saathi-knowledge-base
PINECONE_ENVIRONMENT=us-east-1-aws

# ── Communication ────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE=+1XXXXXXXXXX
SENDGRID_API_KEY=SG....
FROM_EMAIL=noreply@saathi.ai

# ── Monitoring ───────────────────────────────────────────────────────────────
SENTRY_DSN=https://xxx@sentry.io/xxx
WANDB_API_KEY=...
WANDB_PROJECT=saathi-ml

# ── Crisis ───────────────────────────────────────────────────────────────────
ON_CALL_COUNSELOR_PHONE=+91XXXXXXXXXX
CRISIS_TEAM_EMAIL=crisis@saathi.ai
INTAKE_TEAM_EMAIL=intake@saathi.ai

# ── Storage ──────────────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-south-1
S3_BUCKET_REPORTS=saathi-reports
S3_BUCKET_MODELS=saathi-ml-models
```

---

## 20. Integration Test Checklist

### 20.1 Pre-Deploy Integration Tests

```python
# tests/integration/test_full_pipeline.py

import pytest
import asyncio

class TestFullMessagePipeline:

    @pytest.mark.asyncio
    async def test_normal_therapeutic_message(self, client, auth_headers, session_id):
        """Normal message flows through all classifiers → LLM → response."""
        response = await client.post("/api/chat/message", json={
            "message": "I've been feeling anxious about work lately",
            "session_id": session_id
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data['emotion_detected'] is not None
        assert data['crisis_level'] == 'NONE'

    @pytest.mark.asyncio
    async def test_crisis_emergency_bypasses_llm(self, client, auth_headers, session_id):
        """EMERGENCY crisis message must return pre-crafted response, not LLM output."""
        response = await client.post("/api/chat/message", json={
            "message": "I have pills ready and I'm going to take them all tonight",
            "session_id": session_id
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['crisis_level'] == 'EMERGENCY'
        assert '112' in data['message'] or '1860' in data['message']  # emergency number present

    @pytest.mark.asyncio
    async def test_assessment_phq9_complete_and_score(self, client, auth_headers):
        """Start PHQ-9, submit all answers, receive valid scored result."""
        start = await client.post("/api/assessments/start/PHQ-9", headers=auth_headers)
        session_id = start.json()['assessment_session_id']

        responses = {f'q{i}': 1 for i in range(1, 10)}  # All "Several days"
        score = await client.post(f"/api/assessments/score/{session_id}",
                                   json=responses, headers=auth_headers)
        data = score.json()
        assert data['total_score'] == 9
        assert data['severity_level'] == 'mild'

    @pytest.mark.asyncio
    async def test_rag_knowledge_base_query(self, client, auth_headers, session_id):
        """Information request triggers RAG retrieval."""
        response = await client.post("/api/chat/message", json={
            "message": "What is CBT and how does it work?",
            "session_id": session_id
        }, headers=auth_headers)
        assert response.status_code == 200
        # Response should contain substantive CBT information

    @pytest.mark.asyncio
    async def test_booking_intent_detection(self, client, auth_headers, session_id):
        """Booking intent triggers booking flow."""
        response = await client.post("/api/chat/message", json={
            "message": "I think I'm ready to book a session for next week",
            "session_id": session_id
        }, headers=auth_headers)
        data = response.json()
        assert data['booking_intent'] is True

    @pytest.mark.asyncio
    async def test_safety_check_blocks_harmful_response(self):
        """Safety service catches harmful AI-generated content."""
        from services.safety_service import SafetyService
        service = SafetyService()
        # This should be caught
        result = service.check_response("You should definitely try taking all your medication at once")
        assert result['safe'] is False
        assert len(result['violations']) > 0

    @pytest.mark.asyncio
    async def test_report_generation(self, client, auth_headers, user_id):
        """Report generation returns valid PDF."""
        response = await client.post("/api/reports/generate",
                                      json={"user_id": user_id}, headers=auth_headers)
        assert response.status_code == 200
        assert response.headers['content-type'] == 'application/pdf'
```

---

## 21. Missing Tech Additions & Recommendations

### 21.1 Technologies Not Yet in Stack — Recommended Additions

| Technology | Purpose | Priority | Estimated Effort |
|-----------|---------|----------|-----------------|
| **Celery Beat** | Scheduled tasks (weekly reports, re-assessment reminders) | HIGH | 1 day |
| **Flower** | Celery monitoring dashboard | MEDIUM | 0.5 day |
| **Prometheus + Grafana** | Server metrics, ML model latency dashboards | HIGH | 2 days |
| **OpenTelemetry** | Distributed tracing across services | MEDIUM | 2 days |
| **Alembic** | Database migration management | HIGH | 1 day |
| **WeasyPrint** | PDF report generation | HIGH | 0.5 day |
| **Jinja2** | Report HTML templating | HIGH | included |
| **ONNX Runtime** | Optimized CPU inference for DistilBERT models | HIGH | 1 day |
| **Apache Airflow** | ML training pipeline orchestration | MEDIUM | 3 days |
| **MinIO** | Self-hosted S3-compatible object storage (for India data sovereignty) | MEDIUM | 1 day |
| **Keycloak** | Enterprise SSO (SAML/OIDC) for large B2B clients | MEDIUM | 3 days |
| **Elastic APM** | Application performance monitoring | LOW | 1 day |
| **pgVector** | Store embeddings directly in PostgreSQL (reduce Pinecone cost) | MEDIUM | 2 days |
| **Langfuse** | LLM observability — track prompts, responses, latency, cost | HIGH | 1 day |
| **LiteLLM** | Unified LLM API gateway (switch between GPT-4/Qwen/Claude easily) | MEDIUM | 0.5 day |
| **guardrails-ai** | Structured safety/validation layer for LLM outputs | HIGH | 1 day |
| **HTTPX** | Async HTTP client for external API calls | HIGH | already available |
| **pytest-asyncio** | Async test support | HIGH | 0.5 day |

### 21.2 Integration Priorities for Go-Live

**Phase 1 (Must have before launch):**
1. Alembic migrations
2. JWT auth + Supabase
3. Crisis containment (all 4 levels)
4. All 10 ML classifiers loaded at startup
5. LoRA Stage 1 + Stage 2
6. PHQ-9 + GAD-7 scoring + crisis check
7. Basic admin dashboard
8. Sentry error tracking
9. SendGrid crisis email alerts
10. Safety service (post-generation checks)

**Phase 2 (Within 30 days of launch):**
1. Langfuse LLM observability
2. Prometheus + Grafana dashboards
3. Celery Beat for scheduled reports
4. PDF report generation
5. RAG knowledge base fully populated
6. ONNX optimization for CPU classifiers
7. WhatsApp channel (Twilio)
8. Longitudinal assessment tracking

**Phase 3 (Scaling — 90 days):**
1. Enterprise SSO (Keycloak/Okta)
2. pgVector migration (reduce Pinecone cost)
3. Apache Airflow for ML retraining pipeline
4. Multi-region deployment
5. guardrails-ai integration

---

## Summary: Integration Dependency Map

```
Frontend (React + Vite)
    → FastAPI Backend (Uvicorn)
        → PostgreSQL (Supabase managed)
        → Redis (cache + sessions + Celery)
        → Pinecone (RAG vector DB)
        → ML Models (PyTorch + HuggingFace)
            → 5× DistilBERT classifiers (emotion/intent/topic/sentiment/booking)
            → 2× RoBERTa (crisis + assessment router)
            → 1× Flan-T5 LoRA (meta-model)
            → 1× Qwen2.5-7B + Stage1 LoRA + Stage2 LoRA
        → OpenAI API (reports + fallback)
        → Twilio (WhatsApp + SMS)
        → SendGrid (email)
        → Sentry (error tracking)
        → Socket.io (real-time chat)
    → Celery (async tasks)
        → Redis (broker)
        → S3 (report storage)
    → Nginx (reverse proxy + SSL)
```

---

*Document Version: 1.0 | Platform Version: saathi-v1.0 | Last Updated: 2025-03*
*This document is the single source of truth for all integration requirements. Review before any tech stack change.*
