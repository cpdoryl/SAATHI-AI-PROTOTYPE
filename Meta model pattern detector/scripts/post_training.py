#!/usr/bin/env python3
"""
Post-Training Pipeline: Evaluate → Deploy

Run this after train_flan_t5_lora.py completes:
    python "Meta model pattern detector/scripts/post_training.py"

Steps:
1. Run sanity check (model loads, inference works)
2. Run full evaluation on 451 test examples
3. Check all 4 qualification gates
4. If all gates pass: deploy to server
5. Print final status report
"""

import os
import sys
import subprocess
from pathlib import Path

REPO_ROOT   = Path(__file__).parent.parent.parent
MODEL_PATH  = REPO_ROOT / "Meta model pattern detector" / "models" / "best_model"
SCRIPTS_DIR = REPO_ROOT / "Meta model pattern detector" / "scripts"


def run_step(label: str, script: str, args: list = None) -> bool:
    cmd = [sys.executable, str(SCRIPTS_DIR / script)]
    if args:
        cmd.extend(args)
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    return result.returncode == 0


def main():
    print("=" * 60)
    print("POST-TRAINING PIPELINE")
    print("=" * 60)

    if not MODEL_PATH.exists() or not (MODEL_PATH / "adapter_config.json").exists():
        print(f"\n[FAIL] Model not found at: {MODEL_PATH}")
        print("Expected: adapter_config.json + adapter_model.safetensors")
        print("Training may still be in progress.")
        sys.exit(1)

    # Step 1: Sanity check
    ok = run_step("STEP 1: Sanity Check", "quick_eval.py", ["--mode", "sanity"])
    if not ok:
        print("\n[FAIL] Sanity check failed — model may be corrupt or incomplete.")
        sys.exit(1)

    # Step 2: Full evaluation
    ok = run_step("STEP 2: Full Evaluation (451 test examples)", "quick_eval.py", ["--mode", "full"])
    if not ok:
        print("\n[FAIL] Evaluation failed qualification gates.")
        print("Consider retraining with more epochs or a larger dataset.")
        sys.exit(1)

    # Step 3: Deploy
    ok = run_step("STEP 3: Deploy to Server", "deploy_model.py")
    if not ok:
        print("\n[FAIL] Deployment failed.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("ALL STEPS COMPLETE — MODEL IS LIVE")
    print("=" * 60)
    print("\nNext: restart the FastAPI server to load the new model.")
    print("MetaModelDetectorService will auto-load on first request.")
    sys.exit(0)


if __name__ == "__main__":
    main()
