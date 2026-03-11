"""
SAATHI AI -- Emotion Classifier Service
========================================
Singleton service that loads the trained DistilBERT emotion classifier
and exposes a classify() method used on every user message.

Model: distilbert-base-uncased fine-tuned, 8-class emotion classifier
Classes: anxiety, sadness, anger, fear, hopelessness, guilt, shame, neutral
Format: HuggingFace save_pretrained() directory (model.safetensors + tokenizer)
Inference: ~20-40ms on CPU

Usage:
    from services.emotion_classifier_service import get_emotion_service
    svc    = get_emotion_service()          # singleton
    result = svc.classify("I feel empty")
    # result["primary_emotion"]   -> "sadness"
    # result["secondary_emotion"] -> "hopelessness"
    # result["intensity"]         -> 0.83
    # result["confidence"]        -> 0.83
    # result["all_scores"]        -> dict of all 8 class probabilities
    # result["high_intensity_hopelessness"] -> bool (True if hopelessness > 0.80)
    # result["processing_time_ms"] -> float
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_SERVER_DIR  = Path(__file__).resolve().parent.parent
_MODEL_DIR   = _SERVER_DIR / "ml_models" / "emotion_classifier"

EMOTION_LABELS = [
    "anxiety", "sadness", "anger", "fear",
    "hopelessness", "guilt", "shame", "neutral",
]
LABEL2ID = {c: i for i, c in enumerate(EMOTION_LABELS)}
ID2LABEL = {i: c for i, c in enumerate(EMOTION_LABELS)}

# Secondary emotion threshold: show secondary if P >= this value
SECONDARY_THRESHOLD = 0.15

# Hopelessness high-intensity flag: triggers additional crisis pipeline check
HOPELESSNESS_HIGH_INTENSITY = 0.80

BASE_MODEL_NAME = "distilbert-base-uncased"


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class EmotionResult:
    primary_emotion:              str     # dominant emotion label
    secondary_emotion:            Optional[str]  # second emotion if P >= 0.15
    intensity:                    float   # probability of primary class
    confidence:                   float   # same as intensity (alias for API clarity)
    all_scores:                   dict    # {label: probability} for all 8 classes
    high_intensity_hopelessness:  bool    # True -> triggers crisis pipeline check
    processing_time_ms:           float


# ---------------------------------------------------------------------------
# Singleton service
# ---------------------------------------------------------------------------

class EmotionClassifierService:
    """
    Thread-safe singleton. Loads DistilBERT emotion model once at startup.
    classify() is synchronous (~20-40ms CPU). Call via asyncio.to_thread()
    from async routes to avoid blocking the event loop.
    """

    def __init__(self):
        self._model     = None
        self._tokenizer = None
        self._device    = None
        self._ready     = False
        self._load_model()

    def _load_model(self):
        try:
            import torch
            from transformers import (AutoModelForSequenceClassification,
                                       AutoTokenizer)
        except ImportError as e:
            logger.warning(
                f"Emotion service: missing dependency ({e}). "
                "Emotion detection disabled. "
                "Install: pip install torch transformers"
            )
            return

        device = torch.device("cpu")
        self._device = device

        if not (_MODEL_DIR / "model.safetensors").exists() and \
           not (_MODEL_DIR / "pytorch_model.bin").exists():
            logger.warning(
                f"Emotion classifier model not found at: {_MODEL_DIR}. "
                "Run: python server/scripts/setup_emotion_model.py"
            )
            return

        try:
            logger.info(
                f"Loading emotion classifier (DistilBERT, 8-class)..."
            )
            tokenizer = AutoTokenizer.from_pretrained(str(_MODEL_DIR))
            model     = AutoModelForSequenceClassification.from_pretrained(
                str(_MODEL_DIR),
                num_labels=len(EMOTION_LABELS),
            )
            model.to(device)
            model.eval()
            self._tokenizer = tokenizer
            self._model     = model
            self._ready     = True
            logger.info(
                f"Emotion classifier loaded. "
                f"Path: {_MODEL_DIR}"
            )
        except Exception as exc:
            logger.error(
                f"Failed to load emotion classifier: {exc}. "
                "Emotion detection disabled."
            )

    def classify(self, text: str) -> Optional[EmotionResult]:
        """
        Classify the emotion in a single utterance.
        Returns EmotionResult or None if model is not ready.
        """
        if not self._ready:
            return None

        try:
            import torch
            start_ms = time.time() * 1000

            inputs = self._tokenizer(
                text,
                max_length=128,
                truncation=True,
                padding="max_length",
                return_tensors="pt",
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model(**inputs)
                probs   = torch.softmax(outputs.logits, dim=-1)[0]

            probs_list = [round(float(p), 4) for p in probs]
            sorted_idx = sorted(range(len(probs_list)),
                                key=lambda i: probs_list[i], reverse=True)

            primary_idx   = sorted_idx[0]
            primary_label = EMOTION_LABELS[primary_idx]
            primary_prob  = probs_list[primary_idx]

            # Secondary: highest non-primary class above threshold
            secondary_label = None
            for idx in sorted_idx[1:]:
                if probs_list[idx] >= SECONDARY_THRESHOLD:
                    secondary_label = EMOTION_LABELS[idx]
                    break

            all_scores = {
                EMOTION_LABELS[i]: probs_list[i]
                for i in range(len(EMOTION_LABELS))
            }

            high_hopelessness = (
                primary_label == "hopelessness"
                and primary_prob >= HOPELESSNESS_HIGH_INTENSITY
            )

            elapsed_ms = time.time() * 1000 - start_ms

            return EmotionResult(
                primary_emotion=primary_label,
                secondary_emotion=secondary_label,
                intensity=round(primary_prob, 4),
                confidence=round(primary_prob, 4),
                all_scores=all_scores,
                high_intensity_hopelessness=high_hopelessness,
                processing_time_ms=round(elapsed_ms, 1),
            )

        except Exception as exc:
            logger.error(f"Emotion classification error: {exc}")
            return None

    @property
    def is_ready(self) -> bool:
        return self._ready


# ---------------------------------------------------------------------------
# Global singleton accessor
# ---------------------------------------------------------------------------

_service_instance: Optional[EmotionClassifierService] = None
_init_lock = threading.Lock()


def get_emotion_service() -> EmotionClassifierService:
    """Return the singleton EmotionClassifierService (loads model on first call)."""
    global _service_instance
    if _service_instance is None:
        with _init_lock:
            if _service_instance is None:
                _service_instance = EmotionClassifierService()
    return _service_instance
