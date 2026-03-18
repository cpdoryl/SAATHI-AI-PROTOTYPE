"""
SAATHI AI — Assessment Router Service
Routes conversation context to the most clinically appropriate assessment.

Architecture:
  - Rule-based signal detection (production-ready, no ML weights needed)
  - Slot for RoBERTa-based ML model when trained weights are available
  - Called by chat_routes.py after 3+ therapeutic turns in Stage 2

Usage:
    svc = AssessmentRouterService()
    result = svc.route(conversation_history)
    # {'recommended_assessments': [...], 'primary_assessment': 'PHQ-9', ...}
"""
import re
import time
from typing import List, Dict, Optional


ASSESSMENTS = [
    "PHQ-9", "GAD-7", "PCL-5", "ISI",
    "OCI-R", "SPIN", "PSS", "WHO-5",
]

ASSESSMENT_DESCRIPTIONS = {
    "PHQ-9":  "depression screening (9 questions, ~3 minutes)",
    "GAD-7":  "anxiety screening (7 questions, ~2 minutes)",
    "PCL-5":  "PTSD screening (20 questions, ~7 minutes)",
    "ISI":    "insomnia severity assessment (7 questions, ~2 minutes)",
    "OCI-R":  "OCD screening (18 questions, ~5 minutes)",
    "SPIN":   "social anxiety screening (17 questions, ~4 minutes)",
    "PSS":    "perceived stress assessment (10 questions, ~3 minutes)",
    "WHO-5":  "mental wellbeing check (5 questions, ~1 minute)",
}

# ─── Signal dictionaries per assessment ───────────────────────────────────────

_SIGNALS: Dict[str, List[str]] = {
    "PHQ-9": [
        "depress", "hopeless", "sad", "low mood", "can't enjoy",
        "no interest", "anhedonia", "worthless", "no energy", "exhausted",
        "no motivation", "empty inside", "crying", "suicidal", "self-harm",
        "want to die", "better off dead", "sleep all day", "no appetite",
        "weight change",
    ],
    "GAD-7": [
        "anxious", "anxiety", "worry", "worried", "nervous",
        "on edge", "restless", "can't relax", "irritable", "tense",
        "panic", "fear", "dread", "what if", "overthinking",
        "racing thoughts", "can't stop worrying",
    ],
    "PCL-5": [
        "trauma", "accident", "assault", "abuse", "nightmare",
        "flashback", "intrusive", "hypervigilant", "avoid",
        "numb", "detach", "incident", "what happened",
        "can't forget", "reliving", "startle", "on guard",
    ],
    "ISI": [
        "insomnia", "can't sleep", "trouble sleeping", "wake up",
        "early morning", "sleep quality", "tired after sleep",
        "lying awake", "racing mind at night", "sleep problem",
    ],
    "OCI-R": [
        "obsess", "compuls", "checking", "hand wash", "contamination",
        "counting", "ordering", "intrusive thought", "rituals",
        "can't stop thinking", "symmetry", "hoarding",
    ],
    "SPIN": [
        "social anxiety", "afraid of people", "blush", "embarrass",
        "avoid social", "public speaking", "meeting people",
        "judged", "social situation", "parties scare",
    ],
    "PSS": [
        "stressed", "stress", "overwhelm", "burnout", "pressure",
        "out of control", "too much", "can't cope", "overloaded",
        "work stress", "life stress",
    ],
    "WHO-5": [
        "wellbeing", "well-being", "mood check", "how am i doing",
        "track progress", "feeling okay", "general mood",
    ],
}


def _prepare_context(conversation_history: List[Dict], max_turns: int = 5) -> str:
    """Flatten last N user turns into a single string for signal matching."""
    recent = conversation_history[-(max_turns * 2):]
    user_text = " ".join(
        msg.get("content", "")
        for msg in recent
        if msg.get("role") == "user"
    )
    return user_text.lower()


def _score_signals(text: str) -> Dict[str, float]:
    """Return a signal score 0–1 for each assessment."""
    scores: Dict[str, float] = {}
    for assessment, signals in _SIGNALS.items():
        hits = sum(1 for sig in signals if sig in text)
        scores[assessment] = min(hits / max(len(signals) * 0.3, 1), 1.0)
    return scores


class AssessmentRouterService:
    """
    Routes conversation context to recommended clinical assessments.

    Rule-based in production; designed to be swapped with trained
    RoBERTa-base multi-label classifier once weights are available.
    Set ML_ROUTER_MODEL_PATH in config to activate ML mode.
    """

    _instance: Optional["AssessmentRouterService"] = None

    def __new__(cls) -> "AssessmentRouterService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ml_ready = False
            cls._instance._try_load_ml_model()
        return cls._instance

    def _try_load_ml_model(self) -> None:
        """
        Attempt to load trained RoBERTa weights.
        Falls back to rule-based if model not found.
        """
        try:
            from config import settings
            model_path = getattr(settings, "ASSESSMENT_ROUTER_MODEL_PATH", "")
            if not model_path:
                return

            import torch
            from transformers import AutoTokenizer, RobertaForSequenceClassification
            import json, os

            if not os.path.exists(model_path):
                return

            self._tokenizer = AutoTokenizer.from_pretrained(model_path)
            self._model = RobertaForSequenceClassification.from_pretrained(model_path)
            self._model.eval()

            thresholds_path = os.path.join(model_path, "thresholds.json")
            if os.path.exists(thresholds_path):
                with open(thresholds_path) as f:
                    self._thresholds = json.load(f)
            else:
                self._thresholds = {a: 0.50 for a in ASSESSMENTS}

            self._ml_ready = True
            from loguru import logger
            logger.info(
                f"Assessment Router: ML model loaded from {model_path}"
            )
        except Exception:
            self._ml_ready = False

    def route(self, conversation_history: List[Dict]) -> Dict:
        """
        Analyse conversation and recommend assessments.

        Returns:
            {
                recommended_assessments: [{assessment, confidence, description, urgency}],
                primary_assessment: str | None,
                no_assessment_needed: bool,
                mode: 'ml' | 'rule_based',
                processing_time_ms: float,
            }
        """
        start = time.time()

        if self._ml_ready:
            result = self._route_ml(conversation_history)
        else:
            result = self._route_rule_based(conversation_history)

        result["processing_time_ms"] = round((time.time() - start) * 1000, 1)
        return result

    def _route_rule_based(self, conversation_history: List[Dict]) -> Dict:
        """Signal-matching router — no ML weights required."""
        context = _prepare_context(conversation_history)
        scores = _score_signals(context)

        THRESHOLD = 0.15
        recommended = []
        for assessment in ASSESSMENTS:
            conf = scores.get(assessment, 0.0)
            if conf >= THRESHOLD:
                recommended.append({
                    "assessment": assessment,
                    "confidence": round(conf, 2),
                    "description": ASSESSMENT_DESCRIPTIONS[assessment],
                    "urgency": "high" if conf >= 0.6 else "medium",
                })

        recommended.sort(key=lambda x: x["confidence"], reverse=True)
        recommended = recommended[:3]

        return {
            "recommended_assessments": recommended,
            "primary_assessment": recommended[0]["assessment"] if recommended else None,
            "no_assessment_needed": len(recommended) == 0,
            "mode": "rule_based",
        }

    def _route_ml(self, conversation_history: List[Dict]) -> Dict:
        """RoBERTa multi-label classification router."""
        import torch

        context = _prepare_context(conversation_history)
        inputs = self._tokenizer(
            context,
            max_length=512,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        )

        with torch.no_grad():
            probs = torch.sigmoid(
                self._model(**inputs).logits
            ).numpy()[0]

        recommended = []
        for i, assessment in enumerate(ASSESSMENTS):
            threshold = self._thresholds.get(assessment, 0.50)
            if probs[i] >= threshold:
                recommended.append({
                    "assessment": assessment,
                    "confidence": round(float(probs[i]), 3),
                    "description": ASSESSMENT_DESCRIPTIONS[assessment],
                    "urgency": "high" if probs[i] >= 0.80 else "medium",
                })

        recommended.sort(key=lambda x: x["confidence"], reverse=True)
        recommended = recommended[:3]

        return {
            "recommended_assessments": recommended,
            "primary_assessment": recommended[0]["assessment"] if recommended else None,
            "no_assessment_needed": len(recommended) == 0,
            "mode": "ml",
        }

    def build_offer_message(self, result: Dict) -> str:
        """
        Build a natural conversational message to offer the assessment.
        Used by chat_routes.py to suggest assessment in the chat flow.
        """
        if result.get("no_assessment_needed"):
            return ""

        primary = result.get("primary_assessment")
        if not primary:
            return ""

        desc = ASSESSMENT_DESCRIPTIONS.get(primary, "a brief assessment")
        return (
            f"Based on what you've shared with me, it would be helpful to do "
            f"a quick {desc}. It takes just a few minutes and will help me "
            f"understand how you're doing more clearly. Would you be open to that?"
        )
