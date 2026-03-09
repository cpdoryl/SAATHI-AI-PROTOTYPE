"""
ml_pipeline/scripts/clean_data.py
SAATHI AI — Training Data Cleaning Pipeline

Validates, deduplicates, PII-scrubs, and length-filters JSONL conversation
datasets before LoRA fine-tuning.

Usage:
    python clean_data.py --input data/stage1_leads.jsonl --output data/stage1_clean.jsonl
    python clean_data.py --input data/stage2_therapy.jsonl --output data/stage2_clean.jsonl \
                         --max-tokens 2048 --min-turns 3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

# ---------------------------------------------------------------------------
# PII detection patterns
# ---------------------------------------------------------------------------

# Indian mobile: +91-XXXXXXXXXX, 91XXXXXXXXXX, 0XXXXXXXXXX, XXXXXXXXXX (10-digit starting 6-9)
_PHONE_RE = re.compile(
    r"(?<!\d)"
    r"(?:\+91[\s\-]?|91[\s\-]?|0)?"
    r"[6-9]\d{9}"
    r"(?!\d)",
    re.IGNORECASE,
)

# Standard email
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# Aadhaar: 12 consecutive digits, optionally space-grouped as XXXX XXXX XXXX
# Must NOT be part of a longer digit sequence (phone numbers excluded by PII check order)
_AADHAAR_RE = re.compile(
    r"(?<!\d)"
    r"(?:\d{4}[\s\-]\d{4}[\s\-]\d{4}|\d{12})"
    r"(?!\d)",
)

# ---------------------------------------------------------------------------
# Tokenizer (graceful fallback to char-based estimate)
# ---------------------------------------------------------------------------

def _build_token_counter():
    """Return a callable (text: str) -> int that counts tokens."""
    try:
        from transformers import AutoTokenizer  # type: ignore

        _tokenizer = AutoTokenizer.from_pretrained(
            "Qwen/Qwen2.5-7B-Instruct", trust_remote_code=True
        )
        logger.info("Using Qwen2.5 tokenizer for token counting.")

        def count_tokens(text: str) -> int:
            return len(_tokenizer.encode(text, add_special_tokens=False))

    except Exception:
        logger.warning(
            "transformers / Qwen tokenizer not available — using char/4 approximation."
        )

        def count_tokens(text: str) -> int:  # type: ignore[misc]
            return max(1, len(text) // 4)

    return count_tokens


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CleaningStats:
    total_read: int = 0
    invalid_format: int = 0
    duplicate: int = 0
    too_short: int = 0
    pii_flagged: int = 0
    too_long: int = 0
    kept: int = 0
    pii_detail: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "─" * 50,
            "DATA CLEANING SUMMARY",
            "─" * 50,
            f"  Total read          : {self.total_read}",
            f"  Invalid format      : {self.invalid_format}",
            f"  Duplicates removed  : {self.duplicate}",
            f"  Too short (<min turns): {self.too_short}",
            f"  PII flagged         : {self.pii_flagged}",
            f"  Too long (>max tok) : {self.too_long}",
            f"  ── Kept (clean)     : {self.kept}",
            "─" * 50,
        ]
        if self.total_read:
            pct = self.kept / self.total_read * 100
            lines.append(f"  Retention rate      : {pct:.1f}%")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _is_valid_format(record: Any) -> tuple[bool, str]:
    """Check that record is a dict with a non-empty 'messages' list."""
    if not isinstance(record, dict):
        return False, "not a dict"
    messages = record.get("messages")
    if not isinstance(messages, list) or len(messages) == 0:
        return False, "missing or empty 'messages' list"
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            return False, f"messages[{i}] is not a dict"
        if "role" not in msg or "content" not in msg:
            return False, f"messages[{i}] missing 'role' or 'content'"
        if msg["role"] not in {"user", "assistant", "system"}:
            return False, f"messages[{i}] has unknown role '{msg['role']}'"
        if not isinstance(msg["content"], str):
            return False, f"messages[{i}] content is not a string"
    return True, ""


def _count_turns(record: dict) -> int:
    """Number of messages in the conversation (each message = 1 turn)."""
    return len(record["messages"])


def _first_user_message(record: dict) -> str | None:
    """Return the content of the first user message, or None."""
    for msg in record["messages"]:
        if msg["role"] == "user":
            return msg["content"]
    return None


def _full_text(record: dict) -> str:
    """Concatenate all message contents for PII scanning."""
    return " ".join(msg["content"] for msg in record["messages"])


def _detect_pii(text: str, line_number: int) -> list[dict[str, str]]:
    """Return list of PII findings: [{type, match, line}]."""
    findings: list[dict[str, str]] = []

    for match in _EMAIL_RE.finditer(text):
        findings.append(
            {"type": "email", "match": match.group(), "line": str(line_number)}
        )

    # Phone check: exclude 12-digit sequences that look like Aadhaar
    for match in _PHONE_RE.finditer(text):
        raw = re.sub(r"[\s\-+]", "", match.group())
        if len(raw) == 12 and raw.startswith("91"):
            raw = raw[2:]
        if len(raw) == 10:
            findings.append(
                {"type": "phone", "match": match.group().strip(), "line": str(line_number)}
            )

    for match in _AADHAAR_RE.finditer(text):
        raw = re.sub(r"[\s\-]", "", match.group())
        # Exclude 10-digit phone numbers already captured
        if len(raw) == 12:
            findings.append(
                {"type": "aadhaar", "match": "*" * 8 + raw[-4:], "line": str(line_number)}
            )

    return findings


# ---------------------------------------------------------------------------
# Core cleaning pipeline
# ---------------------------------------------------------------------------

def clean_dataset(
    input_path: Path,
    output_path: Path,
    min_turns: int,
    max_tokens: int,
) -> CleaningStats:
    """
    Read input JSONL, apply all cleaning filters, write clean JSONL.

    Filters applied in order:
      1. Format validation — must have 'messages' list with role+content
      2. Deduplication — exact match on first user message (sha256)
      3. Min-turn filter — conversations with < min_turns messages
      4. PII detection — phone / email / Aadhaar regex
      5. Max-token filter — total conversation text > max_tokens
    """
    count_tokens = _build_token_counter()
    stats = CleaningStats()
    seen_hashes: set[str] = set()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with (
        input_path.open("r", encoding="utf-8") as fin,
        output_path.open("w", encoding="utf-8") as fout,
    ):
        for line_no, raw_line in enumerate(fin, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            stats.total_read += 1

            # ── 1. Parse JSON ──────────────────────────────────────────────
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                logger.warning("Line {}: JSON parse error — {}", line_no, exc)
                stats.invalid_format += 1
                continue

            # ── 2. Format validation ───────────────────────────────────────
            valid, reason = _is_valid_format(record)
            if not valid:
                logger.warning("Line {}: invalid format — {}", line_no, reason)
                stats.invalid_format += 1
                continue

            # ── 3. Deduplication (first user message) ─────────────────────
            first_user = _first_user_message(record)
            if first_user is None:
                logger.warning("Line {}: no user message found", line_no)
                stats.invalid_format += 1
                continue

            dup_key = hashlib.sha256(first_user.strip().lower().encode()).hexdigest()
            if dup_key in seen_hashes:
                logger.debug("Line {}: duplicate first-user-message — skipping", line_no)
                stats.duplicate += 1
                continue
            seen_hashes.add(dup_key)

            # ── 4. Min-turn filter ─────────────────────────────────────────
            turn_count = _count_turns(record)
            if turn_count < min_turns:
                logger.debug(
                    "Line {}: too short ({} turns < {} min) — skipping",
                    line_no,
                    turn_count,
                    min_turns,
                )
                stats.too_short += 1
                continue

            # ── 5. PII detection ───────────────────────────────────────────
            full_text = _full_text(record)
            pii_findings = _detect_pii(full_text, line_no)
            if pii_findings:
                logger.warning(
                    "Line {}: {} PII finding(s) — {}",
                    line_no,
                    len(pii_findings),
                    [f"{f['type']}:{f['match']}" for f in pii_findings],
                )
                stats.pii_flagged += 1
                stats.pii_detail.extend(pii_findings)
                continue

            # ── 6. Max-token filter ────────────────────────────────────────
            token_count = count_tokens(full_text)
            if token_count > max_tokens:
                logger.debug(
                    "Line {}: too long ({} tokens > {} max) — skipping",
                    line_no,
                    token_count,
                    max_tokens,
                )
                stats.too_long += 1
                continue

            # ── Write clean record ─────────────────────────────────────────
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            stats.kept += 1

    return stats


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SAATHI AI — Clean and validate training JSONL datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        type=Path,
        help="Path to raw input JSONL file",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        type=Path,
        help="Path for clean output JSONL file",
    )
    parser.add_argument(
        "--min-turns",
        type=int,
        default=3,
        metavar="N",
        help="Minimum number of messages per conversation (default: 3)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=2048,
        metavar="N",
        help="Maximum token count per conversation (default: 2048)",
    )
    parser.add_argument(
        "--pii-report",
        type=Path,
        default=None,
        metavar="FILE",
        help="Optional path to write PII findings JSON report",
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
    output_path: Path = args.output

    if not input_path.exists():
        logger.error("Input file not found: {}", input_path)
        return 1

    logger.info("Starting data cleaning: {} → {}", input_path, output_path)
    logger.info(
        "Filters: min_turns={}, max_tokens={}", args.min_turns, args.max_tokens
    )

    stats = clean_dataset(
        input_path=input_path,
        output_path=output_path,
        min_turns=args.min_turns,
        max_tokens=args.max_tokens,
    )

    logger.info("\n{}", stats.summary())

    # Optionally write PII report
    if args.pii_report and stats.pii_detail:
        args.pii_report.parent.mkdir(parents=True, exist_ok=True)
        with args.pii_report.open("w", encoding="utf-8") as f:
            json.dump(stats.pii_detail, f, indent=2, ensure_ascii=False)
        logger.warning("PII report written to: {}", args.pii_report)

    # Exit 1 if PII found (let CI catch unsafe datasets)
    if stats.pii_flagged > 0:
        logger.error(
            "{} conversation(s) removed due to PII. Fix the source data.", stats.pii_flagged
        )
        return 1

    if stats.kept == 0:
        logger.error("No records survived cleaning — check input data quality.")
        return 1

    logger.info("Clean dataset written: {} records → {}", stats.kept, output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
