#!/usr/bin/env python3
"""
Deploy Meta-Model Pattern Detector to server.

Copies trained model weights from:
  Meta model pattern detector/models/best_model/
To:
  therapeutic-copilot/server/ml_models/meta_model_detector/

Also copies recovery_questions.json from the dataset directory.

Run this AFTER training completes and evaluation passes.
Usage:
    python "Meta model pattern detector/scripts/deploy_model.py"
"""

import json
import os
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent.parent  # c:/saath ai prototype/
SOURCE_MODEL = REPO_ROOT / "Meta model pattern detector" / "models" / "best_model"
DEST_MODEL   = REPO_ROOT / "therapeutic-copilot" / "server" / "ml_models" / "meta_model_detector"
RECOVERY_Q   = REPO_ROOT / "Meta model pattern detector" / "data" / "recovery_questions.json"


def check_training_results() -> bool:
    """Verify training completed and evaluation results exist."""
    results_file = SOURCE_MODEL / "training_results.json"
    if not results_file.exists():
        print(f"[FAIL] Training results not found: {results_file}")
        print("Ensure training has completed before deploying.")
        return False

    with open(results_file) as f:
        results = json.load(f)

    final_loss = results.get("train_loss") or results.get("training_loss", None)
    print(f"[INFO] Training loss: {final_loss}")

    # LoRA training saves adapter weights, not full model
    adapter_file = SOURCE_MODEL / "adapter_model.safetensors"
    if not adapter_file.exists():
        print(f"[FAIL] Adapter weights not found in {SOURCE_MODEL}")
        return False

    size_mb = adapter_file.stat().st_size / (1024 * 1024)
    print(f"[INFO] LoRA adapter weights: {size_mb:.0f} MB")
    return True


def deploy():
    print("=" * 60)
    print("META-MODEL PATTERN DETECTOR — DEPLOYMENT")
    print("=" * 60)

    # 1. Verify training is done
    print("\n1. Checking training results...")
    if not check_training_results():
        return False

    # 2. Create destination directory
    print(f"\n2. Creating destination: {DEST_MODEL}")
    DEST_MODEL.mkdir(parents=True, exist_ok=True)

    # 3. Copy model files
    print(f"\n3. Copying model files...")
    # LoRA saves: adapter weights + tokenizer (no full model.safetensors)
    files_to_copy = [
        "adapter_config.json",
        "adapter_model.safetensors",
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "generation_config.json",
        "training_results.json",
        "README.md",
    ]

    copied = 0
    for fname in files_to_copy:
        src = SOURCE_MODEL / fname
        if src.exists():
            shutil.copy2(src, DEST_MODEL / fname)
            size_kb = src.stat().st_size / 1024
            unit = "MB" if size_kb > 1024 else "KB"
            size_disp = size_kb / 1024 if size_kb > 1024 else size_kb
            print(f"   [OK] {fname} ({size_disp:.1f} {unit})")
            copied += 1
        else:
            print(f"   [SKIP] {fname} not found")

    # 4. Copy recovery questions
    print(f"\n4. Copying recovery_questions.json...")
    if RECOVERY_Q.exists():
        shutil.copy2(RECOVERY_Q, DEST_MODEL / "recovery_questions.json")
        print(f"   [OK] recovery_questions.json")
    else:
        # Create a minimal fallback
        fallback = {
            "universal_quantifiers": [
                "Always? Is there any time when the opposite is true?",
                "Never? What would it mean if there were an exception?"
            ],
            "mind_reading": [
                "How do you know that's what they think?",
                "What evidence do you have for that belief?"
            ],
            "modal_operators_necessity": [
                "What would happen if you didn't?",
                "Who says you must?"
            ],
            "cause_and_effect": [
                "How specifically does that cause this?",
                "Is there another way to look at what's happening?"
            ],
            "nominalization": [
                "Who is [doing/experiencing] this specifically?",
                "What would it look like if you were [verb] instead?"
            ],
            "presupposition": [
                "What are you assuming here?",
                "Is that necessarily true?"
            ],
            "complex_equivalence": [
                "How does that mean that?",
                "Could it mean something else?"
            ],
            "unspecified_referential_index": [
                "Who specifically?",
                "Can you tell me more about who you mean?"
            ],
            "unspecified_verb": [
                "How specifically?",
                "What would that look like in practice?"
            ],
            "comparative_deletion": [
                "Compared to what?",
                "Worse than what or whom?"
            ],
            "modal_operators_possibility": [
                "What stops you?",
                "What would need to change for that to be possible?"
            ]
        }
        with open(DEST_MODEL / "recovery_questions.json", "w") as f:
            json.dump(fallback, f, indent=2)
        print(f"   [OK] recovery_questions.json (generated fallback)")

    # 5. Summary
    print(f"\n{'=' * 60}")
    print(f"DEPLOYMENT COMPLETE")
    print(f"{'=' * 60}")
    print(f"Model deployed to: {DEST_MODEL}")
    print(f"Files copied: {copied}")
    print(f"\nThe server will load the model on next startup.")
    print(f"MetaModelDetectorService reads from: ./ml_models/meta_model_detector/")
    return True


if __name__ == "__main__":
    success = deploy()
    exit(0 if success else 1)
