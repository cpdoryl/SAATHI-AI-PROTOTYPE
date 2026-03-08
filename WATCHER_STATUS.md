# WATCHER STATUS

**Updated**: 2026-03-08 11:41:50
**Status**:  TASK FAILED -- [════════════════════════════════════════════════] Create ml_pipeline/scripts/evaluate_model.py — co

## Progress

- Tasks completed : 53 / 71
- Last task       : `════════════════════════════════════════════════::Create ml_pipeline/scripts/evaluate_model.py — compute perplexity, BLEU-4, ROUGE-L on test set after training`

## Details

Claude Code returned a non-zero exit code for this task.

**Task**: `[════════════════════════════════════════════════] Create ml_pipeline/scripts/evaluate_model.py — compute perplexity, BLEU-4, ROUGE-L on test set after training`

The watcher will move on to the next task.
Please review `watcher.log` and fix manually if needed.

## Recent Log

```
[2026-03-08 11:41:16] [INFO] [49/71] SKIP (failed): [════════════════════════════════════════════════] Create ml_pipeline/requirements-ml.txt — list: transformers==4.44.0, peft==0.12.0, trl==0.9.4, bitsandbytes==0.43.0, datasets==2.21.0, accelerate==0.33.0, torch==2.3.1, sentencepiece, wandb, sacrebleu, rouge-score
[2026-03-08 11:41:16] [INFO] [50/71] START: [════════════════════════════════════════════════] Create ml_pipeline/scripts/clean_data.py — validate JSONL format, remove duplicates, detect PII (phone/email/Aadhaar regex), filter conversations < 3 turns, filter > 2048 tokens
[2026-03-08 11:41:16] [INFO] Invoking Claude: [════════════════════════════════════════════════] Create ml_pipeline/scripts/clean_data.py — validate JSONL format, remove duplicates, detect PII (phone/email/Aadhaar regex), filter conversations < 3 turns, filter > 2048 tokens
[2026-03-08 11:41:20] [ERROR] Claude FAILED for: [════════════════════════════════════════════════] Create ml_pipeline/scripts/clean_data.py — validate JSONL format, remove duplicates, detect PII (phone/email/Aadhaar regex), filter conversations < 3 turns, filter > 2048 tokens
[2026-03-08 11:41:26] [INFO] [50/71] SKIP (failed): [════════════════════════════════════════════════] Create ml_pipeline/scripts/clean_data.py — validate JSONL format, remove duplicates, detect PII (phone/email/Aadhaar regex), filter conversations < 3 turns, filter > 2048 tokens
[2026-03-08 11:41:26] [INFO] [51/71] START: [════════════════════════════════════════════════] Create ml_pipeline/scripts/check_balance.py — count by topic/length/language, report imbalances, flag categories < 10% of total
[2026-03-08 11:41:26] [INFO] Invoking Claude: [════════════════════════════════════════════════] Create ml_pipeline/scripts/check_balance.py — count by topic/length/language, report imbalances, flag categories < 10% of total
[2026-03-08 11:41:30] [ERROR] Claude FAILED for: [════════════════════════════════════════════════] Create ml_pipeline/scripts/check_balance.py — count by topic/length/language, report imbalances, flag categories < 10% of total
[2026-03-08 11:41:33] [INFO] [51/71] SKIP (failed): [════════════════════════════════════════════════] Create ml_pipeline/scripts/check_balance.py — count by topic/length/language, report imbalances, flag categories < 10% of total
[2026-03-08 11:41:33] [INFO] [52/71] START: [════════════════════════════════════════════════] Create ml_pipeline/scripts/split_data.py — stratified 60/20/20 train/val/test split by topic, output separate .jsonl files
[2026-03-08 11:41:33] [INFO] Invoking Claude: [════════════════════════════════════════════════] Create ml_pipeline/scripts/split_data.py — stratified 60/20/20 train/val/test split by topic, output separate .jsonl files
[2026-03-08 11:41:36] [ERROR] Claude FAILED for: [════════════════════════════════════════════════] Create ml_pipeline/scripts/split_data.py — stratified 60/20/20 train/val/test split by topic, output separate .jsonl files
[2026-03-08 11:41:40] [INFO] [52/71] SKIP (failed): [════════════════════════════════════════════════] Create ml_pipeline/scripts/split_data.py — stratified 60/20/20 train/val/test split by topic, output separate .jsonl files
[2026-03-08 11:41:40] [INFO] [53/71] START: [════════════════════════════════════════════════] Create ml_pipeline/scripts/evaluate_data.py — score each sample for therapeutic alignment, empathy, and safety; flag score < 0.5
[2026-03-08 11:41:40] [INFO] Invoking Claude: [════════════════════════════════════════════════] Create ml_pipeline/scripts/evaluate_data.py — score each sample for therapeutic alignment, empathy, and safety; flag score < 0.5
[2026-03-08 11:41:44] [ERROR] Claude FAILED for: [════════════════════════════════════════════════] Create ml_pipeline/scripts/evaluate_data.py — score each sample for therapeutic alignment, empathy, and safety; flag score < 0.5
[2026-03-08 11:41:47] [INFO] [53/71] SKIP (failed): [════════════════════════════════════════════════] Create ml_pipeline/scripts/evaluate_data.py — score each sample for therapeutic alignment, empathy, and safety; flag score < 0.5
[2026-03-08 11:41:47] [INFO] [54/71] START: [════════════════════════════════════════════════] Create ml_pipeline/scripts/evaluate_model.py — compute perplexity, BLEU-4, ROUGE-L on test set after training
[2026-03-08 11:41:47] [INFO] Invoking Claude: [════════════════════════════════════════════════] Create ml_pipeline/scripts/evaluate_model.py — compute perplexity, BLEU-4, ROUGE-L on test set after training
[2026-03-08 11:41:50] [ERROR] Claude FAILED for: [════════════════════════════════════════════════] Create ml_pipeline/scripts/evaluate_model.py — compute perplexity, BLEU-4, ROUGE-L on test set after training
```
