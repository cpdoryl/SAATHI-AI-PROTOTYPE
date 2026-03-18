# MANUAL TRAINING EXECUTION GUIDE

**Status**: Bug fixed in both training scripts
**Error Fixed**: Dataset batch processing issue (TypeError: string indices)
**Scripts Fixed**: train_flan_t5_lora.py, train_lightweight_demo.py

---

## What Was Wrong

The original error occurred during dataset preprocessing:
```
TypeError: string indices must be integers, not 'str'
```

**Root Cause**: When using `Dataset.map(batched=True)`, the `examples` parameter is a dictionary with list values:
```python
# What we got:
{
  "input": ["utterance1", "utterance2", ...],
  "output": ["pattern1", "pattern2", ...]
}

# What the code tried to do:
[ex["input"] for ex in examples]  # WRONG - examples is a dict, not a list
```

**Solution Applied**: Check if `examples` is a dictionary (batched mode) vs list:
```python
def preprocess_function(examples, tokenizer, max_input_length=512, max_output_length=256):
    # When batched=True, examples is a dict with list values
    inputs = examples["input"] if isinstance(examples, dict) else [ex["input"] for ex in examples]
    targets = examples["output"] if isinstance(examples, dict) else [ex["output"] for ex in examples]
```

---

## Scripts Fixed

### ✅ train_flan_t5_lora.py (Line 40-43)
Production model training script - FIXED

### ✅ train_lightweight_demo.py (Line 40-43)
Demo model training script - FIXED

---

## How to Run Training Manually

### Option 1: Demo Training (Quick - 5-10 minutes)
```bash
cd "c:/saath ai prototype"
python "Meta model pattern detector/scripts/train_lightweight_demo.py"
```

### Option 2: Production Training (Full - 12-16 hours)
```bash
cd "c:/saath ai prototype"
python "Meta model pattern detector/scripts/train_flan_t5_lora.py"
```

### Option 3: Run Both (Monitor logs)
**Terminal 1 - Demo**:
```bash
cd "c:/saath ai prototype"
python "Meta model pattern detector/scripts/train_lightweight_demo.py" 2>&1 | tee "Meta model pattern detector/logs/demo_training.log"
```

**Terminal 2 - Production**:
```bash
cd "c:/saath ai prototype"
python "Meta model pattern detector/scripts/train_flan_t5_lora.py" 2>&1 | tee "Meta model pattern detector/logs/production_training.log"
```

---

## Expected Output

### Demo Training (T5-small, 200 examples, 1 epoch)
```
======================================================================
LIGHTWEIGHT DEMO TRAINING - FOR PIPELINE VALIDATION ONLY
======================================================================

Device: cpu (or cuda if GPU available)

1. Loading base model: t5-small
   Model parameters: 60.2M (demo size)

2. Loading training data (subset for demo)
   Using 200 training examples (full: 2100)
   Using 50 validation examples (full: 449)

3. Tokenizing datasets

4. Initializing Seq2SeqTrainer
   Epochs: 1
   Batch size: 4

5. Starting 1-epoch demo training...
[Training progress bar showing loss decreasing]

======================================================================
DEMO TRAINING COMPLETE
======================================================================
Final training loss: 0.XXXX
Output directory: Meta model pattern detector/models/demo_model
```

### Production Training (Flan-T5-large, 2100 examples, 5 epochs)
```
======================================================================
FLAN-T5 LoRA FINE-TUNING FOR META-MODEL PATTERN DETECTION
======================================================================

Device: cpu (or cuda if GPU available)

1. Loading base model: google/flan-t5-large
   Model parameters: 783.2M

2. Applying LoRA (rank=16)
   trainable params: 4,718,592 || all params: 787,868,672 || trainable%: 0.5989

3. Loading training data
   Loaded 2100 training examples
   Loaded 449 validation examples

4. Tokenizing datasets (max_input=512, max_output=256)

5. Initializing Seq2SeqTrainer
   Epochs: 5
   Batch size: 8

6. Starting training...
[Progress bar for Epoch 1/5]
[Progress bar for Epoch 2/5]
[Progress bar for Epoch 3/5]
[Progress bar for Epoch 4/5]
[Progress bar for Epoch 5/5]

======================================================================
TRAINING COMPLETE
======================================================================
Final training loss: 0.XXXX
Output directory: Meta model pattern detector/models/best_model
```

---

## After Training Completes

### 1. Check Demo Model Files
```bash
ls -lah "Meta model pattern detector/models/demo_model/"

# Expected files:
# - adapter_config.json (LoRA config if applicable)
# - pytorch_model.bin (trained weights)
# - tokenizer.json (tokenizer vocab)
# - training_results.json (metrics)
```

### 2. Test Demo Model
```bash
python "Meta model pattern detector/scripts/quick_eval.py" --mode sample
# Expected: Loads model successfully, runs inference on 10 examples
```

### 3. Check Production Model Files
```bash
ls -lah "Meta model pattern detector/models/best_model/"

# Expected files:
# - adapter_config.json
# - pytorch_model.bin
# - config.json
# - tokenizer.json
# - training_results.json
```

### 4. Run Full Evaluation
```bash
python "Meta model pattern detector/scripts/quick_eval.py" --mode full
# Expected: Evaluates all 451 test examples, reports 4 qualification gate metrics
```

### 5. Check Results
```bash
cat "Meta model pattern detector/results/evaluation_results.json"

# Expected:
{
  "test_set_size": 451,
  "exact_match_rate": 0.XX,
  "exact_match_passed": true/false,
  "category_f1": 0.XX,
  "category_f1_passed": true/false,
  "subtype_f1": 0.XX,
  "subtype_f1_passed": true/false,
  "false_positive_rate": 0.XX,
  "false_positive_rate_passed": true/false,
  "all_gates_passed": true/false
}
```

---

## Troubleshooting

### If Training Fails Again

**Check the log file**:
```bash
tail -100 "Meta model pattern detector/logs/training_"*.log
```

**Common Issues**:

1. **CUDA out of memory**:
   - Reduce `batch_size` in training script (from 8 to 4)
   - Or use CPU (slower but uses less memory)

2. **File not found**:
   - Verify data exists: `ls -lah "Meta model pattern detector/data/seq2seq/"`
   - Rerun conversion: `python "Meta model pattern detector/scripts/convert_to_seq2seq_format.py"`

3. **Module not found**:
   ```bash
   pip install -q peft transformers datasets scikit-learn torch
   ```

4. **Disk space**:
   ```bash
   df -h  # Check available disk space
   # Need ~8 GB for models + cache
   ```

5. **Memory**:
   ```bash
   # Check RAM usage during training
   # If too high, reduce batch_size or use gradient_checkpointing
   ```

---

## Timeline Expectations

### Demo Training (T5-small, 200 examples)
- Model download: 2-3 minutes (~300 MB)
- Tokenization: 1-2 minutes
- Training (1 epoch): 5-10 minutes
- **Total: 10-15 minutes**

### Production Training (Flan-T5-large, 2100 examples)
- Model download: 5-10 minutes (~3 GB)
- Tokenization: 5-10 minutes
- Training (5 epochs): 12-16 hours on CPU, 30-45 min on GPU
- **Total: 12-16 hours (CPU) or 45 min (GPU)**

---

## Success Checklist

### ✅ Demo Training
- [ ] Training starts without errors
- [ ] Model downloads successfully
- [ ] Epoch 1/1 runs and completes
- [ ] Loss decreases during epoch
- [ ] Model saved to models/demo_model/
- [ ] Files exist: pytorch_model.bin, tokenizer.json
- [ ] quick_eval.py --mode sample passes

### ✅ Production Training
- [ ] Flan-T5-large downloads successfully
- [ ] LoRA configuration applied
- [ ] All 5 epochs run
- [ ] Training loss decreases overall
- [ ] Best model checkpoint saved
- [ ] Model saved to models/best_model/

### ✅ Evaluation
- [ ] quick_eval.py --mode full completes
- [ ] Exact match ≥ 72%
- [ ] Category F1 ≥ 0.85
- [ ] Subtype F1 ≥ 0.75
- [ ] False positive rate < 15%
- [ ] All 4 gates PASS

---

## Next Steps

1. **Run demo training** (5-15 min):
   ```bash
   python "Meta model pattern detector/scripts/train_lightweight_demo.py"
   ```

2. **While demo trains, start production training** (run in separate terminal):
   ```bash
   python "Meta model pattern detector/scripts/train_flan_t5_lora.py"
   ```

3. **When demo finishes**, evaluate it:
   ```bash
   python "Meta model pattern detector/scripts/quick_eval.py" --mode sample
   ```

4. **When production finishes** (~16 hours), full evaluation:
   ```bash
   python "Meta model pattern detector/scripts/quick_eval.py" --mode full
   ```

5. **If gates pass**, deploy to server:
   ```bash
   cp -r "Meta model pattern detector/models/best_model/"* \
     "therapeutic-copilot/server/ml_models/meta_model_detector/"
   ```

---

**All scripts are now fixed and ready to run!**

The bug was in how batched dataset preprocessing handled examples. This is now correctly fixed in both training scripts. You can run either demo or production training manually using the commands above.
