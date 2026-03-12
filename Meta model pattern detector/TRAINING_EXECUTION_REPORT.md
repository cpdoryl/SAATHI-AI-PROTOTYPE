# META-MODEL PATTERN DETECTOR - TRAINING EXECUTION REPORT

**Date Started**: 2026-03-12
**Model**: Flan-T5-large (770M parameters)
**Fine-tuning Method**: LoRA (Low-Rank Adaptation)
**Status**: TRAINING IN PROGRESS

---

## Training Pipeline Summary

### Phase 1: Data Format Conversion ✅ COMPLETE

**Script**: `Meta model pattern detector/scripts/convert_to_seq2seq_format.py`

**Input**:
- Training: `data/splits/train.jsonl` (2,100 examples)
- Validation: `data/splits/val.jsonl` (449 examples)
- Test: `data/splits/test.jsonl` (451 examples)

**Output**: Seq2Seq format JSON files in `data/seq2seq/`

**Results**:
```
TRAIN SPLIT:
  Loaded 2100 examples
  Saved 2100 examples

VAL SPLIT:
  Loaded 449 examples
  Saved 449 examples

TEST SPLIT:
  Loaded 451 examples
  Saved 451 examples

CONVERSION COMPLETE: 3000 total examples converted
```

**Seq2Seq Format**:
```json
{
  "input": "Identify all linguistic meta-model patterns in the utterance.\nOutput format: CATEGORY|SUBTYPE|MATCHED_TEXT (one pattern per line)\n\nCategories: deletion, generalization, distortion\n\nSubtypes:\n  deletion: unspecified_referential_index, unspecified_verb, comparative_deletion\n  generalization: universal_quantifiers, modal_operators_necessity, modal_operators_possibility\n  distortion: nominalization, mind_reading, cause_and_effect, complex_equivalence, presupposition\n\nUtterance: Nobody ever listens to me\n\nPatterns:",
  "output": "GENERALIZATION|universal_quantifiers|Nobody ever"
}
```

---

### Phase 2: Model Fine-Tuning 🔄 IN PROGRESS

**Script**: `Meta model pattern detector/scripts/train_flan_t5_lora.py`

**Model Configuration**:
```
Base Model: google/flan-t5-large
Parameters: 770M total
Device: CPU or GPU (auto-detected)
```

**LoRA Configuration**:
```
Rank (r): 16
LoRA Alpha: 32
Lora Dropout: 0.05
Target Modules: q, v (attention projections)
Bias: none
Expected Trainable Parameters: ~4.7M (0.61% of 770M)
```

**Training Configuration**:
```
Epochs: 5
Batch Size: 8 (per device)
Gradient Accumulation Steps: 4
Effective Batch Size: 8 * 4 = 32
Learning Rate: 3e-4 (initial)
Warmup Ratio: 0.1 (100 steps for 2100 training examples)
Optimization: AdamW with linear warmup
Max Input Length: 512 tokens
Max Output Length: 256 tokens
```

**Expected Training Time**:
- GPU (NVIDIA A100): ~45-60 minutes
- GPU (NVIDIA T4): ~2-3 hours
- CPU: ~12-16 hours

**Training Strategy**:
- Evaluation metric: Every epoch
- Save strategy: Save best (loaded at end)
- Total checkpoints saved: 3 most recent
- FP16 mixed precision: Enabled (if GPU available)
- Early stopping: Yes (via load_best_model_at_end)

**Output Directory**: `Meta model pattern detector/models/best_model/`

Contains:
- `adapter_config.json` — LoRA configuration
- `adapter_model.bin` — LoRA weights (~38 MB)
- `config.json` — Model config
- `pytorch_model.bin` — Full model weights (if merged)
- `tokenizer.json` — Tokenizer vocabulary
- `training_results.json` — Training metrics

---

### Phase 3: Model Evaluation 🔜 READY

**Script**: `Meta model pattern detector/scripts/evaluate_model.py`

**Input Data**:
- Test set: `data/splits/test.jsonl` (451 examples)
- Trained model: `models/best_model/`

**Evaluation Metrics**:

| Metric | Target | Description |
|--------|--------|-------------|
| **Exact Match** | ≥ 72% | All patterns in utterance correctly identified |
| **Category F1** | ≥ 0.85 | Macro F1 for deletion/generalization/distortion distinction |
| **Subtype F1** | ≥ 0.75 | Macro F1 for 11 pattern subtypes |
| **False Positive Rate** | < 15% | Patterns detected when none exist |

**Output Directory**: `Meta model pattern detector/results/`

Contains:
- `evaluation_results.json` — All metrics and gate status
- `test_evaluation.txt` — Human-readable report (optional)

**Expected Runtime**: 10-30 minutes on CPU

---

## Training Data Characteristics

### Dataset Overview
- **Total Examples**: 3,000 (2,100 train, 449 val, 451 test)
- **Format**: Seq2Seq instruction-response pairs
- **Pattern Categories**: 3 (deletion, generalization, distortion)
- **Pattern Subtypes**: 11 (fine-grained linguistic patterns)

### Example Training Data

**Input Instruction**:
```
Identify all linguistic meta-model patterns in the utterance.
Output format: CATEGORY|SUBTYPE|MATCHED_TEXT (one pattern per line)

Categories: deletion, generalization, distortion

Subtypes:
  deletion: unspecified_referential_index, unspecified_verb, comparative_deletion
  generalization: universal_quantifiers, modal_operators_necessity, modal_operators_possibility
  distortion: nominalization, mind_reading, cause_and_effect, complex_equivalence, presupposition

Utterance: Nobody ever listens to me and I can't talk about this

Patterns:
```

**Expected Output**:
```
GENERALIZATION|universal_quantifiers|Nobody ever
GENERALIZATION|modal_operators_possibility|can't talk about this
```

### Pattern Distribution

**By Category** (maintained across all splits):
- Deletion: 28.3% (850 examples)
- Generalization: 30.3% (910 examples)
- Distortion: 41.4% (1,240 examples)

**By Subtype** (balanced across 11 types):
- universal_quantifiers: 350 examples
- unspecified_referential_index: 350 examples
- unspecified_verb: 300 examples
- nominalization: 250 examples
- presupposition: 230 examples
- complex_equivalence: 220 examples
- mind_reading: 280 examples
- cause_and_effect: 260 examples
- modal_operators_necessity: 280 examples
- modal_operators_possibility: 280 examples
- comparative_deletion: 200 examples

---

## Training Infrastructure

### Environment Requirements
```
Python: 3.9+
PyTorch: >= 1.13.0
Transformers: >= 4.25.0
PEFT: >= 0.3.0
Datasets: >= 2.0.0
scikit-learn: >= 1.0.0
```

### Compute Resources
- **CPU Only**: 12-16 hours, 8+ GB RAM
- **GPU (T4)**: 2-3 hours, 16 GB VRAM
- **GPU (A100)**: 45-60 minutes, 40 GB VRAM
- **Estimated Peak Memory**: 4-6 GB (CPU), 8-12 GB (GPU)

### Key Features
- ✅ Mixed precision training (FP16 on GPU)
- ✅ Gradient accumulation (effective batch size 32)
- ✅ Early stopping (best model checkpoint)
- ✅ Validation every epoch
- ✅ Learning rate warmup
- ✅ Model parameter efficiency (0.61% trainable)

---

## Quality Assurance Plan

### Pre-Training Validation
- [x] Dataset generated with perfect distribution
- [x] Data splits created (70/15/15)
- [x] Zero data leakage verified
- [x] Recovery questions reviewed
- [x] Service integration complete
- [x] Training templates provided

### During Training
- [ ] Monitor training loss (should decrease)
- [ ] Monitor validation loss (should decrease)
- [ ] Check no NaN/Inf gradients
- [ ] Verify checkpoints saving

### Post-Training (Evaluation Phase)
- [ ] Training completes without errors
- [ ] Best checkpoint saved successfully
- [ ] Qualification gates verified (4 metrics)
- [ ] False positive rate assessed (< 15%)
- [ ] Recovery question quality reviewed

### Deployment Gate
- [ ] All qualification gates PASSED
- [ ] Service tested on development server
- [ ] Therapist review of 30 example detections
- [ ] Production deployment approved

---

## Next Steps

### Immediate (Upon Training Completion)
1. **Evaluate Model**: Run `evaluate_model.py` on test set (451 examples)
   - Expected time: 10-30 minutes
   - Output: evaluation_results.json with pass/fail on all 4 gates

2. **Verify Qualification Gates**:
   ```
   exact_match >= 72%
   category_f1 >= 0.85
   subtype_f1 >= 0.75
   false_positive < 15%
   ```

3. **Generate Evaluation Report**:
   - Per-category F1 scores
   - Per-subtype precision/recall
   - Confusion matrix analysis
   - Sample predictions with recovery questions

### Upon Gate Passage
4. **Deploy Model**:
   ```bash
   cp -r Meta\ model\ pattern\ detector/models/best_model/* \
     therapeutic-copilot/server/ml_models/meta_model_detector/
   ```

5. **Test Service Integration**:
   ```python
   from server.services.meta_model_detector_service import get_meta_model_detector_service
   svc = get_meta_model_detector_service()
   result = svc.detect("Nobody ever listens to me")
   print(result)  # Should contain patterns_detected list
   ```

6. **Run Smoke Tests**:
   - Test 10 diverse utterances
   - Verify pattern detection accuracy
   - Check recovery question quality
   - Confirm processing time < 200ms

### Before Production (If Gates Pass)
7. **Therapist Validation Study**:
   - Sample 30 random detections
   - Get clinical review (appropriateness, accuracy)
   - Document feedback

8. **Production Deployment**:
   - Copy model to server ml_models directory
   - Deploy updated service
   - Monitor false positive rate in production

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| **Training fails** | Checkpoint recovery, simplify batch size if OOM |
| **Model overfits** | Validation monitoring, early stopping enabled |
| **Low F1 scores** | Re-examine data quality, retrain with warmup adjustment |
| **High false positives** | Add negative examples, lower confidence threshold |
| **Slow inference** | Use LoRA adapter (38 MB vs 3 GB full model) |
| **Recovery Qs inappropriate** | Therapist validation sample before production |

---

## Files Created

### Training Scripts
- ✅ `scripts/convert_to_seq2seq_format.py` — Data format conversion
- ✅ `scripts/train_flan_t5_lora.py` — LoRA fine-tuning
- ✅ `scripts/evaluate_model.py` — Test set evaluation

### Output Files (Generated)
- ⏳ `models/best_model/` — Best checkpoint (training in progress)
- ⏳ `results/evaluation_results.json` — Metrics + gate status
- ⏳ `logs/training_*.log` — Training log

### Reference Files (Already Complete)
- ✅ `meta_model_patterns_v1.jsonl` — 3,000 examples
- ✅ `data/splits/{train,val,test}.jsonl` — Data splits
- ✅ `META_MODEL_PATTERN_DETECTOR_BUILD_GUIDE.md` — Implementation guide
- ✅ `EXECUTION_SUMMARY.md` — Build checklist

---

## Monitoring Commands

**Check files created**:
```bash
ls -lah Meta\ model\ pattern\ detector/models/best_model/
ls -lah Meta\ model\ pattern\ detector/data/seq2seq/
ls -lah Meta\ model\ pattern\ detector/results/
```

**View logs in real-time**:
```bash
tail -f Meta\ model\ pattern\ detector/logs/training_*.log
```

**Check model size** (after merge):
```bash
du -h Meta\ model\ pattern\ detector/models/best_model/
```

---

## Sign-Off

**Training Status**: 🔄 IN PROGRESS
**Phase**: Fine-tuning with Flan-T5 + LoRA (rank=16)
**Expected Completion**: 12-16 hours (CPU) or 45-60 min (GPU)
**Next Phase**: Evaluation on test set

Started: 2026-03-12 (Task ID: bwyf1eh1f)
