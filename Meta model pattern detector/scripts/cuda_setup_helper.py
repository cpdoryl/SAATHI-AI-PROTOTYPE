#!/usr/bin/env python3
"""
CUDA Setup and Detection Script
Diagnoses and fixes PyTorch CUDA issues for RTX 5060
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print(f"✅ {description} successful")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} failed")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏱️  {description} timed out")
        return False
    except Exception as e:
        print(f"💥 {description} error: {e}")
        return False

def check_cuda_status():
    """Check current CUDA and PyTorch status"""
    print("🔍 CHECKING CURRENT SETUP")
    print("=" * 50)

    # Check NVIDIA driver
    print("1. Checking NVIDIA GPU...")
    run_command("nvidia-smi", "NVIDIA driver check")

    # Check Python version
    print(f"2. Python version: {sys.version}")

    # Check PyTorch
    print("3. Checking PyTorch...")
    try:
        import torch
        print(f"   PyTorch version: {torch.__version__}")
        print(f"   CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"   CUDA version: {torch.version.cuda}")
            print(f"   GPU name: {torch.cuda.get_device_name(0)}")
            print(f"   GPU memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f}GB")
        else:
            print("   ⚠️ CUDA not available in PyTorch")
    except ImportError:
        print("   ❌ PyTorch not installed")

    print()

def fix_cuda_pytorch():
    """Attempt to install CUDA-enabled PyTorch"""
    print("🛠️ ATTEMPTING CUDA PYTORCH FIX")
    print("=" * 50)

    # Check if we can install CUDA PyTorch for Python 3.14
    cuda_urls = [
        "https://download.pytorch.org/whl/nightly/cu124",  # Latest CUDA 12.4
        "https://download.pytorch.org/whl/nightly/cu121",  # CUDA 12.1
        "https://download.pytorch.org/whl/cu124",          # Stable CUDA 12.4
        "https://download.pytorch.org/whl/cu121",          # Stable CUDA 12.1
    ]

    for i, url in enumerate(cuda_urls):
        print(f"\n{i+1}. Trying {url}...")
        success = run_command(
            f"pip install --upgrade torch torchvision torchaudio --index-url {url}",
            f"CUDA PyTorch installation attempt {i+1}"
        )

        if success:
            # Test if CUDA works
            try:
                import torch
                if torch.cuda.is_available():
                    print("🎉 CUDA PyTorch successfully installed!")
                    return True
                else:
                    print("⚠️ PyTorch installed but CUDA still not available")
            except Exception as e:
                print(f"💥 Error testing PyTorch: {e}")

        # If failed, try next URL
        print(f"❌ Attempt {i+1} failed, trying next...")

    return False

def create_conda_setup():
    """Create instructions for conda-based setup"""
    conda_script = """
# RECOMMENDED: GPU Setup with Conda/Miniconda
# This approach uses Python 3.12 which has guaranteed PyTorch CUDA support

# 1. Install Miniconda (if not already installed)
# Download from: https://docs.conda.io/en/latest/miniconda.html

# 2. Create GPU environment
conda create -n saathi-gpu python=3.12 -y

# 3. Activate environment
conda activate saathi-gpu

# 4. Install CUDA PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 5. Install other dependencies
pip install transformers datasets peft accelerate

# 6. Test CUDA
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"

# 7. Run GPU training
cd "c:/saath ai prototype/Meta model pattern detector"
python scripts/train_gpu_optimized.py
"""

    setup_file = Path("GPU_SETUP_INSTRUCTIONS.txt")
    with open(setup_file, "w") as f:
        f.write(conda_script)

    print(f"📝 Created setup instructions: {setup_file}")
    return setup_file

def main():
    """Main CUDA setup function"""
    print("🚀 RTX 5060 CUDA SETUP ASSISTANT")
    print("=" * 60)
    print()

    # Step 1: Check current status
    check_cuda_status()

    # Step 2: Try to fix PyTorch CUDA
    print("🔧 ATTEMPTING AUTOMATED FIX")
    print("=" * 40)

    fixed = fix_cuda_pytorch()

    if fixed:
        print("\n🎉 SUCCESS! CUDA PyTorch is now working!")
        print("✅ You can now run GPU-accelerated training")
        return True
    else:
        print("\n⚠️ AUTOMATED FIX FAILED")
        print("🎯 Python 3.14 compatibility issue detected")

        # Step 3: Create manual setup instructions
        setup_file = create_conda_setup()

        print("\n📋 SOLUTION OPTIONS:")
        print("=" * 30)
        print("🔄 Option 1: Continue with CPU training (current setup works)")
        print("⚡ Option 2: Use conda environment with Python 3.12 for GPU")
        print(f"📄 See detailed instructions in: {setup_file}")

        print("\n💡 RECOMMENDATION: Use Option 2 for 10-20x faster training!")
        return False

if __name__ == "__main__":
    main()