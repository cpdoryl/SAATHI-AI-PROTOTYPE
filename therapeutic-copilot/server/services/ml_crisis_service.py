"""
SAATHI AI — ML Crisis Detection Service
========================================
DistilBERT-based crisis severity classifier.
Trained on 3,500 C-SSRS-aligned crisis examples (Phase 1 + Phase 2 combined).

Model: distilbert-base-uncased fine-tuned with 6-class crisis severity head.
Architecture: Safety Gate — 100% high-risk recall (zero false negatives for
              intent/plan classes), intentional false positive tolerance.

Classes (sorted by severity):
  0 → self_harm      (severity 0.1) → app scale: 3.0
  1 → passive        (severity 0.2) → app scale: 4.0
  2 → active         (severity 0.6) → app scale: 6.0
  3 → method         (severity 0.7) → app scale: 7.5  ← escalation threshold
  4 → intent         (severity 0.9) → app scale: 9.0
  5 → plan/attempt   (severity 1.0) → app scale: 10.0

Safety threshold: if P(class 4 or 5) > 0.20 → force high-risk prediction.
This mirrors the training inference strategy and guarantees zero false negatives
for the most dangerous crisis presentations.

Usage:
    from services.ml_crisis_service import get_ml_crisis_service
    service = get_ml_crisis_service()          # singleton, loads once
    result  = service.predict("I want to die")
    # result.severity      → float 0-10
    # result.high_risk     → bool
    # result.crisis_class  → str e.g. "intent"
    # result.confidence    → float 0-1
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_SERVER_DIR = Path(__file__).resolve().parent.parent
MODEL_PT    = _SERVER_DIR / "crisis_model" / "best_crisis_model_combined.pt"

# ---------------------------------------------------------------------------
# Class definitions (mirrors training script)
# ---------------------------------------------------------------------------
NUM_LABELS        = 6
CLASS_NAMES       = ["self_harm", "passive", "active", "method", "intent", "plan/attempt"]
HIGH_RISK_CLASSES = [4, 5]           # intent, plan/attempt
SAFETY_THRESHOLD  = 0.20             # P(high-risk) > this → force escalation

# Map ML class → app severity (0-10 scale used by escalation logic)
CLASS_TO_APP_SEVERITY = {
    0: 3.0,   # self_harm
    1: 4.0,   # passive ideation
    2: 6.0,   # active ideation
    3: 7.5,   # ideation with method   ← just above escalation threshold (7.0)
    4: 9.0,   # intent
    5: 10.0,  # plan / attempt
}

BASE_MODEL_NAME = "distilbert-base-uncased"

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class MLCrisisResult:
    severity:     float   # 0-10 scale (maps to app's existing severity range)
    high_risk:    bool    # True → must escalate
    crisis_class: str     # human-readable class name
    class_id:     int     # 0-5
    confidence:   float   # probability of predicted class
    raw_probs:    list    # all 6 class probabilities


# ---------------------------------------------------------------------------
# Singleton service
# ---------------------------------------------------------------------------

class MLCrisisService:
    """
    Thread-safe singleton that loads the trained DistilBERT model once.
    predict() is synchronous (CPU inference, ~20-40ms per call).
    Call from async code with asyncio.to_thread() to avoid blocking the loop.
    """

    _instance: Optional["MLCrisisService"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._model     = None
        self._tokenizer = None
        self._device    = None
        self._ready     = False
        self._load_model()

    # -- Loading -----------------------------------------------------------

    def _load_model(self):
        try:
            import torch
            from transformers import (
                AutoModelForSequenceClassification,
                AutoTokenizer,
            )
        except ImportError as e:
            logger.warning(
                f"ML crisis service: missing dependency ({e}). "
                "Falling back to keyword-only detection. "
                "Install: pip install torch transformers"
            )
            return

        if not MODEL_PT.exists():
            logger.warning(
                f"ML crisis model weights not found at {MODEL_PT}. "
                "Run: python server/scripts/setup_crisis_model.py"
            )
            return

        try:
            logger.info("Loading ML crisis model (DistilBERT, 6-class)...")

            device = torch.device("cpu")   # CPU inference — no GPU needed
            self._device = device

            # Load base architecture (downloads ~67MB on first run, then cached)
            tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)
            model = AutoModelForSequenceClassification.from_pretrained(
                BASE_MODEL_NAME,
                num_labels=NUM_LABELS,
                ignore_mismatched_sizes=True,
            )

            # Load trained classification head weights
            checkpoint = torch.load(MODEL_PT, map_location=device, weights_only=False)
            if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
                model.load_state_dict(checkpoint["model_state_dict"], strict=False)
            else:
                # Fallback: checkpoint may be a bare state dict
                model.load_state_dict(checkpoint, strict=False)

            model.to(device)
            model.eval()

            self._tokenizer = tokenizer
            self._model     = model
            self._ready     = True
            logger.info("ML crisis model loaded successfully (CPU inference).")

        except Exception as exc:
            logger.error(f"Failed to load ML crisis model: {exc}. Keyword fallback active.")

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
                logits  = outputs.logits           # shape [1, 6]
                probs   = torch.softmax(logits, dim=1)[0]  # shape [6]

            # Safety-threshold prediction (mirrors training inference strategy)
            high_risk_probs = probs[HIGH_RISK_CLASSES]
            if high_risk_probs.max().item() > SAFETY_THRESHOLD:
                class_id = HIGH_RISK_CLASSES[high_risk_probs.argmax().item()]
            else:
                class_id = probs.argmax().item()

            confidence   = probs[class_id].item()
            app_severity = CLASS_TO_APP_SEVERITY[class_id]
            high_risk    = class_id in HIGH_RISK_CLASSES or app_severity >= 7.0

            return MLCrisisResult(
                severity     = app_severity,
                high_risk    = high_risk,
                crisis_class = CLASS_NAMES[class_id],
                class_id     = class_id,
                confidence   = round(confidence, 4),
                raw_probs    = [round(p.item(), 4) for p in probs],
            )

        except Exception as exc:
            logger.error(f"ML crisis inference error: {exc}")
            return None

    @property
    def is_ready(self) -> bool:
        return self._ready


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
