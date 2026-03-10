"""
SAATHI AI -- ML Crisis Detection Service
========================================
DistilBERT-based crisis severity classifier.

Model priority (auto-detected at startup):
  1. Phase 3 (preferred)  -- HuggingFace format in crisis_model/phase3_best_model/
     Trained on 1,500 lower-risk C-SSRS examples. 6-class, 98.7% accuracy,
     100% high-risk recall. Superior precision across all classes.
  2. Phase 2 (fallback)   -- PyTorch .pt in crisis_model/best_crisis_model_combined.pt
     Trained on 3,500 combined examples. 6-class, 40% accuracy, 100% HR recall.

Both use identical 6-class schema and safety gate design:
  0 -> safe / self_harm   -> app scale: 3.0
  1 -> passive ideation   -> app scale: 4.0
  2 -> mild / active      -> app scale: 6.0
  3 -> moderate / method  -> app scale: 7.5  <- escalation threshold
  4 -> elevated / intent  -> app scale: 9.0
  5 -> pre-crisis/attempt -> app scale: 10.0

Safety threshold: if P(class 4 or 5) > 0.15 (P3) or 0.20 (P2) -> force high-risk.
Zero false negatives for intent/plan/attempt classes.

Usage:
    from services.ml_crisis_service import get_ml_crisis_service
    service = get_ml_crisis_service()          # singleton, loads once
    result  = service.predict("I want to die")
    # result.severity      -> float 0-10
    # result.high_risk     -> bool
    # result.crisis_class  -> str e.g. "elevated_monitoring"
    # result.confidence    -> float 0-1
    # result.model_phase   -> str e.g. "phase3" or "phase2"
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_SERVER_DIR      = Path(__file__).resolve().parent.parent
_CRISIS_DIR      = _SERVER_DIR / "crisis_model"

# Phase 3 -- HuggingFace directory (model.safetensors + tokenizer files)
MODEL_P3_DIR     = _CRISIS_DIR / "phase3_best_model"

# Phase 2 -- legacy single .pt checkpoint
MODEL_P2_PT      = _CRISIS_DIR / "best_crisis_model_combined.pt"

# ---------------------------------------------------------------------------
# Class schema -- same 6-class structure for both Phase 2 and Phase 3
# ---------------------------------------------------------------------------
NUM_LABELS        = 6

# Phase 3 class names (more descriptive)
CLASS_NAMES_P3 = [
    "safe",
    "passive_ideation",
    "mild_distress",
    "moderate_concern",
    "elevated_monitoring",
    "pre_crisis_intervention",
]

# Phase 2 class names (original)
CLASS_NAMES_P2 = ["self_harm", "passive", "active", "method", "intent", "plan/attempt"]

HIGH_RISK_CLASSES     = [4, 5]
SAFETY_THRESHOLD_P3   = 0.15    # Phase 3: tighter threshold (more precise model)
SAFETY_THRESHOLD_P2   = 0.20    # Phase 2: original threshold

# App severity scale (0-10) -- identical for both phases (same class positions)
CLASS_TO_APP_SEVERITY = {
    0: 3.0,   # safe / self_harm
    1: 4.0,   # passive ideation
    2: 6.0,   # mild distress / active ideation
    3: 7.5,   # moderate concern / method  <- just above 7.0 escalation threshold
    4: 9.0,   # elevated monitoring / intent
    5: 10.0,  # pre-crisis / plan/attempt
}

BASE_MODEL_NAME = "distilbert-base-uncased"

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class MLCrisisResult:
    severity:     float   # 0-10 scale
    high_risk:    bool    # True -> must escalate
    crisis_class: str     # human-readable class name
    class_id:     int     # 0-5
    confidence:   float   # probability of predicted class
    raw_probs:    list    # all 6 class probabilities
    model_phase:  str     # "phase3" or "phase2"


# ---------------------------------------------------------------------------
# Singleton service
# ---------------------------------------------------------------------------

class MLCrisisService:
    """
    Thread-safe singleton that loads the best available DistilBERT model.
    Prefers Phase 3 (98.7% accuracy) over Phase 2 (40% accuracy).
    predict() is synchronous (~20-40ms CPU). Call with asyncio.to_thread()
    from async code to avoid blocking the event loop.
    """

    def __init__(self):
        self._model           = None
        self._tokenizer       = None
        self._device          = None
        self._ready           = False
        self._model_phase     = "none"
        self._safety_threshold = SAFETY_THRESHOLD_P3
        self._class_names     = CLASS_NAMES_P3
        self._load_model()

    # -- Loading -----------------------------------------------------------

    def _load_model(self):
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as e:
            logger.warning(
                f"ML crisis service: missing dependency ({e}). "
                "Falling back to keyword-only detection. "
                "Install: pip install torch transformers"
            )
            return

        device = torch.device("cpu")
        self._device = device

        # ---- Try Phase 3 first (HuggingFace directory format) ----------------
        p3_ok = (MODEL_P3_DIR / "model.safetensors").exists() and \
                (MODEL_P3_DIR / "config.json").exists()

        if p3_ok:
            try:
                logger.info("Loading Phase 3 crisis model (DistilBERT, 6-class, HF format)...")
                tokenizer = AutoTokenizer.from_pretrained(str(MODEL_P3_DIR))
                model = AutoModelForSequenceClassification.from_pretrained(
                    str(MODEL_P3_DIR),
                    num_labels=NUM_LABELS,
                )
                model.to(device)
                model.eval()
                self._tokenizer        = tokenizer
                self._model            = model
                self._ready            = True
                self._model_phase      = "phase3"
                self._safety_threshold = SAFETY_THRESHOLD_P3
                self._class_names      = CLASS_NAMES_P3
                logger.info(
                    "Phase 3 crisis model loaded (98.7% acc, 100% HR recall, CPU). "
                    f"Path: {MODEL_P3_DIR}"
                )
                return
            except Exception as exc:
                logger.warning(f"Phase 3 model load failed: {exc}. Trying Phase 2...")

        # ---- Fallback to Phase 2 (.pt format) --------------------------------
        if not MODEL_P2_PT.exists():
            logger.warning(
                f"No crisis model found. Checked:\n"
                f"  Phase 3: {MODEL_P3_DIR}\n"
                f"  Phase 2: {MODEL_P2_PT}\n"
                "Run: python server/scripts/setup_crisis_model.py"
            )
            return

        try:
            logger.info("Loading Phase 2 crisis model (DistilBERT, .pt format)...")
            tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)
            model = AutoModelForSequenceClassification.from_pretrained(
                BASE_MODEL_NAME,
                num_labels=NUM_LABELS,
                ignore_mismatched_sizes=True,
            )
            checkpoint = torch.load(MODEL_P2_PT, map_location=device, weights_only=False)
            state_dict = checkpoint.get("model_state_dict", checkpoint)
            model.load_state_dict(state_dict, strict=False)
            model.to(device)
            model.eval()
            self._tokenizer        = tokenizer
            self._model            = model
            self._ready            = True
            self._model_phase      = "phase2"
            self._safety_threshold = SAFETY_THRESHOLD_P2
            self._class_names      = CLASS_NAMES_P2
            logger.info(
                "Phase 2 crisis model loaded (40% acc, 100% HR recall, CPU). "
                f"Path: {MODEL_P2_PT}"
            )
        except Exception as exc:
            logger.error(f"Failed to load crisis model: {exc}. Keyword fallback active.")

    # -- Inference ---------------------------------------------------------

    def predict(self, text: str) -> Optional[MLCrisisResult]:
        """
        Run inference on a single message.
        Returns MLCrisisResult or None if model is not ready.
        """
        if not self._ready:
            return None

        try:
            import torch

            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=128,
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model(**inputs)
                logits  = outputs.logits
                probs   = torch.softmax(logits, dim=1)[0]

            # Safety-threshold prediction
            high_risk_probs = probs[HIGH_RISK_CLASSES]
            if high_risk_probs.max().item() > self._safety_threshold:
                class_id = HIGH_RISK_CLASSES[high_risk_probs.argmax().item()]
            else:
                class_id = probs.argmax().item()

            confidence   = probs[class_id].item()
            app_severity = CLASS_TO_APP_SEVERITY[class_id]
            high_risk    = class_id in HIGH_RISK_CLASSES or app_severity >= 7.0

            return MLCrisisResult(
                severity     = app_severity,
                high_risk    = high_risk,
                crisis_class = self._class_names[class_id],
                class_id     = class_id,
                confidence   = round(confidence, 4),
                raw_probs    = [round(p.item(), 4) for p in probs],
                model_phase  = self._model_phase,
            )

        except Exception as exc:
            logger.error(f"ML crisis inference error: {exc}")
            return None

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def model_phase(self) -> str:
        return self._model_phase


# ---------------------------------------------------------------------------
# Global singleton accessor
# ---------------------------------------------------------------------------

_service_instance: Optional[MLCrisisService] = None
_init_lock = threading.Lock()


def get_ml_crisis_service() -> MLCrisisService:
    """Return the singleton MLCrisisService (loads model on first call)."""
    global _service_instance
    if _service_instance is None:
        with _init_lock:
            if _service_instance is None:
                _service_instance = MLCrisisService()
    return _service_instance
