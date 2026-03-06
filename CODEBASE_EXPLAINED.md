# SAATHI AI — CODEBASE EXPLAINED
## Every Folder, Every File, Every Line — For the Vibes Coder
### Written in plain English. No jargon. Real talk.

---

> **How to use this document:**
> Read the folder section first to understand the big picture.
> Then read the line-by-line code breakdown for each file.
> Think of this as someone sitting next to you explaining the code out loud.

---

## THE BIG PICTURE — What Is This App?

Imagine you are a mental health clinic. You have a website. You want an AI chatbot that:
1. **Talks to visitors** and convinces them to book a therapy session (Stage 1 — Lead)
2. **Supports patients** between their weekly therapy sessions with structured AI conversations (Stage 2 — Therapy)
3. **Reaches out** to patients who disappeared and brings them back (Stage 3 — Re-engagement)

The clinician (therapist) sits at a dashboard and watches everything in real time. If the AI detects a patient is in crisis (suicidal thoughts), it instantly alerts the clinician.

That is the entire app. Everything in this codebase exists to make that happen.

---

## HOW THE APP IS STRUCTURED — The Restaurant Analogy

Think of this app like a restaurant:

| Restaurant Part | Saathi AI Part |
|----------------|----------------|
| The menu visible to customers | **Widget** — the chatbot bubble on the clinic's website |
| The front-of-house staff taking orders | **Routes** — receive requests from the browser |
| The kitchen doing the actual cooking | **Services** — do the real work (AI, payments, crisis detection) |
| The recipe book | **Models** — define what the database looks like |
| The fridge/pantry | **Database** — stores all the data |
| The restaurant's rulebook | **Config** — all settings in one place |

---

## FOLDER STRUCTURE — FULL MAP

```
SAATHI-AI-PROTOTYPE/
│
├── therapeutic-copilot/               ← THE ENTIRE APP LIVES HERE
│   │
│   ├── server/                        ← THE BRAIN (Python/FastAPI backend)
│   │   ├── main.py                    ← Front door of the backend
│   │   ├── config.py                  ← All settings/secrets
│   │   ├── database.py                ← How the app talks to the database
│   │   ├── models.py                  ← Blueprint of all database tables
│   │   ├── config_manager.py          ← Startup check: "did you set all secrets?"
│   │   ├── requirements.txt           ← Shopping list of Python packages
│   │   ├── Dockerfile                 ← How to pack this into a container
│   │   │
│   │   ├── api/                       ← SIMPLE ROUTE HANDLERS (just receive & pass on)
│   │   ├── routes/                    ← SMART ROUTE HANDLERS (do some logic)
│   │   ├── services/                  ← THE ACTUAL BRAIN (all real logic lives here)
│   │   ├── middleware/                ← SECURITY GUARDS (check tokens, throttle requests)
│   │   ├── auth/                      ← LOGIN SYSTEM (passwords + tokens)
│   │   ├── models/                    ← DATA SHAPES (what data looks like in/out)
│   │   └── alembic/                   ← DATABASE MIGRATION TOOL
│   │
│   ├── client/                        ← THE FACE (React frontend — what clinicians see)
│   │   └── src/
│   │       ├── components/            ← UI BUILDING BLOCKS
│   │       │   ├── chatbot/           ← The chat window component
│   │       │   ├── clinician/         ← The clinician's dashboard
│   │       │   ├── patient/           ← The patient's portal
│   │       │   ├── analytics/         ← Charts and stats
│   │       │   ├── admin/             ← Admin control panel
│   │       │   ├── landing/           ← The public marketing website
│   │       │   ├── payment/           ← Razorpay payment screen
│   │       │   └── ui/                ← Reusable small pieces (Button, Badge, etc.)
│   │       ├── contexts/              ← GLOBAL STATE (who is logged in?)
│   │       ├── hooks/                 ← REUSABLE LOGIC (WebSocket chat hook)
│   │       ├── lib/                   ← API CALLER (talks to backend)
│   │       ├── pages/                 ← PAGE EXPORTS
│   │       └── types/                 ← TYPESCRIPT TYPES (data shape definitions)
│   │
│   ├── widget/                        ← THE EMBED (the chatbot that goes on client websites)
│   │   └── src/
│   │       ├── widget.ts              ← Entry point, creates the floating chat button
│   │       └── components/            ← Widget UI components
│   │
│   ├── ml_pipeline/                   ← AI TRAINING (how the AI was taught)
│   ├── tests/                         ← AUTOMATED TESTS (making sure nothing breaks)
│   ├── scripts/                       ← HELPER SCRIPTS (setup database, generate tokens)
│   └── docker-compose.yml             ← RUN EVERYTHING WITH ONE COMMAND
│
├── DEVELOPER_GUIDE.md                 ← Build log (every step recorded)
├── DEVELOPER_SETUP_README.md          ← How to set up the project
├── PROTOTYPE_BUILDING_DOCUMENT.md     ← Business + investor spec
├── CODEBASE_EXPLAINED.md              ← THIS FILE
└── docker-compose.prod.yml            ← Production deployment
```

---

---

# PART 1 — EVERY FOLDER EXPLAINED

---

## FOLDER: `therapeutic-copilot/server/`
### Working Principle: The Brain

**Why does this folder exist?**
Everything the AI does, every database operation, every payment, every login — all of that runs in this folder. This is the backend. It is a Python server that listens for requests from the frontend (React app) or from the widget (chat bubble) and responds with data.

**What technology?** FastAPI — a Python web framework that is extremely fast and automatically creates documentation for every endpoint at `/docs`.

**How does it work?**
- The frontend (React) sends an HTTP request: "here is a patient message"
- The backend receives it, runs it through crisis detection, sends it to the AI, gets a response
- The backend sends that response back to the frontend
- The frontend shows it to the user

**What is the main job of each sub-file?**

| File | Job in the App |
|------|---------------|
| `main.py` | Opens the front door. Connects all routes together. Like the reception desk of the restaurant |
| `config.py` | Holds all secrets and settings. API keys, database address, port numbers |
| `database.py` | Sets up the connection to the database. Like the water pipes — runs in background |
| `models.py` | Defines the shape of every database table (Tenant, Clinician, Patient, etc.) |
| `config_manager.py` | On startup, checks: "did the developer set all required environment variables?" |
| `requirements.txt` | List of all Python libraries the app needs to install |

---

## FOLDER: `therapeutic-copilot/server/api/`
### Working Principle: The Simple Waiters

**Why does this folder exist?**
These are the simplest route handlers. They just receive a request, check the shape of the data, and hand it off. Think of them as the junior staff who take your order and walk it to the kitchen.

**What lives here:**
- `tenants.py` — Handles creating and listing clinics (B2B customers)
- `users.py` — Handles clinician profile (who is logged in, update profile)
- `leads.py` — Handles Stage 1 leads (new visitors who started chatting)
- `appointments.py` — Handles booking therapy sessions
- `chat.py` — Basic chat endpoint (simplified version)
- `payments.py` — Basic payment endpoints (simplified version)

**How it connects to the app:**
When someone calls `POST /api/v1/leads/`, it hits this folder's `leads.py` file, which calls the appropriate service to save the lead.

---

## FOLDER: `therapeutic-copilot/server/routes/`
### Working Principle: The Senior Waiters With Brain

**Why does this folder exist?**
These are more complex route handlers. Unlike `api/`, these routes contain real decision-making logic and use FastAPI features like `BackgroundTasks` (do something in background after responding). They are the smart staff who know the menu inside out.

**What lives here and why:**

| File | Why It Exists |
|------|--------------|
| `auth_routes.py` | Manages login, registration, and token refresh |
| `chat_routes.py` | The MOST IMPORTANT route — handles the full AI conversation pipeline |
| `assessment_routes.py` | Handles PHQ-9, GAD-7 and 6 other clinical questionnaires |
| `crisis_routes.py` | Scans messages for crisis keywords. Can trigger emergency protocols |
| `rag_routes.py` | Queries the AI knowledge base (Pinecone) for relevant context |
| `widget_routes.py` | Serves the widget's configuration and JavaScript bundle |
| `payment_routes.py` | Handles the full Razorpay payment cycle |
| `websocket_routes.py` | Real-time connections — how the clinician gets instant crisis alerts |

**How it works in the app:**
Patient sends a message → `chat_routes.py` receives it → calls `TherapeuticAIService` → gets response → sends back

---

## FOLDER: `therapeutic-copilot/server/services/`
### Working Principle: The Kitchen — Where Everything Actually Happens

**Why does this folder exist?**
This is the heart of the entire application. All real logic lives here. Routes just receive and respond. Services do the actual work. If you want to understand how Saathi AI works, read the services.

**The key rule:** Routes talk to the browser. Services talk to the AI, database, payment systems, and other services.

**What each service does in the app:**

| Service File | What It Does — Plain English |
|-------------|------------------------------|
| `therapeutic_ai_service.py` | **THE MAIN ORCHESTRATOR.** When a patient sends a message, this is the conductor that calls all other services in the right order: first crisis scan, then RAG, then AI generation |
| `chatbot_service.py` | Knows the 11-step therapy structure. Builds the AI's instructions based on which stage/step we are at |
| `crisis_detection_service.py` | Reads every patient message and checks for danger words. If severity is 7/10 or above, it triggers the emergency protocol |
| `assessment_service.py` | Scores clinical assessments. You give it a list of answers (0-3 for each PHQ-9 question) and it returns the total score and severity label |
| `qwen_inference.py` | Talks to the AI model. In development, calls Together AI's cloud. In production, calls the self-hosted Qwen model |
| `rag_service.py` | Searches the knowledge base. If a patient asks about a clinic's specific policy, it finds the relevant text and gives it to the AI |
| `lora_model_service.py` | Switches the AI adapter based on stage. Stage 1 uses a lighter adapter trained on booking conversations. Stage 2 uses a heavier one trained on therapy |
| `payment_service.py` | Creates Razorpay orders and verifies payment signatures |
| `lead_service.py` | Captures new leads and converts them to active patients |
| `dropout_service.py` | Finds patients who have been inactive and generates personalised re-engagement messages |
| `websocket_manager.py` | Manages real-time connections. When crisis is detected, this instantly pushes an alert to the clinician's browser |
| `embedding_service.py` | Converts text into numbers (vectors) so it can be stored in Pinecone and searched semantically |

---

## FOLDER: `therapeutic-copilot/server/middleware/`
### Working Principle: The Security Guard at the Door

**Why does this folder exist?**
Before any request reaches the routes, it passes through middleware. Think of it as the bouncer at a club — checks your ID before letting you in.

**What lives here:**
- `auth_middleware.py` — Checks if the JWT token in the request is valid. If not, blocks the request
- `rate_limit_middleware.py` — Limits how many requests one user can make per minute (prevents abuse)

**How it works in the app:**
Every request to a protected route (like `/api/v1/chat/message`) passes through `auth_middleware.py` first. If no valid token → 401 Unauthorized response is returned immediately.

---

## FOLDER: `therapeutic-copilot/server/auth/`
### Working Principle: The ID Card System

**Why does this folder exist?**
This handles login security. When a clinician logs in, they get a JWT (JSON Web Token) — think of it as a digital ID card. Every future request includes this ID card. The auth system creates, signs, and verifies these cards.

**What lives here:**
- `jwt_handler.py` — Creates tokens, decodes tokens, hashes passwords, verifies passwords

---

## FOLDER: `therapeutic-copilot/server/models/`
### Working Principle: The Order Form Templates

**Why does this folder exist?**
When data comes INTO the API from the frontend, it needs to match a specific shape. These Pydantic schemas define what shape each request/response must have. If the data doesn't match, FastAPI automatically rejects it with a clear error.

**What lives here:**
- `schemas.py` — All request and response data shapes (LoginRequest, ChatResponse, etc.)

**Note:** This is different from the `models.py` at the root of server/ which defines DATABASE tables. This folder defines API INPUT/OUTPUT shapes.

---

## FOLDER: `therapeutic-copilot/server/alembic/`
### Working Principle: The Database Version Control

**Why does this folder exist?**
When you add a new column to a database table or create a new table, you need to update the actual database without losing existing data. Alembic handles this with "migration scripts" — like git commits but for database structure.

**How it works:**
1. You change a model in `models.py` (e.g., add a column)
2. Run `alembic revision --autogenerate` — Alembic detects the change and creates a migration script
3. Run `alembic upgrade head` — the change is applied to the real database

---

## FOLDER: `therapeutic-copilot/client/`
### Working Principle: The Face of the App (What Clinicians See)

**Why does this folder exist?**
This is the React frontend. It is a Single Page Application (SPA) — meaning it loads once and then dynamically updates without full page reloads. Clinicians use this to:
- See patient lists and their stages
- Get real-time crisis alerts
- View session summaries
- Manage appointments

**Technology:** React 18 + TypeScript + Vite + Tailwind CSS

---

## FOLDER: `therapeutic-copilot/client/src/components/`
### Working Principle: The LEGO Bricks

**Why does this folder exist?**
Each sub-folder is a set of LEGO bricks for a specific part of the UI. They are kept separate so:
- Each section can be developed independently
- Finding a specific UI piece is easy (look in the folder that matches the name)
- Changes in one section don't accidentally break another

**Sub-folders:**

| Folder | What it builds | Who uses it |
|--------|----------------|-------------|
| `chatbot/` | The chat window that shows AI conversation | Clinician monitoring a session, or the widget |
| `clinician/` | The full dashboard with patient list, crisis alerts, tabs | Clinicians (therapists) |
| `patient/` | The patient-facing portal (assessments, history, appointments) | Patients |
| `analytics/` | Charts showing session counts, assessment trends, crisis events | Clinicians, admin |
| `admin/` | Tenant management, billing, system health | Super admin only |
| `landing/` | The public website where clinics sign up for the service | Anyone visiting the website |
| `payment/` | The Razorpay checkout screen for booking payment | Patients booking sessions |
| `ui/` | Tiny reusable pieces: Button, Badge, Card, Spinner | Used everywhere in the app |

---

## FOLDER: `therapeutic-copilot/client/src/contexts/`
### Working Principle: The Shared Memory

**Why does this folder exist?**
In React, data normally flows from parent to child. But some data (like "who is logged in?") needs to be available everywhere in the app without passing it through 10 layers of components. React Context solves this — it is like a shared brain that any component can read from.

**What lives here:**
- `AuthContext.tsx` — Stores: is the clinician logged in? What is their name/email/tenantId?

---

## FOLDER: `therapeutic-copilot/client/src/hooks/`
### Working Principle: The Reusable Logic Packages

**Why does this folder exist?**
Sometimes you have logic (not UI) that you want to reuse across multiple components. Custom React hooks package that logic. The rule: if it has `useState` or `useEffect` and you need it in more than one place, make it a hook.

**What lives here:**
- `useChat.ts` — Manages the WebSocket connection for a chat session. Any component that needs live chat uses this hook.

---

## FOLDER: `therapeutic-copilot/client/src/lib/`
### Working Principle: The Telephone Directory

**Why does this folder exist?**
Every time the frontend needs to talk to the backend, it makes an HTTP request. Instead of writing the request code inside every component (messy), all API calls are defined once here. Components just call `sendMessage()` and don't worry about how HTTP works.

**What lives here:**
- `api.ts` — All API functions. Login, send message, create appointment, verify payment — all defined here with the correct URL and method.

---

## FOLDER: `therapeutic-copilot/client/src/types/`
### Working Principle: The Dictionary

**Why does this folder exist?**
TypeScript needs to know what shape every piece of data has. Instead of defining `Patient` or `ChatMessage` in multiple places, they are defined once here and imported wherever needed.

**What lives here:**
- `index.ts` — All TypeScript interfaces: `Patient`, `TherapySession`, `ChatMessage`, `Assessment`, `Appointment`, `CrisisAlert`, `Tenant`

---

## FOLDER: `therapeutic-copilot/widget/`
### Working Principle: The Standalone Product You Sell to Clinics

**Why does this folder exist?**
This builds a completely separate JavaScript bundle — a tiny self-contained app that clinics can embed on their website with ONE line of code:
```html
<script src="https://api.saathi-ai.com/api/v1/widget/bundle.js" data-token="CLINIC_TOKEN"></script>
```

Once embedded, a floating chat button appears on the clinic's website. Visitors click it and start talking to Saathi AI.

**Why is it separate from `client/`?**
The clinician dashboard (`client/`) is a full React app with many pages. The widget must be:
- Tiny (~50KB, not 5MB)
- Self-contained (no external dependencies)
- Isolated (the clinic's CSS must not affect the widget's look)

**Technology:** Shadow DOM — a browser feature that creates a private, isolated DOM tree inside the widget so clinic styles cannot leak in.

---

## FOLDER: `therapeutic-copilot/ml_pipeline/`
### Working Principle: The AI Training Gym

**Why does this folder exist?**
The Qwen 2.5-7B model is a general AI. We need to teach it to be a therapist. We do this by fine-tuning it with 3,651 real therapeutic conversations using a technique called LoRA (Low-Rank Adaptation).

**What lives here:**
- `train_lora.py` — The training script. Run it with a dataset and it teaches the model
- `data/` — Where training conversation files go (not committed to git — too large)

**Two separate models are trained:**
1. Stage 1 model — trained on 634 booking/lead conversations (lighter, rank=8)
2. Stage 2 model — trained on 3,017 therapy conversations (heavier, rank=16)

---

## FOLDER: `therapeutic-copilot/tests/`
### Working Principle: The Quality Control Department

**Why does this folder exist?**
Before pushing code, automated tests verify that nothing is broken. Tests are especially critical for crisis detection — you cannot have the safety system fail.

**What gets tested:**
- `test_crisis_detection.py` — Does "I want to kill myself" correctly score 9/10? Does scanning run in <100ms?
- `test_chat.py` — Does starting a session return a greeting? Does a crisis message trigger escalation?
- `test_assessments.py` — Does PHQ-9 with all 3s correctly return "Severe" with score 27?

---

## FOLDER: `therapeutic-copilot/scripts/`
### Working Principle: The Utility Belt

**Why does this folder exist?**
One-time or occasional tasks that are too specific for the app itself to run. You run these from the terminal when setting up or administering the system.

**What lives here:**
- `setup_db.py` — Creates all database tables + optionally seeds demo data
- `generate_widget_token.py` — Generates a secure token for a new clinic and prints the embed code

---

---

# PART 2 — LINE-BY-LINE CODE BREAKDOWN

---

## FILE: `therapeutic-copilot/server/main.py`
**The front door of the entire backend**

```python
# Line 1-4: This is a docstring — documentation at the top of the file.
# It tells any developer what this file is for.
"""
SAATHI AI — FastAPI Application Entry Point
"""

# Line 5: Import FastAPI — the web framework.
# FastAPI is what receives HTTP requests (GET, POST, etc.) and sends responses.
from fastapi import FastAPI

# Line 6: Import CORS middleware.
# CORS = Cross-Origin Resource Sharing.
# The browser blocks requests from localhost:5173 (React app) to localhost:8000 (backend)
# UNLESS the backend explicitly says "yes, you are allowed."
# This middleware adds that permission.
from fastapi.middleware.cors import CORSMiddleware

# Line 7: Import GZip middleware.
# GZip compresses the HTTP response before sending.
# This makes the data transfer faster (smaller file = faster download).
from fastapi.middleware.gzip import GZipMiddleware

# Line 8: asynccontextmanager — a Python tool to run code at app startup AND shutdown.
from contextlib import asynccontextmanager

# Line 9: loguru is a logging library. Better than Python's built-in print().
# It automatically adds timestamps, colors, and log levels.
from loguru import logger

# Line 11: Import our own settings object from config.py
from config import settings

# Line 12: Import the database engine and the Base class.
# async_engine = the actual database connection
# Base = the parent class all our database table models inherit from
from database import async_engine, Base

# Lines 15-28: Import all "routers."
# A router is a collection of related routes (URL endpoints).
# Each router handles a specific domain: auth, chat, assessments, etc.
# We import them all here and register them with the main app below.
from routes.auth_routes import router as auth_router
from routes.chat_routes import router as chat_router
# ... (same pattern for all other routers)

# Lines 25-28: These come from the simpler api/ folder.
from api.tenants import router as tenants_router
# ... etc.


# Lines 31-41: The LIFESPAN function.
# This runs code BEFORE the app starts accepting requests (startup)
# and AFTER it stops (shutdown).
# Think of it as the open/close routine for a shop.
@asynccontextmanager          # This decorator makes it work with FastAPI's lifespan system
async def lifespan(app: FastAPI):
    # STARTUP CODE:
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    # This line creates all database tables if they don't already exist.
    # In production we use Alembic migrations instead, but for quick dev this works.
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialised.")

    yield   # ← This is the moment the app starts running and accepting requests

    # SHUTDOWN CODE (runs after yield when app is stopped):
    logger.info("Shutting down Saathi AI backend.")
    await async_engine.dispose()   # ← Closes all database connections cleanly


# Lines 45-52: CREATE THE APP.
# This is the FastAPI application object. It is the central object everything connects to.
app = FastAPI(
    title=settings.APP_NAME,          # Shown at /docs
    version=settings.APP_VERSION,     # Shown at /docs
    description="B2B SaaS...",        # Shown at /docs
    docs_url="/docs",                  # Where to find the interactive API docs
    redoc_url="/redoc",                # Alternative docs UI
    lifespan=lifespan,                 # Connect our startup/shutdown function
)

# Lines 55-61: ADD CORS MIDDLEWARE.
# This says: "Allow requests from the React dev server and any configured origins."
# allow_credentials=True means cookies and auth headers are allowed.
# allow_methods=["*"] means GET, POST, PUT, DELETE, etc. — all methods allowed.
# allow_headers=["*"] means any HTTP header is allowed (including Authorization).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,   # ["http://localhost:5173", etc.]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Line 62: ADD GZIP MIDDLEWARE.
# Only compress if response is larger than 1000 bytes. Smaller responses are not worth compressing.
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Lines 65-76: REGISTER ALL ROUTERS.
# Each line connects a router to the main app with a URL prefix and a tag.
# prefix="/api/v1/chat" means all routes in chat_router are accessible at /api/v1/chat/...
# tags=["Chat"] is just for organizing the /docs page into sections.
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])
# ... (same pattern for all others)

# Lines 79-81: ROOT ENDPOINT.
# A simple GET / that returns a confirmation message.
# Used to confirm the server is running. Not really used by the app itself.
@app.get("/", tags=["Health"])
async def root():
    return {"message": "Saathi AI is running", "version": settings.APP_VERSION}

# Lines 84-86: HEALTH CHECK ENDPOINT.
# Used by Docker and load balancers to verify the server is alive.
# Docker can restart the container if /health stops responding.
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}

# Lines 89-91: DIRECT RUN.
# If you run "python main.py" directly (not via uvicorn command), this starts the server.
# In production, you run "uvicorn main:app" from the command line instead.
# reload=settings.DEBUG_MODE means auto-restart when files change (only in development).
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG_MODE)
```

---

## FILE: `therapeutic-copilot/server/config.py`
**The master list of all settings**

```python
# Line 5: pydantic_settings automatically reads environment variables.
# When you set DATABASE_URL=postgresql://... in your .env file,
# pydantic_settings reads it and makes it available as settings.DATABASE_URL
from pydantic_settings import BaseSettings

# Line 9: Our Settings class inherits from BaseSettings.
# This gives it the superpower of reading from .env files and environment variables.
class Settings(BaseSettings):

    # Lines 11-16: APP SETTINGS
    # These have default values. If not set in .env, these defaults are used.
    APP_NAME: str = "Saathi AI — Therapeutic Co-Pilot"
    APP_VERSION: str = "1.0.0"
    DEBUG_MODE: bool = False          # True in dev, False in production
    LOG_LEVEL: str = "INFO"           # How much logging output to show
    PORT: int = 8000                  # Which port the server listens on
    # CORS_ORIGINS is a comma-separated string because .env files don't support lists
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Line 19: DATABASE URL
    # SQLite is a file-based database — no server needed. Perfect for local development.
    # In production, this is replaced with a PostgreSQL URL.
    DATABASE_URL: str = "sqlite:///./saathi_copilot.db"

    # Line 22: REDIS URL
    # Redis is used for caching session data and rate limiting.
    REDIS_URL: str = "redis://localhost:6379"

    # Lines 25-27: JWT AUTH SETTINGS
    # JWT_SECRET_KEY: The password used to sign tokens. If someone knows this, they can
    # forge tokens. Change this in production!
    # JWT_ALGORITHM: HS256 is the standard symmetric signing algorithm.
    # ACCESS_TOKEN_EXPIRE_MINUTES: Tokens expire after 30 min for security.
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Line 30: ENCRYPTION KEY
    # Used to encrypt sensitive data in the database (like Google Calendar OAuth tokens).
    # Generated with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = ""

    # Lines 33-35: AI INFERENCE SETTINGS
    # TOGETHER_API_KEY: For development. Together AI runs Qwen on their servers.
    # TOGETHER_MODEL: The specific model to call.
    # LLAMA_CPP_SERVER_URL: For production. Points to our self-hosted model server.
    TOGETHER_API_KEY: str = ""
    TOGETHER_MODEL: str = "Qwen/Qwen2.5-7B-Instruct-Turbo"
    LLAMA_CPP_SERVER_URL: str = "http://localhost:8080"

    # Lines 38-40: PINECONE SETTINGS (for RAG knowledge base)
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "us-east-1-aws"   # Which cloud region Pinecone runs in
    PINECONE_INDEX: str = "therapeutic-kb"         # Name of our Pinecone index

    # Lines 43-44: RAZORPAY PAYMENT KEYS
    RAZORPAY_KEY_ID: str = ""        # Public key (shown in browser)
    RAZORPAY_KEY_SECRET: str = ""    # Secret key (NEVER show in browser)

    # Lines 47-48: EMAIL SETTINGS (SendGrid)
    SENDGRID_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@saathi-ai.com"

    # Lines 51-52: GOOGLE CALENDAR OAUTH
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Lines 54-56: A Python "property" — computed from other values.
    # Converts "http://localhost:3000,http://localhost:5173"
    # into ["http://localhost:3000", "http://localhost:5173"]
    # The strip() removes any accidental spaces around the commas.
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    # Lines 58-60: Tell pydantic_settings to read from a .env file.
    # case_sensitive=True means DATABASE_URL and database_url are treated differently.
    class Config:
        env_file = ".env"
        case_sensitive = True

# Line 63: Create ONE instance of Settings that the whole app imports and uses.
# This is the "singleton" pattern — there is only ever one settings object.
settings = Settings()
```

---

## FILE: `therapeutic-copilot/server/database.py`
**Setting up the database connection pipes**

```python
# Line 5: create_engine — creates a synchronous (blocking) database connection.
# Used only for Alembic migrations (which can't be async).
from sqlalchemy import create_engine

# Line 6: declarative_base — creates the Base class that all ORM models inherit from.
# "ORM" = Object-Relational Mapper. It lets you work with Python classes instead of raw SQL.
from sqlalchemy.ext.declarative import declarative_base

# Line 7: sessionmaker — creates a factory that produces database sessions.
from sqlalchemy.orm import sessionmaker

# Line 8: Async versions. FastAPI is async (non-blocking), so we need async DB sessions.
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from config import settings  # Our settings object

# Lines 13-17: SYNC ENGINE (for Alembic migrations only)
# connect_args={"check_same_thread": False} — SQLite needs this to work with FastAPI.
#   SQLite by default only allows the thread that created it to use it.
#   This turns off that restriction so FastAPI's async threads can use it.
# echo=settings.DEBUG_MODE — When True, prints all SQL queries to the console.
#   Very helpful for debugging, but too noisy for production.
sync_engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.DEBUG_MODE,
)

# Lines 20-22: CONVERT DATABASE URL FOR ASYNC USE
# Async database drivers have different names than sync drivers.
# postgresql://  →  postgresql+asyncpg://   (asyncpg is the async PostgreSQL driver)
# sqlite:///     →  sqlite+aiosqlite:///    (aiosqlite is the async SQLite driver)
async_db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://").replace(
    "sqlite:///", "sqlite+aiosqlite:///"
)

# Line 23: ASYNC ENGINE — Used by all FastAPI routes.
async_engine = create_async_engine(async_db_url, echo=settings.DEBUG_MODE)

# Lines 25-29: SESSION FACTORY
# AsyncSessionLocal() creates a database session when called.
# bind=async_engine — connect this session factory to our async engine.
# class_=AsyncSession — produce async sessions (not regular sync sessions).
# expire_on_commit=False — keep objects accessible after committing (important for async).
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Line 31: BASE CLASS for all ORM models.
# Every model (Tenant, Patient, etc.) inherits from this.
# SQLAlchemy uses this to track all models and create their tables.
Base = declarative_base()


# Lines 34-42: DATABASE DEPENDENCY FUNCTION
# This is used in route functions as a dependency injection.
# Example in a route: async def my_route(db: AsyncSession = Depends(get_db))
# FastAPI calls get_db() automatically and passes the session to the route.
async def get_db():
    # Open a new session
    async with AsyncSessionLocal() as session:
        try:
            yield session          # Give the session to the route function
            await session.commit() # After the route finishes, commit all changes
        except Exception:
            await session.rollback()  # If something went wrong, undo all changes
            raise                     # Re-raise the error so FastAPI can handle it
```

---

## FILE: `therapeutic-copilot/server/models.py`
**The blueprint for every database table**

```python
# Line 5: uuid — generates random unique IDs (like "550e8400-e29b-41d4-a716-446655440000")
import uuid

# Line 6: datetime — for timestamps (created_at, last_active, etc.)
from datetime import datetime

# Lines 7-10: SQLAlchemy column types.
# Column = creates a database column
# String, Integer, Float, Boolean, DateTime, Text, JSON = different data types
# ForeignKey = links one table to another (like patient.clinician_id → clinicians.id)
# SAEnum = creates an ENUM column (fixed list of allowed values)
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Text, JSON, Enum as SAEnum
)

# Line 11: relationship — lets you navigate between related records in Python.
# e.g., patient.sessions gives you all TherapySession records for that patient
from sqlalchemy.orm import relationship

# Line 14: Python's built-in enum module — for defining the allowed values in enums.
import enum


# Lines 17-18: Helper function that generates a new unique ID.
# Every time a new record is created (Tenant, Patient, etc.), this runs automatically
# and generates a fresh UUID for the id column.
def gen_uuid():
    return str(uuid.uuid4())   # Returns something like "a1b2c3d4-..."


# Lines 23-27: PATIENT STAGE ENUM
# A patient can only be in one of these 4 stages. The database will reject any other value.
# LEAD = just discovered the clinic through the website widget
# ACTIVE = booked a session, actively receiving therapy co-pilot support
# DROPOUT = was active but has been inactive for 7-30+ days
# ARCHIVED = finished treatment, no longer active
class PatientStage(str, enum.Enum):
    LEAD = "lead"
    ACTIVE = "active"
    DROPOUT = "dropout"
    ARCHIVED = "archived"


# Lines 30-34: SESSION STATUS ENUM
class SessionStatus(str, enum.Enum):
    PENDING = "pending"                       # Session started but AI hasn't responded yet
    IN_PROGRESS = "in_progress"               # Conversation is happening
    COMPLETED = "completed"                   # Session finished normally
    CRISIS_ESCALATED = "crisis_escalated"     # Session was escalated due to crisis


# Lines 47-61: TENANT TABLE (represents a B2B clinic customer)
class Tenant(Base):
    __tablename__ = "tenants"    # The actual SQL table name in the database

    id = Column(String, primary_key=True, default=gen_uuid)
    # primary_key=True means this column uniquely identifies each row
    # default=gen_uuid means if no ID is provided, generate one automatically

    name = Column(String(255), nullable=False)
    # String(255) means max 255 characters
    # nullable=False means this column MUST have a value — cannot be empty

    domain = Column(String(255), unique=True, nullable=False)
    # unique=True means no two tenants can have the same domain

    widget_token = Column(String(255), unique=True, nullable=False)
    # This is the secret token in the clinic's embed script
    # When the widget loads, it sends this token to identify which clinic it is

    plan = Column(String(50), default="basic")
    # default="basic" means new tenants start on the basic plan
    # Possible values: "basic", "professional", "enterprise"

    is_active = Column(Boolean, default=True)
    # Allows disabling a tenant without deleting them

    pinecone_namespace = Column(String(255))
    # Each clinic gets their own isolated section of the Pinecone knowledge base
    # This is the namespace name (usually the tenant ID)

    razorpay_account_id = Column(String(255))
    # For marketplace payments — the clinic's Razorpay account to split payments to

    created_at = Column(DateTime, default=datetime.utcnow)
    # datetime.utcnow is called at INSERT time to record when the tenant was created

    # RELATIONSHIPS — these are Python-level, not actual database columns
    # They let you do things like: tenant.clinicians (gets all clinicians for this tenant)
    clinicians = relationship("Clinician", back_populates="tenant")
    patients = relationship("Patient", back_populates="tenant")


# Lines 66-80: CLINICIAN TABLE (therapist accounts)
class Clinician(Base):
    __tablename__ = "clinicians"

    id = Column(String, primary_key=True, default=gen_uuid)

    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    # ForeignKey("tenants.id") means this column references the id column in the tenants table
    # This links each clinician to their clinic
    # nullable=False means every clinician must belong to a clinic

    email = Column(String(255), unique=True, nullable=False)
    # Email must be unique — two clinicians can't have the same email

    hashed_password = Column(String(255), nullable=False)
    # NEVER store plain passwords. This stores the bcrypt hash.
    # bcrypt makes it impossible to reverse-engineer the original password

    full_name = Column(String(255), nullable=False)
    specialization = Column(String(255))    # e.g., "CBT", "Trauma", "Child Psychology" — optional

    google_calendar_token = Column(Text)
    # Stores the OAuth token to access the clinician's Google Calendar
    # Text (not String) because OAuth tokens can be very long
    # This is encrypted before storage using ENCRYPTION_KEY from settings

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="clinicians")
    patients = relationship("Patient", back_populates="clinician")


# Lines 85-105: PATIENT TABLE
class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)   # Which clinic this patient belongs to
    clinician_id = Column(String, ForeignKey("clinicians.id"), nullable=True)
    # nullable=True because a patient may not be assigned to a clinician yet (still a lead)

    full_name = Column(String(255))   # Optional — patient may not share name immediately
    phone = Column(String(20))        # For WhatsApp/SMS re-engagement
    email = Column(String(255))       # For email re-engagement

    stage = Column(SAEnum(PatientStage), default=PatientStage.LEAD)
    # Uses our PatientStage enum. New patients start as LEAD.

    language = Column(String(10), default="en")
    # e.g., "en", "hi", "ta" — determines which language AI responds in

    cultural_context = Column(String(50))
    # e.g., "South Indian", "North Indian", "Urban" — used to tailor AI responses

    last_active = Column(DateTime, default=datetime.utcnow)
    # Updated every time patient sends a message.
    # The dropout service checks this to find inactive patients.

    dropout_risk_score = Column(Float, default=0.0)
    # 0.0 to 1.0 — calculated by dropout_service based on inactivity + assessment scores
    # High score (0.7+) means the patient is likely to drop out

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships — lets you do: patient.sessions, patient.assessments, patient.appointments
    tenant = relationship("Tenant", back_populates="patients")
    clinician = relationship("Clinician", back_populates="patients")
    sessions = relationship("TherapySession", back_populates="patient")
    assessments = relationship("Assessment", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")


# Lines 110-125: THERAPY SESSION TABLE
class TherapySession(Base):
    __tablename__ = "therapy_sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)

    stage = Column(Integer, default=1)
    # Which of the 3 stages is this session in? 1=Lead, 2=Therapy, 3=Re-engagement

    current_step = Column(Integer, default=0)
    # Only meaningful in Stage 2. Which of the 11 therapeutic steps are we on?
    # 0=Rapport Building, 1=Challenge Context, ... , 10=Session Summary

    status = Column(SAEnum(SessionStatus), default=SessionStatus.PENDING)
    crisis_score = Column(Float, default=0.0)   # Highest crisis score seen in this session

    session_summary = Column(Text)   # AI-generated summary shown to clinician after session
    ai_insights = Column(JSON)       # Structured AI insights: themes, emotions, recommendations

    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)      # Null until session ends

    patient = relationship("Patient", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session")


# Lines 130-140: CHAT MESSAGE TABLE
# Every single message (patient + AI) is stored here.
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, ForeignKey("therapy_sessions.id"), nullable=False)

    role = Column(String(20), nullable=False)
    # "user" = patient's message
    # "assistant" = Saathi AI's response

    content = Column(Text, nullable=False)   # The actual message text

    crisis_keywords_detected = Column(JSON)
    # If crisis keywords were found in this message, they are stored here as a list
    # e.g., [{"keyword": "want to die", "weight": 9.5}]
    # This is used for audit trails and clinician review

    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("TherapySession", back_populates="messages")
```

---

## FILE: `therapeutic-copilot/server/services/therapeutic_ai_service.py`
**The main conductor — orchestrates everything when a message comes in**

```python
# Lines 5-11: Import all the sub-services this orchestrator uses.
# Think of TherapeuticAIService as a manager, and these are the specialists it calls.
from services.chatbot_service import ChatbotService           # Knows the 11-step therapy structure
from services.crisis_detection_service import CrisisDetectionService  # Detects danger
from services.rag_service import RAGService                   # Searches knowledge base
from services.qwen_inference import QwenInferenceService      # Talks to the AI model
from services.lora_model_service import LoRAModelService      # Switches AI adapters
from loguru import logger                                      # For logging


class TherapeuticAIService:
    # Line 23-29: The __init__ (constructor) — runs when you create a new instance.
    # It creates one instance of each specialist service and stores them as self.X
    # so they can be used in other methods.
    def __init__(self, db: AsyncSession):
        self.db = db                              # Database session, passed in from the route
        self.chatbot = ChatbotService()           # For prompt building and step management
        self.crisis_detector = CrisisDetectionService()   # For safety scanning
        self.rag = RAGService()                   # For knowledge base lookup
        self.llm = QwenInferenceService()         # For AI text generation
        self.lora = LoRAModelService()            # For adapter selection

    # Lines 31-49: START SESSION
    # Called when the widget first opens or when the chat starts.
    # Returns the first AI message (the greeting).
    async def start_session(self, patient_id: str, tenant_id: str, widget_token: str) -> dict:
        # Determine which stage this patient is in (1, 2, or 3) based on database records
        stage = await self._detect_patient_stage(patient_id)

        logger.info(f"Starting session for patient {patient_id} at stage {stage}")

        # Ask the LLM to generate a greeting appropriate to the stage
        greeting = await self.llm.generate(
            prompt=self.chatbot.build_greeting_prompt(stage=stage),   # Get the right prompt
            stage=stage,
        )
        # Return the session info and greeting back to the route (which sends it to the browser)
        return {
            "session_id": "generated_uuid",   # TODO: Generate real UUID and save to DB
            "stage": stage,
            "greeting": greeting,
        }

    # Lines 51-84: PROCESS MESSAGE — THE HEART OF THE APP
    # This runs every time a patient sends a message. The pipeline has 4 steps.
    async def process_message(self, session_id: str, message: str, stage: int) -> dict:

        # STEP 1: CRISIS SCAN — This ALWAYS runs first, before anything else.
        # Why first? Because crisis detection is the most important safety check.
        # If crisis is detected, we skip everything else and respond with emergency info.
        crisis_result = self.crisis_detector.scan(message)

        # If severity is 7 or above (out of 10), handle as crisis immediately
        if crisis_result["severity"] >= 7:
            logger.warning(f"Crisis detected in session {session_id}: score={crisis_result['severity']}")
            return await self._handle_crisis(session_id, crisis_result)

        # STEP 2: RAG RETRIEVAL — Search the clinic's knowledge base.
        # This fetches relevant text snippets (like FAQ answers, clinic policies)
        # that the AI can use to give accurate, clinic-specific answers.
        # top_k=3 means: return the 3 most relevant passages.
        rag_context = await self.rag.query(query=message, tenant_id="placeholder", top_k=3)

        # STEP 3: BUILD THE FULL PROMPT
        # Combine: the system instructions + RAG context + the patient's message
        # This is the full text sent to the AI model.
        prompt = self.chatbot.build_response_prompt(
            message=message,
            stage=stage,
            rag_context=rag_context,
        )

        # STEP 4: LLM INFERENCE — Send the prompt to Qwen 2.5-7B and get a response.
        response = await self.llm.generate(prompt=prompt, stage=stage)

        # Return the response along with the crisis score (even if not critical)
        return {
            "response": response,
            "crisis_score": crisis_result["severity"],   # Frontend can show this to clinician
            "stage": stage,
        }

    # Lines 86-89: DETECT STAGE (PLACEHOLDER — needs to be implemented)
    # In the real implementation, this queries the Patient table in the database
    # and returns 1 (lead), 2 (active), or 3 (dropout) based on patient.stage
    async def _detect_patient_stage(self, patient_id: str) -> int:
        # TODO: Query Patient table and map stage enum to int
        return 1    # Currently always returns Stage 1 (lead)

    # Lines 91-102: CRISIS RESPONSE
    # When crisis is detected, skip the AI and return a pre-written safe response
    # with emergency helpline numbers. This is hard-coded for safety.
    async def _handle_crisis(self, session_id: str, crisis_result: dict) -> dict:
        return {
            "response": "I hear that you're going through something very difficult...",
            "crisis_detected": True,       # Frontend shows a crisis alert banner
            "severity": crisis_result["severity"],
            "escalated": True,             # Triggers clinician notification
        }
```

---

## FILE: `therapeutic-copilot/server/services/crisis_detection_service.py`
**The safety scanner — reads every message for danger**

```python
# Lines 12-46: THE CRISIS KEYWORDS DICTIONARY
# This is a Python dictionary: keyword → severity weight (1 to 10)
# The higher the weight, the more dangerous the keyword.
CRISIS_KEYWORDS: Dict[str, float] = {
    # "kill myself" is the most severe — weight 10.0 (maximum)
    "kill myself": 10.0,
    "end my life": 10.0,
    "want to die": 9.5,
    "suicide": 9.0,
    # ...
    "hopeless": 6.0,          # Weight 6 — significant but not immediately dangerous
    "overwhelmed": 4.0,       # Weight 4 — worth noting but not escalating
    # Hinglish (Hindi + English mix) — important for Indian users
    "mar jaana chahta": 9.0,  # "I want to die" in Hindi romanized
    "jeena nahi chahta": 9.0, # "I don't want to live" in Hindi
}

class CrisisDetectionService:

    # Lines 52-76: THE SCAN FUNCTION
    def scan(self, message: str) -> Dict:

        # Convert to lowercase so "WANT TO DIE" matches "want to die"
        message_lower = message.lower()

        # Start with empty detected list and zero scores
        detected = []
        max_score = 0.0        # Track the single highest-weight keyword found
        cumulative_score = 0.0  # Track the sum of all keyword weights found

        # Go through every keyword in the dictionary
        for keyword, weight in CRISIS_KEYWORDS.items():
            # Check if this keyword appears anywhere in the message
            if keyword in message_lower:
                # Record that we found it, with its weight
                detected.append({"keyword": keyword, "weight": weight})
                # Update the max score if this keyword is heavier than the previous max
                max_score = max(max_score, weight)
                # Add a partial contribution to the cumulative score
                # 0.3 means: add 30% of the weight (prevents single keyword from dominating)
                cumulative_score += weight * 0.3

        # FINAL SEVERITY CALCULATION:
        # severity = max_score + a small bonus for multiple keywords
        # min(2.0, ...) caps the cumulative bonus at 2.0 (can't exceed 10)
        # min(10.0, ...) caps the total severity at 10.0
        severity = min(10.0, max_score + min(2.0, cumulative_score * 0.1))

        return {
            "severity": round(severity, 2),     # Round to 2 decimal places (e.g., 9.25)
            "escalate": severity >= 7.0,         # True/False: should we trigger emergency protocol?
            "detected_keywords": detected,        # List of found keywords with weights
            "message_scanned": True,              # Confirmation that scan ran
        }
```

---

## FILE: `therapeutic-copilot/server/services/chatbot_service.py`
**Knows the 11-step therapy structure and builds AI prompts**

```python
# Lines 8-20: THE 11 STEPS OF STAGE 2 THERAPY
# These are stored in order. The session starts at index 0 (rapport_building)
# and progresses through to index 10 (session_summary).
STAGE2_STEPS = [
    "rapport_building",           # Step 1: Build trust and comfort
    "challenge_context",          # Step 2: Understand what the patient is dealing with
    "empathetic_connection",      # Step 3: Show understanding and validation
    "challenge_prioritization",   # Step 4: What is the most pressing issue?
    "exploration_consent",        # Step 5: Ask permission to go deeper
    "vak_narrative_collection",   # Step 6: Collect the patient's experience (Visual/Auditory/Kinesthetic)
    "meta_model_clarification",   # Step 7: Clarify distortions, deletions, generalizations
    "third_person_perspective",   # Step 8: Look at the issue from outside perspective
    "pattern_mapping",            # Step 9: Identify recurring patterns
    "feedback_collection",        # Step 10: How did this session feel?
    "session_summary",            # Step 11: AI generates a summary
]


class ChatbotService:

    # Lines 26-48: BUILD GREETING PROMPT
    # Returns a different set of instructions to the AI based on which stage.
    # This is the "system prompt" — the instructions before the patient's message.
    def build_greeting_prompt(self, stage: int) -> str:
        if stage == 1:      # LEAD — new visitor, convince them to book
            return "You are Saathi, a warm and empathetic AI... help them book an appointment..."
        elif stage == 2:    # ACTIVE THERAPY — structured 11-step session
            return "You are Saathi, conducting a structured therapeutic co-pilot session..."
        else:               # DROPOUT RE-ENGAGEMENT — bring them back gently
            return "You are Saathi, reaching out to a patient who has been inactive..."

    # Lines 50-71: BUILD RESPONSE PROMPT — assembles the complete text sent to the AI
    def build_response_prompt(self, message: str, stage: int, rag_context=None, current_step=0) -> str:

        # Start with the system instructions for this stage
        system = self.build_greeting_prompt(stage)

        # RAG CONTEXT SECTION: If we found relevant knowledge base content, add it
        rag_section = ""
        if rag_context:
            rag_section = "\n\nRelevant knowledge base context:\n" + "\n".join(
                [f"- {item}" for item in rag_context]   # Format each item as a bullet point
            )

        # STEP INSTRUCTION: In Stage 2, tell the AI which step we're on
        step_instruction = ""
        if stage == 2 and current_step < len(STAGE2_STEPS):
            # Convert "rapport_building" to "Rapport Building"
            step_name = STAGE2_STEPS[current_step].replace("_", " ").title()
            step_instruction = f"\n\nCurrent therapeutic step: {step_name} (Step {current_step + 1} of 11)"

        # ASSEMBLE THE FINAL PROMPT:
        # [System instructions] + [RAG context] + [Step instruction] + [Patient message] + [Saathi:]
        # The "Saathi:" at the end is a completion cue — the AI completes the text after it
        return f"{system}{rag_section}{step_instruction}\n\nPatient: {message}\nSaathi:"

    # Line 73-75: Advance to next step (but never beyond step 10, which is index 10)
    def get_next_step(self, current_step: int) -> int:
        return min(current_step + 1, len(STAGE2_STEPS) - 1)

    # Line 77-79: Check if all 11 steps are done
    def is_session_complete(self, current_step: int) -> bool:
        return current_step >= len(STAGE2_STEPS) - 1
```

---

## FILE: `therapeutic-copilot/server/services/qwen_inference.py`
**Talks to the AI model — either cloud or self-hosted**

```python
class QwenInferenceService:

    def __init__(self):
        # If TOGETHER_API_KEY is set in .env, use Together AI (cloud).
        # bool("") is False. bool("some_key") is True.
        # This auto-detects which mode to use.
        self.use_together = bool(settings.TOGETHER_API_KEY)
        self.model = settings.TOGETHER_MODEL    # The model name to call

    async def generate(self, prompt: str, stage: int = 1, max_tokens: int = 512) -> str:
        # Route to the appropriate backend based on config
        if self.use_together:
            return await self._together_generate(prompt, max_tokens)
        else:
            return await self._llama_cpp_generate(prompt, max_tokens)

    async def _together_generate(self, prompt: str, max_tokens: int) -> str:
        # httpx is like requests but async (non-blocking)
        import httpx

        # Set the Authorization header with the API key
        headers = {
            "Authorization": f"Bearer {settings.TOGETHER_API_KEY}",
            "Content-Type": "application/json",
        }
        # Build the request body in the OpenAI-compatible format
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,    # Maximum tokens to generate (1 token ≈ 0.75 words)
            "temperature": 0.7,          # 0=deterministic, 1=very random. 0.7 = slightly creative
            "top_p": 0.9,                # Only consider top 90% probability tokens (filters garbage)
        }
        # Make the API call. timeout=30.0 means give up after 30 seconds.
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.together.xyz/v1/chat/completions",
                                     headers=headers, json=payload)
            resp.raise_for_status()   # Raises an exception if status is 4xx or 5xx
            data = resp.json()
            # Navigate the response JSON to get the actual text:
            # data["choices"][0] = first (and only) choice
            # ["message"]["content"] = the generated text
            return data["choices"][0]["message"]["content"]

    async def _llama_cpp_generate(self, prompt: str, max_tokens: int) -> str:
        import httpx
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,     # llama.cpp uses n_predict instead of max_tokens
            "temperature": 0.7,
            "top_p": 0.9,
            "stop": ["Patient:", "\n\n"],  # Stop generating when it writes "Patient:" — prevents loop
        }
        async with httpx.AsyncClient(timeout=60.0) as client:  # 60s timeout — self-hosted is slower
            resp = await client.post(f"{settings.LLAMA_CPP_SERVER_URL}/completion", json=payload)
            resp.raise_for_status()
            return resp.json().get("content", "")  # .get("content", "") = return "" if key missing
```

---

## FILE: `therapeutic-copilot/server/auth/jwt_handler.py`
**The ID card system — creates and verifies login tokens**

```python
# Line 4: jose is a library for working with JWT tokens.
from jose import JWTError, jwt

# Line 5: passlib handles password hashing with bcrypt.
from passlib.context import CryptContext

# Line 8: Create a CryptContext using bcrypt scheme.
# bcrypt is a deliberately slow hashing algorithm — making brute-force attacks expensive.
# deprecated="auto" means old hashing schemes are automatically upgraded.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Lines 11-12: HASH A PASSWORD
# Takes a plain text password ("mypassword123")
# Returns a bcrypt hash ("$2b$12$5RqoafdTOp...")
# The hash is what gets stored in the database — never the plain password.
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# Lines 15-16: VERIFY A PASSWORD
# Takes the plain password from the login form AND the stored hash from the database.
# Returns True if they match, False if not.
# bcrypt handles the comparison securely — no timing attacks.
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# Lines 19-23: CREATE AN ACCESS TOKEN
# Called after successful login. Returns a token the frontend stores and sends back.
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()   # Don't modify the original dict

    # Set the expiry time. If no custom expiry given, use the setting (30 min by default).
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    # Add the expiry time to the payload that gets encoded into the token
    to_encode.update({"exp": expire})

    # Encode the payload into a JWT token string, signed with our secret key.
    # The token looks like: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM...
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# Lines 26-30: DECODE/VERIFY A TOKEN
# Called when a protected request comes in. Verifies the token is real and not expired.
def decode_token(token: str) -> Optional[dict]:
    try:
        # Decode the token and verify the signature using the same secret key.
        # If the token was tampered with or expired, this raises JWTError.
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None   # Return None instead of raising — caller decides what to do
```

---

## FILE: `therapeutic-copilot/widget/src/widget.ts`
**The chat bubble that embeds on any clinic's website**

```typescript
// Lines 14-16: Import React and the ChatBubble component.
// React = the UI library
// ReactDOM = renders React components into real browser DOM elements
// ChatBubble = the actual floating chat UI
import React from 'react'
import ReactDOM from 'react-dom/client'
import { ChatBubble } from './components/ChatBubble'

// Line 18-19: Define a custom HTML element class.
// This extends HTMLElement — the base class for all HTML elements (<div>, <p>, etc.)
// We are creating a brand new HTML element called <saathi-widget>
class SaathiWidget extends HTMLElement {
  private shadowRoot!: ShadowRoot   // Will hold our isolated DOM tree

  // Lines 21-45: connectedCallback() runs automatically when <saathi-widget> is added to the page.
  // This is a Web Components lifecycle hook — like React's componentDidMount.
  connectedCallback() {

    // Line 23: CREATE THE SHADOW DOM.
    // mode: 'closed' means external JavaScript CANNOT access the shadow DOM.
    // This isolates our widget completely from the host page.
    // The clinic's JavaScript cannot accidentally break our widget.
    this.shadowRoot = this.attachShadow({ mode: 'closed' })

    // Lines 26-31: Inject base CSS styles into the Shadow DOM.
    // We create a <style> element and add CSS to it.
    // *, *::before, *::after — reset box-sizing for all elements inside the widget.
    //   This prevents the clinic's CSS from affecting how our elements are sized.
    // :host — styles the custom element itself (the outer container).
    //   position: fixed keeps it pinned to the bottom-right of the screen.
    //   z-index: 999999 makes it appear on top of everything on the clinic's page.
    const style = document.createElement('style')
    style.textContent = `
      *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
      :host { position: fixed; bottom: 24px; right: 24px; z-index: 999999; ... }
    `
    this.shadowRoot.appendChild(style)   // Add the styles to our isolated DOM

    // Lines 34-35: Create a <div> that React will render into.
    const container = document.createElement('div')
    this.shadowRoot.appendChild(container)   // Add the div to our isolated DOM

    // Lines 38-39: Read the widget token from the <script> tag's data-token attribute.
    // The clinic's embed code looks like:
    // <script src="bundle.js" data-token="saathi_xyz123"></script>
    // document.currentScript points to THAT script element.
    const script = document.currentScript as HTMLScriptElement
    const token = script?.dataset?.token || this.getAttribute('data-token') || ''

    // Lines 42-44: Mount React inside our Shadow DOM container.
    // React.createElement(ChatBubble, { widgetToken: token }) creates the React element.
    // ReactDOM.createRoot(container).render(...) renders it into the Shadow DOM.
    ReactDOM.createRoot(container).render(
      React.createElement(ChatBubble, { widgetToken: token })
    )
  }
}

// Lines 49-51: Register our custom element in the browser's element registry.
// After this, any <saathi-widget> tag in the HTML will use this class.
// We check first — if the script loads twice, we don't re-register.
if (!customElements.get('saathi-widget')) {
  customElements.define('saathi-widget', SaathiWidget)
}

// Lines 54-55: AUTO-INJECT — We don't wait for the clinic to add <saathi-widget> to their HTML.
// We create the element ourselves and add it to <body>.
// This means the embed code is truly ONE LINE — just the <script> tag.
const el = document.createElement('saathi-widget')
document.body.appendChild(el)
```

---

## FILE: `therapeutic-copilot/client/src/App.tsx`
**The router — decides which page to show based on the URL**

```typescript
// Line 5: React Router components.
// BrowserRouter = enables URL-based routing (like a multi-page app in a single page)
// Routes = container for all route definitions
// Route = maps a URL path to a component
// Navigate = redirects to another URL
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

// Line 6: Our auth context hook and provider
import { AuthProvider, useAuth } from '@/contexts/AuthContext'

// Line 7: The page-level components
import { LandingPage, ClinicianDashboard, PatientPortal, AdminPanel } from '@/pages'

// Lines 9-12: PROTECTED ROUTE COMPONENT
// A wrapper that checks if the user is logged in.
// If logged in → show the component (children)
// If NOT logged in → redirect to /login
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()   // Get login state from global auth context
  // Ternary: if authenticated, render children, else redirect to /login
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

// Lines 14-28: THE APP COMPONENT
function App() {
  return (
    // AuthProvider wraps everything — makes auth state available to all components
    <AuthProvider>
      {/* BrowserRouter enables URL-based navigation */}
      <BrowserRouter>
        <Routes>
          {/* "/" = the homepage — anyone can see this (public) */}
          <Route path="/" element={<LandingPage />} />

          {/* "/dashboard" = clinician's dashboard — protected, must be logged in */}
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <ClinicianDashboard />
            </ProtectedRoute>
          } />

          {/* "/patient" = patient's portal — protected */}
          <Route path="/patient" element={<ProtectedRoute><PatientPortal /></ProtectedRoute>} />

          {/* "/admin" = admin panel — protected */}
          <Route path="/admin" element={<ProtectedRoute><AdminPanel /></ProtectedRoute>} />

          {/* Any URL not matching above → redirect to homepage */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
```

---

## FILE: `therapeutic-copilot/client/src/lib/api.ts`
**The telephone — all calls to the backend go through here**

```typescript
// Line 5: Import axios — a popular HTTP client library.
// Axios is like fetch() but with more features: interceptors, timeouts, auto JSON parsing.
import axios from 'axios'

// Lines 7-11: CREATE THE AXIOS INSTANCE
// baseURL: '/api/v1' means every API call automatically prefixes with /api/v1.
//   So api.get('/chat/session/123') becomes a GET to /api/v1/chat/session/123
// headers: every request sends Content-Type: application/json by default
// timeout: if the backend doesn't respond in 30 seconds, the request fails
const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// Lines 14-20: REQUEST INTERCEPTOR
// Runs BEFORE every request is sent.
// Reads the JWT token from localStorage and adds it to the Authorization header.
// Why localStorage? It persists across browser refreshes — the user stays logged in.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('saathi_token')
  if (token) {
    // This is the standard Bearer token format expected by our JWT middleware
    config.headers.Authorization = `Bearer ${token}`
  }
  return config   // Must return config for the request to continue
})

// Lines 23-31: RESPONSE INTERCEPTOR
// Runs AFTER every response comes back.
// If response is 200-299: the first function (res) => res just passes it through.
// If response is an error:
//   - If it is a 401 (Unauthorized) — the token expired or is invalid
//   - Delete the token from localStorage and redirect to /login
//   - This handles session expiry automatically — no code needed in every component
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('saathi_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)   // Re-throw the error so the calling code can handle it
  }
)

// Lines 36-37: AUTH — LOGIN
// Arrow function that calls POST /api/v1/auth/login with email and password
export const login = (email: string, password: string) =>
  api.post('/auth/login', { email, password })

// Lines 44-48: CHAT API CALLS
export const startSession = (data: object) =>
  api.post('/chat/start', data)

export const sendMessage = (sessionId: string, message: string, stage: number) =>
  api.post('/chat/message', { session_id: sessionId, message, stage })

// Lines 55-58: ASSESSMENT API CALLS
export const getAssessmentQuestions = (type: string) =>
  api.get(`/assessments/${type}/questions`)   // Template literal — inserts type into URL

// Lines 71-72: PAYMENT API CALLS
export const createPaymentOrder = (data: object) =>
  api.post('/payments/create-order', data)
```

---

## FILE: `therapeutic-copilot/client/src/hooks/useChat.ts`
**The live phone line — WebSocket connection for real-time AI chat**

```typescript
// Lines 5-6: React hooks used in this file.
// useState = store state values (messages list, isTyping, isConnected)
// useEffect = run code when component mounts or when dependencies change
// useCallback = memoize a function so it doesn't re-create every render
// useRef = hold a value that persists across renders WITHOUT causing re-renders
import { useState, useEffect, useCallback, useRef } from 'react'

// Lines 13-53: THE HOOK
export function useChat({ sessionId, onCrisisDetected }: UseChatOptions) {

  const [messages, setMessages] = useState<ChatMessage[]>([])   // All chat messages
  const [isTyping, setIsTyping] = useState(false)               // Is AI generating?
  const [isConnected, setIsConnected] = useState(false)         // Is WebSocket connected?
  const wsRef = useRef<WebSocket | null>(null)   // Holds the WebSocket instance

  // Lines 19-39: CONNECT TO WEBSOCKET
  // useEffect runs after the component mounts.
  // [sessionId] in the dependency array means: re-run if sessionId changes.
  useEffect(() => {
    // Create WebSocket connection to the backend's WebSocket endpoint
    const ws = new WebSocket(`ws://localhost:8000/ws/chat/${sessionId}`)
    wsRef.current = ws   // Store in ref so sendMessage() can access it later

    ws.onopen = () => setIsConnected(true)    // Connected! Show green dot.
    ws.onclose = () => setIsConnected(false)  // Disconnected. Show red dot.

    // Handle incoming messages from the backend
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)   // Parse the JSON string into an object

      if (data.type === 'CRISIS_ALERT' && onCrisisDetected) {
        // If backend sent a crisis alert, call the callback the parent passed in
        onCrisisDetected(data.severity)
      } else if (data.type === 'AI_RESPONSE') {
        setIsTyping(false)                              // AI done thinking
        setMessages((prev) => [...prev, data.message]) // Add AI message to list
      } else if (data.type === 'AI_TYPING') {
        setIsTyping(true)   // Show typing indicator
      }
    }

    // CLEANUP: When the component unmounts or sessionId changes, close the WebSocket.
    // Without this, old connections would pile up.
    return () => ws.close()
  }, [sessionId])   // Re-run this effect if sessionId changes

  // Lines 41-50: SEND A MESSAGE
  // useCallback memoizes this function — it doesn't change unless sessionId changes.
  const sendMessage = useCallback((content: string) => {
    // Safety check: don't try to send if WebSocket isn't open
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return

    const msg = { type: 'USER_MESSAGE', content, sessionId }
    wsRef.current.send(JSON.stringify(msg))   // Send as JSON string over WebSocket

    // Optimistic UI update: add the user's message to the list IMMEDIATELY
    // (before the server confirms it), so the UI feels instant
    setMessages((prev) => [
      ...prev,   // Keep all existing messages
      { id: Date.now().toString(), sessionId, role: 'user', content, createdAt: new Date().toISOString() },
    ])

    setIsTyping(true)   // Show the typing indicator while AI generates
  }, [sessionId])

  // Return everything the component needs
  return { messages, isTyping, isConnected, sendMessage }
}
```

---

---

# PART 3 — HOW EVERYTHING CONNECTS

## The Flow When a Patient Sends a Message

```
PATIENT types in widget chat box (ChatBubble.tsx)
    │
    ▼
WIDGET sends REST request: POST /api/v1/chat/message
    │
    ▼
BACKEND: main.py receives it, routes to chat_routes.py
    │
    ▼
ROUTE: chat_routes.py creates TherapeuticAIService and calls process_message()
    │
    ▼
SERVICE: therapeutic_ai_service.py runs the pipeline:
    ├─ 1. crisis_detection_service.scan(message)   ← Is this dangerous?
    │        If YES → return emergency helplines (stop here)
    │        If NO → continue
    ├─ 2. rag_service.query(message)               ← Find relevant knowledge
    ├─ 3. chatbot_service.build_response_prompt()  ← Build the full AI prompt
    └─ 4. qwen_inference.generate(prompt)          ← Get AI response
    │
    ▼
ROUTE: returns JSON response to the widget
    │
    ▼
WIDGET: ChatBubble.tsx displays the AI response in the chat window

SIMULTANEOUSLY:
    If crisis_score >= 7 → WebSocket alert sent to clinician dashboard
    ClinicianDashboard.tsx shows a RED BANNER with patient ID and severity
```

---

## The Flow When Clinician Logs In

```
CLINICIAN enters email + password on login form
    │
    ▼
FRONTEND: api.ts calls POST /api/v1/auth/login
    │
    ▼
BACKEND: auth_routes.py receives credentials
    → Looks up clinician by email in database
    → Calls jwt_handler.verify_password(entered_password, stored_hash)
    → If correct: calls jwt_handler.create_access_token({"sub": clinician.email})
    │
    ▼
BACKEND: Returns {"access_token": "eyJ...", "token_type": "bearer"}
    │
    ▼
FRONTEND: AuthContext.tsx stores token in localStorage
    → All future API calls automatically include: Authorization: Bearer eyJ...
    → Every protected route is now accessible
```

---

## The Payment Flow

```
PATIENT selects appointment time
    │
    ▼
FRONTEND: PaymentFlow.tsx calls api.createPaymentOrder({amount_inr: 999, appointment_id: "..."})
    │
    ▼
BACKEND: payment_service.create_order() calls Razorpay API
    → Razorpay creates an order and returns an order_id
    │
    ▼
FRONTEND: Gets order_id and opens the Razorpay checkout popup
    │
    ▼
PATIENT: Pays with UPI / Card / NetBanking inside Razorpay popup
    │
    ▼
RAZORPAY: Sends back razorpay_payment_id + razorpay_signature
    │
    ▼
FRONTEND: Calls api.verifyPayment() with those values
    │
    ▼
BACKEND: payment_service.verify() checks the HMAC signature
    → Signature verification proves Razorpay really sent this (not a fake request)
    → Marks appointment as paid in database
```

---

# QUICK REFERENCE — What File to Edit for Each Feature

| What you want to change | File to edit |
|------------------------|-------------|
| AI personality / system prompt | `server/services/chatbot_service.py` |
| Crisis keywords or thresholds | `server/services/crisis_detection_service.py` |
| Add a new API endpoint | `server/routes/` or `server/api/` |
| Change which AI model to use | `server/config.py` (TOGETHER_MODEL) |
| Database table structure | `server/models.py` |
| Clinician dashboard look | `client/src/components/clinician/ClinicianDashboard.tsx` |
| Widget chat bubble appearance | `widget/src/components/ChatBubble.tsx` |
| Add a new assessment type | `server/services/assessment_service.py` |
| Payment amount / currency | `server/services/payment_service.py` |
| Login / logout behaviour | `client/src/contexts/AuthContext.tsx` |
| All API function calls (frontend) | `client/src/lib/api.ts` |
| WebSocket real-time behaviour | `client/src/hooks/useChat.ts` |
| Environment variables / secrets | `therapeutic-copilot/.env` |
| Port / debug mode / log level | `server/config.py` |

---

*Last updated: March 6, 2026 — Session 1*
*Written for vibes coders who learn by understanding, not by memorizing*
