# WATCHER STATUS

**Updated**: 2026-03-09 07:50:05
**Status**:  IN PROGRESS -- 58 done, 11 remaining

## Progress

- Tasks completed : 58 / 12
- Last task       : `None`

## Details

**Just completed**: `[P5-ML] Create ml_pipeline/scripts/evaluate_model.py — compute perplexity, BLEU-4, ROUGE-L on test set after training`

**Up next**: `[P5-ML] Create ml_pipeline/scripts/merge_lora.py — merge trained LoRA adapter into base Qwen 2.5-7B model for GGUF conversion`

## Recent Log

```
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
[2026-03-09 07:39:09] [INFO] Cooldown 60s before next task (token budget recovery)...
[2026-03-09 07:40:09] [INFO] [4/16] START: [P5-ML] Create ml_pipeline/scripts/evaluate_data.py — score each sample for therapeutic alignment, empathy, and safety; flag score < 0.5
[2026-03-09 07:40:09] [INFO] Invoking Claude: [P5-ML] Create ml_pipeline/scripts/evaluate_data.py — score each sample for therapeutic alignment, empathy, and safety; flag score < 0.5
[2026-03-09 07:44:51] [INFO] [4/16] DONE: [P5-ML] Create ml_pipeline/scripts/evaluate_data.py — score each sample for therapeutic alignment, empathy, and safety; flag score < 0.5
[2026-03-09 07:44:55] [INFO] Cooldown 60s before next task (token budget recovery)...
[2026-03-09 07:45:55] [INFO] [5/16] START: [P5-ML] Create ml_pipeline/scripts/evaluate_model.py — compute perplexity, BLEU-4, ROUGE-L on test set after training
[2026-03-09 07:45:55] [INFO] Invoking Claude: [P5-ML] Create ml_pipeline/scripts/evaluate_model.py — compute perplexity, BLEU-4, ROUGE-L on test set after training
[2026-03-09 07:50:05] [INFO] [5/16] DONE: [P5-ML] Create ml_pipeline/scripts/evaluate_model.py — compute perplexity, BLEU-4, ROUGE-L on test set after training
```
