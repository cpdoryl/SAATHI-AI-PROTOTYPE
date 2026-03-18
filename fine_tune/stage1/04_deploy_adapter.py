#!/usr/bin/env python3
"""
SAATHI AI — Stage 1 Adapter Deployment Script
==============================================
Copies trained LoRA adapter weights to the server's ml_models directory
and verifies the deployment.

Usage:
    python 04_deploy_adapter.py
    python 04_deploy_adapter.py --adapter ./output/qwen-lora-stage1
    python 04_deploy_adapter.py --adapter ./output/qwen-lora-stage1 --verify

After deployment, the adapter is available at:
    ../../therapeutic-copilot/server/ml_models/stage1_sales_model/
"""

import json
import shutil
import argparse
import sys
from pathlib import Path


# ─── Deployment Configuration ──────────────────────────────────────────────────

ADAPTER_SOURCE_DEFAULT = "./output/qwen-lora-stage1"
DEPLOY_TARGET = "../../therapeutic-copilot/server/ml_models/stage1_sales_model"

# Required files that must be present in the adapter
REQUIRED_FILES = [
    "adapter_config.json",
]

# Optional files (present if tokenizer was saved alongside adapter)
OPTIONAL_FILES = [
    "adapter_model.safetensors",
    "adapter_model.bin",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.json",
    "merges.txt",
    "training_report.json",
    "evaluation_report.json",
]

# Tokenizer fallback: if not in adapter, save reference to base model
BASE_MODEL_REFERENCE = "Qwen/Qwen2.5-7B-Instruct"


def check_adapter(adapter_path: Path) -> dict:
    """Verify adapter directory is valid before deployment."""
    issues = []
    found_files = []

    if not adapter_path.exists():
        return {
            "valid": False,
            "issues": [f"Adapter path does not exist: {adapter_path}"],
            "found_files": [],
        }

    for req in REQUIRED_FILES:
        if (adapter_path / req).exists():
            found_files.append(req)
        else:
            issues.append(f"Missing required file: {req}")

    for opt in OPTIONAL_FILES:
        if (adapter_path / opt).exists():
            found_files.append(opt)

    # Check adapter config is valid
    config_path = adapter_path / "adapter_config.json"
    if config_path.exists():
        with open(config_path) as f:
            cfg = json.load(f)
        r = cfg.get("r", "?")
        base = cfg.get("base_model_name_or_path", "?")
        found_files.append(f"  → LoRA rank: r={r}")
        found_files.append(f"  → Base model: {base}")

        if str(r) != "8":
            issues.append(f"WARNING: Expected LoRA r=8, got r={r}")

    # Check for model weights
    has_weights = any(
        (adapter_path / f).exists()
        for f in ["adapter_model.safetensors", "adapter_model.bin"]
    )
    if not has_weights:
        issues.append("No adapter weights found (adapter_model.safetensors or .bin)")

    return {
        "valid": len([i for i in issues if not i.startswith("WARNING")]) == 0,
        "issues": issues,
        "found_files": found_files,
    }


def get_adapter_size(adapter_path: Path) -> str:
    """Get total size of adapter files."""
    total_bytes = sum(
        f.stat().st_size
        for f in adapter_path.rglob("*")
        if f.is_file()
    )
    if total_bytes < 1024 * 1024:
        return f"{total_bytes / 1024:.1f} KB"
    elif total_bytes < 1024 * 1024 * 1024:
        return f"{total_bytes / (1024 * 1024):.1f} MB"
    return f"{total_bytes / (1024 * 1024 * 1024):.2f} GB"


def create_deployment_manifest(
    adapter_path: Path,
    target_path: Path,
    adapter_check: dict,
) -> dict:
    """Create deployment manifest for audit trail."""
    import time

    # Read adapter config
    cfg = {}
    config_path = adapter_path / "adapter_config.json"
    if config_path.exists():
        with open(config_path) as f:
            cfg = json.load(f)

    # Read training report if available
    training_report = {}
    report_path = adapter_path / "training_report.json"
    if report_path.exists():
        with open(report_path) as f:
            training_report = json.load(f)

    # Read evaluation report if available
    eval_report = {}
    eval_path = adapter_path / "evaluation_report.json"
    if eval_path.exists():
        with open(eval_path) as f:
            eval_report = json.load(f)

    return {
        "deployment_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "adapter_source": str(adapter_path.resolve()),
        "deployment_target": str(target_path.resolve()),
        "model_type": "qwen2.5-7b-instruct-lora-stage1",
        "lora_rank": cfg.get("r", 8),
        "lora_alpha": cfg.get("lora_alpha", 16),
        "base_model": cfg.get("base_model_name_or_path", BASE_MODEL_REFERENCE),
        "target_modules": cfg.get("target_modules", []),
        "adapter_size": get_adapter_size(adapter_path),
        "training_report": training_report,
        "evaluation_summary": eval_report.get("summary", {}),
        "deployment_files": [f.name for f in target_path.iterdir() if f.is_file()],
        "service_config": {
            "model_path": str(target_path),
            "base_model": cfg.get("base_model_name_or_path", BASE_MODEL_REFERENCE),
            "max_new_tokens": 300,
            "temperature": 0.8,
            "top_p": 0.92,
            "top_k": 50,
            "repetition_penalty": 1.1,
        },
    }


def update_server_config(target_path: Path):
    """
    Write a model_config.json to the target directory so the
    LoRA service can discover the adapter automatically.
    """
    config = {
        "model_name": "qwen-lora-stage1-saathi-v1",
        "model_type": "peft_lora",
        "stage": 1,
        "base_model": BASE_MODEL_REFERENCE,
        "adapter_path": str(target_path),
        "lora_rank": 8,
        "lora_alpha": 16,
        "max_new_tokens": 300,
        "temperature": 0.8,
        "top_p": 0.92,
        "top_k": 50,
        "repetition_penalty": 1.1,
        "generation_config": {
            "do_sample": True,
            "pad_token_id": None,   # Set at runtime from tokenizer
        },
        "ready": True,
    }
    with open(target_path / "model_config.json", "w") as f:
        json.dump(config, f, indent=2)
    print(f"  → model_config.json written")


def deploy(adapter_source: str, target: str = DEPLOY_TARGET, dry_run: bool = False) -> bool:
    adapter_path = Path(adapter_source).resolve()
    target_path  = Path(target).resolve()

    print("=" * 60)
    print("SAATHI AI — Stage 1 Adapter Deployment")
    print("=" * 60)
    print(f"Source:  {adapter_path}")
    print(f"Target:  {target_path}")

    # ── Verify adapter ────────────────────────────────────────────────────────
    print("\nVerifying adapter...")
    check = check_adapter(adapter_path)
    for f in check["found_files"]:
        print(f"  ✓ {f}")
    for issue in check["issues"]:
        prefix = "  ⚠" if issue.startswith("WARNING") else "  ✗"
        print(f"{prefix} {issue}")

    if not check["valid"]:
        print(f"\n✗ Adapter verification FAILED. Deployment aborted.")
        return False

    print(f"  Adapter size: {get_adapter_size(adapter_path)}")

    if dry_run:
        print("\n[Dry run] No files copied.")
        return True

    # ── Create target directory ───────────────────────────────────────────────
    target_path.mkdir(parents=True, exist_ok=True)
    print(f"\nDeploying to {target_path}...")

    # ── Copy files ────────────────────────────────────────────────────────────
    copied = []
    for src_file in adapter_path.iterdir():
        if src_file.is_file() and src_file.suffix not in [".py", ".sh", ".log"]:
            dst = target_path / src_file.name
            shutil.copy2(src_file, dst)
            copied.append(src_file.name)
            size = src_file.stat().st_size / (1024 * 1024)
            print(f"  → {src_file.name} ({size:.2f} MB)")

    # ── Write model_config.json ───────────────────────────────────────────────
    update_server_config(target_path)

    # ── Write deployment manifest ─────────────────────────────────────────────
    manifest = create_deployment_manifest(adapter_path, target_path, check)
    manifest_path = target_path / "deployment_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  → deployment_manifest.json")

    # ── Verify deployment ─────────────────────────────────────────────────────
    print("\nVerifying deployment...")
    deploy_check = check_adapter(target_path)
    if deploy_check["valid"]:
        print("  ✓ Deployment verified")
    else:
        print("  ✗ Deployment verification failed:")
        for issue in deploy_check["issues"]:
            print(f"    {issue}")
        return False

    # ── Print server startup note ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Deployment complete!")
    print("=" * 60)
    print(f"  Files copied: {len(copied) + 2}")
    print(f"  Location: {target_path}")
    print()
    print("Server will load this adapter automatically on next startup.")
    print("Environment variable to set (in .env):")
    print(f"  STAGE1_LORA_ADAPTER_PATH={target_path}")
    print()
    print("To test the deployment:")
    print("  python 03_evaluate_stage1.py --adapter " + str(target_path))
    print("=" * 60)

    return True


def main():
    parser = argparse.ArgumentParser(description="Deploy Stage 1 LoRA adapter")
    parser.add_argument("--adapter", default=ADAPTER_SOURCE_DEFAULT,
                        help=f"Source adapter directory (default: {ADAPTER_SOURCE_DEFAULT})")
    parser.add_argument("--target", default=DEPLOY_TARGET,
                        help=f"Deployment target (default: {DEPLOY_TARGET})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Verify without copying files")
    parser.add_argument("--verify", action="store_true",
                        help="Verify existing deployment at target")
    args = parser.parse_args()

    if args.verify:
        target_path = Path(args.target).resolve()
        print(f"Verifying existing deployment at {target_path}...")
        check = check_adapter(target_path)
        for f in check["found_files"]:
            print(f"  ✓ {f}")
        for issue in check["issues"]:
            print(f"  ✗ {issue}")
        print(f"\n{'✓ VALID' if check['valid'] else '✗ INVALID'}")
        sys.exit(0 if check["valid"] else 1)

    success = deploy(
        adapter_source=args.adapter,
        target=args.target,
        dry_run=args.dry_run,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
