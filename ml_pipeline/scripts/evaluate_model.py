"""
ml_pipeline/scripts/evaluate_model.py
SAATHI AI — Post-Training Model Evaluator

Computes automated quality metrics on the held-out test set after LoRA fine-tuning:
  • Perplexity  — token-level cross-entropy loss (target < 8.0)
  • BLEU-4      — n-gram overlap of generated vs reference responses (target > 0.15)
  • ROUGE-L     — longest-common-subsequence overlap (target > 0.35)

Supported inference backends:
  • HuggingFace transformers  (--model-path <HF dir or hub ID>)
  • llama.cpp GGUF             (--gguf-path  <.gguf file>)
    Note: perplexity is unavailable for the GGUF backend (no logit access).

Test JSONL format (same as training data):
  {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}

Evaluation strategy:
  For each conversation in the test set the script strips the *last* assistant
  turn, feeds the remaining context to the model, and compares the generated
  response to the reference.  BLEU-4 and ROUGE-L are computed over the full
  set of (hypothesis, reference) pairs.

Usage:
    # HuggingFace model / merged LoRA adapter
    python evaluate_model.py \\
        --model-path ./merged/saathi-stage2 \\
        --test-data  ./data/stage2_test.jsonl \\
        --report     ./reports/eval_stage2.json

    # GGUF (llama-cpp-python)
    python evaluate_model.py \\
        --gguf-path  ./models/saathi-stage2-q4.gguf \\
        --test-data  ./data/stage2_test.jsonl \\
        --report     ./reports/eval_stage2_gguf.json \\
        --max-samples 100

    # Fail CI when targets not met
    python evaluate_model.py \\
        --model-path ./merged/saathi-stage2 \\
        --test-data  ./data/stage2_test.jsonl \\
        --fail-on-miss
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

# ---------------------------------------------------------------------------
# Blueprint targets (Section 6 of ML_BLUEPRINT.md)
# ---------------------------------------------------------------------------

TARGET_PERPLEXITY_MAX: float = 8.0
TARGET_BLEU4_MIN: float = 0.15
TARGET_ROUGE_L_MIN: float = 0.35

# ---------------------------------------------------------------------------
# Optional heavy imports — handled gracefully
# ---------------------------------------------------------------------------

def _import_transformers():
    """Return (AutoModelForCausalLM, AutoTokenizer) or raise ImportError."""
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
        return AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise ImportError(
            "transformers is not installed.  "
            "Run: pip install transformers>=4.44.0 torch"
        ) from exc


def _import_torch():
    try:
        import torch  # type: ignore
        return torch
    except ImportError as exc:
        raise ImportError("torch is not installed.  Run: pip install torch") from exc


def _import_sacrebleu():
    try:
        import sacrebleu  # type: ignore
        return sacrebleu
    except ImportError as exc:
        raise ImportError(
            "sacrebleu is not installed.  Run: pip install sacrebleu"
        ) from exc


def _import_rouge():
    try:
        from rouge_score import rouge_scorer  # type: ignore
        return rouge_scorer
    except ImportError as exc:
        raise ImportError(
            "rouge-score is not installed.  Run: pip install rouge-score"
        ) from exc


def _import_llama_cpp():
    try:
        from llama_cpp import Llama  # type: ignore
        return Llama
    except ImportError as exc:
        raise ImportError(
            "llama-cpp-python is not installed.  Run: pip install llama-cpp-python"
        ) from exc


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_test_records(path: Path, max_samples: int) -> list[dict]:
    """
    Load JSONL test records.

    Each record must have a 'messages' list with at least one user and one
    assistant turn.  Malformed records are skipped with a warning.

    Returns up to max_samples valid records.
    """
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.warning("Line {}: JSON parse error — {} (skipping)", line_no, exc)
                continue

            messages = rec.get("messages")
            if not isinstance(messages, list) or len(messages) < 2:
                logger.warning(
                    "Line {}: expected 'messages' list with ≥2 entries (skipping)", line_no
                )
                continue

            roles = [m.get("role") for m in messages]
            if "user" not in roles or "assistant" not in roles:
                logger.warning(
                    "Line {}: must have at least one 'user' and one 'assistant' turn (skipping)",
                    line_no,
                )
                continue

            records.append(rec)
            if len(records) >= max_samples:
                logger.info(
                    "Reached --max-samples limit ({}) — stopping early.", max_samples
                )
                break

    return records


def _split_context_reference(record: dict) -> tuple[list[dict], str]:
    """
    Split a conversation into:
      - context  : all messages except the last assistant turn
      - reference: the text of the last assistant turn

    The last assistant turn is the ground-truth response the model should
    reproduce (or closely match).  If the final message is not from an
    assistant the function walks backwards to find the last assistant message.
    """
    messages = record["messages"]
    # Find the index of the last assistant message
    last_asst_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "assistant":
            last_asst_idx = i
            break

    if last_asst_idx == -1:
        # No assistant message — use all messages as context, empty reference
        return messages, ""

    context = messages[:last_asst_idx]
    reference = messages[last_asst_idx].get("content", "").strip()
    return context, reference


# ---------------------------------------------------------------------------
# Prompt formatting (Qwen2.5-Instruct chat template)
# ---------------------------------------------------------------------------

def _format_prompt_qwen(messages: list[dict]) -> str:
    """
    Format messages as a Qwen2.5-Instruct chat prompt.

    Uses the standard <|im_start|>/<|im_end|> tokens.  The prompt ends with
    <|im_start|>assistant\\n so the model continues as the assistant.
    """
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        parts.append(f"<|im_start|>{role}\n{content}<|im_end|>\n")
    parts.append("<|im_start|>assistant\n")
    return "".join(parts)


# ---------------------------------------------------------------------------
# HuggingFace backend
# ---------------------------------------------------------------------------

class HFBackend:
    """
    Wraps a HuggingFace CausalLM model for generation and perplexity.

    Loads the model with device_map="auto" to support multi-GPU or CPU fallback.
    Uses 4-bit quantization via bitsandbytes when available (QLoRA inference).
    Falls back to fp32 when bitsandbytes is not installed.
    """

    def __init__(self, model_path: str, max_new_tokens: int) -> None:
        torch = _import_torch()
        AutoModelForCausalLM, AutoTokenizer = _import_transformers()

        self.torch = torch
        self.max_new_tokens = max_new_tokens

        logger.info("Loading tokenizer from '{}'…", model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path, trust_remote_code=True
        )
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

        load_kwargs: dict[str, Any] = {
            "trust_remote_code": True,
            "device_map": "auto",
        }

        # Try 4-bit quantisation (optional)
        try:
            import bitsandbytes  # type: ignore  # noqa: F401
            load_kwargs["load_in_4bit"] = True
            load_kwargs["bnb_4bit_compute_dtype"] = torch.float16
            load_kwargs["bnb_4bit_quant_type"] = "nf4"
            logger.info("bitsandbytes available — loading in 4-bit (QLoRA inference).")
        except ImportError:
            logger.info("bitsandbytes not available — loading in full precision.")

        logger.info("Loading model from '{}'…", model_path)
        self.model = AutoModelForCausalLM.from_pretrained(model_path, **load_kwargs)
        self.model.eval()

        # Determine device for tensor operations
        self.device = next(self.model.parameters()).device
        logger.info("Model device: {}", self.device)

    # ------------------------------------------------------------------
    # Perplexity

    def compute_perplexity(self, records: list[dict]) -> float:
        """
        Compute mean perplexity over all records.

        For each record the entire conversation is tokenised and passed through
        the model.  The loss (cross-entropy over all tokens) is exponentiated
        to obtain perplexity.  Per-record perplexities are averaged in
        log-space (geometric mean) to avoid skew from long conversations.

        Returns exp(mean_log_perplexity).
        """
        torch = self.torch
        log_ppx_sum = 0.0
        count = 0

        for idx, record in enumerate(records):
            messages = record.get("messages", [])
            full_text = _format_prompt_qwen(messages)

            inputs = self.tokenizer(
                full_text,
                return_tensors="pt",
                truncation=True,
                max_length=2048,
            ).to(self.device)

            input_ids = inputs["input_ids"]
            if input_ids.shape[1] < 2:
                logger.warning("Record {}: too short to compute perplexity — skipping", idx)
                continue

            with torch.no_grad():
                outputs = self.model(input_ids=input_ids, labels=input_ids)
                loss: float = outputs.loss.item()

            log_ppx_sum += loss
            count += 1

            if (idx + 1) % 10 == 0:
                logger.debug(
                    "Perplexity progress: {}/{} | current loss={:.4f}", idx + 1, len(records), loss
                )

        if count == 0:
            return float("inf")

        return math.exp(log_ppx_sum / count)

    # ------------------------------------------------------------------
    # Generation

    def generate(self, messages: list[dict]) -> str:
        """Generate a single response for the given conversation context."""
        torch = self.torch
        prompt = _format_prompt_qwen(messages)

        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=1800,  # leave room for generation
        ).to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,          # greedy for reproducibility
                temperature=1.0,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        # Decode only the newly generated tokens
        new_tokens = output_ids[0][inputs["input_ids"].shape[1]:]
        generated = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return generated.strip()


# ---------------------------------------------------------------------------
# GGUF backend (llama-cpp-python)
# ---------------------------------------------------------------------------

class GGUFBackend:
    """
    Wraps a llama-cpp-python Llama instance for generation.

    Perplexity computation is NOT available for the GGUF backend because
    llama-cpp-python does not expose per-token log probabilities in a form
    suitable for loss calculation.
    """

    def __init__(self, gguf_path: str, max_new_tokens: int, n_ctx: int = 2048) -> None:
        Llama = _import_llama_cpp()

        logger.info("Loading GGUF model from '{}'…", gguf_path)
        self.llm = Llama(
            model_path=gguf_path,
            n_ctx=n_ctx,
            n_gpu_layers=-1,   # offload all layers to GPU if available
            verbose=False,
        )
        self.max_new_tokens = max_new_tokens
        logger.info("GGUF model loaded.")

    def compute_perplexity(self, records: list[dict]) -> float:  # noqa: ARG002
        """Perplexity is not available for the GGUF backend."""
        logger.warning(
            "Perplexity computation is unavailable for the GGUF backend. "
            "Use --model-path with a HuggingFace model instead."
        )
        return float("nan")

    def generate(self, messages: list[dict]) -> str:
        """Generate a response using the llama.cpp chat completion API."""
        # Build messages list for llama-cpp chat completion
        chat_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in {"system", "user", "assistant"}:
                chat_messages.append({"role": role, "content": content})

        response = self.llm.create_chat_completion(
            messages=chat_messages,
            max_tokens=self.max_new_tokens,
            temperature=0.0,   # greedy for reproducibility
        )
        text: str = response["choices"][0]["message"]["content"]
        return text.strip()


# ---------------------------------------------------------------------------
# Generation loop — shared by both backends
# ---------------------------------------------------------------------------

def run_generation(
    backend: "HFBackend | GGUFBackend",
    records: list[dict],
    batch_log_every: int = 10,
) -> tuple[list[str], list[str]]:
    """
    For each record:
      1. Split into context (messages) and reference (last assistant turn).
      2. Generate hypothesis from the model.
      3. Collect (hypothesis, reference) pairs.

    Returns (hypotheses, references).  Records where the reference is empty
    are skipped (cannot contribute to BLEU/ROUGE).
    """
    hypotheses: list[str] = []
    references: list[str] = []

    for idx, record in enumerate(records):
        context, reference = _split_context_reference(record)
        if not reference:
            logger.warning("Record {}: no reference found — skipping generation", idx)
            continue

        if not context:
            logger.warning("Record {}: empty context — skipping generation", idx)
            continue

        try:
            hypothesis = backend.generate(context)
        except Exception as exc:
            logger.warning("Record {}: generation failed — {} (skipping)", idx, exc)
            continue

        hypotheses.append(hypothesis)
        references.append(reference)

        if (idx + 1) % batch_log_every == 0:
            logger.info(
                "Generation progress: {}/{} samples done.",
                idx + 1,
                len(records),
            )

    logger.info(
        "Generation complete: {}/{} samples produced hypothesis+reference pairs.",
        len(hypotheses),
        len(records),
    )
    return hypotheses, references


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

def compute_bleu4(hypotheses: list[str], references: list[str]) -> float:
    """
    Compute corpus-level BLEU-4 using sacrebleu.

    sacrebleu expects:
      - sys_stream : list[str]   — one hypothesis per sentence
      - ref_streams: list[list[str]] — one list of references per reference set

    Returns the BLEU score as a float in [0, 100].  Blueprint target > 15.0
    (i.e. > 0.15 when normalised to [0,1]).
    """
    sacrebleu = _import_sacrebleu()
    bleu = sacrebleu.corpus_bleu(hypotheses, [references])
    return bleu.score  # float 0–100


def compute_rouge_l(hypotheses: list[str], references: list[str]) -> float:
    """
    Compute mean ROUGE-L F1 across all (hypothesis, reference) pairs.

    Uses the rouge-score library with tokenization.  Returns a float in [0, 1].
    Blueprint target > 0.35.
    """
    rouge_scorer = _import_rouge()
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)

    scores: list[float] = []
    for hyp, ref in zip(hypotheses, references):
        result = scorer.score(ref, hyp)
        scores.append(result["rougeL"].fmeasure)

    if not scores:
        return 0.0
    return sum(scores) / len(scores)


# ---------------------------------------------------------------------------
# Results data structures
# ---------------------------------------------------------------------------

@dataclass
class EvalTargetCheck:
    metric: str
    value: float
    target: str
    passed: bool

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "value": round(self.value, 6) if not math.isnan(self.value) else None,
            "target": self.target,
            "passed": self.passed,
        }


@dataclass
class EvalReport:
    model_path: str
    backend: str           # "hf" or "gguf"
    test_file: str
    total_records: int
    evaluated: int
    perplexity: float
    bleu4: float           # 0–100 (sacrebleu scale)
    rouge_l: float         # 0–1
    latency_mean_s: float  # mean generation latency per sample
    targets: list[EvalTargetCheck] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------

    def all_targets_met(self) -> bool:
        return all(t.passed for t in self.targets if not math.isnan(t.value))

    def summary(self) -> str:
        ppx_str = f"{self.perplexity:.4f}" if not math.isnan(self.perplexity) else "N/A (GGUF)"
        lines = [
            "=" * 66,
            "SAATHI AI — MODEL EVALUATION REPORT",
            f"Model   : {self.model_path}",
            f"Backend : {self.backend.upper()}",
            f"Test    : {self.test_file}",
            f"Samples : {self.evaluated} / {self.total_records} records evaluated",
            "=" * 66,
            f"  Perplexity       : {ppx_str:<12} target < {TARGET_PERPLEXITY_MAX}",
            f"  BLEU-4           : {self.bleu4:<12.4f} target > {TARGET_BLEU4_MIN * 100:.1f}",
            f"  ROUGE-L          : {self.rouge_l:<12.4f} target > {TARGET_ROUGE_L_MIN}",
            f"  Latency (mean)   : {self.latency_mean_s:.3f}s / sample",
            "-" * 66,
            "  TARGET CHECKS",
        ]
        for tc in self.targets:
            val_str = f"{tc.value:.4f}" if not math.isnan(tc.value) else "N/A"
            status = "PASS" if tc.passed else ("SKIP" if math.isnan(tc.value) else "FAIL")
            lines.append(f"    [{status}]  {tc.metric:<20} {val_str}  ({tc.target})")
        overall = "ALL TARGETS MET" if self.all_targets_met() else "SOME TARGETS MISSED"
        lines += ["-" * 66, f"  {overall}", "=" * 66]
        if self.errors:
            lines.append("ERRORS")
            for e in self.errors:
                lines.append(f"  • {e}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "model_path": self.model_path,
            "backend": self.backend,
            "test_file": self.test_file,
            "total_records": self.total_records,
            "evaluated": self.evaluated,
            "metrics": {
                "perplexity": round(self.perplexity, 6) if not math.isnan(self.perplexity) else None,
                "bleu4": round(self.bleu4, 6),
                "rouge_l": round(self.rouge_l, 6),
                "latency_mean_s": round(self.latency_mean_s, 4),
            },
            "targets": [t.to_dict() for t in self.targets],
            "all_targets_met": self.all_targets_met(),
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Core evaluation pipeline
# ---------------------------------------------------------------------------

def evaluate(
    backend: "HFBackend | GGUFBackend",
    records: list[dict],
    model_label: str,
    backend_name: str,
    test_file: str,
) -> EvalReport:
    """
    Run the full evaluation pipeline:
      1. Perplexity (HF only)
      2. Response generation
      3. BLEU-4
      4. ROUGE-L
      5. Latency measurement
    """
    errors: list[str] = []

    # ── 1. Perplexity ──────────────────────────────────────────────────
    logger.info("Computing perplexity over {} records…", len(records))
    t0 = time.perf_counter()
    perplexity = backend.compute_perplexity(records)
    ppx_elapsed = time.perf_counter() - t0
    if not math.isnan(perplexity):
        logger.info("Perplexity: {:.4f}  ({:.1f}s)", perplexity, ppx_elapsed)

    # ── 2. Generation + latency ────────────────────────────────────────
    logger.info("Generating responses for BLEU / ROUGE scoring…")
    gen_start = time.perf_counter()
    hypotheses, references = run_generation(backend, records)
    gen_elapsed = time.perf_counter() - gen_start
    latency_mean = gen_elapsed / max(len(hypotheses), 1)

    # ── 3. BLEU-4 ──────────────────────────────────────────────────────
    bleu4 = 0.0
    if hypotheses:
        try:
            bleu4 = compute_bleu4(hypotheses, references)
            logger.info("BLEU-4: {:.4f}", bleu4)
        except ImportError as exc:
            msg = f"BLEU-4 skipped: {exc}"
            logger.warning(msg)
            errors.append(msg)
    else:
        logger.warning("No hypothesis/reference pairs — BLEU-4 = 0.0")

    # ── 4. ROUGE-L ─────────────────────────────────────────────────────
    rouge_l = 0.0
    if hypotheses:
        try:
            rouge_l = compute_rouge_l(hypotheses, references)
            logger.info("ROUGE-L: {:.4f}", rouge_l)
        except ImportError as exc:
            msg = f"ROUGE-L skipped: {exc}"
            logger.warning(msg)
            errors.append(msg)
    else:
        logger.warning("No hypothesis/reference pairs — ROUGE-L = 0.0")

    # ── 5. Target checks ───────────────────────────────────────────────
    targets = [
        EvalTargetCheck(
            metric="Perplexity",
            value=perplexity,
            target=f"< {TARGET_PERPLEXITY_MAX}",
            passed=(not math.isnan(perplexity)) and (perplexity < TARGET_PERPLEXITY_MAX),
        ),
        EvalTargetCheck(
            metric="BLEU-4",
            value=bleu4,
            target=f"> {TARGET_BLEU4_MIN * 100:.1f}",
            # bleu4 is on 0–100 scale; blueprint target is > 0.15 i.e. > 15.0
            passed=bleu4 > TARGET_BLEU4_MIN * 100,
        ),
        EvalTargetCheck(
            metric="ROUGE-L",
            value=rouge_l,
            target=f"> {TARGET_ROUGE_L_MIN}",
            passed=rouge_l > TARGET_ROUGE_L_MIN,
        ),
    ]

    return EvalReport(
        model_path=model_label,
        backend=backend_name,
        test_file=test_file,
        total_records=len(records),
        evaluated=len(hypotheses),
        perplexity=perplexity,
        bleu4=bleu4,
        rouge_l=rouge_l,
        latency_mean_s=latency_mean,
        targets=targets,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "SAATHI AI — Evaluate a trained model on the test set. "
            "Computes perplexity, BLEU-4, and ROUGE-L."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    backend_group = parser.add_mutually_exclusive_group(required=True)
    backend_group.add_argument(
        "--model-path",
        metavar="PATH_OR_HUB_ID",
        help=(
            "HuggingFace model directory or hub model ID "
            "(e.g. ./merged/saathi-stage2 or Qwen/Qwen2.5-7B-Instruct)"
        ),
    )
    backend_group.add_argument(
        "--gguf-path",
        metavar="FILE",
        help="Path to a GGUF model file (llama-cpp-python backend).",
    )

    parser.add_argument(
        "--test-data",
        required=True,
        type=Path,
        metavar="FILE",
        help="Test JSONL file (output of split_data.py, e.g. stage2_test.jsonl).",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        metavar="FILE",
        help="Optional path to write JSON evaluation report.",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=500,
        metavar="N",
        help="Maximum number of test records to evaluate (default: 500).",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=256,
        metavar="N",
        help="Maximum tokens to generate per response (default: 256).",
    )
    parser.add_argument(
        "--n-ctx",
        type=int,
        default=2048,
        metavar="N",
        help="Context window size for GGUF backend (default: 2048).",
    )
    parser.add_argument(
        "--fail-on-miss",
        action="store_true",
        help="Exit with code 1 if any blueprint target is not met (for CI gating).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Loguru log level (default: INFO).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logger.remove()
    logger.add(sys.stderr, level=args.log_level, colorize=True)

    # ── Load test data ─────────────────────────────────────────────────
    test_path: Path = args.test_data
    if not test_path.exists():
        logger.error("Test data file not found: {}", test_path)
        return 1

    logger.info("Loading test records from '{}' (max={})…", test_path, args.max_samples)
    records = load_test_records(test_path, max_samples=args.max_samples)
    if not records:
        logger.error("No valid records found in {}", test_path)
        return 1
    logger.info("Loaded {} test records.", len(records))

    # ── Initialise backend ─────────────────────────────────────────────
    try:
        if args.model_path:
            backend: "HFBackend | GGUFBackend" = HFBackend(
                model_path=args.model_path,
                max_new_tokens=args.max_new_tokens,
            )
            backend_name = "hf"
            model_label = args.model_path
        else:
            gguf_path = args.gguf_path
            if not Path(gguf_path).exists():
                logger.error("GGUF file not found: {}", gguf_path)
                return 1
            backend = GGUFBackend(
                gguf_path=gguf_path,
                max_new_tokens=args.max_new_tokens,
                n_ctx=args.n_ctx,
            )
            backend_name = "gguf"
            model_label = gguf_path
    except ImportError as exc:
        logger.error("Backend initialisation failed: {}", exc)
        return 1
    except Exception as exc:
        logger.error("Failed to load model: {}", exc)
        return 1

    # ── Run evaluation ─────────────────────────────────────────────────
    logger.info("Starting evaluation…")
    report = evaluate(
        backend=backend,
        records=records,
        model_label=model_label,
        backend_name=backend_name,
        test_file=str(test_path),
    )

    logger.info("\n{}", report.summary())

    # ── Write JSON report ──────────────────────────────────────────────
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("w", encoding="utf-8") as fh:
            json.dump(report.to_dict(), fh, indent=2, ensure_ascii=False)
        logger.info("JSON report written → {}", args.report)

    # ── CI gate ────────────────────────────────────────────────────────
    if args.fail_on_miss and not report.all_targets_met():
        logger.error(
            "One or more blueprint targets were not met.  "
            "Review the evaluation report and retrain or tune the model."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
