# SAATHI AI — GitHub Command Board
## RYL NEUROACADEMY PRIVATE LIMITED

> **HOW TO USE**: Add `- [ ] task` under the correct section on GitHub web UI and commit to `main`.
> The watcher on the local PC detects it within 5 minutes and Claude executes it automatically.
> Claude marks `[x]` when done and pushes back.

---

## HOW TO WRITE A GOOD TASK

```
- [x] Task title — context: what file, what problem, what expected result
```

**Examples:**
```
- [x] Complete ChatWidget WebSocket token streaming — connect to /ws/chat/{session_id}, receive tokens, append to message bubble in real time. File: therapeutic-copilot/client/src/components/chatbot/ChatWidget.tsx
- [x] Fix: GET /api/v1/chat/session/{id} returns empty [] — query ChatMessage table by session_id ordered by created_at. File: therapeutic-copilot/server/routes/chat_routes.py
```

---

## STANDING INSTRUCTIONS FOR CLAUDE

- Always commit with message format: `feat(scope): description`
- Push to `main` after each completed task
- Update `DEVELOPER_GUIDE.md` after significant architectural changes
- Run `git status` before each commit to avoid committing `.env` files
- If blocked on a task, add a `BLOCKED:` note below the task item
- **MANDATORY after every session**: Update `BUILD_DESIGN_RECORD.md` with a new dated session block — file changed, problem solved, code pattern, design decision. Commit as: `docs(build-record): update for YYYY-MM-DD session`
- Read the relevant blueprint document FIRST before starting any task:
  - Backend tasks → `therapeutic-copilot/server/BACKEND_BLUEPRINT.md`
  - Frontend tasks → `therapeutic-copilot/client/FRONTEND_BLUEPRINT.md`
  - ML/AI tasks → `ml_pipeline/ML_BLUEPRINT.md`
  - RAG tasks → `therapeutic-copilot/server/RAG_BLUEPRINT.md`
  - Database tasks → `therapeutic-copilot/server/DATABASE_BLUEPRINT.md`
  - Widget tasks → `therapeutic-copilot/widget/WIDGET_BLUEPRINT.md`

---

## ════════════════════════════════════════════════
## PHASE 1 — BACKEND COMPLETION
## Blueprint: therapeutic-copilot/server/BACKEND_BLUEPRINT.md
## ════════════════════════════════════════════════

### P1-BE — Backend (All Gaps)

- [x] Auth /login route — real DB query + bcrypt verify + return JWT
- [x] _detect_patient_stage() with real async DB query
- [x] Persist TherapySession to DB in start_session()
- [x] Persist ChatMessage to DB after each AI response
- [x] Update TherapySession.current_step after each Stage 2 message
- [x] Crisis escalation: WebSocket alert to clinician room
- [x] Widget token validation: real DB lookup
- [x] Redis sliding-window rate limiting
- [x] Redis session state management
- [x] APScheduler dropout re-engagement cron
- [x] Complete GET /api/v1/chat/session/{id} — query TherapySession + ChatMessage rows from DB, return real data instead of []. File: therapeutic-copilot/server/routes/chat_routes.py
- [x] Complete POST /api/v1/chat/session/{id}/end — fetch last 10 messages, call LLM to summarize, persist to TherapySession.session_summary, update status=COMPLETED, delete Redis key. File: therapeutic-copilot/server/services/therapeutic_ai_service.py
- [x] Complete GET /api/v1/assessments/{patient_id}/history — query Assessment table by patient_id ordered by administered_at desc, return real list. File: therapeutic-copilot/server/routes/assessment_routes.py
- [x] Complete crisis escalation SendGrid email — when severity >= 7, send email to clinician using SENDGRID_API_KEY + SENDGRID_FROM_EMAIL. File: therapeutic-copilot/server/services/crisis_detection_service.py
- [x] Complete Razorpay webhook handlers — handle payment.captured (update Appointment.payment_status="paid"), payment.failed, refund.created. File: therapeutic-copilot/server/services/payment_service.py
- [x] Add GET /api/v1/auth/me endpoint — return current clinician profile from JWT. Add POST /api/v1/auth/logout — blacklist token in Redis. File: therapeutic-copilot/server/routes/auth_routes.py
- [x] Add GET /api/v1/patients/{id}/sessions endpoint — list TherapySession rows for patient, ordered by started_at desc. File: therapeutic-copilot/server/api/patients.py
- [ ] Complete LoRA adapter hot-swap API call in lora_model_service.py — POST to {LLAMA_CPP_SERVER_URL}/lora with adapter path on stage change. File: therapeutic-copilot/server/services/lora_model_service.py
- [ ] Complete Google Calendar routes — implement GET /auth-url, GET /callback (OAuth token exchange + store in clinicians.google_calendar_token), POST /events (create Google Calendar event). Files: therapeutic-copilot/server/routes/calendar_routes.py, therapeutic-copilot/server/services/calendar_service.py
- [ ] Complete appointments API — implement CREATE (POST /api/v1/appointments): save to DB + create Razorpay order + create Google Calendar event. Implement list (GET) with real DB query. File: therapeutic-copilot/server/api/appointments.py
- [ ] Write test_auth.py — test login correct password→JWT, wrong password→401, unknown email→401, register→201, refresh→new token. File: therapeutic-copilot/server/tests/test_auth.py
- [ ] Write test_rag.py — test ingest→Pinecone upsert, query→top-k chunks returned, wrong tenant→empty, fallback to default namespace. File: therapeutic-copilot/server/tests/test_rag.py
- [ ] Write test_websocket.py — test clinician connects to room, crisis alert broadcasts, chat session WS streams tokens. File: therapeutic-copilot/server/tests/test_websocket.py
- [ ] Create scripts/setup_db.py — seed demo data: 1 tenant (Demo Clinic, widget_token=demo-token-123), 1 clinician (admin@demo.com / Demo@1234), 3 patients (LEAD/ACTIVE/DROPOUT), 1 session with 5 messages, 1 PHQ-9 assessment. File: therapeutic-copilot/server/scripts/setup_db.py
- [ ] Add audit_logs model to models.py — fields: id, actor_id, action, resource, ip_address, created_at. Create Alembic migration. File: therapeutic-copilot/server/models.py

---

## ════════════════════════════════════════════════
## PHASE 2 — FRONTEND COMPLETION
## Blueprint: therapeutic-copilot/client/FRONTEND_BLUEPRINT.md
## ════════════════════════════════════════════════

### P2-FE — Frontend (All Gaps)

- [x] ClinicianDashboard: wire patient list to real /api/v1/patients API
- [x] Assessment flow: wire to /api/v1/assessments endpoints
- [x] Real SSE token streaming from Together AI
- [x] Complete ChatWidget — implement full chat UI: WebSocket connect to /ws/chat/{session_id}, send message, receive and stream tokens into assistant message bubble, typing indicator (animated dots), auto-scroll. File: therapeutic-copilot/client/src/components/chatbot/ChatWidget.tsx and hooks/useChat.ts
- [x] Complete useChat hook — must export: messages[], sendMessage(), isStreaming, crisisDetected, crisisResources[], endSession(). File: therapeutic-copilot/client/src/hooks/useChat.ts
- [x] Crisis banner component — red overlay in ChatWidget showing helpline numbers when crisis detected via WebSocket. File: therapeutic-copilot/client/src/components/chatbot/ChatWidget.tsx
- [ ] PatientPortal session history tab — call GET /api/v1/patients/{id}/sessions, render session cards with: date, stage badge, crisis_score, expandable message preview. File: therapeutic-copilot/client/src/components/patient/PatientPortal.tsx
- [ ] PatientPortal assessment history — call GET /api/v1/assessments/{id}/history, render past scores as cards with type/score/severity/date. File: therapeutic-copilot/client/src/components/patient/PatientPortal.tsx
- [ ] PatientPortal appointments tab — call GET /api/v1/appointments, render appointment list. Add "Book Appointment" button that opens clinician selector + date picker + triggers PaymentFlow. File: therapeutic-copilot/client/src/components/patient/PatientPortal.tsx
- [ ] ClinicianDashboard Analytics tab — implement with Recharts: (1) weekly sessions BarChart, (2) crisis rate AreaChart, (3) patient stage PieChart (LEAD/ACTIVE/DROPOUT), (4) assessment score distribution. Wire to real API. File: therapeutic-copilot/client/src/components/clinician/ClinicianDashboard.tsx
- [ ] ClinicianDashboard Appointments tab — list appointments with GET /api/v1/appointments, show clinician's calendar, add Create Appointment form. File: therapeutic-copilot/client/src/components/clinician/ClinicianDashboard.tsx
- [ ] Patient risk score badge in Dashboard — show dropout_risk_score as colored badge: red(>0.7), yellow(0.3-0.7), green(<0.3) next to each patient name. File: therapeutic-copilot/client/src/components/clinician/ClinicianDashboard.tsx
- [ ] Patient detail drawer — clicking a patient in ClinicianDashboard opens a slide-over drawer showing: patient info, session count, last PHQ-9 score, risk score, recent sessions list. File: therapeutic-copilot/client/src/components/clinician/ClinicianDashboard.tsx
- [ ] LandingPage completion — add: "How It Works" 3-step section, Pricing cards (Basic ₹2,999/mo, Pro ₹7,999/mo, Enterprise custom), Footer with links. File: therapeutic-copilot/client/src/components/landing/LandingPage.tsx
- [ ] Login/Register form improvements — add inline validation (red border + error text), show/hide password toggle, loading spinner on submit. File: therapeutic-copilot/client/src/contexts/AuthContext.tsx and auth pages
- [ ] Add GET /auth/me and logout to api.ts — add getPatientSessions(), getAssessmentHistory(), getAppointments(), createAppointment(), cancelAppointment(), getAnalyticsSummary(), ingestDocument(). File: therapeutic-copilot/client/src/lib/api.ts
- [ ] Add Razorpay SDK script to index.html — add <script src="https://checkout.razorpay.com/v1/checkout.js"> before closing </body>. File: therapeutic-copilot/client/index.html
- [ ] AdminPanel — implement tenant CRUD table (list tenants from GET /api/v1/tenants), document upload form (POST /api/v1/rag/ingest), widget embed code generator. File: therapeutic-copilot/client/src/components/admin/AdminPanel.tsx
- [ ] Write Vitest tests — create client/src/__tests__/: auth.test.tsx (login form), clinician-dashboard.test.tsx (patient list renders), patient-portal.test.tsx (assessment submit), chat-widget.test.tsx (WS mock → stream). Use MSW for API mocking.
- [ ] TypeScript types completion — ensure all interfaces in types/index.ts match backend response schemas: Patient, TherapySession, ChatMessage, Assessment, Appointment, CrisisAlert, Tenant. File: therapeutic-copilot/client/src/types/index.ts

---

## ════════════════════════════════════════════════
## PHASE 3 — WIDGET COMPLETION
## Blueprint: therapeutic-copilot/widget/WIDGET_BLUEPRINT.md
## ════════════════════════════════════════════════

### P3-WI — Widget

- [x] Shadow DOM encapsulation + Custom Element registration
- [ ] Widget token validation on mount — call GET /api/v1/widget/validate-token?token={data-token}, hide widget if invalid, show bubble if valid. File: therapeutic-copilot/widget/src/widget.ts
- [ ] Full ChatBubble UI — floating 60px circle button (bottom-right), click expands 320×480 chat panel with header/message area/input bar. Style with Tailwind inside shadow DOM. File: therapeutic-copilot/widget/src/components/ChatBubble.tsx
- [ ] Widget WebSocket chat — on first open: POST /api/v1/chat/session, open WebSocket /ws/chat/{session_id}, display greeting, send/receive messages with token streaming. File: therapeutic-copilot/widget/src/components/ChatBubble.tsx
- [ ] Widget crisis banner — red banner inside chat panel when crisis detected, show helpline numbers. File: therapeutic-copilot/widget/src/components/ChatBubble.tsx
- [ ] Widget mobile responsive — full-screen chat panel on screen width < 480px. File: therapeutic-copilot/widget/src/components/ChatBubble.tsx
- [ ] Widget session persistence — store session_id in sessionStorage so re-open shows message history. File: therapeutic-copilot/widget/src/components/ChatBubble.tsx
- [ ] Widget build test — run npm run build, verify single saathi-widget.js produced under 500KB. Create test HTML: <script src="./dist/saathi-widget.js" data-token="demo-token-123"></script>, verify widget appears.

---

## ════════════════════════════════════════════════
## PHASE 4 — RAG SYSTEM COMPLETION
## Blueprint: therapeutic-copilot/server/RAG_BLUEPRINT.md
## ════════════════════════════════════════════════

### P4-RAG — RAG Pipeline

- [x] Pinecone client with per-tenant namespaces
- [x] SentenceTransformer singleton
- [x] Basic query and ingest routes
- [ ] Implement document chunking in rag_service.py — add _chunk_text(text, chunk_size=512, overlap=50) method, update ingest() to chunk full content and upsert all chunks as separate vectors with metadata {source, chunk_index, total_chunks}. File: therapeutic-copilot/server/services/rag_service.py
- [ ] Add similarity threshold + fallback to query() — filter results with score < 0.75, fallback to "default" namespace if tenant namespace returns empty. File: therapeutic-copilot/server/services/rag_service.py
- [ ] Create scripts/ingest_default_kb.py — script to bulk-ingest all files from knowledge_base/default/ folder into Pinecone namespace="default". Support .txt and .pdf files. File: therapeutic-copilot/server/scripts/ingest_default_kb.py
- [ ] Create scripts/ingest_clinic_docs.py — script to bulk-ingest clinic-specific documents into tenant namespace. File: therapeutic-copilot/server/scripts/ingest_clinic_docs.py
- [ ] Write test_rag.py — tests: ingest document → verify Pinecone upsert called, query → returns top-k, threshold filtering, fallback to default. File: therapeutic-copilot/server/tests/test_rag.py
- [ ] BLOCKED: Create knowledge_base/default/ content files — WAITING FOR USER TO PROVIDE: cbt_techniques_guide.txt, crisis_resources_india.txt, safe_messaging_guidelines.txt, psychoeducation_depression.txt, psychoeducation_anxiety.txt, psychoeducation_ocd.txt

---

## ════════════════════════════════════════════════
## PHASE 5 — ML/AI PIPELINE
## Blueprint: ml_pipeline/ML_BLUEPRINT.md
## ════════════════════════════════════════════════

### P5-ML — Machine Learning Pipeline

- [ ] Replace train_lora.py pseudocode with real implementation — implement full QLoRA training using transformers + PEFT + TRL + bitsandbytes as specified in ML_BLUEPRINT.md. File: ml_pipeline/train_lora.py
- [ ] Create ml_pipeline/requirements-ml.txt — list: transformers==4.44.0, peft==0.12.0, trl==0.9.4, bitsandbytes==0.43.0, datasets==2.21.0, accelerate==0.33.0, torch==2.3.1, sentencepiece, wandb, sacrebleu, rouge-score
- [ ] Create ml_pipeline/scripts/clean_data.py — validate JSONL format, remove duplicates, detect PII (phone/email/Aadhaar regex), filter conversations < 3 turns, filter > 2048 tokens
- [ ] Create ml_pipeline/scripts/check_balance.py — count by topic/length/language, report imbalances, flag categories < 10% of total
- [ ] Create ml_pipeline/scripts/split_data.py — stratified 60/20/20 train/val/test split by topic, output separate .jsonl files
- [ ] Create ml_pipeline/scripts/evaluate_data.py — score each sample for therapeutic alignment, empathy, and safety; flag score < 0.5
- [ ] Create ml_pipeline/scripts/evaluate_model.py — compute perplexity, BLEU-4, ROUGE-L on test set after training
- [ ] Create ml_pipeline/scripts/merge_lora.py — merge trained LoRA adapter into base Qwen 2.5-7B model for GGUF conversion
- [ ] BLOCKED: Stage 1 training data (634 conversations) — WAITING FOR USER TO PROVIDE: ml_pipeline/data/stage1_leads.jsonl
- [ ] BLOCKED: Stage 2 training data (3,017 conversations) — WAITING FOR USER TO PROVIDE: ml_pipeline/data/stage2_therapy.jsonl

---

## ════════════════════════════════════════════════
## PHASE 6 — DATABASE COMPLETION
## Blueprint: therapeutic-copilot/server/DATABASE_BLUEPRINT.md
## ════════════════════════════════════════════════

### P6-DB — Database

- [x] All 7 ORM models defined
- [x] Alembic initial migration
- [x] Redis session management
- [ ] Add audit_logs ORM model — fields: id (UUID PK), actor_id, action VARCHAR(100), resource VARCHAR(100), ip_address VARCHAR(45), created_at. Create Alembic migration. File: therapeutic-copilot/server/models.py
- [ ] Add indexes to hot query paths — add to Alembic migration: (patients: tenant_id+stage), (therapy_sessions: patient_id+status), (chat_messages: session_id+created_at), (assessments: patient_id+assessment_type). File: therapeutic-copilot/server/alembic/versions/
- [ ] Create scripts/setup_db.py seeding script — creates: 1 demo tenant (widget_token=demo-token-123), 1 clinician (admin@demo.com / Demo@1234 bcrypt), 3 patients, 1 session with messages, 1 PHQ-9. File: therapeutic-copilot/server/scripts/setup_db.py
- [ ] Create scripts/seed_test_data.py — larger test dataset for load testing: 10 tenants, 50 clinicians, 200 patients, 500 sessions. File: therapeutic-copilot/server/scripts/seed_test_data.py
- [ ] Verify Alembic migration — run alembic upgrade head on fresh SQLite, confirm all tables + indexes created. Write result to DB_MIGRATION_RESULTS.md

---

## ════════════════════════════════════════════════
## PHASE 7 — TESTING & QUALITY
## ════════════════════════════════════════════════

### P7-TEST — Testing

- [x] test_smoke_p0.py (10/10 PASS)
- [x] test_crisis_detection.py (8 tests)
- [x] test_razorpay_sandbox.py (4/4 PASS)
- [ ] Write test_auth.py — login happy path, wrong password, unknown email, token refresh, /me endpoint. File: therapeutic-copilot/server/tests/test_auth.py
- [ ] Write test_rag.py — ingest, query, threshold filter, namespace fallback. File: therapeutic-copilot/server/tests/test_rag.py
- [ ] Write test_websocket.py — clinician room connect, crisis broadcast, chat token stream. File: therapeutic-copilot/server/tests/test_websocket.py
- [ ] Write test_database.py — verify all tables exist, seed script works, relationships load correctly. File: therapeutic-copilot/server/tests/test_database.py
- [ ] Write Vitest frontend tests — auth form, dashboard patient list, assessment flow, chat widget. File: therapeutic-copilot/client/src/__tests__/
- [ ] Run full backend test suite and report — run pytest tests/ -v --tb=short, write results to TEST_RESULTS.md
- [ ] Load test — use locust or k6: simulate 50 concurrent chat sessions, measure: response time p95 < 3s, error rate < 1%. Write results to LOAD_TEST_RESULTS.md

---

## ════════════════════════════════════════════════
## PHASE 8 — DEVOPS & DEPLOYMENT PREP
## ════════════════════════════════════════════════

### P8-OPS — DevOps

- [x] Docker Compose (dev) — PostgreSQL + Redis + backend + frontend
- [x] Redis rate limiting
- [ ] Production Dockerfile — multi-stage build: (1) builder stage installs deps, (2) runtime stage copies only needed files. Add non-root user. File: therapeutic-copilot/server/Dockerfile.prod
- [ ] Create .env.example with all required variables — document every env var with description and example value. File: therapeutic-copilot/.env.example
- [ ] Create GitHub Actions CI pipeline — on push to main: run pytest, run npm test, check no .env files committed. File: .github/workflows/ci.yml
- [ ] Startup smoke test script — bash script that starts server, hits /health, /docs, /api/v1/auth/login with demo creds, verifies 200 responses. File: scripts/smoke_test.sh

---

## ════════════════════════════════════════════════
## COMPLETED LOG
## ════════════════════════════════════════════════

| Date | Phase | Task | Commit |
|------|-------|------|--------|
| 2026-03-06 | Scaffold | Full codebase scaffold (87 files, 7,019 lines) | Initial commits |
| 2026-03-06 | Docs | DEVELOPER_GUIDE.md + CODEBASE_EXPLAINED.md | docs: add guides |
| 2026-03-06 | Infra | Create TASKS.md command board | P0 start |
| 2026-03-07 | Backend | _detect_patient_stage() real DB query | feat(ai): detect patient stage |
| 2026-03-07 | Backend | Persist TherapySession to DB | feat(session): persist to DB |
| 2026-03-07 | Backend | Auth /login real bcrypt + JWT | feat(auth): real login route |
| 2026-03-07 | Backend | ChatMessage persistence | feat(chat): persist messages |
| 2026-03-07 | Backend | TherapySession.current_step advance | feat(session): step tracking |
| 2026-03-07 | Backend | Crisis escalation WebSocket alert | feat(crisis): WS alert |
| 2026-03-07 | Backend | Widget token DB validation | feat(widget): token validation |
| 2026-03-07 | Backend | P0 smoke tests (10/10 PASS) | test(p0): smoke test |
| 2026-03-07 | Backend | Razorpay e2e sandbox test (4/4 PASS) | test(payments): sandbox test |
| 2026-03-07 | Backend | Google Calendar OAuth + event creation | feat(calendar): OAuth |
| 2026-03-07 | Frontend | ClinicianDashboard real API wiring | feat(dashboard): real API |
| 2026-03-07 | Frontend | Assessment flow frontend wiring | feat(assessment): frontend wire |
| 2026-03-07 | Backend | Real SSE token streaming Together AI | feat(inference): SSE streaming |
| 2026-03-07 | Infra | GitHub watcher: full autonomous loop | fix(watcher): loop working |
| 2026-03-08 | Backend | Redis sliding-window rate limiting | feat(ratelimit): Redis middleware |
| 2026-03-08 | Backend | Alembic initial migration (7 tables) | feat(alembic): initial migration |
| 2026-03-08 | Backend | Redis session state management | feat(session): Redis cache |
| 2026-03-08 | Backend | APScheduler dropout cron | feat(scheduler): cron job |
| 2026-03-08 | Backend | SentenceTransformer singleton | feat(rag): singleton |
| 2026-03-08 | Backend | llama-cpp-python native streaming | feat(inference): native stream |
| 2026-03-08 | Docs | BUILD_DESIGN_RECORD.md | docs: build record |
| 2026-03-08 | Docs | All 6 blueprint documents | docs: blueprints |
