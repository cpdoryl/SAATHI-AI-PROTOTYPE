#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAATHI AI -- Safety Classifier Deployment
==========================================
Deploys trained safety classifier to server/ml_models/safety_guardrail/
and writes model_config.json for auto-discovery by safety_guardrail_service.py.

Usage:
  python 04_deploy_safety_model.py
  python 04_deploy_safety_model.py --model ./output/safety-classifier --verify
"""

import sys, io, json, shutil, time, argparse
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE        = Path(__file__).parent
REPO_ROOT   = BASE.parent
SRC_DEFAULT = BASE / "output" / "safety-classifier"
DEPLOY_TARGET = REPO_ROOT / "therapeutic-copilot" / "server" / "ml_models" / "safety_guardrail"

REQUIRED_FILES = ["config.json", "label_config.json"]
OPTIONAL_FILES = [
    "model.safetensors", "pytorch_model.bin",
    "tokenizer.json", "tokenizer_config.json",
    "special_tokens_map.json", "spm.model",
    "training_report.json", "evaluation_report.json",
]


def check_adapter(path: Path) -> dict:
    if not path.exists():
        return {"valid": False, "issues": [f"Not found: {path}"], "found": []}
    issues, found = [], []

    for req in REQUIRED_FILES:
        if (path / req).exists():
            found.append(req)
        else:
            issues.append(f"Missing required: {req}")

    for opt in OPTIONAL_FILES:
        if (path / opt).exists():
            found.append(opt)

    # Check evaluation gate
    eval_path = path / "evaluation_report.json"
    if eval_path.exists():
        rpt = json.loads(eval_path.read_text(encoding="utf-8"))
        if rpt.get("summary", {}).get("overall_pass") is True:
            found.append("  -> All evaluation gates passed [OK]")
        elif rpt.get("summary", {}).get("overall_pass") is False:
            failed = rpt["summary"].get("failed_gates", [])
            issues.append(f"Evaluation gates FAILED: {failed}")

    valid = len(issues) == 0
    return {"valid": valid, "issues": issues, "found": found}


def write_model_config(target: Path, label_cfg: dict):
    config = {
        "model_name":                "saathi-safety-classifier-v1",
        "model_type":                "deberta-v3-small-multilabel",
        "base_model":                "microsoft/deberta-v3-small",
        "adapter_path":              str(target),
        "labels":                    label_cfg.get("labels", []),
        "classification_threshold":  label_cfg.get("classification_threshold", 0.40),
        "critical_threshold":        label_cfg.get("critical_threshold", 0.30),
        "critical_labels":           label_cfg.get("critical_labels", []),
        "max_length":                256,
        "ready":                     True,
        "deployed_at":               time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "guardrail_version":         "1.0.0",
    }
    with open(target / "model_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print("  -> model_config.json written")


def deploy(src: str, target_dir: str = str(DEPLOY_TARGET), dry_run: bool = False) -> bool:
    src_path    = Path(src).resolve()
    target_path = Path(target_dir).resolve()

    print("=" * 60)
    print("SAATHI AI -- Safety Classifier Deployment")
    print("=" * 60)
    print(f"Source: {src_path}")
    print(f"Target: {target_path}")

    check = check_adapter(src_path)
    for f in check["found"]:
        print(f"  [OK] {f}")
    for issue in check["issues"]:
        prefix = "[WARN]" if "WARNING" in issue else "[ERR]"
        print(f"  {prefix} {issue}")

    if not check["valid"]:
        print("\n[FAIL] Source verification failed. Deployment aborted.")
        return False

    if dry_run:
        print("\n[Dry run] No files copied.")
        return True

    target_path.mkdir(parents=True, exist_ok=True)
    copied = []
    for f in src_path.iterdir():
        if f.is_file() and f.suffix not in [".py", ".log", ".sh"]:
            shutil.copy2(f, target_path / f.name)
            size_kb = f.stat().st_size / 1024
            print(f"  -> {f.name} ({size_kb:.1f} KB)")
            copied.append(f.name)

    # Write model_config.json
    label_cfg_path = target_path / "label_config.json"
    label_cfg = json.loads(label_cfg_path.read_text(encoding="utf-8")) if label_cfg_path.exists() else {}
    write_model_config(target_path, label_cfg)

    # Write deployment manifest
    manifest = {
        "deployed_at":    time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source":         str(src_path),
        "target":         str(target_path),
        "files_copied":   len(copied),
    }
    with open(target_path / "deployment_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Verify deployment
    verify = check_adapter(target_path)
    if verify["valid"]:
        print("  [OK] Deployment verified")
    else:
        print("  [FAIL] Deployment verification failed:")
        for issue in verify["issues"]:
            print(f"    {issue}")
        return False

    print("\n" + "=" * 60)
    print("Deployment COMPLETE")
    print("=" * 60)
    print(f"  Files: {len(copied)+2} | Location: {target_path}")
    print()
    print("Add to therapeutic-copilot/server/.env:")
    print(f"  SAFETY_GUARDRAIL_MODEL_PATH={target_path}")
    print()
    print("Restart server -- safety_guardrail_service.py will auto-load.")
    print("=" * 60)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",   default=str(SRC_DEFAULT))
    parser.add_argument("--target",  default=str(DEPLOY_TARGET))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify",  action="store_true",
                        help="Verify an existing deployment without copying")
    args = parser.parse_args()

    if args.verify:
        target_path = Path(args.target).resolve()
        check = check_adapter(target_path)
        for f in check["found"]: print(f"  [OK] {f}")
        for i in check["issues"]: print(f"  [ERR] {i}")
        verdict = "[VALID]" if check["valid"] else "[INVALID]"
        print(f"\n{verdict}")
        sys.exit(0 if check["valid"] else 1)

    ok = deploy(args.model, args.target, dry_run=args.dry_run)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
