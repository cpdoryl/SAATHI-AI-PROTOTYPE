# WATCHER STATUS

**Updated**: 2026-03-09 07:39:06
**Status**:  IN PROGRESS -- 55 done, 13 remaining

## Progress

- Tasks completed : 55 / 14
- Last task       : `None`

## Details

**Just completed**: `[P5-ML] Create ml_pipeline/scripts/split_data.py — stratified 60/20/20 train/val/test split by topic, output separate .jsonl files`

**Up next**: `[P5-ML] Create ml_pipeline/scripts/evaluate_data.py — score each sample for therapeutic alignment, empathy, and safety; flag score < 0.5`

## Recent Log

```
[2026-03-09 07:22:23] [WARN] Reconcile: fixing unchecked entry in TASKS.md: Widget token validation on mount — call GET /api/v1/widget/validate-to
[2026-03-09 07:22:23] [WARN] Reconcile: fixing unchecked entry in TASKS.md: Replace train_lora.py pseudocode with real implementation — implement 
[2026-03-09 07:22:23] [WARN] Reconcile: fixing unchecked entry in TASKS.md: AdminPanel — implement tenant CRUD table (list tenants from GET /api/v
[2026-03-09 07:22:23] [WARN] Reconcile: fixing unchecked entry in TASKS.md: Full ChatBubble UI — floating 60px circle button (bottom-right), click
[2026-03-09 07:22:23] [WARN] Reconcile: fixing unchecked entry in TASKS.md: Widget mobile responsive — full-screen chat panel on screen width < 48
[2026-03-09 07:22:23] [WARN] Reconcile: fixing unchecked entry in TASKS.md: Create ml_pipeline/requirements-ml.txt — list: transformers==4.44.0, p
[2026-03-09 07:22:25] [INFO] TASKS.md reconciliation committed and pushed.
[2026-03-09 07:22:25] [INFO] Task queue: 16 task(s) to execute (skipped 51 already completed).
[2026-03-09 07:22:25] [WARN] Resuming interrupted task: [P5-ML] Create ml_pipeline/scripts/clean_data.py — validate JSONL format, remove duplicates, detect PII (phone/email/Aadhaar regex), filter conversations < 3 turns, filter > 2048 tokens
[2026-03-09 07:22:32] [INFO] [1/16] START: [P5-ML] Create ml_pipeline/scripts/clean_data.py — validate JSONL format, remove duplicates, detect PII (phone/email/Aadhaar regex), filter conversations < 3 turns, filter > 2048 tokens
[2026-03-09 07:22:32] [INFO] Invoking Claude: [P5-ML] Create ml_pipeline/scripts/clean_data.py — validate JSONL format, remove duplicates, detect PII (phone/email/Aadhaar regex), filter conversations < 3 turns, filter > 2048 tokens
[2026-03-09 07:29:45] [INFO] [1/16] DONE: [P5-ML] Create ml_pipeline/scripts/clean_data.py — validate JSONL format, remove duplicates, detect PII (phone/email/Aadhaar regex), filter conversations < 3 turns, filter > 2048 tokens
[2026-03-09 07:29:47] [INFO] Cooldown 60s before next task (token budget recovery)...
[2026-03-09 07:30:47] [INFO] [2/16] START: [P5-ML] Create ml_pipeline/scripts/check_balance.py — count by topic/length/language, report imbalances, flag categories < 10% of total
[2026-03-09 07:30:47] [INFO] Invoking Claude: [P5-ML] Create ml_pipeline/scripts/check_balance.py — count by topic/length/language, report imbalances, flag categories < 10% of total
[2026-03-09 07:35:20] [INFO] [2/16] DONE: [P5-ML] Create ml_pipeline/scripts/check_balance.py — count by topic/length/language, report imbalances, flag categories < 10% of total
[2026-03-09 07:35:23] [INFO] Cooldown 60s before next task (token budget recovery)...
[2026-03-09 07:36:23] [INFO] [3/16] START: [P5-ML] Create ml_pipeline/scripts/split_data.py — stratified 60/20/20 train/val/test split by topic, output separate .jsonl files
[2026-03-09 07:36:23] [INFO] Invoking Claude: [P5-ML] Create ml_pipeline/scripts/split_data.py — stratified 60/20/20 train/val/test split by topic, output separate .jsonl files
[2026-03-09 07:39:06] [INFO] [3/16] DONE: [P5-ML] Create ml_pipeline/scripts/split_data.py — stratified 60/20/20 train/val/test split by topic, output separate .jsonl files
```
