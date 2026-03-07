# SAATHI AI — P0 Smoke Test Results

**Date:** 2026-03-07
**Runner:** pytest 9.0.2 + pytest-asyncio 1.3.0 (auto mode)
**Database:** SQLite in-memory (aiosqlite)
**Test files:** `therapeutic-copilot/tests/test_smoke_p0.py`, `tests/test_razorpay_sandbox.py`

---

## P0 Smoke Tests — `test_smoke_p0.py`

| # | Test | Impl File | Result |
|---|------|-----------|--------|
| 1 | Auth `/login` — valid bcrypt password → JWT returned | `routes/auth_routes.py` | **PASS** |
| 1b | Auth `/login` — wrong password → 401 Unauthorized | `routes/auth_routes.py` | **PASS** |
| 2 | `_detect_patient_stage()` — ACTIVE patient → stage 2 | `services/therapeutic_ai_service.py` | **PASS** |
| 2b | `_detect_patient_stage()` — unknown patient → stage 1 (default) | `services/therapeutic_ai_service.py` | **PASS** |
| 3 | `start_session()` → TherapySession row created in DB | `services/therapeutic_ai_service.py` | **PASS** |
| 4 | `process_message()` → user + assistant ChatMessage rows saved | `services/therapeutic_ai_service.py` | **PASS** |
| 5 | Stage 2 step advance → `current_step` incremented twice in DB | `services/therapeutic_ai_service.py` | **PASS** |
| 6 | Crisis keyword "suicide" → `crisis_detected=True`, WebSocket alert fired to clinician | `services/therapeutic_ai_service.py`, `services/websocket_manager.py` | **PASS** |
| 7 | Widget `/validate-token` — valid token → 200 `{valid: true}` | `routes/widget_routes.py` | **PASS** |
| 7b | Widget `/validate-token` — invalid token → 401 | `routes/widget_routes.py` | **PASS** |

**Result: 10/10 PASS**

---

## P1 Razorpay Sandbox Tests — `test_razorpay_sandbox.py`

| # | Test | Result |
|---|------|--------|
| 1 | Order creation — ₹500 → 50000 paise, correct receipt format | **PASS** |
| 2 | Signature verification — valid HMAC-SHA256 → `verified=True` | **PASS** |
| 3 | Invalid signature → `verified=False` (tamper protection works) | **PASS** |
| 4 | Full e2e via HTTP API: POST `/create-order` → compute sig → POST `/verify` | **PASS** |

**Result: 4/4 PASS**

---

## Notes

- **LLM calls mocked** in P0 tests: `QwenInferenceService.generate` returns a fixed string. No Together AI key required to run tests.
- **RAG calls mocked**: `RAGService.query` returns `[]` in all tests.
- **WebSocket alerts tested via mock**: `ws_manager.send_crisis_alert` patched to capture calls.
- **Razorpay SDK mocked**: Sandbox keys used for HMAC verification; Razorpay HTTP client mocked for order creation to avoid live API calls.
- **bcrypt dependency**: requires `bcrypt==4.0.1` (passlib 1.7.4 is incompatible with bcrypt ≥5.0). Add `bcrypt==4.0.1` to `requirements.txt`.

---

## Infrastructure Notes

- `models/__init__.py` updated to re-export ORM models (was empty, causing `ImportError`). The `models/` package shadows `models.py`, so the re-export is needed for all imports like `from models import Clinician`.
- New endpoint `GET /api/v1/widget/validate-token` added (delegates to same DB lookup as `/config`).
- `pytest.ini` added with `asyncio_mode = auto` for module-scoped async fixtures.
