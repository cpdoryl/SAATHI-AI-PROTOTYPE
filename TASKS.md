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

## P0 — Investor Demo Critical (Must Ship) execute the below  task 

- [x] Create TASKS.md for GitHub command-board workflow
- [ ] Implement `_detect_patient_stage()` with real async DB query (Patient table)
- [ ] Persist TherapySession record to DB in `start_session()`
- [ ] Complete auth `/login` route — real DB query + bcrypt verify + return JWT
- [ ] Wire chat pipeline: persist ChatMessage to DB after each AI response
- [ ] Update `TherapySession.current_step` after each Stage 2 message
- [ ] Crisis escalation: WebSocket alert to clinician room + SendGrid email
- [ ] Widget token validation: real DB lookup in `widget_routes.py`

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
