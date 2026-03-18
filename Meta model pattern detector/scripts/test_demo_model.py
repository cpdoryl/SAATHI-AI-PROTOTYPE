#!/usr/bin/env python3
"""
Test the trained demo model for Meta-Model Pattern Detector
"""

import os
import torch

def test_demo_model():
    """Test the demo model we just trained."""

    print("=" * 60)
    print("TESTING TRAINED DEMO MODEL")
    print("=" * 60)

    model_path = "Meta model pattern detector/models/demo_model"

    print(f"\n1. Checking model files in: {model_path}")
    if not os.path.exists(model_path):
        print(f"   [FAIL] Model directory not found: {model_path}")
        return False

    files = os.listdir(model_path)
    required_files = ["model.safetensors", "tokenizer.json", "config.json"]

    for req_file in required_files:
        if req_file in files:
            size = os.path.getsize(os.path.join(model_path, req_file)) / 1024 / 1024
            print(f"   [PASS] {req_file} ({size:.1f} MB)")
        else:
            print(f"   [FAIL] {req_file} missing")
            return False

    print(f"\n2. Loading model and testing inference")
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

        # Load model and tokenizer
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
        model.to(device)
        model.eval()

        print(f"   [PASS] Model loaded successfully on {device}")

        # Test inference on sample utterance
        test_utterance = "Nobody ever listens to me"
        prompt = f"""Identify all linguistic meta-model patterns in the utterance.
Output format: CATEGORY|SUBTYPE|MATCHED_TEXT (one pattern per line)

Categories: deletion, generalization, distortion

Subtypes:
  deletion: unspecified_referential_index, unspecified_verb, comparative_deletion
  generalization: universal_quantifiers, modal_operators_necessity, modal_operators_possibility
  distortion: nominalization, mind_reading, cause_and_effect, complex_equivalence, presupposition

Utterance: {test_utterance}

Patterns:"""

        inputs = tokenizer(prompt, return_tensors='pt', max_length=512, truncation=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                inputs['input_ids'],
                attention_mask=inputs['attention_mask'],
                max_length=256,
                num_beams=2,
                early_stopping=True,
                do_sample=False
            )

        prediction = tokenizer.decode(outputs[0], skip_special_tokens=True)

        print(f"   [PASS] Inference successful")
        print(f"   Input: '{test_utterance}'")
        print(f"   Output: '{prediction}'")

        # Check if output looks reasonable
        if len(prediction.strip()) > 0:
            print(f"   [PASS] Model generated non-empty output")
        else:
            print(f"   [WARN] Model generated empty output (may need more training)")

        print(f"\n3. Training results")
        results_file = os.path.join(model_path, "training_results.json")
        if os.path.exists(results_file):
            import json
            with open(results_file, 'r') as f:
                results = json.load(f)
            print(f"   Training loss: {results.get('training_loss', 'N/A'):.3f}")
            print(f"   Model type: {results.get('model', 'N/A')}")
            print(f"   Epochs: {results.get('epochs', 'N/A')}")
            print(f"   [PASS] Training results available")
        else:
            print(f"   [WARN] Training results file not found")

        print(f"\n{'=' * 60}")
        print(f"DEMO MODEL TEST: SUCCESS")
        print(f"{'=' * 60}")
        print(f"✓ Model files present and correct")
        print(f"✓ Model loads and runs inference")
        print(f"✓ Pipeline validation complete")
        print(f"\nNext step: Run production training for clinical-grade model")
        print(f"Command: python \"Meta model pattern detector/scripts/train_flan_t5_lora.py\"")

        return True

    except Exception as e:
        print(f"   [FAIL] Error testing model: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_demo_model()
    exit(0 if success else 1)