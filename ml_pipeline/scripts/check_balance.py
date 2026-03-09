"""
ml_pipeline/scripts/check_balance.py
SAATHI AI — Training Dataset Balance Checker

Counts conversations by topic, length bucket, and language.
Reports imbalances and flags every category that falls below 10% of its
dimension total — so training data is not skewed before fine-tuning begins.

Usage:
    python check_balance.py --input data/stage1_clean.jsonl
    python check_balance.py --input data/stage2_clean.jsonl --threshold 0.10
    python check_balance.py --input data/stage2_clean.jsonl \
                            --report balance_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

# ---------------------------------------------------------------------------
# Topic detection — keyword-based classifier
# ---------------------------------------------------------------------------

# Each topic maps to a set of lower-cased keywords / phrases.
# Evaluation order matters: the FIRST matching topic wins.
# "other" is the fallback when nothing matches.
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

# Hinglish signal words — common Hindi words transliterated to Latin script.
# Presence of ≥ _HINGLISH_THRESHOLD of these tokens in the conversation
# indicates Hinglish / code-switched content.
_HINGLISH_WORDS: frozenset[str] = frozenset(
    [
        "aur", "hai", "hain", "nahi", "nhi", "kya", "kyun", "kyu",
        "kaise", "kaisa", "bohot", "bahut", "thoda", "zyada", "zyadha",
        "accha", "achha", "theek", "theek hai", "matlab", "samajh",
        "samajhna", "baat", "log", "ghar", "kaam", "dost", "yaar",
        "bhi", "toh", "to", "mujhe", "mera", "meri", "apna", "apni",
        "unka", "unki", "uska", "uski", "hum", "aap", "tum", "woh",
        "ye", "yeh", "iss", "iska", "iski", "isliye", "lekin",
        "lakin", "phir", "phr", "abhi", "abhi bhi", "pehle", "baad",
        "din", "raat", "subah", "kal", "aaj", "sirf", "bilkul",
        "shukriya", "dhanyawad", "pareshaan", "takleef", "dukh",
        "khushi", "dar", "dard",
    ]
)

# Fraction of total whitespace-delimited tokens that must be Hinglish words
# for the conversation to be classified as "hinglish".
_HINGLISH_THRESHOLD: float = 0.05


def _detect_topic(text: str) -> str:
    """
    Return the first matching topic from _TOPIC_KEYWORDS, or 'other'.

    Converts text to lower-case before matching so keywords are
    case-insensitive.
    """
    lower = text.lower()
    for topic, keywords in _TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return topic
    return "other"


def _detect_language(text: str) -> str:
    """
    Classify conversation language as 'english', 'hinglish', or 'mixed'.

    Algorithm:
      1. Tokenise on whitespace.
      2. Count how many tokens appear in _HINGLISH_WORDS.
      3. hinglish_ratio = hinglish_token_count / total_tokens
      4. If ratio >= _HINGLISH_THRESHOLD  → 'hinglish'
         Else if any non-ASCII character exists → 'mixed'
         Else → 'english'

    'mixed' covers Devanagari / other scripts embedded in text.
    """
    tokens = text.lower().split()
    if not tokens:
        return "english"

    hinglish_count = sum(1 for t in tokens if t.strip(".,!?\"'();:") in _HINGLISH_WORDS)
    hinglish_ratio = hinglish_count / len(tokens)

    if hinglish_ratio >= _HINGLISH_THRESHOLD:
        return "hinglish"

    # Check for non-ASCII characters (Devanagari, etc.)
    if any(ord(ch) > 127 for ch in text):
        return "mixed"

    return "english"


def _classify_length(num_messages: int) -> str:
    """
    Return length bucket label based on number of messages.

    short  : 3–8 messages   (Stage 1 typical range)
    medium : 9–15 messages
    long   : 16+ messages   (Stage 2 full-session range)
    """
    if num_messages <= 8:
        return "short (3-8)"
    if num_messages <= 15:
        return "medium (9-15)"
    return "long (16+)"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DimensionReport:
    """Counts and imbalance flags for one classification dimension."""

    name: str
    counts: Counter = field(default_factory=Counter)
    imbalanced: list[str] = field(default_factory=list)

    def analyse(self, threshold: float) -> None:
        """Populate self.imbalanced — categories < threshold fraction of total."""
        total = sum(self.counts.values())
        if total == 0:
            return
        self.imbalanced = [
            cat
            for cat, cnt in self.counts.items()
            if cnt / total < threshold
        ]

    def format(self, threshold: float) -> str:
        """Return a human-readable block for this dimension."""
        total = sum(self.counts.values())
        lines = [f"  {self.name.upper()} ({total} total)"]

        for cat in sorted(self.counts):
            cnt = self.counts[cat]
            pct = cnt / total * 100 if total else 0.0
            flag = "  *** IMBALANCED ***" if cat in self.imbalanced else ""
            lines.append(f"    {cat:<22} {cnt:>5}  ({pct:5.1f}%){flag}")

        if self.imbalanced:
            lines.append(
                f"  WARNING: {len(self.imbalanced)} category(s) below "
                f"{threshold * 100:.0f}% threshold: {', '.join(sorted(self.imbalanced))}"
            )

        return "\n".join(lines)


@dataclass
class BalanceReport:
    """Aggregated balance report across all dimensions."""

    total: int = 0
    topic: DimensionReport = field(default_factory=lambda: DimensionReport("topic"))
    length: DimensionReport = field(default_factory=lambda: DimensionReport("length"))
    language: DimensionReport = field(default_factory=lambda: DimensionReport("language"))
    threshold: float = 0.10

    def analyse(self) -> None:
        """Run imbalance detection on all dimensions."""
        for dim in (self.topic, self.length, self.language):
            dim.analyse(self.threshold)

    @property
    def any_imbalanced(self) -> bool:
        return bool(
            self.topic.imbalanced
            or self.length.imbalanced
            or self.language.imbalanced
        )

    def summary(self) -> str:
        lines = [
            "=" * 60,
            "SAATHI AI — DATASET BALANCE REPORT",
            f"Total conversations analysed: {self.total}",
            f"Imbalance threshold: {self.threshold * 100:.0f}% of dimension total",
            "=" * 60,
            self.topic.format(self.threshold),
            "-" * 60,
            self.length.format(self.threshold),
            "-" * 60,
            self.language.format(self.threshold),
            "=" * 60,
        ]
        if self.any_imbalanced:
            lines.append(
                "RESULT: IMBALANCED — fix underrepresented categories before training."
            )
        else:
            lines.append("RESULT: BALANCED — all categories meet the 10% threshold.")
        lines.append("=" * 60)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialisable dict for JSON report output."""
        return {
            "total": self.total,
            "threshold": self.threshold,
            "any_imbalanced": self.any_imbalanced,
            "topic": {
                "counts": dict(self.topic.counts),
                "imbalanced": self.topic.imbalanced,
            },
            "length": {
                "counts": dict(self.length.counts),
                "imbalanced": self.length.imbalanced,
            },
            "language": {
                "counts": dict(self.language.counts),
                "imbalanced": self.language.imbalanced,
            },
        }


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def _full_text(record: dict) -> str:
    """Concatenate all message contents for classification."""
    return " ".join(
        msg.get("content", "")
        for msg in record.get("messages", [])
        if isinstance(msg.get("content"), str)
    )


def check_balance(
    input_path: Path,
    threshold: float = 0.10,
) -> BalanceReport:
    """
    Read a clean JSONL dataset and produce a BalanceReport.

    Each valid record is classified along three dimensions:
      • topic    — depression / anxiety / OCD / PTSD / relationship / other
      • length   — short (3-8) / medium (9-15) / long (16+)
      • language — english / hinglish / mixed

    Records that cannot be parsed or lack a 'messages' list are skipped
    with a warning (they should have been removed by clean_data.py).
    """
    report = BalanceReport(threshold=threshold)

    with input_path.open("r", encoding="utf-8") as fin:
        for line_no, raw_line in enumerate(fin, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            # Parse
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                logger.warning("Line {}: JSON parse error — {} (skipping)", line_no, exc)
                continue

            messages = record.get("messages")
            if not isinstance(messages, list) or len(messages) == 0:
                logger.warning(
                    "Line {}: missing or empty 'messages' list (skipping)", line_no
                )
                continue

            report.total += 1
            text = _full_text(record)
            num_messages = len(messages)

            report.topic.counts[_detect_topic(text)] += 1
            report.length.counts[_classify_length(num_messages)] += 1
            report.language.counts[_detect_language(text)] += 1

    report.analyse()
    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SAATHI AI — Check dataset balance by topic / length / language",
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
        "--threshold",
        type=float,
        default=0.10,
        metavar="FRAC",
        help=(
            "Minimum acceptable fraction per category within its dimension "
            "(default: 0.10 = 10%%)"
        ),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        metavar="FILE",
        help="Optional path to write a JSON balance report",
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

    if not (0.0 < args.threshold < 1.0):
        logger.error("--threshold must be between 0 and 1, got {}", args.threshold)
        return 1

    logger.info("Analysing dataset: {}", input_path)
    report = check_balance(input_path, threshold=args.threshold)

    if report.total == 0:
        logger.error("No valid records found in {}.", input_path)
        return 1

    logger.info("\n{}", report.summary())

    # Optionally write JSON report
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info("JSON report written to: {}", args.report)

    # Non-zero exit when imbalances detected (lets CI/scripts catch it)
    if report.any_imbalanced:
        logger.warning(
            "Dataset is IMBALANCED — add more samples for flagged categories."
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
