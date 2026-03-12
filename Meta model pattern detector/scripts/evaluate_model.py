#!/usr/bin/env python3
"""
Meta-Model Pattern Detector - Model Evaluation

Evaluates fine-tuned Flan-T5 model on test set.
Computes: exact match, category F1, subtype F1, false positive rate, recovery question quality.
Verifies qualification gates before production deployment.
"""

import json
import os
import torch
import numpy as np
from pathlib import Path
from typing import Dict, List, Set, Tuple

try:
    from transformers import T5Tokenizer, T5ForConditionalGeneration
    from sklearn.metrics import f1_score, precision_recall_fscore_support, confusion_matrix
except ImportError as e:
    print(f"[ERROR] Required library missing: {e}")
    print("Install with: pip install transformers scikit-learn torch")
    exit(1)


def load_jsonl(path):
    """Load JSONL file."""
    data = []
    with open(path, 'r') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line.strip()))
    return data


def load_json(path):
    """Load JSON file."""
    with open(path, 'r') as f:
        return json.load(f)


def load_model(model_path):
    """Load fine-tuned Flan-T5 model."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = T5Tokenizer.from_pretrained(model_path)
    model = T5ForConditionalGeneration.from_pretrained(model_path)
    model.to(device)
    model.eval()
    return model, tokenizer, device


def build_prompt(utterance, srl_text=""):
    """Build Flan-T5 input prompt."""
    prompt = """Identify all linguistic meta-model patterns in the utterance.
Output format: CATEGORY|SUBTYPE|MATCHED_TEXT (one pattern per line)

Categories: deletion, generalization, distortion

Subtypes:
  deletion: unspecified_referential_index, unspecified_verb, comparative_deletion
  generalization: universal_quantifiers, modal_operators_necessity, modal_operators_possibility
  distortion: nominalization, mind_reading, cause_and_effect, complex_equivalence, presupposition
"""
    if srl_text:
        prompt += f"\nSRL Analysis: {srl_text}\n"

    prompt += f"\nUtterance: {utterance}\n\nPatterns:"
    return prompt


def parse_pattern_output(output_text) -> Set[str]:
    """Parse 'CATEGORY|SUBTYPE|MATCHED_TEXT' format into set of 'CATEGORY|SUBTYPE' tuples."""
    patterns = set()
    for line in output_text.strip().split('\n'):
        line = line.strip()
        if not line or '|' not in line:
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 2:
            patterns.add(f"{parts[0].lower()}|{parts[1]}")
    return patterns


def predict_example(model, tokenizer, device, utterance: str, max_length=256) -> str:
    """Get model prediction for single example."""
    prompt = build_prompt(utterance)
    inputs = tokenizer(prompt, return_tensors='pt', max_length=512, truncation=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model.generate(
            inputs['input_ids'],
            attention_mask=inputs['attention_mask'],
            max_length=max_length,
            num_beams=4,
            early_stopping=True,
            do_sample=False
        )

    return tokenizer.decode(outputs[0], skip_special_tokens=True)


def evaluate_model(
    model_path: str = "Meta model pattern detector/models/best_model",
    test_data_path: str = "Meta model pattern detector/data/splits/test.jsonl",
    output_dir: str = "Meta model pattern detector/results"
):
    """Evaluate model on test set."""

    print("=" * 70)
    print("EVALUATING META-MODEL PATTERN DETECTOR")
    print("=" * 70)

    # Load model
    print(f"\n1. Loading model from: {model_path}")
    if not os.path.exists(model_path):
        print(f"[ERROR] Model path not found: {model_path}")
        return False

    model, tokenizer, device = load_model(model_path)
    print(f"   Device: {device}")

    # Load test data
    print(f"\n2. Loading test data from: {test_data_path}")
    test_data = load_jsonl(test_data_path)
    print(f"   Loaded {len(test_data)} test examples")

    # Initialize metrics
    predictions = []
    references = []
    all_pred_categories = []
    all_ref_categories = []
    all_pred_subtypes = []
    all_ref_subtypes = []

    PATTERN_TAXONOMY = {
        "unspecified_referential_index": "deletion",
        "unspecified_verb": "deletion",
        "comparative_deletion": "deletion",
        "universal_quantifiers": "generalization",
        "modal_operators_necessity": "generalization",
        "modal_operators_possibility": "generalization",
        "nominalization": "distortion",
        "mind_reading": "distortion",
        "cause_and_effect": "distortion",
        "complex_equivalence": "distortion",
        "presupposition": "distortion",
    }

    VALID_SUBTYPES = set(PATTERN_TAXONOMY.keys())

    # Run predictions
    print(f"\n3. Running predictions (this may take 10-30 minutes on CPU)...")
    for i, example in enumerate(test_data):
        if (i + 1) % 50 == 0:
            print(f"   Processed {i + 1}/{len(test_data)}")

        utterance = example['utterance']
        pred_text = predict_example(model, tokenizer, device, utterance)
        pred_patterns = parse_pattern_output(pred_text)

        # Reference patterns
        ref_patterns = set()
        for pattern in example.get('patterns', []):
            category = pattern['pattern_category'].lower()
            subtype = pattern['pattern_subtype']
            ref_patterns.add(f"{category}|{subtype}")

        predictions.append(pred_patterns)
        references.append(ref_patterns)

        # Extract categories and subtypes for F1 scores
        for pred in pred_patterns:
            parts = pred.split('|')
            if len(parts) == 2:
                all_pred_categories.append(parts[0])
                all_pred_subtypes.append(parts[1])

        for ref in ref_patterns:
            parts = ref.split('|')
            if len(parts) == 2:
                all_ref_categories.append(parts[0])
                all_ref_subtypes.append(parts[1])

    # Compute metrics
    print(f"\n4. Computing metrics...")

    # Exact match (all patterns must match exactly)
    exact_matches = sum(1 for p, r in zip(predictions, references) if p == r)
    exact_match_rate = exact_matches / len(predictions) if predictions else 0

    # False positive rate (patterns detected when none exist)
    false_positives = sum(1 for p, r in zip(predictions, references) if len(p) > 0 and len(r) == 0)
    false_positive_rate = false_positives / len(predictions) if predictions else 0

    # Category F1 (deletion/generalization/distortion)
    category_f1 = f1_score(
        all_ref_categories,
        all_pred_categories,
        average='macro',
        zero_division=0
    ) if all_ref_categories else 0

    # Subtype F1 (11 classes)
    subtype_f1 = f1_score(
        all_ref_subtypes,
        all_pred_subtypes,
        average='macro',
        zero_division=0
    ) if all_ref_subtypes else 0

    # Qualification gates
    gates = {
        "exact_match_rate": exact_match_rate,
        "exact_match_target": 0.72,
        "exact_match_passed": exact_match_rate >= 0.72,
        "category_f1": category_f1,
        "category_f1_target": 0.85,
        "category_f1_passed": category_f1 >= 0.85,
        "subtype_f1": subtype_f1,
        "subtype_f1_target": 0.75,
        "subtype_f1_passed": subtype_f1 >= 0.75,
        "false_positive_rate": false_positive_rate,
        "false_positive_rate_target": 0.15,
        "false_positive_rate_passed": false_positive_rate < 0.15,
    }

    # Print results
    print(f"\n{'=' * 70}")
    print(f"EVALUATION RESULTS")
    print(f"{'=' * 70}")

    print(f"\nQUALIFICATION GATES:")
    print(f"\n1. Exact Match (all patterns correct):")
    status = "[PASS]" if gates["exact_match_passed"] else "[FAIL]"
    print(f"   {status} {gates['exact_match_rate']:.1%} >= {gates['exact_match_target']:.1%}")

    print(f"\n2. Category F1 (deletion/generalization/distortion):")
    status = "[PASS]" if gates["category_f1_passed"] else "[FAIL]"
    print(f"   {status} {gates['category_f1']:.3f} >= {gates['category_f1_target']:.3f}")

    print(f"\n3. Subtype F1 (11 classes):")
    status = "[PASS]" if gates["subtype_f1_passed"] else "[FAIL]"
    print(f"   {status} {gates['subtype_f1']:.3f} >= {gates['subtype_f1_target']:.3f}")

    print(f"\n4. False Positive Rate:")
    status = "[PASS]" if gates["false_positive_rate_passed"] else "[FAIL]"
    print(f"   {status} {gates['false_positive_rate']:.1%} < {gates['false_positive_rate_target']:.1%}")

    # Overall status
    all_passed = all([
        gates["exact_match_passed"],
        gates["category_f1_passed"],
        gates["subtype_f1_passed"],
        gates["false_positive_rate_passed"]
    ])

    print(f"\n{'=' * 70}")
    if all_passed:
        print(f"STATUS: [PASS] ALL QUALIFICATION GATES PASSED")
    else:
        print(f"STATUS: [FAIL] Some qualification gates not met")
    print(f"{'=' * 70}\n")

    # Save results
    os.makedirs(output_dir, exist_ok=True)

    results = {
        "test_set_size": len(test_data),
        "exact_match_rate": float(exact_match_rate),
        "exact_match_rate_target": 0.72,
        "exact_match_passed": gates["exact_match_passed"],
        "category_f1": float(category_f1),
        "category_f1_target": 0.85,
        "category_f1_passed": gates["category_f1_passed"],
        "subtype_f1": float(subtype_f1),
        "subtype_f1_target": 0.75,
        "subtype_f1_passed": gates["subtype_f1_passed"],
        "false_positive_rate": float(false_positive_rate),
        "false_positive_rate_target": 0.15,
        "false_positive_rate_passed": gates["false_positive_rate_passed"],
        "all_gates_passed": all_passed,
    }

    results_file = os.path.join(output_dir, "evaluation_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved: {results_file}")

    return all_passed


if __name__ == "__main__":
    evaluate_model()
