"""
SAATHI AI -- Intent Classifier Service
=======================================
Singleton service: loads DistilBERT 7-class intent model, exposes classify().

Intent classes:
  seek_support, book_appointment, crisis_emergency,
  information_request, feedback_complaint, general_chat, assessment_request

Routing actions:
  THERAPEUTIC_CONVERSATION, BOOKING_FLOW, CRISIS_PROTOCOL,
  RAG_KNOWLEDGE_BASE, SUPPORT_HANDLER, CONVERSATIONAL, ASSESSMENT_ROUTER
"""

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

# ─── Constants ────────────────────────────────────────────────────────────────
INTENT_CLASSES = [
    "seek_support",
    "book_appointment",
    "crisis_emergency",
    "information_request",
    "feedback_complaint",
    "general_chat",
    "assessment_request",
]

INTENT_ROUTING: Dict[str, str] = {
    "seek_support":        "THERAPEUTIC_CONVERSATION",
    "book_appointment":    "BOOKING_FLOW",
    "crisis_emergency":    "CRISIS_PROTOCOL",
    "information_request": "RAG_KNOWLEDGE_BASE",
    "feedback_complaint":  "SUPPORT_HANDLER",
    "general_chat":        "CONVERSATIONAL",
    "assessment_request":  "ASSESSMENT_ROUTER",
}

# Secondary intent confidence threshold (lower than primary)
SECONDARY_THRESHOLD = 0.35

MODEL_PATH = Path(__file__).resolve().parents[1] / "ml_models" / "intent_classifier"


@dataclass
class IntentResult:
    primary_intent:      str
    confidence:          float
    routing_action:      str
    secondary_intent:    Optional[str]
    secondary_confidence: Optional[float]
    all_scores:          Dict[str, float]
    processing_time_ms:  float


class IntentClassifierService:
    """Thread-safe singleton — loads once, classifies on every message."""

    _instance = None
    _lock     = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._model     = None
            self._tokenizer = None
            self.is_ready   = False
            self._load_model()
            self._initialized = True

    def _load_model(self):
        try:
            import torch
            import numpy as np
            from transformers import (
                AutoModelForSequenceClassification,
                AutoTokenizer,
            )

            if not MODEL_PATH.exists():
                logger.warning(
                    f"Intent classifier model not found at {MODEL_PATH}. "
                    "Run: python scripts/setup_intent_model.py"
                )
                return

            logger.info("Loading intent classifier (DistilBERT, 7-class)...")
            self._tokenizer = AutoTokenizer.from_pretrained(str(MODEL_PATH))
            self._model     = AutoModelForSequenceClassification.from_pretrained(
                str(MODEL_PATH)
            )
            self._model.eval()

            # Store for inference
            import torch as _torch
            import numpy as _np
            self._torch = _torch
            self._np    = _np

            self.is_ready = True
            logger.info(f"Intent classifier loaded. Path: {MODEL_PATH}")

        except Exception as exc:
            logger.error(f"Intent classifier load failed: {exc}")
            self.is_ready = False

    def classify(self, text: str) -> Optional[IntentResult]:
        """
        Classify intent of `text`.
        Returns IntentResult or None if model not ready.
        """
        if not self.is_ready:
            return None

        t0 = time.time()
        try:
            inputs = self._tokenizer(
                text,
                max_length=128,
                truncation=True,
                padding="max_length",
                return_tensors="pt",
            )
            with self._torch.no_grad():
                logits = self._model(**inputs).logits
                probs  = self._torch.softmax(logits, dim=-1).numpy()[0]

            sorted_idx     = self._np.argsort(probs)[::-1]
            primary_idx    = sorted_idx[0]
            secondary_idx  = (
                sorted_idx[1]
                if probs[sorted_idx[1]] >= SECONDARY_THRESHOLD
                else None
            )

            primary_intent = INTENT_CLASSES[primary_idx]
            processing_ms  = round((time.time() - t0) * 1000, 1)

            return IntentResult(
                primary_intent       = primary_intent,
                confidence           = float(probs[primary_idx]),
                routing_action       = INTENT_ROUTING[primary_intent],
                secondary_intent     = (INTENT_CLASSES[secondary_idx]
                                        if secondary_idx is not None else None),
                secondary_confidence = (float(probs[secondary_idx])
                                        if secondary_idx is not None else None),
                all_scores           = {c: float(probs[i])
                                        for i, c in enumerate(INTENT_CLASSES)},
                processing_time_ms   = processing_ms,
            )

        except Exception as exc:
            logger.error(f"Intent classifier inference error: {exc}")
            return None


# ─── Global singleton accessor ────────────────────────────────────────────────
_service_instance: Optional[IntentClassifierService] = None
_service_lock = threading.Lock()


def get_intent_service() -> IntentClassifierService:
    """Returns the singleton IntentClassifierService, initializing if needed."""
    global _service_instance
    if _service_instance is None:
        with _service_lock:
            if _service_instance is None:
                _service_instance = IntentClassifierService()
    return _service_instance
