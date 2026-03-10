"""
SAATHI AI — Crisis Model Setup Script
=======================================
Copies the trained DistilBERT crisis model weights from the local
training folder into the server's crisis_model/ directory.

Run once after cloning the repo or after re-training:
    cd therapeutic-copilot/server
    python scripts/setup_crisis_model.py

The model file (~256MB) is excluded from git via .gitignore.
"""

import sys
import shutil
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parents[3]   # c:/saath ai prototype
SERVER_DIR = Path(__file__).resolve().parents[1]   # therapeutic-copilot/server

SOURCE_MODEL = (
    REPO_ROOT
    / "Crises detection models dataset, training and testing scripts model"
    / "phase 2"
    / "models"
    / "best_crisis_model_combined.pt"
)

DEST_DIR   = SERVER_DIR / "crisis_model"
DEST_MODEL = DEST_DIR / "best_crisis_model_combined.pt"

# ── Main ──────────────────────────────────────────────────────────────────

def main():
    if not SOURCE_MODEL.exists():
        print(f"[ERROR] Source model not found:\n  {SOURCE_MODEL}")
        print("Ensure the 'Crises detection models dataset...' folder is present.")
        sys.exit(1)

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    if DEST_MODEL.exists():
        size_mb = DEST_MODEL.stat().st_size // (1024 * 1024)
        print(f"[OK] Model already present at:\n  {DEST_MODEL} ({size_mb} MB)")
        return

    print(f"Copying crisis model weights...")
    print(f"  From: {SOURCE_MODEL}")
    print(f"  To  : {DEST_MODEL}")
    shutil.copy2(SOURCE_MODEL, DEST_MODEL)
    size_mb = DEST_MODEL.stat().st_size // (1024 * 1024)
    print(f"[OK] Model copied successfully ({size_mb} MB)")
    print()
    print("Next step: the server will automatically load the model on startup.")
    print("Base model (distilbert-base-uncased, ~67MB) downloads from HuggingFace")
    print("on first inference run and is then cached locally.")

if __name__ == "__main__":
    main()
