"""
Audit fix: restore falsely-completed tasks back to - [ ] in TASKS.md
and remove them from .watcher_state.json so the watcher re-runs them.
"""
import json
from pathlib import Path

REPO       = Path(r"c:\saath ai prototype")
TASKS_FILE = REPO / "TASKS.md"
STATE_FILE = REPO / ".watcher_state.json"

# Tasks confirmed NOT built — restore to - [ ]
# Exactly as they appear in TASKS.md after "- [x] "
FAILED_TASKS = [
    # P2-FE
    "PatientPortal session history tab — call GET /api/v1/patients/{id}/sessions, render session cards with: date, stage badge, crisis_score, expandable message preview. File: therapeutic-copilot/client/src/components/patient/PatientPortal.tsx",
    "PatientPortal assessment history — call GET /api/v1/assessments/{id}/history, render past scores as cards with type/score/severity/date. File: therapeutic-copilot/client/src/components/patient/PatientPortal.tsx",
    'PatientPortal appointments tab — call GET /api/v1/appointments, render appointment list. Add "Book Appointment" button that opens clinician selector + date picker + triggers PaymentFlow. File: therapeutic-copilot/client/src/components/patient/PatientPortal.tsx',
    "ClinicianDashboard Analytics tab — implement with Recharts: (1) weekly sessions BarChart, (2) crisis rate AreaChart, (3) patient stage PieChart (LEAD/ACTIVE/DROPOUT), (4) assessment score distribution. Wire to real API. File: therapeutic-copilot/client/src/components/clinician/ClinicianDashboard.tsx",
    "ClinicianDashboard Appointments tab — list appointments with GET /api/v1/appointments, show clinician's calendar, add Create Appointment form. File: therapeutic-copilot/client/src/components/clinician/ClinicianDashboard.tsx",
    "Patient risk score badge in Dashboard — show dropout_risk_score as colored badge: red(>0.7), yellow(0.3-0.7), green(<0.3) next to each patient name. File: therapeutic-copilot/client/src/components/clinician/ClinicianDashboard.tsx",
    "Patient detail drawer — clicking a patient in ClinicianDashboard opens a slide-over drawer showing: patient info, session count, last PHQ-9 score, risk score, recent sessions list. File: therapeutic-copilot/client/src/components/clinician/ClinicianDashboard.tsx",
    "LandingPage completion — add: \"How It Works\" 3-step section, Pricing cards (Basic \u20b92,999/mo, Pro \u20b97,999/mo, Enterprise custom), Footer with links. File: therapeutic-copilot/client/src/components/landing/LandingPage.tsx",
    "Login/Register form improvements — add inline validation (red border + error text), show/hide password toggle, loading spinner on submit. File: therapeutic-copilot/client/src/contexts/AuthContext.tsx and auth pages",
    "Add GET /auth/me and logout to api.ts — add getPatientSessions(), getAssessmentHistory(), getAppointments(), createAppointment(), cancelAppointment(), getAnalyticsSummary(), ingestDocument(). File: therapeutic-copilot/client/src/lib/api.ts",
    "Add Razorpay SDK script to index.html — add <script src=\"https://checkout.razorpay.com/v1/checkout.js\"> before closing </body>. File: therapeutic-copilot/client/index.html",
    "AdminPanel — implement tenant CRUD table (list tenants from GET /api/v1/tenants), document upload form (POST /api/v1/rag/ingest), widget embed code generator. File: therapeutic-copilot/client/src/components/admin/AdminPanel.tsx",
    "Write Vitest tests — create client/src/__tests__/: auth.test.tsx (login form), clinician-dashboard.test.tsx (patient list renders), patient-portal.test.tsx (assessment submit), chat-widget.test.tsx (WS mock \u2192 stream). Use MSW for API mocking.",
    "TypeScript types completion — ensure all interfaces in types/index.ts match backend response schemas: Patient, TherapySession, ChatMessage, Assessment, Appointment, CrisisAlert, Tenant. File: therapeutic-copilot/client/src/types/index.ts",
    # P3-WI
    "Widget token validation on mount — call GET /api/v1/widget/validate-token?token={data-token}, hide widget if invalid, show bubble if valid. File: therapeutic-copilot/widget/src/widget.ts",
    "Full ChatBubble UI — floating 60px circle button (bottom-right), click expands 320\u00d7480 chat panel with header/message area/input bar. Style with Tailwind inside shadow DOM. File: therapeutic-copilot/widget/src/components/ChatBubble.tsx",
    "Widget WebSocket chat — on first open: POST /api/v1/chat/session, open WebSocket /ws/chat/{session_id}, display greeting, send/receive messages with token streaming. File: therapeutic-copilot/widget/src/components/ChatBubble.tsx",
    "Widget crisis banner — red banner inside chat panel when crisis detected, show helpline numbers. File: therapeutic-copilot/widget/src/components/ChatBubble.tsx",
    "Widget mobile responsive — full-screen chat panel on screen width < 480px. File: therapeutic-copilot/widget/src/components/ChatBubble.tsx",
    "Widget session persistence — store session_id in sessionStorage so re-open shows message history. File: therapeutic-copilot/widget/src/components/ChatBubble.tsx",
    "Widget build test — run npm run build, verify single saathi-widget.js produced under 500KB. Create test HTML: <script src=\"./dist/saathi-widget.js\" data-token=\"demo-token-123\"></script>, verify widget appears.",
    # P4-RAG — ingest scripts only (chunking/similarity already in rag_service.py)
    "Create scripts/ingest_default_kb.py — script to bulk-ingest all files from knowledge_base/default/ folder into Pinecone namespace=\"default\". Support .txt and .pdf files. File: therapeutic-copilot/server/scripts/ingest_default_kb.py",
    "Create scripts/ingest_clinic_docs.py — script to bulk-ingest clinic-specific documents into tenant namespace. File: therapeutic-copilot/server/scripts/ingest_clinic_docs.py",
    # P5-ML — all 8
    "Replace train_lora.py pseudocode with real implementation — implement full QLoRA training using transformers + PEFT + TRL + bitsandbytes as specified in ML_BLUEPRINT.md. File: ml_pipeline/train_lora.py",
    "Create ml_pipeline/requirements-ml.txt — list: transformers==4.44.0, peft==0.12.0, trl==0.9.4, bitsandbytes==0.43.0, datasets==2.21.0, accelerate==0.33.0, torch==2.3.1, sentencepiece, wandb, sacrebleu, rouge-score",
    "Create ml_pipeline/scripts/clean_data.py — validate JSONL format, remove duplicates, detect PII (phone/email/Aadhaar regex), filter conversations < 3 turns, filter > 2048 tokens",
    "Create ml_pipeline/scripts/check_balance.py — count by topic/length/language, report imbalances, flag categories < 10% of total",
    "Create ml_pipeline/scripts/split_data.py — stratified 60/20/20 train/val/test split by topic, output separate .jsonl files",
    "Create ml_pipeline/scripts/evaluate_data.py — score each sample for therapeutic alignment, empathy, and safety; flag score < 0.5",
    "Create ml_pipeline/scripts/evaluate_model.py — compute perplexity, BLEU-4, ROUGE-L on test set after training",
    "Create ml_pipeline/scripts/merge_lora.py — merge trained LoRA adapter into base Qwen 2.5-7B model for GGUF conversion",
    # P6-DB
    "Add indexes to hot query paths — add to Alembic migration: (patients: tenant_id+stage), (therapy_sessions: patient_id+status), (chat_messages: session_id+created_at), (assessments: patient_id+assessment_type). File: therapeutic-copilot/server/alembic/versions/",
    "Create scripts/seed_test_data.py — larger test dataset for load testing: 10 tenants, 50 clinicians, 200 patients, 500 sessions. File: therapeutic-copilot/server/scripts/seed_test_data.py",
    "Verify Alembic migration — run alembic upgrade head on fresh SQLite, confirm all tables + indexes created. Write result to DB_MIGRATION_RESULTS.md",
    # P7-TEST
    "Write test_database.py — verify all tables exist, seed script works, relationships load correctly. File: therapeutic-copilot/server/tests/test_database.py",
    "Write Vitest frontend tests — auth form, dashboard patient list, assessment flow, chat widget. File: therapeutic-copilot/client/src/__tests__/",
    "Run full backend test suite and report — run pytest tests/ -v --tb=short, write results to TEST_RESULTS.md",
    "Load test — use locust or k6: simulate 50 concurrent chat sessions, measure: response time p95 < 3s, error rate < 1%. Write results to LOAD_TEST_RESULTS.md",
    # P8-OPS
    "Production Dockerfile — multi-stage build: (1) builder stage installs deps, (2) runtime stage copies only needed files. Add non-root user. File: therapeutic-copilot/server/Dockerfile.prod",
    "Create GitHub Actions CI pipeline — on push to main: run pytest, run npm test, check no .env files committed. File: .github/workflows/ci.yml",
    "Startup smoke test script — bash script that starts server, hits /health, /docs, /api/v1/auth/login with demo creds, verifies 200 responses. File: scripts/smoke_test.sh",
]

content  = TASKS_FILE.read_text(encoding="utf-8", errors="replace")
restored = 0
not_found = []

for task_text in FAILED_TASKS:
    checked   = f"- [x] {task_text}"
    unchecked = f"- [ ] {task_text}"
    if checked in content:
        content = content.replace(checked, unchecked, 1)
        restored += 1
    elif unchecked not in content:
        not_found.append(task_text[:70])

TASKS_FILE.write_text(content, encoding="utf-8")
print(f"Restored {restored} tasks to - [ ]")
if not_found:
    print(f"\nNOT FOUND in TASKS.md (text mismatch — check manually):")
    for t in not_found:
        print(f"  - {t}")

# Remove these from completed_tasks in state
state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
original_count = len(state["completed_tasks"])
texts_to_remove = set(FAILED_TASKS)

new_completed = [
    key for key in state["completed_tasks"]
    if (key.split("::", 1)[1] if "::" in key else key) not in texts_to_remove
]

state["completed_tasks"] = new_completed
STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"\nState: removed {original_count - len(new_completed)} failed keys")
print(f"State now has {len(new_completed)} completed tasks")

done    = content.count("- [x]")
pending = content.count("- [ ]")
print(f"\nTASKS.md now:")
print(f"  [x] confirmed done : {done}")
print(f"  [ ] pending re-run : {pending}")
