"""
ml_pipeline/scripts/split_data.py
SAATHI AI — Stratified Train / Val / Test Split

Reads a clean JSONL dataset (output of clean_data.py), classifies each
conversation by topic, and splits the data using a reproducible 60 / 20 / 20
stratified split so every topic category is proportionally represented in each
output file.

Output files are written alongside the input (or to --output-dir):
    {stem}_train.jsonl   — 60 % of each topic stratum
    {stem}_val.jsonl     — 20 % of each topic stratum
    {stem}_test.jsonl    — remaining 20 % of each topic stratum

Usage:
    python split_data.py --input data/stage1_clean.jsonl
    python split_data.py --input data/stage2_clean.jsonl --output-dir data/splits
    python split_data.py --input data/stage1_clean.jsonl \\
                         --train 0.6 --val 0.2 --test 0.2 --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

# ---------------------------------------------------------------------------
# Topic detection — identical to check_balance.py so classifications are
# consistent across the whole pipeline.
# ---------------------------------------------------------------------------

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "depression": [
        "depress", "hopeless", "worthless", "sad", "empty", "numb",
        "tearful", "crying", "low mood", "no motivation", "suicidal",
        "self-harm", "self harm", "not worth living", "nihilism",
        "anhedonia", "lost interest",
    ],
    "anxiety": [
        "anxious", "anxiety", "panic attack", "panic", "worry", "worried",
        "nervousness", "nervous", "tense", "tension", "phobia", "phobic",
        "fear", "sweating", "palpitation", "restless", "overthinking",
        "over-thinking", "catastrophize",
    ],
    "ocd": [
        "ocd", "obsessive", "compulsive", "intrusive thought", "ritual",
        "checking", "contamination", "obsession", "compulsion",
    ],
    "ptsd": [
        "ptsd", "trauma", "traumatic", "flashback", "nightmare",
        "abuse", "assault", "sexual abuse", "domestic violence",
        "accident", "re-experiencing",
    ],
    "relationship": [
        "relationship", "marriage", "arranged marriage", "divorce",
        "breakup", "partner", "spouse", "husband", "wife",
        "girlfriend", "boyfriend", "family", "parents", "in-laws",
        "loneliness", "lonely", "social isolation", "friendship",
    ],
}


def _full_text(record: dict) -> str:
    """Concatenate all message contents for topic classification."""
    return " ".join(
        msg.get("content", "")
        for msg in record.get("messages", [])
        if isinstance(msg.get("content"), str)
    )


def _detect_topic(text: str) -> str:
    """Return the first matching topic from _TOPIC_KEYWORDS, or 'other'."""
    lower = text.lower()
    for topic, keywords in _TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return topic
    return "other"


# ---------------------------------------------------------------------------
# Split logic
# ---------------------------------------------------------------------------

def _split_stratum(
    records: list[dict],
    train_frac: float,
    val_frac: float,
    rng: random.Random,
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Shuffle a single topic stratum and split into train / val / test.

    The test set receives everything not assigned to train or val so that
    rounding errors never silently drop records.

    For very small strata (< 3 records), all records go to train only.
    """
    rng.shuffle(records)
    n = len(records)

    if n < 3:
        # Too small to split meaningfully — keep everything in train
        logger.warning(
            "Stratum has only {} record(s) — assigning all to train.", n
        )
        return records[:], [], []

    n_train = max(1, round(n * train_frac))
    n_val = max(1, round(n * val_frac))

    # Ensure test gets at least 1 record when n >= 3
    if n_train + n_val >= n:
        n_val = max(0, n - n_train - 1)

    train = records[:n_train]
    val = records[n_train : n_train + n_val]
    test = records[n_train + n_val :]

    return train, val, test


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SplitStats:
    total_read: int = 0
    skipped: int = 0
    topic_counts: dict[str, int] = field(default_factory=dict)
    train_count: int = 0
    val_count: int = 0
    test_count: int = 0
    train_path: Path = field(default=Path())
    val_path: Path = field(default=Path())
    test_path: Path = field(default=Path())

    def summary(self) -> str:
        total_out = self.train_count + self.val_count + self.test_count
        lines = [
            "=" * 60,
            "SAATHI AI — DATASET SPLIT SUMMARY",
            f"Total records read   : {self.total_read}",
            f"Skipped (bad format) : {self.skipped}",
            f"Total split          : {total_out}",
            "-" * 60,
            "  TOPIC DISTRIBUTION (input)",
        ]
        for topic, cnt in sorted(self.topic_counts.items()):
            pct = cnt / self.total_read * 100 if self.total_read else 0.0
            lines.append(f"    {topic:<22} {cnt:>5}  ({pct:5.1f}%)")
        lines += [
            "-" * 60,
            f"  Train  : {self.train_count:>5}  ({self.train_path})",
            f"  Val    : {self.val_count:>5}  ({self.val_path})",
            f"  Test   : {self.test_count:>5}  ({self.test_path})",
            "=" * 60,
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_read": self.total_read,
            "skipped": self.skipped,
            "topic_counts": self.topic_counts,
            "splits": {
                "train": {"count": self.train_count, "path": str(self.train_path)},
                "val": {"count": self.val_count, "path": str(self.val_path)},
                "test": {"count": self.test_count, "path": str(self.test_path)},
            },
        }


# ---------------------------------------------------------------------------
# Core split pipeline
# ---------------------------------------------------------------------------

def split_dataset(
    input_path: Path,
    output_dir: Path,
    train_frac: float,
    val_frac: float,
    seed: int,
) -> SplitStats:
    """
    Load all valid records from input_path, stratify by topic, split, and
    write three output JSONL files.

    Algorithm:
      1. Parse every line; skip malformed records with a warning.
      2. Classify each record by topic using keyword matching.
      3. Group records by topic into strata.
      4. For each stratum: shuffle (RNG seeded per-topic for reproducibility),
         then allocate floor(n * train_frac) to train, floor(n * val_frac) to
         val, remainder to test.
      5. Concatenate all strata's splits; shuffle each output split once more
         so topics are interleaved rather than grouped.
      6. Write to {stem}_train.jsonl / _val.jsonl / _test.jsonl.
    """
    rng = random.Random(seed)
    stats = SplitStats()

    # ── 1. Load records ────────────────────────────────────────────────────
    strata: dict[str, list[dict]] = defaultdict(list)

    with input_path.open("r", encoding="utf-8") as fin:
        for line_no, raw_line in enumerate(fin, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                logger.warning("Line {}: JSON parse error — {} (skipping)", line_no, exc)
                stats.skipped += 1
                continue

            if not isinstance(record.get("messages"), list) or not record["messages"]:
                logger.warning(
                    "Line {}: missing or empty 'messages' list (skipping)", line_no
                )
                stats.skipped += 1
                continue

            stats.total_read += 1
            topic = _detect_topic(_full_text(record))
            strata[topic].append(record)

    if stats.total_read == 0:
        logger.error("No valid records found in {}.", input_path)
        return stats

    stats.topic_counts = {t: len(v) for t, v in sorted(strata.items())}
    logger.info(
        "Loaded {} records across {} topic(s): {}",
        stats.total_read,
        len(strata),
        stats.topic_counts,
    )

    # ── 2. Stratified split per topic ──────────────────────────────────────
    train_all: list[dict] = []
    val_all: list[dict] = []
    test_all: list[dict] = []

    for topic, records in sorted(strata.items()):
        # Seed per-topic so each stratum is independently reproducible
        topic_rng = random.Random(seed ^ hash(topic) & 0xFFFFFFFF)
        tr, va, te = _split_stratum(records, train_frac, val_frac, topic_rng)
        logger.debug(
            "  topic={:12s}  total={:4d}  train={:4d}  val={:4d}  test={:4d}",
            topic, len(records), len(tr), len(va), len(te),
        )
        train_all.extend(tr)
        val_all.extend(va)
        test_all.extend(te)

    # ── 3. Interleave topics in each split (final shuffle) ─────────────────
    rng.shuffle(train_all)
    rng.shuffle(val_all)
    rng.shuffle(test_all)

    stats.train_count = len(train_all)
    stats.val_count = len(val_all)
    stats.test_count = len(test_all)

    # ── 4. Write output files ──────────────────────────────────────────────
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem  # e.g. "stage1_clean"

    train_path = output_dir / f"{stem}_train.jsonl"
    val_path = output_dir / f"{stem}_val.jsonl"
    test_path = output_dir / f"{stem}_test.jsonl"

    stats.train_path = train_path
    stats.val_path = val_path
    stats.test_path = test_path

    def _write(path: Path, records: list[dict]) -> None:
        with path.open("w", encoding="utf-8") as fout:
            for rec in records:
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
        logger.info("Wrote {:>5} records → {}", len(records), path)

    _write(train_path, train_all)
    _write(val_path, val_all)
    _write(test_path, test_all)

    return stats


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SAATHI AI — Stratified 60/20/20 train/val/test split by topic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        type=Path,
        help="Path to clean JSONL dataset (output of clean_data.py)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "Directory for output .jsonl files. "
            "Defaults to the same directory as --input."
        ),
    )
    parser.add_argument(
        "--train",
        type=float,
        default=0.60,
        metavar="FRAC",
        help="Fraction of data for training set (default: 0.60)",
    )
    parser.add_argument(
        "--val",
        type=float,
        default=0.20,
        metavar="FRAC",
        help="Fraction of data for validation set (default: 0.20)",
    )
    parser.add_argument(
        "--test",
        type=float,
        default=0.20,
        metavar="FRAC",
        help=(
            "Fraction of data for test set. Informational only — test always "
            "receives the remainder after train+val (default: 0.20)"
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible splits (default: 42)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        metavar="FILE",
        help="Optional path to write a JSON split report",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Loguru log level (default: INFO)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Configure Loguru
    logger.remove()
    logger.add(sys.stderr, level=args.log_level, colorize=True)

    input_path: Path = args.input
    if not input_path.exists():
        logger.error("Input file not found: {}", input_path)
        return 1

    # Validate fractions
    train_frac: float = args.train
    val_frac: float = args.val
    if not (0 < train_frac < 1) or not (0 < val_frac < 1):
        logger.error(
            "--train and --val must each be between 0 and 1, got {} and {}",
            train_frac, val_frac,
        )
        return 1
    if train_frac + val_frac >= 1.0:
        logger.error(
            "--train + --val must be < 1.0 (test receives the remainder), "
            "got {} + {} = {}",
            train_frac, val_frac, train_frac + val_frac,
        )
        return 1

    output_dir: Path = args.output_dir if args.output_dir else input_path.parent

    logger.info(
        "Splitting '{}' → train={:.0%} / val={:.0%} / test={:.0%}  seed={}",
        input_path.name,
        train_frac,
        val_frac,
        1.0 - train_frac - val_frac,
        args.seed,
    )

    stats = split_dataset(
        input_path=input_path,
        output_dir=output_dir,
        train_frac=train_frac,
        val_frac=val_frac,
        seed=args.seed,
    )

    if stats.total_read == 0:
        return 1

    logger.info("\n{}", stats.summary())

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("w", encoding="utf-8") as f:
            json.dump(stats.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info("JSON report written to: {}", args.report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
