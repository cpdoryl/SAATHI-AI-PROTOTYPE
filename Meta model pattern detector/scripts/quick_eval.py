#!/usr/bin/env python3
"""
Meta-Model Pattern Detector - Quick-Start Evaluation Script

This script allows testing the evaluation pipeline without waiting for full training.
It can:
1. Use the best_model checkpoint (once training completes)
2. Perform a quick sanity check on model loading
3. Run evaluation on test set
4. Generate qualification gate results

Usage:
    python quick_eval.py --mode sanity     # Quick model load test
    python quick_eval.py --mode sample     # Test 10 random examples
    python quick_eval.py --mode full       # Full test set evaluation
"""

import json
import os
import sys
import torch
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List
import argparse

try:
    from transformers import AutoTokenizer, T5ForConditionalGeneration
    from peft import PeftModel
    from sklearn.metrics import f1_score
except ImportError as e:
    print(f"[ERROR] Required library missing: {e}")
    print("Install with: pip install transformers peft scikit-learn torch")
    exit(1)


def load_lora_model(model_path: str, device):
    """Load Flan-T5 base + LoRA adapter weights."""
    base_model_name = "google/flan-t5-large"
    print(f"   Loading base model: {base_model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    base_model = T5ForConditionalGeneration.from_pretrained(base_model_name)
    print(f"   Loading LoRA adapters from: {model_path}")
    model = PeftModel.from_pretrained(base_model, model_path)
    model = model.merge_and_unload()  # Merge for faster inference
    model.eval()
    model.to(device)
    return tokenizer, model


def load_jsonl(path):
    """Load JSONL file."""
    data = []
    with open(path, 'r') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line.strip()))
    return data


def build_prompt(utterance: str) -> str:
    """Build Flan-T5 input prompt."""
    prompt = """Identify all linguistic meta-model patterns in the utterance.
Output format: CATEGORY|SUBTYPE|MATCHED_TEXT (one pattern per line)

Categories: deletion, generalization, distortion

Subtypes:
  deletion: unspecified_referential_index, unspecified_verb, comparative_deletion
  generalization: universal_quantifiers, modal_operators_necessity, modal_operators_possibility
  distortion: nominalization, mind_reading, cause_and_effect, complex_equivalence, presupposition

Utterance: {utterance}

Patterns:"""
    return prompt.format(utterance=utterance)


_CATEGORY_NORM = {
    'deletion': 'deletion', 'deleted': 'deletion', 'delete': 'deletion',
    'generalization': 'generalization', 'generalized': 'generalization',
    'general': 'generalization', 'generalisation': 'generalization',
    'distortion': 'distortion', 'distorted': 'distortion', 'distort': 'distortion',
}

_SUBTYPE_NORM = {
    'unspecified_referential_index': 'unspecified_referential_index',
    'referential_index': 'unspecified_referential_index',
    'unspecified_verb': 'unspecified_verb',
    'verb': 'unspecified_verb',
    'comparative_deletion': 'comparative_deletion',
    'comparative': 'comparative_deletion',
    'universal_quantifiers': 'universal_quantifiers',
    'universal': 'universal_quantifiers',
    'modal_operators_necessity': 'modal_operators_necessity',
    'modal_necessity': 'modal_operators_necessity',
    'necessity': 'modal_operators_necessity',
    'modal_operators_possibility': 'modal_operators_possibility',
    'modal_possibility': 'modal_operators_possibility',
    'possibility': 'modal_operators_possibility',
    'nominalization': 'nominalization',
    'nominalisation': 'nominalization',
    'mind_reading': 'mind_reading',
    'mind_read': 'mind_reading',
    'cause_and_effect': 'cause_and_effect',
    'cause_effect': 'cause_and_effect',
    'complex_equivalence': 'complex_equivalence',
    'presupposition': 'presupposition',
}


def parse_pattern_output(output_text: str) -> set:
    """Parse 'CATEGORY|SUBTYPE|MATCHED_TEXT' with normalization."""
    patterns = set()
    for line in output_text.strip().split('\n'):
        line = line.strip()
        if not line or '|' not in line:
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 2:
            cat = _CATEGORY_NORM.get(parts[0].lower().strip(), parts[0].lower())
            sub = _SUBTYPE_NORM.get(parts[1].lower().strip(), parts[1].lower())
            patterns.add(f"{cat}|{sub}")
    return patterns


def sanity_check(model_path: str = "Meta model pattern detector/models/best_model") -> bool:
    """Quick sanity check - can we load the model?"""
    print("=" * 70)
    print("SANITY CHECK: Model Loading & Basic Inference")
    print("=" * 70)

    if not os.path.exists(model_path):
        print(f"\n[FAIL] Model path not found: {model_path}")
        print("Training must complete before evaluation can run.")
        return False

    try:
        print(f"\n1. Loading model from: {model_path}")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        tokenizer, model = load_lora_model(model_path, device)
        print(f"   Device: {device}")
        print(f"   [PASS] Model loaded successfully")

        print(f"\n2. Testing inference on sample utterance")
        test_utterance = "Nobody ever listens to me"
        prompt = build_prompt(test_utterance)
        inputs = tokenizer(prompt, return_tensors='pt', max_length=512, truncation=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                inputs['input_ids'],
                attention_mask=inputs['attention_mask'],
                max_length=256,
                num_beams=4,
                early_stopping=True,
                do_sample=False
            )

        prediction = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"   Input: '{test_utterance}'")
        print(f"   Output: {prediction[:100]}..." if len(prediction) > 100 else f"   Output: {prediction}")
        print(f"   [PASS] Inference successful")

        print(f"\n3. Checking model files")
        for fname in ['config.json', 'tokenizer.json']:
            fpath = os.path.join(model_path, fname)
            if os.path.exists(fpath):
                size = os.path.getsize(fpath) / 1024
                print(f"   [PASS] {fname} ({size:.1f} KB)")
            else:
                print(f"   [WARN] {fname} not found")

        print(f"\n{'=' * 70}")
        print(f"[PASS] SANITY CHECK COMPLETE - Model is ready for evaluation")
        print(f"{'=' * 70}\n")
        return True

    except Exception as e:
        print(f"\n[FAIL] Error loading model: {e}")
        print(f"Training may still be in progress. Check logs:")
        print(f"  tail -f Meta\\ model\\ pattern\\ detector/logs/training_*.log")
        return False


def sample_evaluation(
    model_path: str = "Meta model pattern detector/models/best_model",
    test_data_path: str = "Meta model pattern detector/data/splits/test.jsonl",
    num_samples: int = 10
) -> bool:
    """Quick evaluation on random sample (no training wait needed)."""

    print("=" * 70)
    print(f"SAMPLE EVALUATION: {num_samples} Random Test Examples")
    print("=" * 70)

    if not os.path.exists(model_path):
        print(f"\n[FAIL] Model not found: {model_path}")
        return False

    print(f"\n1. Loading model and tokenizer")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        tokenizer, model = load_lora_model(model_path, device)
        print(f"   Device: {device}")
        print(f"   [PASS] Model loaded")
    except Exception as e:
        print(f"   [FAIL] {e}")
        return False

    print(f"\n2. Loading test data")
    if not os.path.exists(test_data_path):
        print(f"   [FAIL] Test data not found: {test_data_path}")
        return False

    test_data = load_jsonl(test_data_path)
    print(f"   Loaded {len(test_data)} total test examples")

    # Random sample
    np.random.seed(42)
    sample_indices = np.random.choice(len(test_data), min(num_samples, len(test_data)), replace=False)
    sample_data = [test_data[i] for i in sample_indices]

    print(f"\n3. Running predictions on {len(sample_data)} samples")
    correct = 0

    for idx, example in enumerate(sample_data, 1):
        utterance = example['utterance']
        prompt = build_prompt(utterance)

        try:
            inputs = tokenizer(prompt, return_tensors='pt', max_length=512, truncation=True)
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model.generate(
                    inputs['input_ids'],
                    attention_mask=inputs['attention_mask'],
                    max_length=256,
                    num_beams=4,
                    early_stopping=True,
                    do_sample=False
                )

            pred_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            pred_patterns = parse_pattern_output(pred_text)

            # Reference patterns
            ref_patterns = set()
            for pattern in example.get('patterns', []):
                category = pattern['pattern_category'].lower()
                subtype = pattern['pattern_subtype']
                ref_patterns.add(f"{category}|{subtype}")

            is_correct = pred_patterns == ref_patterns
            if is_correct:
                correct += 1

            match_str = "[MATCH]" if is_correct else "[MISMATCH]"
            print(f"\n   Sample {idx} {match_str}")
            print(f"   Utterance: {utterance[:60]}...")
            print(f"   Reference: {ref_patterns if ref_patterns else 'NO PATTERNS'}")
            print(f"   Predicted: {pred_patterns if pred_patterns else 'NO PATTERNS'}")

        except Exception as e:
            print(f"\n   Sample {idx} [ERROR]: {e}")

    accuracy = correct / len(sample_data) if sample_data else 0
    print(f"\n{'=' * 70}")
    print(f"SAMPLE RESULTS: {correct}/{len(sample_data)} correct ({accuracy*100:.1f}%)")
    print(f"{'=' * 70}\n")

    return accuracy >= 0.5  # Basic pass threshold


def full_evaluation(
    model_path: str = "Meta model pattern detector/models/best_model",
    test_data_path: str = "Meta model pattern detector/data/splits/test.jsonl",
    output_dir: str = "Meta model pattern detector/results"
) -> bool:
    """Full test set evaluation with qualification gates."""

    print("=" * 70)
    print("FULL EVALUATION: All Test Examples (451)")
    print("=" * 70)

    if not os.path.exists(model_path):
        print(f"\n[FAIL] Model not found: {model_path}")
        return False

    print(f"\n1. Loading model and tokenizer")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        tokenizer, model = load_lora_model(model_path, device)
        print(f"   Device: {device}")
        print(f"   [PASS] Model loaded")
    except Exception as e:
        print(f"   [FAIL] {e}")
        return False

    print(f"\n2. Loading test data")
    test_data = load_jsonl(test_data_path)
    print(f"   Loaded {len(test_data)} test examples")

    print(f"\n3. Running predictions (this may take 10-30 minutes)...")

    predictions = []
    references = []
    all_pred_categories = []
    all_ref_categories = []
    all_pred_subtypes = []
    all_ref_subtypes = []

    for i, example in enumerate(test_data):
        if (i + 1) % 50 == 0:
            print(f"   Processed {i + 1}/{len(test_data)}")

        utterance = example['utterance']
        prompt = build_prompt(utterance)

        try:
            inputs = tokenizer(prompt, return_tensors='pt', max_length=512, truncation=True)
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model.generate(
                    inputs['input_ids'],
                    attention_mask=inputs['attention_mask'],
                    max_length=256,
                    num_beams=4,
                    early_stopping=True,
                    do_sample=False
                )

            pred_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            pred_patterns = parse_pattern_output(pred_text)

            # Reference patterns
            ref_patterns = set()
            for pattern in example.get('patterns', []):
                category = pattern['pattern_category'].lower()
                subtype = pattern['pattern_subtype']
                ref_patterns.add(f"{category}|{subtype}")

            predictions.append(pred_patterns)
            references.append(ref_patterns)

            # Build per-example aligned lists for F1 (use first pattern or "none")
            pred_cat = next(
                (p.split('|')[0] for p in pred_patterns if '|' in p), "none"
            )
            ref_cat = next(
                (r.split('|')[0] for r in ref_patterns if '|' in r), "none"
            )
            pred_sub = next(
                (p.split('|')[1] for p in pred_patterns if '|' in p), "none"
            )
            ref_sub = next(
                (r.split('|')[1] for r in ref_patterns if '|' in r), "none"
            )
            all_pred_categories.append(pred_cat)
            all_ref_categories.append(ref_cat)
            all_pred_subtypes.append(pred_sub)
            all_ref_subtypes.append(ref_sub)

        except Exception as e:
            print(f"   Error on example {i+1}: {e}")
            continue

    # Compute metrics
    print(f"\n4. Computing metrics...")

    exact_matches = sum(1 for p, r in zip(predictions, references) if p == r)
    exact_match_rate = exact_matches / len(predictions) if predictions else 0

    false_positives = sum(1 for p, r in zip(predictions, references) if len(p) > 0 and len(r) == 0)
    false_positive_rate = false_positives / len(predictions) if predictions else 0

    category_f1 = f1_score(
        all_ref_categories,
        all_pred_categories,
        average='macro',
        zero_division=0
    ) if all_ref_categories else 0

    subtype_f1 = f1_score(
        all_ref_subtypes,
        all_pred_subtypes,
        average='macro',
        zero_division=0
    ) if all_ref_subtypes else 0

    # Qualification gates
    gates = {
        "exact_match_rate": exact_match_rate,
        "exact_match_passed": exact_match_rate >= 0.72,
        "category_f1": category_f1,
        "category_f1_passed": category_f1 >= 0.85,
        "subtype_f1": subtype_f1,
        "subtype_f1_passed": subtype_f1 >= 0.75,
        "false_positive_rate": false_positive_rate,
        "false_positive_rate_passed": false_positive_rate < 0.15,
    }

    # Print results
    print(f"\n{'=' * 70}")
    print(f"EVALUATION RESULTS ({len(test_data)} examples)")
    print(f"{'=' * 70}")

    print(f"\nQUALIFICATION GATES:")
    print(f"\n1. Exact Match (all patterns correct):")
    status = "[PASS]" if gates["exact_match_passed"] else "[FAIL]"
    print(f"   {status} {gates['exact_match_rate']:.1%} >= 72%")

    print(f"\n2. Category F1 (deletion/generalization/distortion):")
    status = "[PASS]" if gates["category_f1_passed"] else "[FAIL]"
    print(f"   {status} {gates['category_f1']:.3f} >= 0.85")

    print(f"\n3. Subtype F1 (11 classes):")
    status = "[PASS]" if gates["subtype_f1_passed"] else "[FAIL]"
    print(f"   {status} {gates['subtype_f1']:.3f} >= 0.75")

    print(f"\n4. False Positive Rate:")
    status = "[PASS]" if gates["false_positive_rate_passed"] else "[FAIL]"
    print(f"   {status} {gates['false_positive_rate']:.1%} < 15%")

    all_passed = all([
        gates["exact_match_passed"],
        gates["category_f1_passed"],
        gates["subtype_f1_passed"],
        gates["false_positive_rate_passed"]
    ])

    print(f"\n{'=' * 70}")
    if all_passed:
        print(f"STATUS: [PASS] ALL QUALIFICATION GATES PASSED - READY FOR DEPLOYMENT")
    else:
        print(f"STATUS: [FAIL] Some qualification gates not met - RETRAINING NEEDED")
    print(f"{'=' * 70}\n")

    # Save results
    os.makedirs(output_dir, exist_ok=True)
    results = {
        "test_set_size": len(test_data),
        "exact_match_rate": float(exact_match_rate),
        "exact_match_passed": gates["exact_match_passed"],
        "category_f1": float(category_f1),
        "category_f1_passed": gates["category_f1_passed"],
        "subtype_f1": float(subtype_f1),
        "subtype_f1_passed": gates["subtype_f1_passed"],
        "false_positive_rate": float(false_positive_rate),
        "false_positive_rate_passed": gates["false_positive_rate_passed"],
        "all_gates_passed": all_passed,
    }

    results_file = os.path.join(output_dir, "evaluation_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved: {results_file}")

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Meta-Model Pattern Detector - Quick-Start Evaluation")
    parser.add_argument(
        '--mode',
        choices=['sanity', 'sample', 'full'],
        default='sanity',
        help='Evaluation mode'
    )

    args = parser.parse_args()

    if args.mode == 'sanity':
        success = sanity_check()
    elif args.mode == 'sample':
        success = sample_evaluation()
    elif args.mode == 'full':
        success = full_evaluation()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
