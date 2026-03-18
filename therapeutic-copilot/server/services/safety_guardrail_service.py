"""
SAATHI AI -- Safety Guardrail Service
======================================
5-layer safety pipeline that intercepts every LLM response before it
reaches the user.  Designed to medical-grade standards (IEC 62304 /
FDA AI/ML SaMD guidance).

Pipeline order (fail-fast: first triggered layer wins):
  Layer 1 -- Hard block rules          (regex, <1ms,   BLOCK)
  Layer 2 -- Crisis protocol validator (<2ms,           ESCALATE)
  Layer 3 -- Hallucination detector    (<5ms,           REDACT)
  Layer 4 -- ML safety classifier      (~30ms,          BLOCK/ESCALATE/REDACT)
  Layer 5 -- Response sanitizer        (always runs,    builds safe fallback)

Actions:
  PASS      -- response is safe, return as-is
  REDACT    -- response contains correctable content; return modified_response
  BLOCK     -- response is harmful; return category-specific safe fallback
  ESCALATE  -- crisis not adequately handled; inject crisis resources

All interventions are written to a structured audit log for clinical compliance.
"""

import re
import os
import sys
import io
import json
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from loguru import logger

# ---------------------------------------------------------------------------
# Validated Indian mental-health crisis resources (verified 2026)
# ---------------------------------------------------------------------------
CRISIS_RESOURCES = (
    "iCall: +91-9152987821 | "
    "Vandrevala Foundation: 1860-2662-345 | "
    "NIMHANS: 080-46110007 | "
    "AASRA: 9820466627"
)

# ---------------------------------------------------------------------------
# Layer 1 -- Hard-block regex patterns
# Matches self-harm instructions, overdose guidance, suicide methods.
# Any match -> immediate BLOCK regardless of context.
# ---------------------------------------------------------------------------
HARD_BLOCK_PATTERNS: list[tuple[str, str]] = [
    # (pattern, reason_code)
    (r"how\s+to\s+(hang|overdose|cut|hurt|kill|end\s+your\s+life)", "SELF_HARM_INSTRUCTION"),
    (r"step[- ]by[- ]step.{0,40}?(suicide|self[- ]?harm)", "SELF_HARM_INSTRUCTION"),
    (r"(take|swallow|consume).{0,30}(all|entire|whole).{0,20}(pills|tablets|medication|capsules)", "OVERDOSE_INSTRUCTION"),
    (r"carbon\s+monoxide.{0,30}(method|technique|way|use|effective)", "SELF_HARM_INSTRUCTION"),
    (r"(deeper|effective|better).{0,20}(cut|cutting|slash|wrist)", "SELF_HARM_INSTRUCTION"),
    (r"(best|easiest|painless|quick).{0,30}(way|method).{0,30}(to\s+die|suicide|end\s+(it|life))", "SELF_HARM_INSTRUCTION"),
    (r"(tie|knot|noose).{0,30}(neck|hang)", "SELF_HARM_INSTRUCTION"),
    (r"(lethal|fatal)\s+dose.{0,20}(of\s+)?\w+", "OVERDOSE_INSTRUCTION"),
]

# ---------------------------------------------------------------------------
# Layer 2 -- Crisis protocol validator
# If the user message signals active crisis (severity >= 7) and the LLM
# response does NOT include any escalation markers, inject resources.
# ---------------------------------------------------------------------------
CRISIS_ESCALATION_MARKERS = [
    r"icall", r"vandrevala", r"nimhans", r"aasra",
    r"\+91[-\s]?9152987821", r"1860[-\s]?2662[-\s]?345",
    r"080[-\s]?46110007", r"9820466627",
    r"helpline", r"hotline", r"emergency", r"crisis\s+line",
    r"call\s+\d{3,}",
]

# ---------------------------------------------------------------------------
# Layer 3 -- Hallucination detector
# Three categories:
#   A) Phone number hallucination   -- wrong/invented crisis numbers
#   B) Medication dosage            -- dangerously high or fabricated doses
#   C) Scope violation              -- AI claiming to diagnose/prescribe
# ---------------------------------------------------------------------------

# Approved phone numbers (regex strings) -- add more as validated
APPROVED_PHONE_PATTERNS = [
    r"\+91[-\s]?9152987821",   # iCall
    r"9152987821",
    r"1860[-\s]?2662[-\s]?345",  # Vandrevala
    r"18602662345",
    r"080[-\s]?46110007",      # NIMHANS
    r"08046110007",
    r"9820466627",             # AASRA
    r"1[-\s]?800",             # generic toll-free OK
    r"112",                    # national emergency
    r"100",                    # police
    r"102",                    # ambulance
    r"108",                    # emergency
]

# Regex to find any phone-number-like string in the response
PHONE_CANDIDATE_RE = re.compile(
    r"\b(\+?91[-\s]?)?(\d[\d\s\-]{7,14}\d)\b"
)

# Medication dosage: flag doses that seem dangerously high
# Pattern: <number> <unit> of <drug> or <drug> <number> <unit>
DANGEROUS_DOSAGE_RE = re.compile(
    r"\b(\d{3,})\s*(mg|mcg|ml|g)\b.{0,30}?(sertraline|fluoxetine|paroxetine|escitalopram|"
    r"venlafaxine|duloxetine|quetiapine|olanzapine|risperidone|lithium|clonazepam|"
    r"alprazolam|diazepam|lorazepam|zolpidem|tramadol|codeine|morphine|oxycodone)",
    re.IGNORECASE,
)

# Scope-violation phrases: AI claiming clinical authority
SCOPE_VIOLATION_RE = re.compile(
    r"\b(I\s+(diagnose|am\s+diagnosing|can\s+diagnose|prescribe|am\s+prescribing|"
    r"recommend\s+you\s+take|advise\s+you\s+to\s+take)\b)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Safe fallback responses by category
# ---------------------------------------------------------------------------
SAFE_FALLBACKS = {
    "SELF_HARM_INSTRUCTION": (
        "I want you to know you're not alone in this. "
        "If you're in crisis right now, please reach out to someone who can help immediately.\n\n"
        f"{CRISIS_RESOURCES}"
    ),
    "OVERDOSE_INSTRUCTION": (
        "I'm not able to provide information about medications in that way. "
        "If you're in distress, please contact a healthcare professional or crisis line.\n\n"
        f"{CRISIS_RESOURCES}"
    ),
    "CRISIS_MISSING_ESCALATION": (
        "It sounds like you may be going through a really difficult time. "
        "Please know there are people who can support you right now.\n\n"
        f"{CRISIS_RESOURCES}"
    ),
    "HALLUCINATED_PHONE": (
        "I want to make sure you have accurate crisis support information. "
        "Please use these verified resources:\n\n"
        f"{CRISIS_RESOURCES}"
    ),
    "DANGEROUS_DOSAGE": (
        "I'm not able to provide specific medication dosage guidance. "
        "Please consult your doctor or pharmacist for any questions about medications."
    ),
    "SCOPE_VIOLATION": (
        "As an AI support tool, I'm not able to diagnose conditions or prescribe treatments. "
        "Please speak with a qualified mental health professional for clinical guidance."
    ),
    "ML_HARMFUL": (
        "I want to make sure our conversation stays supportive and helpful. "
        "Could you share more about what's on your mind right now?"
    ),
    "ML_CRISIS_MISSING": (
        "I hear that things feel very hard. You don't have to face this alone.\n\n"
        f"{CRISIS_RESOURCES}"
    ),
    "ML_TOXIC": (
        "I want to make sure I'm being as helpful as possible. "
        "Let's take a breath and approach this together with kindness."
    ),
}


# ---------------------------------------------------------------------------
# GuardrailResult dataclass
# ---------------------------------------------------------------------------
@dataclass
class GuardrailResult:
    """
    Result from the 5-layer safety pipeline.

    action          : PASS | REDACT | BLOCK | ESCALATE
    reason_codes    : list of triggered reason codes (empty if PASS)
    original_response: the raw LLM output
    modified_response: safe response to return to user (= original if PASS)
    layers_triggered: which layers fired (for audit)
    latency_ms      : total guardrail processing time
    audit_entry     : structured dict for compliance log
    """
    action: str
    reason_codes: list = field(default_factory=list)
    original_response: str = ""
    modified_response: str = ""
    layers_triggered: list = field(default_factory=list)
    latency_ms: float = 0.0
    audit_entry: dict = field(default_factory=dict)

    @property
    def safe_response(self) -> str:
        return self.modified_response or self.original_response


# ---------------------------------------------------------------------------
# Singleton ML model loader (Layer 4)
# ---------------------------------------------------------------------------
class _MLSafetyClassifier:
    """
    Lazy-loaded DeBERTa-v3-small multi-label safety classifier.
    Singleton -- model loaded once per process.
    """
    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._label_cfg: Optional[dict] = None
        self._device = None
        self._ready = False
        self._load_attempted = False

    def _load(self):
        if self._load_attempted:
            return
        self._load_attempted = True

        model_path_str = os.environ.get("SAFETY_GUARDRAIL_MODEL_PATH", "")
        if not model_path_str:
            logger.warning(
                "SAFETY_GUARDRAIL_MODEL_PATH not set -- "
                "Layer 4 ML classifier disabled (Layers 1-3 still active)"
            )
            return

        model_path = Path(model_path_str)
        cfg_path = model_path / "model_config.json"
        label_path = model_path / "label_config.json"

        if not cfg_path.exists() or not label_path.exists():
            logger.warning(
                f"Safety model config not found at {model_path} -- "
                "Layer 4 ML classifier disabled"
            )
            return

        try:
            import torch
            from transformers import (
                AutoTokenizer,
                AutoModelForSequenceClassification,
            )
            import numpy as np

            self._np = np

            self._label_cfg = json.loads(label_path.read_text(encoding="utf-8"))
            self._tokenizer = AutoTokenizer.from_pretrained(
                str(model_path), trust_remote_code=True
            )
            self._model = AutoModelForSequenceClassification.from_pretrained(
                str(model_path), trust_remote_code=True
            )
            self._model.eval()
            self._device = torch.device(
                "cuda" if torch.cuda.is_available() else "cpu"
            )
            self._model.to(self._device)
            self._torch = torch
            self._ready = True
            logger.info(
                f"[SafetyGuardrail] ML classifier loaded from {model_path} "
                f"on {self._device}"
            )
        except Exception as exc:
            logger.error(
                f"[SafetyGuardrail] Failed to load ML classifier: {exc} -- "
                "Layer 4 disabled"
            )

    @property
    def is_ready(self) -> bool:
        if not self._load_attempted:
            self._load()
        return self._ready

    def predict(self, text: str) -> dict:
        """
        Returns {label: probability} dict.
        Empty dict if model not loaded.
        """
        if not self.is_ready:
            return {}
        try:
            import numpy as np
            enc = self._tokenizer(
                text,
                max_length=256,
                padding="max_length",
                truncation=True,
                return_tensors="pt",
            ).to(self._device)
            with self._torch.no_grad():
                logits = self._model(**enc).logits[0].cpu().numpy()
            probs = 1.0 / (1.0 + np.exp(-logits))
            cfg = self._label_cfg
            result = {}
            for i, lbl in enumerate(cfg["labels"]):
                threshold = (
                    cfg["critical_threshold"]
                    if lbl in cfg.get("critical_labels", [])
                    else cfg["classification_threshold"]
                )
                result[lbl] = float(probs[i])
                result[f"{lbl}_triggered"] = bool(probs[i] >= threshold)
            return result
        except Exception as exc:
            logger.warning(f"[SafetyGuardrail] ML predict error: {exc}")
            return {}


_ml_classifier = _MLSafetyClassifier()


# ---------------------------------------------------------------------------
# Main SafetyGuardrailService
# ---------------------------------------------------------------------------
class SafetyGuardrailService:
    """
    5-layer safety guardrail.  Instantiate once and call .inspect() for
    every LLM response before delivering to user.

    Usage:
        guardrail = SafetyGuardrailService()
        result = guardrail.inspect(
            response=llm_response,
            user_message=user_text,
            crisis_active=crisis_result["severity"] >= 7,
            session_id=session_id,
        )
        final_response = result.safe_response
    """

    def __init__(self):
        # Pre-compile all regexes for performance
        self._hard_block_re = [
            (re.compile(pat, re.IGNORECASE), code)
            for pat, code in HARD_BLOCK_PATTERNS
        ]
        self._crisis_marker_re = [
            re.compile(m, re.IGNORECASE)
            for m in CRISIS_ESCALATION_MARKERS
        ]
        self._approved_phone_re = [
            re.compile(p) for p in APPROVED_PHONE_PATTERNS
        ]
        self._phone_candidate_re = PHONE_CANDIDATE_RE
        self._dangerous_dosage_re = DANGEROUS_DOSAGE_RE
        self._scope_violation_re = SCOPE_VIOLATION_RE

        # Audit log file path (structured JSONL)
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        self._audit_log_path = log_dir / "safety_guardrail_audit.jsonl"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def inspect(
        self,
        response: str,
        user_message: str = "",
        crisis_active: bool = False,
        session_id: str = "",
        stage: int = 0,
    ) -> GuardrailResult:
        """
        Run all 5 layers against the LLM response.
        Returns GuardrailResult — caller uses .safe_response for delivery.
        """
        t_start = time.perf_counter()
        reason_codes: list[str] = []
        layers_triggered: list[str] = []
        action = "PASS"
        modified_response = response

        # ── Layer 1: Hard block rules ─────────────────────────────────
        layer1_codes = self._layer1_hard_block(response)
        if layer1_codes:
            reason_codes.extend(layer1_codes)
            layers_triggered.append("L1_HARD_BLOCK")
            action = "BLOCK"
            # Choose most-specific fallback
            primary_code = layer1_codes[0]
            modified_response = SAFE_FALLBACKS.get(
                primary_code, SAFE_FALLBACKS["SELF_HARM_INSTRUCTION"]
            )
            # Hard block is terminal — skip remaining layers
            return self._finalise(
                action, reason_codes, response, modified_response,
                layers_triggered, t_start, session_id, stage, user_message,
            )

        # ── Layer 2: Crisis protocol validator ───────────────────────
        if crisis_active:
            escalation_missing = not self._has_crisis_escalation(response)
            if escalation_missing:
                reason_codes.append("CRISIS_MISSING_ESCALATION")
                layers_triggered.append("L2_CRISIS_VALIDATOR")
                action = "ESCALATE"
                modified_response = (
                    response.rstrip()
                    + "\n\n---\n"
                    + SAFE_FALLBACKS["CRISIS_MISSING_ESCALATION"]
                )

        # ── Layer 3: Hallucination detector ──────────────────────────
        l3_action, l3_codes, l3_response = self._layer3_hallucination(
            response if action == "PASS" else modified_response
        )
        if l3_codes:
            reason_codes.extend(l3_codes)
            layers_triggered.append("L3_HALLUCINATION")
            if action in ("PASS",):
                action = l3_action
            modified_response = l3_response

        # ── Layer 4: ML safety classifier ────────────────────────────
        if action == "PASS":
            ml_action, ml_codes = self._layer4_ml_classify(response)
            if ml_codes:
                reason_codes.extend(ml_codes)
                layers_triggered.append("L4_ML_CLASSIFIER")
                action = ml_action
                primary_ml = ml_codes[0]
                modified_response = SAFE_FALLBACKS.get(
                    primary_ml, SAFE_FALLBACKS["ML_HARMFUL"]
                )

        # ── Layer 5: Sanitizer ────────────────────────────────────────
        # Always run to apply final cleanup (even on PASS)
        modified_response = self._layer5_sanitize(modified_response)

        return self._finalise(
            action, reason_codes, response, modified_response,
            layers_triggered, t_start, session_id, stage, user_message,
        )

    # ------------------------------------------------------------------
    # Layer implementations
    # ------------------------------------------------------------------
    def _layer1_hard_block(self, text: str) -> list[str]:
        """Return list of triggered reason codes; empty if safe."""
        codes = []
        for compiled_re, code in self._hard_block_re:
            if compiled_re.search(text):
                codes.append(code)
        return codes

    def _has_crisis_escalation(self, text: str) -> bool:
        """True if response already contains at least one crisis marker."""
        for compiled_re in self._crisis_marker_re:
            if compiled_re.search(text):
                return True
        return False

    def _layer3_hallucination(self, text: str) -> tuple[str, list[str], str]:
        """
        Returns (action, reason_codes, possibly_modified_text).
        action is REDACT if hallucination found, PASS otherwise.
        """
        codes: list[str] = []
        modified = text

        # A) Phone number validation
        # Find all phone-number-like strings in response
        candidates = self._phone_candidate_re.findall(text)
        for _prefix, number_raw in candidates:
            number_clean = re.sub(r"[\s\-]", "", (_prefix or "") + number_raw)
            # Check if this number matches any approved pattern
            approved = any(
                r.search(number_clean) for r in self._approved_phone_re
            )
            if not approved and len(number_clean) >= 7:
                codes.append("HALLUCINATED_PHONE")
                # Redact the hallucinated number and append correct resources
                modified = re.sub(
                    re.escape((_prefix or "") + number_raw),
                    "[VERIFIED RESOURCES BELOW]",
                    modified,
                )
                modified = (
                    modified.rstrip()
                    + "\n\nPlease use these verified crisis resources:\n"
                    + CRISIS_RESOURCES
                )
                break  # one pass; re-check not needed for prototype

        # B) Dangerous medication dosage
        if self._dangerous_dosage_re.search(text):
            codes.append("DANGEROUS_DOSAGE")
            modified = SAFE_FALLBACKS["DANGEROUS_DOSAGE"]

        # C) Scope violation (AI claiming to diagnose / prescribe)
        if self._scope_violation_re.search(text):
            codes.append("SCOPE_VIOLATION")
            modified = SAFE_FALLBACKS["SCOPE_VIOLATION"]

        action = "REDACT" if codes else "PASS"
        return action, codes, modified

    def _layer4_ml_classify(self, text: str) -> tuple[str, list[str]]:
        """
        Run DeBERTa multi-label classifier.
        Returns (action, reason_codes).
        """
        if not _ml_classifier.is_ready:
            return "PASS", []

        predictions = _ml_classifier.predict(text)
        if not predictions:
            return "PASS", []

        codes: list[str] = []
        action = "PASS"

        if predictions.get("harmful_content_triggered"):
            codes.append("ML_HARMFUL")
            action = "BLOCK"

        if predictions.get("crisis_escalation_missing_triggered"):
            codes.append("ML_CRISIS_MISSING")
            action = "ESCALATE" if action == "PASS" else action

        if predictions.get("toxic_language_triggered"):
            codes.append("ML_TOXIC")
            action = "BLOCK" if action == "PASS" else action

        if predictions.get("hallucinated_fact_triggered"):
            codes.append("ML_HALLUCINATED_FACT")
            action = "REDACT" if action == "PASS" else action

        if predictions.get("scope_violation_triggered"):
            codes.append("ML_SCOPE_VIOLATION")
            action = "REDACT" if action == "PASS" else action

        return action, codes

    def _layer5_sanitize(self, text: str) -> str:
        """
        Final cleanup pass on whatever text will be returned:
        - Remove any residual hard-block phrases that might have crept into
          an otherwise sanitized response.
        - Trim excessive whitespace.
        """
        for compiled_re, _code in self._hard_block_re:
            if compiled_re.search(text):
                # Shouldn't happen (L1 catches these), but belt-and-suspenders
                text = SAFE_FALLBACKS["SELF_HARM_INSTRUCTION"]
                break
        return text.strip()

    # ------------------------------------------------------------------
    # Result finalisation + audit logging
    # ------------------------------------------------------------------
    def _finalise(
        self,
        action: str,
        reason_codes: list,
        original: str,
        modified: str,
        layers_triggered: list,
        t_start: float,
        session_id: str,
        stage: int,
        user_message: str,
    ) -> GuardrailResult:
        latency_ms = (time.perf_counter() - t_start) * 1000

        audit_entry = {
            "ts":              time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "session_id":      session_id,
            "stage":           stage,
            "action":          action,
            "reason_codes":    reason_codes,
            "layers_triggered": layers_triggered,
            "latency_ms":      round(latency_ms, 2),
            "response_len":    len(original),
            "user_msg_snippet": user_message[:80] if user_message else "",
        }

        # Only log non-PASS events to reduce log volume; always log BLOCK/ESCALATE
        if action != "PASS":
            self._write_audit(audit_entry)
            logger.warning(
                f"[SafetyGuardrail] {action} | session={session_id} | "
                f"codes={reason_codes} | layers={layers_triggered} | "
                f"{latency_ms:.1f}ms"
            )
        else:
            logger.debug(
                f"[SafetyGuardrail] PASS | session={session_id} | "
                f"{latency_ms:.1f}ms"
            )

        return GuardrailResult(
            action=action,
            reason_codes=reason_codes,
            original_response=original,
            modified_response=modified,
            layers_triggered=layers_triggered,
            latency_ms=round(latency_ms, 2),
            audit_entry=audit_entry,
        )

    def _write_audit(self, entry: dict):
        """Append structured audit entry to JSONL log file."""
        try:
            with open(self._audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.error(f"[SafetyGuardrail] Audit log write failed: {exc}")


# ---------------------------------------------------------------------------
# Module-level singleton accessor (mirrors other service patterns in repo)
# ---------------------------------------------------------------------------
_guardrail_instance: Optional[SafetyGuardrailService] = None


def get_guardrail_service() -> SafetyGuardrailService:
    """Return the module-level singleton SafetyGuardrailService."""
    global _guardrail_instance
    if _guardrail_instance is None:
        _guardrail_instance = SafetyGuardrailService()
        logger.info("[SafetyGuardrail] Service initialised")
    return _guardrail_instance
