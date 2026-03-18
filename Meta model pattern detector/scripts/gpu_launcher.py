#!/usr/bin/env python3
"""
GPU Training Launcher - RTX 5060 Optimized
Launches training with Python 3.12 + CUDA PyTorch for maximum performance
"""

import subprocess
import sys
import os
from pathlib import Path

def check_gpu_ready():
    """Check if GPU environment is ready"""
    try:
        # Test Python 3.12 and CUDA PyTorch
        result = subprocess.run([
            "py", "-3.12", "-c",
            "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            print("GPU Environment Check:")
            for line in result.stdout.strip().split('\n'):
                print(f"  {line}")
            return "CUDA: True" in result.stdout
        else:
            print(f"GPU check failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"GPU environment error: {e}")
        return False

def main():
    print("RTX 5060 GPU TRAINING LAUNCHER")
    print("=" * 50)

    # Check GPU readiness
    if not check_gpu_ready():
        print("GPU not ready yet. Please wait for PyTorch installation to complete.")
        return False

    print("GPU Environment Ready! RTX 5060 detected.")
    print()

    print("Installing additional ML dependencies...")

    # Install ML packages
    ml_packages = ["transformers", "datasets", "peft", "accelerate"]
    for package in ml_packages:
        print(f"Installing {package}...")
        result = subprocess.run([
            "py", "-3.12", "-m", "pip", "install", package
        ], capture_output=True)

        if result.returncode == 0:
            print(f"  ✓ {package} installed")
        else:
            print(f"  ⚠ {package} installation issue")

    print()
    print("Starting GPU-accelerated training...")
    print("Expected time: 30-45 minutes (vs 4+ hours on CPU)")
    print()

    # Launch GPU training
    try:
        subprocess.run([
            "py", "-3.12", "scripts/train_gpu_continuation.py"
        ], check=True)

        print("GPU training completed successfully!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"GPU training failed: {e}")
        return False
    except KeyboardInterrupt:
        print("Training interrupted by user")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\\n🎉 GPU training completed! Model ready for deployment.")
    else:
        print("\\n⚠ Check error messages above for issues.")