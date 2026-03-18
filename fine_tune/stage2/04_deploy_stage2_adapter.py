#!/usr/bin/env python3
"""
SAATHI AI — Stage 2 Adapter Deployment
=======================================
Deploys trained Stage 2 LoRA adapter to the server's ml_models directory
and writes model_config.json for service auto-discovery.

Usage:
    python 04_deploy_stage2_adapter.py
    python 04_deploy_stage2_adapter.py --adapter ./output/qwen-lora-stage2
    python 04_deploy_stage2_adapter.py --verify
"""

import json
import shutil
import argparse
import sys
import time
from pathlib import Path

ADAPTER_SOURCE_DEFAULT = "./output/qwen-lora-stage2"
DEPLOY_TARGET = "../../therapeutic-copilot/server/ml_models/stage2_therapy_model"
BASE_MODEL_REFERENCE = "Qwen/Qwen2.5-3B-Instruct"

REQUIRED_FILES   = ["adapter_config.json"]
OPTIONAL_FILES   = [
    "adapter_model.safetensors", "adapter_model.bin",
    "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
    "training_report.json", "evaluation_report.json",
]


def check_adapter(adapter_path: Path) -> dict:
    if not adapter_path.exists():
        return {"valid": False, "issues": [f"Not found: {adapter_path}"], "found_files": []}

    issues, found_files = [], []

    for req in REQUIRED_FILES:
        if (adapter_path / req).exists():
            found_files.append(req)
        else:
            issues.append(f"Missing required: {req}")

    for opt in OPTIONAL_FILES:
        if (adapter_path / opt).exists():
            found_files.append(opt)

    # Validate LoRA rank
    cfg_path = adapter_path / "adapter_config.json"
    if cfg_path.exists():
        with open(cfg_path) as f:
            cfg = json.load(f)
        r    = cfg.get("r", "?")
        base = cfg.get("base_model_name_or_path", "?")
        found_files.append(f"  ->LoRA rank: r={r}")
        found_files.append(f"  ->Base model: {base}")
        if str(r) != "16":
            issues.append(f"WARNING: Expected LoRA r=16, got r={r}")

    # Check weights exist
    has_weights = any(
        (adapter_path / f).exists()
        for f in ["adapter_model.safetensors", "adapter_model.bin"]
    )
    if not has_weights:
        issues.append("No adapter weights found")

    # Check evaluation gate was passed
    eval_path = adapter_path / "evaluation_report.json"
    if eval_path.exists():
        with open(eval_path) as f:
            eval_report = json.load(f)
        overall = eval_report.get("summary", {}).get("overall_pass", None)
        if overall is False:
            failed = eval_report.get("summary", {}).get("failed_gate_names", [])
            issues.append(f"Evaluation gates FAILED: {failed}")
        elif overall is True:
            found_files.append("  -> Evaluation: ALL GATES PASSED [OK]")

    valid = len([i for i in issues if not i.startswith("WARNING")]) == 0
    return {"valid": valid, "issues": issues, "found_files": found_files}


def get_adapter_size(path: Path) -> str:
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    if total < 1024 * 1024:
        return f"{total/1024:.1f} KB"
    elif total < 1024**3:
        return f"{total/(1024**2):.1f} MB"
    return f"{total/(1024**3):.2f} GB"


def write_model_config(target_path: Path, adapter_cfg: dict):
    config = {
        "model_name":       "qwen-lora-stage2-saathi-v1",
        "model_type":       "peft_lora",
        "stage":            2,
        "base_model":       adapter_cfg.get("base_model_name_or_path", BASE_MODEL_REFERENCE),
        "adapter_path":     str(target_path),
        "lora_rank":        adapter_cfg.get("r", 16),
        "lora_alpha":       adapter_cfg.get("lora_alpha", 32),
        "max_new_tokens":   400,
        "temperature":      0.75,
        "top_p":            0.90,
        "top_k":            40,
        "repetition_penalty": 1.15,
        "generation_config": {"do_sample": True, "pad_token_id": None},
        "max_seq_length":   4096,
        "therapeutic_steps": 11,
        "ready": True,
    }
    with open(target_path / "model_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print("  ->model_config.json written")


def deploy(adapter_source: str, target: str = DEPLOY_TARGET, dry_run: bool = False) -> bool:
    adapter_path = Path(adapter_source).resolve()
    target_path  = Path(target).resolve()

    print("=" * 60)
    print("SAATHI AI — Stage 2 Adapter Deployment")
    print("=" * 60)
    print(f"Source: {adapter_path}")
    print(f"Target: {target_path}")

    print("\nVerifying adapter...")
    check = check_adapter(adapter_path)
    for f in check["found_files"]:
        print(f"  [OK]{f}")
    for issue in check["issues"]:
        prefix = "  [WARN]" if issue.startswith("WARNING") else "  [ERR]"
        print(f"{prefix} {issue}")

    if not check["valid"]:
        print("\n[FAIL]Adapter verification FAILED. Deployment aborted.")
        return False

    print(f"  Adapter size: {get_adapter_size(adapter_path)}")

    if dry_run:
        print("\n[Dry run] No files copied.")
        return True

    target_path.mkdir(parents=True, exist_ok=True)
    print(f"\nDeploying to {target_path}...")

    copied = []
    for src_file in adapter_path.iterdir():
        if src_file.is_file() and src_file.suffix not in [".py", ".sh", ".log"]:
            dst = target_path / src_file.name
            shutil.copy2(src_file, dst)
            copied.append(src_file.name)
            size = src_file.stat().st_size / (1024 * 1024)
            print(f"  ->{src_file.name} ({size:.2f} MB)")

    # Write model_config.json
    adapter_cfg = {}
    cfg_path = adapter_path / "adapter_config.json"
    if cfg_path.exists():
        with open(cfg_path) as f:
            adapter_cfg = json.load(f)
    write_model_config(target_path, adapter_cfg)

    # Write deployment manifest
    manifest = {
        "deployment_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "adapter_source": str(adapter_path),
        "deployment_target": str(target_path),
        "model_type": "qwen2.5-3b-instruct-lora-stage2",
        "lora_rank": adapter_cfg.get("r", 16),
        "lora_alpha": adapter_cfg.get("lora_alpha", 32),
        "base_model": adapter_cfg.get("base_model_name_or_path", BASE_MODEL_REFERENCE),
        "adapter_size": get_adapter_size(adapter_path),
        "files_copied": len(copied) + 2,
    }
    # Add training + eval summaries if available
    for report_file, key in [("training_report.json", "training"), ("evaluation_report.json", "evaluation")]:
        rpath = target_path / report_file
        if rpath.exists():
            with open(rpath) as f:
                r = json.load(f)
            manifest[f"{key}_summary"] = r.get("summary", r)
    with open(target_path / "deployment_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("  ->deployment_manifest.json")

    # Final verification
    print("\nVerifying deployment...")
    verify = check_adapter(target_path)
    if verify["valid"]:
        print("  [OK]Deployment verified")
    else:
        print("  [FAIL]Verification failed:")
        for issue in verify["issues"]:
            print(f"    {issue}")
        return False

    print("\n" + "=" * 60)
    print("Deployment COMPLETE")
    print("=" * 60)
    print(f"  Files: {len(copied) + 2} | Location: {target_path}")
    print()
    print("Add to therapeutic-copilot/server/.env:")
    print(f"  STAGE2_LORA_ADAPTER_PATH={target_path}")
    print()
    print("Restart server — it will auto-load Stage 2 adapter.")
    print("=" * 60)
    return True


def main():
    parser = argparse.ArgumentParser(description="Deploy Stage 2 LoRA adapter")
    parser.add_argument("--adapter", default=ADAPTER_SOURCE_DEFAULT)
    parser.add_argument("--target",  default=DEPLOY_TARGET)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify",  action="store_true",
                        help="Verify existing deployment without copying")
    args = parser.parse_args()

    if args.verify:
        target_path = Path(args.target).resolve()
        print(f"Verifying deployment at {target_path}...")
        check = check_adapter(target_path)
        for f in check["found_files"]:
            print(f"  [OK]{f}")
        for issue in check["issues"]:
            print(f"  [FAIL]{issue}")
        print(f"\n{'[VALID]' if check['valid'] else '[INVALID]'}")
        sys.exit(0 if check["valid"] else 1)

    success = deploy(args.adapter, args.target, args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
