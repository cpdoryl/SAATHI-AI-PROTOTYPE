# SAATHI AI — GitHub Command Board

> Edit this file from GitHub web UI to give Claude tasks between sessions.
> Claude reads this file at the start of each session and executes pending items.

---

## HOW TO USE
1. Open this file on GitHub: `github.com/cpdoryl/SAATHI-AI-PROTOTYPE/blob/main/TASKS.md`
2. Click the pencil (Edit) icon
3. Add your task under the correct priority section using the format below
4. Commit directly to `main`
5. Claude will pick it up next session

**Task format:**
```
- [ ] Task description — any extra context here
```

Mark done with `[x]` after Claude confirms completion.

---

## P0 — Investor Demo Critical (Must Ship)

- [x] Create TASKS.md for GitHub command-board workflow
- [x] Implement `_detect_patient_stage()` with real async DB query (Patient table)
- [x] Persist TherapySession record to DB in `start_session()`
- [x] Complete auth `/login` route — real DB query + bcrypt verify + return JWT
- [x] Wire chat pipeline: persist ChatMessage to DB after each AI response
- [x] Update `TherapySession.current_step` after each Stage 2 message
- [x] Crisis escalation: WebSocket alert to clinician room (via ws_manager singleton)
- [x] Widget token validation: real DB lookup in `widget_routes.py` 
- [ ] Smoke test all P0 implementations and write results to RESULTS.md — test each item below using pytest or direct async calls, mark PASS/FAIL with error details if failing:
  1. Auth /login — POST with valid bcrypt-hashed password from DB, expect JWT returned. File: therapeutic-copilot/server/routes/auth_routes.py
  2. _detect_patient_stage() — call with a real patient_id from DB (or seed one), expect PatientStage enum returned. File: therapeutic-copilot/server/services/therapeutic_ai_service.py
  3. TherapySession persist — call start_session(), query DB to confirm TherapySession row was created. File: therapeutic-copilot/server/services/therapeutic_ai_service.py
  4. ChatMessage persist — call process_message(), query DB to confirm user + assistant ChatMessage rows saved. File: therapeutic-copilot/server/services/therapeutic_ai_service.py
  5. Stage 2 step advance — call process_message() with stage=2 twice, confirm TherapySession.current_step incremented in DB.
  6. Crisis WebSocket alert — send message containing "suicide" keyword, confirm WebSocket alert fires to clinician room and SendGrid email attempted. File: therapeutic-copilot/server/services/therapeutic_ai_service.py, therapeutic-copilot/server/services/websocket_manager.py
  7. Widget token validation — call GET /api/v1/widget/validate-token with a valid token, expect 200. File: therapeutic-copilot/server/routes/widget_routes.py
  Write all results to RESULTS.md in the repo root. Commit with message: test(p0): smoke test all P0 implementations

---

## P1 — Demo Polish

- [ ] Razorpay end-to-end test in sandbox mode
- [ ] Google Calendar OAuth token storage + event creation
- [ ] ClinicianDashboard: wire to real patient/session API (currently empty arrays)
- [ ] Assessment flow: wire frontend to `/api/v1/assessments` endpoints
- [ ] Real token streaming from Together AI (replace word-split hack in `stream()`)

---

## P2 — Production Readiness

- [ ] Redis sliding-window rate limiting in `rate_limit_middleware.py`
- [ ] Alembic first migration: `alembic revision --autogenerate -m "initial"`
- [ ] Redis session state management (replace in-memory dict)
- [ ] APScheduler dropout re-engagement job (daily cron)
- [ ] Pinecone `_embed()` — move SentenceTransformer to module-level singleton (perf)
- [ ] llama.cpp token streaming for production inference

---

## STANDING INSTRUCTIONS FOR CLAUDE

- Always commit with message format: `feat(scope): description`
- Push to `main` after each completed P0 task
- Update `DEVELOPER_GUIDE.md` after significant architectural changes
- Run `git status` before each commit to avoid committing `.env` files
- If blocked on a task, add a `BLOCKED:` note below the task item

---

## COMPLETED LOG

| Date | Task | Commit |
|------|------|--------|
| 2026-03-06 | Full codebase scaffold (all folders/files) | Initial commits |
| 2026-03-06 | DEVELOPER_GUIDE.md + CODEBASE_EXPLAINED.md | docs: add guides |
| 2026-03-06 | Merge master → main (GitHub default branch) | merge commit |
| 2026-03-06 | Create TASKS.md command board | P0 start |
