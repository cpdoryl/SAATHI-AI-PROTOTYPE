"""
SAATHI AI -- Crisis Model Setup Script
=======================================
Copies trained DistilBERT crisis model weights from the local training
folders into the server's crisis_model/ directory.

Supports both:
  - Phase 2 Combined: single .pt checkpoint (legacy PyTorch format)
  - Phase 3 Lower-Risk: HuggingFace model directory (model.safetensors)

Priority: Phase 3 (if available) > Phase 2 fallback

Run once after cloning the repo or after re-training:
    cd therapeutic-copilot/server
    python scripts/setup_crisis_model.py

Model files (~256MB each) are excluded from git via .gitignore.
"""

import sys
import shutil
from pathlib import Path

# -- Paths -------------------------------------------------------------------
REPO_ROOT  = Path(__file__).resolve().parents[3]   # c:/saath ai prototype
SERVER_DIR = Path(__file__).resolve().parents[1]   # therapeutic-copilot/server

TRAINING_ROOT = REPO_ROOT / "Crises detection models dataset, training and testing scripts model"

# Phase 2 -- single .pt file (legacy)
PHASE2_MODEL = TRAINING_ROOT / "phase 2" / "models" / "best_crisis_model_combined.pt"

# Phase 3 -- HuggingFace directory (model.safetensors + tokenizer files)
PHASE3_MODEL_DIR = TRAINING_ROOT / "Phase 3" / "models" / "best_model"

# Server destination directories
DEST_DIR        = SERVER_DIR / "crisis_model"
DEST_PT         = DEST_DIR / "best_crisis_model_combined.pt"       # Phase 2 legacy
DEST_HF_DIR     = DEST_DIR / "phase3_best_model"                   # Phase 3 HF format


# -- Main --------------------------------------------------------------------

def setup_phase3():
    """Copy Phase 3 HuggingFace model directory to server."""
    required_files = ["model.safetensors", "config.json", "tokenizer.json", "tokenizer_config.json"]
    missing = [f for f in required_files if not (PHASE3_MODEL_DIR / f).exists()]
    if missing:
        print(f"[WARN] Phase 3 model incomplete — missing: {missing}")
        return False

    DEST_HF_DIR.mkdir(parents=True, exist_ok=True)

    # Check if already up to date
    if (DEST_HF_DIR / "model.safetensors").exists():
        size_mb = (DEST_HF_DIR / "model.safetensors").stat().st_size // (1024 * 1024)
        print(f"[OK] Phase 3 model already present: {DEST_HF_DIR} ({size_mb} MB)")
        return True

    print("Copying Phase 3 model (HuggingFace format)...")
    print(f"  From: {PHASE3_MODEL_DIR}")
    print(f"  To  : {DEST_HF_DIR}")
    for f in PHASE3_MODEL_DIR.iterdir():
        shutil.copy2(f, DEST_HF_DIR / f.name)
    size_mb = (DEST_HF_DIR / "model.safetensors").stat().st_size // (1024 * 1024)
    print(f"[OK] Phase 3 model copied ({size_mb} MB)")
    return True


def setup_phase2():
    """Copy Phase 2 .pt file to server (fallback)."""
    if not PHASE2_MODEL.exists():
        print(f"[WARN] Phase 2 model not found: {PHASE2_MODEL}")
        return False

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    if DEST_PT.exists():
        size_mb = DEST_PT.stat().st_size // (1024 * 1024)
        print(f"[OK] Phase 2 model already present: {DEST_PT} ({size_mb} MB)")
        return True

    print("Copying Phase 2 model (.pt format)...")
    print(f"  From: {PHASE2_MODEL}")
    print(f"  To  : {DEST_PT}")
    shutil.copy2(PHASE2_MODEL, DEST_PT)
    size_mb = DEST_PT.stat().st_size // (1024 * 1024)
    print(f"[OK] Phase 2 model copied ({size_mb} MB)")
    return True


def main():
    print("=" * 60)
    print("SAATHI AI -- Crisis Model Setup")
    print("=" * 60)
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    p3_ok = setup_phase3()
    p2_ok = setup_phase2()

    if not p3_ok and not p2_ok:
        print("\n[ERROR] No crisis model found. Ensure training folders are present.")
        sys.exit(1)

    print()
    if p3_ok:
        print("Active model: Phase 3 (98.7% accuracy, 100% HR recall) -- preferred")
    else:
        print("Active model: Phase 2 fallback (40% accuracy, 100% HR recall)")

    print()
    print("Next steps:")
    print("  1. pip install -r requirements.txt  (includes torch, transformers)")
    print("  2. uvicorn main:app --reload         (model loads automatically at startup)")


if __name__ == "__main__":
    main()
