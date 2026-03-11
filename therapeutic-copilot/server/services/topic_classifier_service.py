"""
SAATHI AI -- Topic Classifier Service
========================================
Singleton service: loads multi-label DistilBERT 5-class topic model,
exposes classify() which returns TopicResult.

Topic classes (can overlap — multi-label):
  workplace_stress, relationship_issues, academic_stress,
  health_concerns, financial_stress

BCEWithLogitsLoss model — per-class sigmoid thresholds, not softmax.
"""

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

# ─── Constants ────────────────────────────────────────────────────────────────
TOPICS = [
    "workplace_stress",
    "relationship_issues",
    "academic_stress",
    "health_concerns",
    "financial_stress",
]
NUM_LABELS = len(TOPICS)

DEFAULT_THRESHOLD = 0.50

MODEL_PATH     = Path(__file__).resolve().parents[1] / "ml_models" / "topic_classifier"
THRESHOLD_FILE = MODEL_PATH / "thresholds.json"


@dataclass
class TopicResult:
    primary_topics:     List[str]           # 1–2 detected topic(s)
    all_scores:         Dict[str, float]    # sigmoid prob per topic
    thresholds:         Dict[str, float]    # per-class threshold used
    is_multi_label:     bool                # True if 2+ topics detected
    processing_time_ms: float


class TopicClassifierService:
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
            self._model      = None
            self._tokenizer  = None
            self._thresholds = None
            self.is_ready    = False
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
                    f"Topic classifier model not found at {MODEL_PATH}. "
                    "Run: python scripts/setup_topic_model.py"
                )
                return

            logger.info("Loading topic classifier (DistilBERT, 5-label multi-label)...")
            self._tokenizer = AutoTokenizer.from_pretrained(str(MODEL_PATH))
            self._model     = AutoModelForSequenceClassification.from_pretrained(
                str(MODEL_PATH)
            )
            self._model.eval()

            # Load per-class thresholds from thresholds.json
            if THRESHOLD_FILE.exists():
                with open(THRESHOLD_FILE) as f:
                    thr_dict = json.load(f)
                self._thresholds = np.array(
                    [thr_dict.get(t, DEFAULT_THRESHOLD) for t in TOPICS],
                    dtype=np.float32,
                )
                logger.info(f"Topic thresholds loaded: {dict(zip(TOPICS, self._thresholds.round(3)))}")
            else:
                self._thresholds = np.full(NUM_LABELS, DEFAULT_THRESHOLD, dtype=np.float32)
                logger.warning("thresholds.json not found; using 0.50 for all topic classes.")

            import torch as _torch
            import numpy as _np
            self._torch = _torch
            self._np    = _np

            self.is_ready = True
            logger.info(f"Topic classifier loaded. Path: {MODEL_PATH}")

        except Exception as exc:
            logger.error(f"Topic classifier load failed: {exc}")
            self.is_ready = False

    def classify(self, text: str) -> Optional[TopicResult]:
        """
        Classify topics of `text` (multi-label).
        Returns TopicResult or None if model not ready.
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
                logits = self._model(**inputs).logits.numpy()[0]

            probs = 1.0 / (1.0 + self._np.exp(-logits))  # sigmoid
            preds = (probs >= self._thresholds).astype(int)

            # Edge case: if nothing predicted, assign topic with highest prob
            if preds.sum() == 0:
                preds[self._np.argmax(probs)] = 1

            primary_topics = [TOPICS[i] for i in range(NUM_LABELS) if preds[i] == 1]
            processing_ms  = round((time.time() - t0) * 1000, 1)

            return TopicResult(
                primary_topics     = primary_topics,
                all_scores         = {t: float(probs[i]) for i, t in enumerate(TOPICS)},
                thresholds         = {t: float(self._thresholds[i]) for i, t in enumerate(TOPICS)},
                is_multi_label     = len(primary_topics) > 1,
                processing_time_ms = processing_ms,
            )

        except Exception as exc:
            logger.error(f"Topic classifier inference error: {exc}")
            return None


# ─── Global singleton accessor ────────────────────────────────────────────────
_service_instance: Optional[TopicClassifierService] = None
_service_lock = threading.Lock()


def get_topic_service() -> TopicClassifierService:
    """Returns the singleton TopicClassifierService, initializing if needed."""
    global _service_instance
    if _service_instance is None:
        with _service_lock:
            if _service_instance is None:
                _service_instance = TopicClassifierService()
    return _service_instance
