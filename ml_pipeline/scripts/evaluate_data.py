"""
ml_pipeline/scripts/evaluate_data.py
SAATHI AI — Training Data Quality Evaluator

Scores each conversation sample across three therapeutic quality dimensions:
  1. Therapeutic alignment  — assistant responses follow CBT principles
  2. Empathy                — assistant acknowledges patient emotion
  3. Safety                 — assistant avoids harmful advice / crisis neglect

A composite score is the mean of the three sub-scores (0.0–1.0).
Samples with composite score < 0.5 are flagged for manual review.

Output:
  • Annotated JSONL  — each record gains an "_eval" field with scores + flag
  • JSON report      — aggregate statistics over the full dataset

Usage:
    python evaluate_data.py --input data/stage1_clean.jsonl
    python evaluate_data.py --input data/stage2_clean.jsonl \\
                            --output data/stage2_evaluated.jsonl \\
                            --report reports/stage2_eval_report.json \\
                            --threshold 0.5
    python evaluate_data.py --input data/stage1_clean.jsonl --flagged-only
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

# ---------------------------------------------------------------------------
# Scoring vocabulary
# ---------------------------------------------------------------------------

# Phrases that indicate the assistant is actively applying CBT or structured
# therapeutic techniques.  Each hit adds to therapeutic_alignment.
_THERAPEUTIC_POSITIVE: list[str] = [
    # Thought monitoring / cognitive techniques
    "what thoughts", "thought pattern", "cognitive", "reframe", "restructur",
    "automatic thought", "core belief", "thought record",
    # Behavioural activation
    "behavioral", "behavioural", "activity", "step by step", "small step",
    "gradual", "try this", "practice",
    # Exploration / Socratic questioning
    "can you tell me", "tell me more", "what do you mean", "help me understand",
    "what does that feel like", "how does that affect", "when did this start",
    "how long have you", "have you noticed", "what happened",
    # Coping and problem-solving
    "coping", "cope", "strategy", "breathing", "grounding", "mindful",
    "relaxation", "problem-solving", "alternative", "perspective",
    # Session structure
    "last session", "this session", "our work", "homework", "between sessions",
    "progress", "goal",
    # Validation within therapeutic frame
    "makes sense", "understandable", "common feeling", "you're not alone",
    "many people", "normal to feel",
]

# Phrases that undermine therapeutic quality (penalise).
_THERAPEUTIC_NEGATIVE: list[str] = [
    "just cheer up", "snap out of it", "man up", "get over it",
    "stop overthinking", "it's all in your head", "you'll be fine",
    "don't worry about it", "just be positive", "just ignore",
]

# Phrases that indicate the assistant is acknowledging and validating emotion.
_EMPATHY_POSITIVE: list[str] = [
    "i hear you", "i can hear", "that sounds", "that must be",
    "sounds difficult", "sounds hard", "sounds tough", "i understand",
    "i can imagine", "must feel", "that feeling", "it's okay to feel",
    "it is okay to feel", "valid", "makes sense to feel",
    "completely understandable", "thank you for sharing", "thank you for telling",
    "appreciate you sharing", "opening up", "reaching out",
    "you're not alone", "you are not alone", "you matter",
    "i'm here", "i am here", "we'll work through", "we will work",
    "support you", "here to help",
]

# Dismissive phrases that lack empathy (penalise).
_EMPATHY_NEGATIVE: list[str] = [
    "stop feeling", "no reason to feel", "you shouldn't feel",
    "you should not feel", "don't be sad", "don't be anxious",
    "everyone goes through this so", "just move on",
]

# Phrases in assistant responses that indicate unsafe / harmful content.
_SAFETY_NEGATIVE: list[str] = [
    # Self-harm or suicide facilitation
    "ways to hurt yourself", "how to end your life", "method to die",
    "painless way", "best way to suicide", "cut yourself deeper",
    # Medical misguidance
    "take more pills", "double the dose", "stop your medication",
    "stop taking your medication", "you don't need a doctor",
    # Harmful reassurance in crisis
    "it's just a phase", "it is just a phase",
    "they're overreacting", "they are overreacting",
    # Toxic positivity that dismisses crisis
    "nothing bad will happen", "i'm sure you're fine",
]

# Crisis signals in USER messages.  When present, we check whether the
# assistant responded with appropriate safety language.
_CRISIS_USER_SIGNALS: list[str] = [
    "want to die", "kill myself", "end my life", "suicid",
    "self-harm", "self harm", "cut myself", "hurt myself",
    "no reason to live", "don't want to live", "don't want to be alive",
    "worthless", "hopeless", "can't go on",
]

# When a crisis signal is present in the user turn, the assistant response
# must contain at least one of these to maintain a safe score.
_CRISIS_RESPONSE_REQUIRED: list[str] = [
    "helpline", "hotline", "emergency", "professional help",
    "please reach out", "speak to a", "talk to a", "contact a",
    "seek help", "see a therapist", "see a doctor", "seek support",
    "iCall", "vandrevala", "snehi", "aasra",   # Indian helplines
    "here with you", "i care", "your safety",
    "safe", "safety", "we take this seriously", "crisis",
    "please tell someone", "tell a trusted",
]

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _count_hits(text: str, phrases: list[str]) -> int:
    """Count how many phrases appear in text (case-insensitive, each once)."""
    lower = text.lower()
    return sum(1 for p in phrases if p in lower)


def _score_therapeutic_alignment(assistant_text: str) -> float:
    """
    Score 0.0–1.0 for therapeutic alignment of a single assistant message.

    Algorithm:
      pos_hits = count of _THERAPEUTIC_POSITIVE phrases present
      neg_hits = count of _THERAPEUTIC_NEGATIVE phrases present
      raw = (pos_hits * 2 - neg_hits * 3) / normaliser
      clamped to [0, 1]

    A response with 2+ positive hits and 0 negative hits scores >= 0.5.
    """
    pos = _count_hits(assistant_text, _THERAPEUTIC_POSITIVE)
    neg = _count_hits(assistant_text, _THERAPEUTIC_NEGATIVE)
    # Normalise against a target of 4 positive hits = perfect score
    normaliser = max(1, len(_THERAPEUTIC_POSITIVE) / 10)
    raw = (pos * 2 - neg * 3) / (normaliser * 2)
    return max(0.0, min(1.0, raw))


def _score_empathy(assistant_text: str) -> float:
    """
    Score 0.0–1.0 for empathetic content in a single assistant message.

    Algorithm:
      pos_hits = count of _EMPATHY_POSITIVE phrases
      neg_hits = count of _EMPATHY_NEGATIVE phrases
      raw = (pos_hits - neg_hits * 2) / normaliser
    """
    pos = _count_hits(assistant_text, _EMPATHY_POSITIVE)
    neg = _count_hits(assistant_text, _EMPATHY_NEGATIVE)
    normaliser = max(1, len(_EMPATHY_POSITIVE) / 10)
    raw = (pos - neg * 2) / normaliser
    return max(0.0, min(1.0, raw))


def _score_safety(
    assistant_text: str,
    user_text_before: str,
) -> float:
    """
    Score 0.0–1.0 for safety of a single assistant message.

    Two deductions:
      1. Harmful content in assistant response → large penalty
      2. Crisis signal in preceding user turn + NO safe response → penalty

    Starts at 1.0 and deducts:
      - 0.5 per harmful phrase found in assistant
      - 0.4 if user mentioned crisis but assistant gave no appropriate response
    """
    score = 1.0

    harm_hits = _count_hits(assistant_text, _SAFETY_NEGATIVE)
    score -= min(1.0, harm_hits * 0.5)

    has_crisis = any(sig in user_text_before.lower() for sig in _CRISIS_USER_SIGNALS)
    if has_crisis:
        has_safe_response = any(
            phrase in assistant_text.lower() for phrase in _CRISIS_RESPONSE_REQUIRED
        )
        if not has_safe_response:
            score -= 0.4

    return max(0.0, score)


# ---------------------------------------------------------------------------
# Per-conversation evaluation
# ---------------------------------------------------------------------------

@dataclass
class TurnEval:
    turn_index: int          # index of the assistant message in messages[]
    therapeutic: float
    empathy: float
    safety: float
    composite: float


@dataclass
class ConversationEval:
    therapeutic: float       # mean across assistant turns
    empathy: float
    safety: float
    composite: float         # mean of three dimension means
    flagged: bool            # True when composite < threshold
    turn_evals: list[TurnEval] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "therapeutic_alignment": round(self.therapeutic, 4),
            "empathy": round(self.empathy, 4),
            "safety": round(self.safety, 4),
            "composite": round(self.composite, 4),
            "flagged": self.flagged,
            "turn_evals": [
                {
                    "turn_index": te.turn_index,
                    "therapeutic_alignment": round(te.therapeutic, 4),
                    "empathy": round(te.empathy, 4),
                    "safety": round(te.safety, 4),
                    "composite": round(te.composite, 4),
                }
                for te in self.turn_evals
            ],
        }


def evaluate_conversation(
    record: dict,
    threshold: float,
) -> ConversationEval:
    """
    Evaluate a single conversation record.

    Iterates through messages[].  For each assistant message, locates the
    immediately preceding user message (if any) to provide crisis context for
    the safety scorer.

    Returns a ConversationEval with per-dimension and composite scores.
    """
    messages: list[dict] = record.get("messages", [])
    turn_evals: list[TurnEval] = []

    last_user_text = ""
    for idx, msg in enumerate(messages):
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "user":
            last_user_text = content
        elif role == "assistant" and content.strip():
            t = _score_therapeutic_alignment(content)
            e = _score_empathy(content)
            s = _score_safety(content, last_user_text)
            composite = (t + e + s) / 3.0
            turn_evals.append(
                TurnEval(
                    turn_index=idx,
                    therapeutic=t,
                    empathy=e,
                    safety=s,
                    composite=composite,
                )
            )

    if not turn_evals:
        # No scorable assistant turns — treat as worst possible
        return ConversationEval(
            therapeutic=0.0,
            empathy=0.0,
            safety=0.0,
            composite=0.0,
            flagged=True,
            turn_evals=[],
        )

    mean_t = sum(te.therapeutic for te in turn_evals) / len(turn_evals)
    mean_e = sum(te.empathy for te in turn_evals) / len(turn_evals)
    mean_s = sum(te.safety for te in turn_evals) / len(turn_evals)
    composite = (mean_t + mean_e + mean_s) / 3.0

    return ConversationEval(
        therapeutic=mean_t,
        empathy=mean_e,
        safety=mean_s,
        composite=composite,
        flagged=composite < threshold,
        turn_evals=turn_evals,
    )


# ---------------------------------------------------------------------------
# Report data structures
# ---------------------------------------------------------------------------

@dataclass
class EvalReport:
    total: int = 0
    flagged: int = 0
    threshold: float = 0.5
    mean_therapeutic: float = 0.0
    mean_empathy: float = 0.0
    mean_safety: float = 0.0
    mean_composite: float = 0.0
    score_distribution: dict[str, int] = field(default_factory=dict)
    flagged_lines: list[int] = field(default_factory=list)

    def summary(self) -> str:
        flag_pct = self.flagged / self.total * 100 if self.total else 0
        lines = [
            "=" * 62,
            "SAATHI AI — DATA QUALITY EVALUATION SUMMARY",
            f"Threshold : {self.threshold}  (samples below → flagged)",
            "=" * 62,
            f"  Total evaluated          : {self.total}",
            f"  Flagged (composite<{self.threshold:.1f}) : {self.flagged}  ({flag_pct:.1f}%)",
            "-" * 62,
            f"  Mean therapeutic alignment : {self.mean_therapeutic:.4f}",
            f"  Mean empathy               : {self.mean_empathy:.4f}",
            f"  Mean safety                : {self.mean_safety:.4f}",
            f"  Mean composite             : {self.mean_composite:.4f}",
            "-" * 62,
            "  COMPOSITE SCORE DISTRIBUTION",
        ]
        for bracket in sorted(self.score_distribution.keys()):
            cnt = self.score_distribution[bracket]
            pct = cnt / self.total * 100 if self.total else 0
            lines.append(f"    {bracket}  {cnt:>5}  ({pct:5.1f}%)")
        lines.append("=" * 62)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "flagged": self.flagged,
            "threshold": self.threshold,
            "mean_scores": {
                "therapeutic_alignment": round(self.mean_therapeutic, 4),
                "empathy": round(self.mean_empathy, 4),
                "safety": round(self.mean_safety, 4),
                "composite": round(self.mean_composite, 4),
            },
            "score_distribution": self.score_distribution,
            "flagged_lines": self.flagged_lines,
        }


def _score_bracket(score: float) -> str:
    """Map 0–1 score to a human-readable bracket string."""
    if score < 0.2:
        return "0.0–0.2 (very low)"
    if score < 0.4:
        return "0.2–0.4 (low)"
    if score < 0.6:
        return "0.4–0.6 (medium)"
    if score < 0.8:
        return "0.6–0.8 (good)"
    return "0.8–1.0 (excellent)"


# ---------------------------------------------------------------------------
# Core evaluation pipeline
# ---------------------------------------------------------------------------

def evaluate_dataset(
    input_path: Path,
    output_path: Path | None,
    threshold: float,
    flagged_only: bool,
) -> EvalReport:
    """
    Evaluate every conversation in input_path, optionally write annotated
    JSONL, and return an EvalReport.

    Algorithm:
      For each record:
        1. Parse JSON; skip malformed lines with a warning.
        2. Call evaluate_conversation() to get per-dimension + composite scores.
        3. Attach scores as record["_eval"] in the output JSONL.
        4. If flagged_only=True, write only flagged records; else write all.
      Accumulate report statistics.
    """
    report = EvalReport(threshold=threshold)

    t_sum = e_sum = s_sum = c_sum = 0.0

    out_file = None
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        out_file = output_path.open("w", encoding="utf-8")

    try:
        with input_path.open("r", encoding="utf-8") as fin:
            for line_no, raw_line in enumerate(fin, start=1):
                raw_line = raw_line.strip()
                if not raw_line:
                    continue

                try:
                    record = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    logger.warning("Line {}: JSON parse error — {} (skipping)", line_no, exc)
                    continue

                if not isinstance(record.get("messages"), list):
                    logger.warning(
                        "Line {}: missing 'messages' list (skipping)", line_no
                    )
                    continue

                ev = evaluate_conversation(record, threshold)

                report.total += 1
                t_sum += ev.therapeutic
                e_sum += ev.empathy
                s_sum += ev.safety
                c_sum += ev.composite

                bracket = _score_bracket(ev.composite)
                report.score_distribution[bracket] = (
                    report.score_distribution.get(bracket, 0) + 1
                )

                if ev.flagged:
                    report.flagged += 1
                    report.flagged_lines.append(line_no)
                    logger.warning(
                        "Line {:>5}: FLAGGED  composite={:.3f}  "
                        "therapeutic={:.3f}  empathy={:.3f}  safety={:.3f}",
                        line_no,
                        ev.composite,
                        ev.therapeutic,
                        ev.empathy,
                        ev.safety,
                    )
                else:
                    logger.debug(
                        "Line {:>5}: ok       composite={:.3f}",
                        line_no,
                        ev.composite,
                    )

                if out_file is not None:
                    if not flagged_only or ev.flagged:
                        annotated = {**record, "_eval": ev.to_dict()}
                        out_file.write(
                            json.dumps(annotated, ensure_ascii=False) + "\n"
                        )
    finally:
        if out_file is not None:
            out_file.close()

    if report.total:
        report.mean_therapeutic = t_sum / report.total
        report.mean_empathy = e_sum / report.total
        report.mean_safety = s_sum / report.total
        report.mean_composite = c_sum / report.total

    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "SAATHI AI — Score training samples for therapeutic quality. "
            "Flags samples with composite score < threshold for manual review."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        type=Path,
        help="Clean JSONL dataset to evaluate (output of clean_data.py)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        metavar="FILE",
        help=(
            "Path for annotated output JSONL (with '_eval' field added). "
            "Omit to skip writing output."
        ),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        metavar="FILE",
        help="Optional path to write a JSON evaluation report.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        metavar="SCORE",
        help="Composite score below which a sample is flagged (default: 0.5).",
    )
    parser.add_argument(
        "--flagged-only",
        action="store_true",
        help=(
            "When writing --output, include only flagged samples "
            "(useful for focused manual review)."
        ),
    )
    parser.add_argument(
        "--fail-on-flagged",
        action="store_true",
        help="Exit with code 1 if any samples are flagged (for CI gating).",
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

    logger.remove()
    logger.add(sys.stderr, level=args.log_level, colorize=True)

    input_path: Path = args.input
    if not input_path.exists():
        logger.error("Input file not found: {}", input_path)
        return 1

    if not (0.0 < args.threshold <= 1.0):
        logger.error(
            "--threshold must be in (0, 1], got {}.", args.threshold
        )
        return 1

    logger.info(
        "Evaluating '{}' (threshold={})…", input_path.name, args.threshold
    )

    report = evaluate_dataset(
        input_path=input_path,
        output_path=args.output,
        threshold=args.threshold,
        flagged_only=args.flagged_only,
    )

    if report.total == 0:
        logger.error("No valid records found in {}.", input_path)
        return 1

    logger.info("\n{}", report.summary())

    if args.output:
        label = "flagged records" if args.flagged_only else "annotated records"
        logger.info("Annotated output ({}) written → {}", label, args.output)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info("JSON report written → {}", args.report)

    if args.fail_on_flagged and report.flagged > 0:
        logger.error(
            "{} sample(s) flagged below threshold {}. "
            "Review and fix before training.",
            report.flagged,
            args.threshold,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
