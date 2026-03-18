#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAATHI AI -- Safety Guardrail Dataset Builder
=============================================
Reads the three raw CSV seed files, validates schema, augments with paraphrase
variants, merges into a unified training dataset, and writes train/val/test
splits in ChatML format for DeBERTa-v3-small fine-tuning.

Output labels (multi-label, non-exclusive):
  safe                      - response is appropriate, no action needed
  harmful_content           - contains harmful suggestions or content
  crisis_escalation_missing - crisis input received but no escalation in response
  hallucinated_fact         - factually incorrect claim (medication, resource, context)
  toxic_language            - stigmatising, shaming, dismissive, or abusive
  scope_violation           - AI claiming capabilities beyond its authorised scope

Usage:
  python 01_build_safety_dataset.py
  python 01_build_safety_dataset.py --out ./data --seed 42
"""

import sys, io, os, csv, json, re, random, argparse
from pathlib import Path
from typing import Dict, List, Tuple

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
BASE      = Path(__file__).parent
DATA_OUT  = BASE / "data"

CRISIS_CSV  = BASE / "safety_crisis_v1.csv"
HALLUC_CSV  = BASE / "facts_hallucination_v1.csv"
TOXIC_CSV   = BASE / "toxicity_adv_v1.csv"

# ── Label vocabulary ──────────────────────────────────────────────────────────
LABELS = [
    "safe",
    "harmful_content",
    "crisis_escalation_missing",
    "hallucinated_fact",
    "toxic_language",
    "scope_violation",
]

# ── Action -> primary label mapping ──────────────────────────────────────────
ACTION_LABEL_MAP = {
    "PASS":     ["safe"],
    "BLOCK":    [],          # derived from reason_code
    "ESCALATE": ["crisis_escalation_missing"],
    "REDACT":   ["harmful_content"],
}

REASON_LABEL_MAP = {
    "SELF_HARM_METHOD":              ["harmful_content"],
    "OVERDOSE_INSTRUCTION":          ["harmful_content"],
    "SUICIDE_METHOD":                ["harmful_content"],
    "SUICIDE_INSTRUCTIONS":          ["harmful_content"],
    "ENCOURAGES_SUICIDE":            ["harmful_content"],
    "HARMFUL_BELIEF_REINFORCEMENT":  ["harmful_content"],
    "HOPELESSNESS_REINFORCEMENT":    ["harmful_content"],
    "DISMISSES_SUICIDAL_IDEATION":   ["harmful_content"],
    "TOXIC_POSITIVITY_IN_CRISIS":    ["harmful_content"],
    "MINIMISES_DISTRESS":            ["harmful_content"],
    "PROVIDES_SELF_HARM_GUIDANCE":   ["harmful_content"],
    "MENTAL_HEALTH_STIGMA":          ["toxic_language"],
    "DISMISSES_MENTAL_ILLNESS":      ["harmful_content", "toxic_language"],
    "GUILT_INDUCING":                ["harmful_content", "toxic_language"],
    "ENCOURAGES_SUICIDAL_IDEATION":  ["harmful_content"],
    "FALSE_HOPELESS_PROGNOSIS":      ["harmful_content", "hallucinated_fact"],
    "DISCOURAGES_CRISIS_RESOURCES":  ["harmful_content"],
    "THERAPEUTIC_HOPELESSNESS":      ["harmful_content"],
    "DISMISSES_NEED_FOR_SUPPORT":    ["harmful_content"],
    "DISMISSES_MENTAL_ILLNESS":      ["harmful_content", "toxic_language"],
    "INVALID_CRISIS_NUMBER":         ["hallucinated_fact"],
    "HALLUCINATED_RESOURCE":         ["hallucinated_fact"],
    "CONTEXT_HALLUCINATION":         ["hallucinated_fact"],
    "DANGEROUS_MEDICATION_DOSAGE":   ["hallucinated_fact", "harmful_content"],
    "DANGEROUS_MEDICATION_GUIDANCE": ["hallucinated_fact", "harmful_content"],
    "DANGEROUS_DRUG_INTERACTION":    ["hallucinated_fact", "harmful_content"],
    "DANGEROUS_MEDICATION_MISINFORMATION": ["hallucinated_fact", "harmful_content"],
    "HARMFUL_MEDICATION_MYTH":       ["hallucinated_fact", "harmful_content"],
    "HARMFUL_TREATMENT_MYTH":        ["hallucinated_fact", "harmful_content"],
    "FALSE_MEDICAL_GUARANTEE":       ["hallucinated_fact"],
    "FALSE_RECOVERY_STATISTIC":      ["hallucinated_fact"],
    "FALSE_PRODUCT_CLAIM":           ["hallucinated_fact"],
    "FALSE_EFFICACY_CLAIM":          ["hallucinated_fact"],
    "INAPPROPRIATE_DIAGNOSTIC_CLAIM":["scope_violation"],
    "FALSE_CREDENTIALS_CLAIM":       ["scope_violation", "hallucinated_fact"],
    "DANGEROUS_SCOPE_CLAIM":         ["scope_violation", "harmful_content"],
    "OVERSTATED_TREATMENT_CLAIM":    ["hallucinated_fact"],
    "ATTACKS_PATIENT":               ["toxic_language"],
    "MENTAL_HEALTH_STIGMA":          ["toxic_language"],
    "COMPARATIVE_MINIMISATION":      ["toxic_language"],
    "DISMISSES_EMOTIONAL_EXPERIENCE":["toxic_language"],
    "BURDENSOMENESS_REINFORCEMENT":  ["toxic_language", "harmful_content"],
    "SOCIAL_ISOLATION_REINFORCEMENT":["toxic_language", "harmful_content"],
    "ERODES_THERAPEUTIC_ALLIANCE":   ["toxic_language"],
    "MEDICAL_CONSPIRACY":            ["toxic_language", "hallucinated_fact"],
    "ATTACKS_FOR_MENTAL_HEALTH":     ["toxic_language"],
    "DENIES_CARE_DISCRIMINATORILY":  ["toxic_language"],
    "BLAME_ATTRIBUTION":             ["toxic_language"],
    "INVALIDATES_EMOTIONAL_EXPERIENCE": ["toxic_language"],
    "STRENGTH_SHAMING":              ["toxic_language"],
    "MINIMISES_INDIVIDUAL_DISTRESS": ["toxic_language"],
    "DISMISSES_AS_ATTENTION_SEEKING":["toxic_language"],
    "ACCUSES_OF_FABRICATING":        ["toxic_language"],
    "CULTURAL_DISMISSAL_OF_CARE":    ["toxic_language"],
    "GENDER_STEREOTYPING":           ["toxic_language"],
    "MEDICATION_STIGMA":             ["toxic_language"],
    "DENIES_MENTAL_ILLNESS":         ["toxic_language", "hallucinated_fact"],
    "ATTACKS_COPING_STRATEGIES":     ["toxic_language"],
    "INDUCES_SHAME":                 ["toxic_language"],
    "GENERATIONAL_DISMISSAL":        ["toxic_language"],
    "RELIGIOUS_STIGMA":              ["toxic_language"],
    "RACIST_DISMISSAL":              ["toxic_language"],
    "WORTH_CONDITIONAL_ON_ACHIEVEMENT": ["toxic_language"],
    "THERAPEUTIC_SHAMING":           ["toxic_language"],
    "FAILURE_LABELLING":             ["toxic_language"],
    "TRAUMA_MINIMISATION":           ["toxic_language"],
    "SEVERE_PERSONAL_ATTACK":        ["toxic_language"],
}


# ── Schema validators ─────────────────────────────────────────────────────────
def validate_crisis_row(row: Dict) -> Tuple[bool, str]:
    required = {"id", "text", "context", "label", "severity", "action", "reason_code"}
    missing = required - set(row.keys())
    if missing:
        return False, f"Missing fields: {missing}"
    if not row["text"].strip():
        return False, "Empty text"
    if row["action"] not in {"PASS", "BLOCK", "ESCALATE", "REDACT"}:
        return False, f"Invalid action: {row['action']}"
    return True, "ok"


def validate_halluc_row(row: Dict) -> Tuple[bool, str]:
    required = {"id", "text", "claim_type", "is_hallucinated", "action"}
    missing = required - set(row.keys())
    if missing:
        return False, f"Missing fields: {missing}"
    if not row["text"].strip():
        return False, "Empty text"
    return True, "ok"


def validate_toxic_row(row: Dict) -> Tuple[bool, str]:
    required = {"id", "text", "toxicity_type", "severity", "action"}
    missing = required - set(row.keys())
    if missing:
        return False, f"Missing fields: {missing}"
    if not row["text"].strip():
        return False, "Empty text"
    return True, "ok"


# ── Label derivation ──────────────────────────────────────────────────────────
def derive_labels(action: str, reason_code: str) -> List[str]:
    """Derive multi-labels from action + reason_code."""
    labels = set()
    action_labels = ACTION_LABEL_MAP.get(action, [])
    labels.update(action_labels)

    reason_labels = REASON_LABEL_MAP.get(reason_code, [])
    labels.update(reason_labels)

    # PASS always includes safe
    if action == "PASS":
        labels.add("safe")
        labels.discard("harmful_content")
        labels.discard("toxic_language")
        labels.discard("hallucinated_fact")
        labels.discard("scope_violation")

    return sorted(labels) if labels else ["safe"]


def labels_to_binary(label_list: List[str]) -> Dict[str, int]:
    return {lbl: int(lbl in label_list) for lbl in LABELS}


# ── Paraphrase augmentation (rule-based, no external model needed) ────────────
PARAPHRASE_TEMPLATES = {
    # Swap first-person framing
    "I hear": ["I can hear", "I notice", "It sounds like"],
    "I am concerned": ["I am worried", "I want to flag", "I am deeply concerned"],
    "Let us": ["Let's", "We can", "I would like us to"],
    "right now": ["at this moment", "immediately", "at this point"],
    "I want to make sure": ["I need to ensure", "I want to check that", "My priority is to make sure"],
    "Please call": ["I encourage you to call", "Reach out to", "You can call"],
    "Are you safe": ["Do you feel safe", "How safe do you feel", "Are you in a safe place"],
}


def paraphrase(text: str, n: int = 1) -> List[str]:
    """Generate simple rule-based paraphrases."""
    results = []
    for _ in range(n):
        new_text = text
        keys = list(PARAPHRASE_TEMPLATES.keys())
        random.shuffle(keys)
        changed = 0
        for key in keys:
            if key.lower() in new_text.lower() and changed < 2:
                replacement = random.choice(PARAPHRASE_TEMPLATES[key])
                new_text = re.sub(re.escape(key), replacement, new_text, count=1, flags=re.IGNORECASE)
                changed += 1
        if new_text != text:
            results.append(new_text)
    return results


# ── CSV readers ───────────────────────────────────────────────────────────────
def read_csv(path: Path) -> List[Dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Unified example builder ───────────────────────────────────────────────────
def build_unified_examples(augment: bool = True, seed: int = 42) -> List[Dict]:
    random.seed(seed)
    examples = []
    stats = {"crisis": 0, "halluc": 0, "toxic": 0, "augmented": 0, "skipped": 0}

    # -- Crisis rows
    for row in read_csv(CRISIS_CSV):
        ok, msg = validate_crisis_row(row)
        if not ok:
            print(f"[SKIP] {row.get('id','?')} crisis: {msg}", file=sys.stderr)
            stats["skipped"] += 1
            continue

        labels = derive_labels(row["action"], row["reason_code"])
        ex = {
            "id":       row["id"],
            "source":   "safety_crisis",
            "text":     row["text"].strip(),
            "labels":   labels,
            "binary":   labels_to_binary(labels),
            "action":   row["action"],
            "severity": int(row.get("severity", 0)),
            "reason":   row["reason_code"],
        }
        examples.append(ex)
        stats["crisis"] += 1

        # Augment PASS examples to balance dataset
        if augment and row["action"] == "PASS":
            for para in paraphrase(row["text"], n=1):
                aug = ex.copy()
                aug["id"] = ex["id"] + "_AUG"
                aug["text"] = para
                aug["source"] = "safety_crisis_aug"
                examples.append(aug)
                stats["augmented"] += 1

    # -- Hallucination rows
    for row in read_csv(HALLUC_CSV):
        ok, msg = validate_halluc_row(row)
        if not ok:
            print(f"[SKIP] {row.get('id','?')} halluc: {msg}", file=sys.stderr)
            stats["skipped"] += 1
            continue

        is_halluc = str(row["is_hallucinated"]).lower() in {"true", "1", "yes"}
        reason = row.get("reason_code", "HALLUCINATED_FACT" if is_halluc else "ACCURATE_FACT")
        labels = ["hallucinated_fact", "harmful_content"] if is_halluc else ["safe"]

        # Scope violations
        if "scope" in reason.lower() or "diagnostic" in reason.lower() or "credential" in reason.lower():
            labels = list(set(labels + ["scope_violation"]))

        ex = {
            "id":       row["id"],
            "source":   "hallucination",
            "text":     row["text"].strip(),
            "labels":   sorted(labels),
            "binary":   labels_to_binary(labels),
            "action":   row["action"],
            "severity": int(row.get("severity", 0)),
            "reason":   reason,
        }
        examples.append(ex)
        stats["halluc"] += 1

    # -- Toxicity rows
    for row in read_csv(TOXIC_CSV):
        ok, msg = validate_toxic_row(row)
        if not ok:
            print(f"[SKIP] {row.get('id','?')} toxic: {msg}", file=sys.stderr)
            stats["skipped"] += 1
            continue

        reason = row.get("reason_code", "TOXIC")
        labels = derive_labels(row["action"], reason)
        ex = {
            "id":       row["id"],
            "source":   "toxicity",
            "text":     row["text"].strip(),
            "labels":   labels,
            "binary":   labels_to_binary(labels),
            "action":   row["action"],
            "severity": int(row.get("severity", 0)),
            "reason":   reason,
        }
        examples.append(ex)
        stats["toxic"] += 1

        if augment and row["action"] == "PASS":
            for para in paraphrase(row["text"], n=1):
                aug = ex.copy()
                aug["id"] = ex["id"] + "_AUG"
                aug["text"] = para
                aug["source"] = "toxicity_aug"
                examples.append(aug)
                stats["augmented"] += 1

    print(f"\n[OK] Loaded: crisis={stats['crisis']} halluc={stats['halluc']} toxic={stats['toxic']}")
    print(f"     Augmented: {stats['augmented']} | Skipped: {stats['skipped']}")
    print(f"     Total: {len(examples)} examples")
    return examples


# ── Label distribution reporter ───────────────────────────────────────────────
def print_label_distribution(examples: List[Dict]):
    counts = {lbl: 0 for lbl in LABELS}
    for ex in examples:
        for lbl in ex["labels"]:
            if lbl in counts:
                counts[lbl] += 1
    print("\nLabel distribution:")
    total = len(examples)
    for lbl, cnt in counts.items():
        bar = "#" * int(cnt / max(counts.values()) * 30)
        print(f"  {lbl:<30} {cnt:>4} ({cnt/total*100:.1f}%) {bar}")


# ── Train / val / test split ──────────────────────────────────────────────────
def split_dataset(examples: List[Dict], train_r=0.70, val_r=0.15, seed=42):
    random.seed(seed)
    shuffled = examples[:]
    random.shuffle(shuffled)
    n = len(shuffled)
    t1 = int(n * train_r)
    t2 = int(n * (train_r + val_r))
    return shuffled[:t1], shuffled[t1:t2], shuffled[t2:]


# ── Writers ───────────────────────────────────────────────────────────────────
def write_jsonl(examples: List[Dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"  [OK] {path.name}: {len(examples)} examples")


def write_report(examples: List[Dict], train, val, test, path: Path):
    counts = {lbl: sum(1 for e in examples if lbl in e["labels"]) for lbl in LABELS}
    report = {
        "total_examples": len(examples),
        "train": len(train),
        "val": len(val),
        "test": len(test),
        "label_counts": counts,
        "sources": {
            src: sum(1 for e in examples if e["source"] == src)
            for src in ["safety_crisis", "safety_crisis_aug", "hallucination", "toxicity", "toxicity_aug"]
        },
        "action_counts": {
            a: sum(1 for e in examples if e["action"] == a)
            for a in ["PASS", "BLOCK", "ESCALATE", "REDACT"]
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"  [OK] dataset_report.json written")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Build SAATHI safety dataset")
    parser.add_argument("--out",    default=str(DATA_OUT), help="Output directory")
    parser.add_argument("--seed",   type=int, default=42)
    parser.add_argument("--no-aug", action="store_true", help="Disable augmentation")
    args = parser.parse_args()

    out_dir = Path(args.out)

    print("=" * 60)
    print("SAATHI AI -- Safety Guardrail Dataset Builder")
    print("=" * 60)

    examples = build_unified_examples(augment=not args.no_aug, seed=args.seed)
    print_label_distribution(examples)

    train, val, test = split_dataset(examples, seed=args.seed)
    print(f"\nSplits: train={len(train)} val={len(val)} test={len(test)}")

    print("\nWriting output files...")
    write_jsonl(train, out_dir / "train.jsonl")
    write_jsonl(val,   out_dir / "val.jsonl")
    write_jsonl(test,  out_dir / "test.jsonl")
    write_jsonl(examples, out_dir / "full_dataset.jsonl")
    write_report(examples, train, val, test, out_dir / "dataset_report.json")

    print("\n[DONE] Safety dataset build complete.")
    print(f"       Files in: {out_dir}")


if __name__ == "__main__":
    main()
