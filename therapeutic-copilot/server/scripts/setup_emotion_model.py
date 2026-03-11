"""
SAATHI AI -- Emotion Model Setup Script
========================================
Copies the trained emotion classifier from the training folder
to the server's ml_models directory.

Run ONCE after training completes:
    python server/scripts/setup_emotion_model.py
    (from repo root: c:/saath ai prototype/)
"""

import os
import shutil
import sys
from pathlib import Path

REPO_ROOT    = Path(__file__).resolve().parents[3]
TRAINING_DIR = (REPO_ROOT / "Emotion detection model" /
                "models" / "best_model")
SERVER_DIR   = Path(__file__).resolve().parents[1]
DEST_DIR     = SERVER_DIR / "ml_models" / "emotion_classifier"

REQUIRED_FILES = [
    "model.safetensors",
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
]


def copy_emotion_model():
    print(f"\nSource      : {TRAINING_DIR}")
    print(f"Destination : {DEST_DIR}\n")

    if not TRAINING_DIR.exists():
        print("ERROR: Training source directory not found.")
        print("  Run training first:")
        print("  python 'Emotion detection model/scripts/train_emotion_distilbert.py'")
        sys.exit(1)

    # Check required files present
    missing = [f for f in REQUIRED_FILES
               if not (TRAINING_DIR / f).exists()]
    if missing:
        print(f"ERROR: Missing required files in source: {missing}")
        sys.exit(1)

    # Copy
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    copied = []
    for item in TRAINING_DIR.iterdir():
        dest_file = DEST_DIR / item.name
        shutil.copy2(item, dest_file)
        size_mb = item.stat().st_size / (1024 * 1024)
        print(f"  Copied: {item.name} ({size_mb:.1f} MB)")
        copied.append(item.name)

    print(f"\nCopied {len(copied)} files to {DEST_DIR}")

    # Verify
    ok = all((DEST_DIR / f).exists() for f in REQUIRED_FILES)
    print(f"Verification: {'PASS' if ok else 'FAIL'}")
    if not ok:
        print("ERROR: Some required files are missing after copy.")
        sys.exit(1)

    print("\nEmotion model setup complete.")
    print("Start the server and check startup logs for:")
    print("  'Emotion classifier loaded. Path: ...'")


if __name__ == "__main__":
    copy_emotion_model()
