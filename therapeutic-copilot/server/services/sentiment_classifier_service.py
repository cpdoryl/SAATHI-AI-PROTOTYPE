#!/usr/bin/env python3
"""
Sentiment Classifier Service for SAATHI AI Server

Singleton service that:
1. Loads the trained DistilBERT sentiment classifier
2. Classifies user messages into positive/negative/neutral
3. Computes valence scores (-1.0 to +1.0)
4. Tracks session-level sentiment trends
5. Provides contextual prompts for the LLM

Integration point:
  therapeutic_ai_service.py :: process_message()
    ↓
    await sentiment_classifier_service.classify(utterance, session_id)
"""

import torch
import numpy as np
import time
from collections import deque
from typing import Optional, Dict, List
from transformers import AutoTokenizer, AutoModelForSequenceClassification


class SentimentClassifierService:
    """
    Singleton service for sentiment classification with session tracking.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_path: str = "./server/ml_models/sentiment_classifier"):
        """
        Initialize sentiment classifier.

        Args:
            model_path: Path to trained model directory
        """
        if self._initialized:
            return

        self.model_path = model_path
        self.sentiment_classes = ["negative", "neutral", "positive"]

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
            self.model.eval()

            # Try to use GPU if available
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)

            # Session-level tracking: session_id → deque of valence scores
            self.session_history: Dict[str, deque] = {}

            self.is_ready = True
            self._initialized = True

            print("[SentimentClassifierService] Model loaded successfully.")

        except Exception as e:
            print(f"[SentimentClassifierService] Failed to load model: {e}")
            self.is_ready = False
            self._initialized = True

    def classify(self, utterance: str, session_id: Optional[str] = None) -> Optional[Dict]:
        """
        Classify sentiment of a user utterance.

        Args:
            utterance: User message text
            session_id: Optional session ID for trend tracking

        Returns:
            Dict with sentiment, valence_score, confidence, and session trend
            or None if model not ready
        """

        if not self.is_ready:
            return None

        start_time = time.time()

        try:
            # Tokenize
            inputs = self.tokenizer(
                utterance,
                max_length=128,
                truncation=True,
                padding='max_length',
                return_tensors='pt'
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Inference
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits[0].cpu().numpy()
                probs = torch.softmax(outputs.logits, dim=-1)[0].cpu().numpy()

            # Get primary sentiment
            primary_idx = np.argmax(probs)
            sentiment = self.sentiment_classes[primary_idx]
            confidence = float(probs[primary_idx])

            # Compute valence score: positive=1.0, neutral=0.0, negative=-1.0
            valence_score = float(
                probs[2] * 1.0 +  # positive
                probs[1] * 0.0 +  # neutral
                probs[0] * -1.0   # negative
            )

            result = {
                "sentiment": sentiment,
                "valence_score": valence_score,
                "confidence": confidence,
                "all_scores": {
                    self.sentiment_classes[i]: float(probs[i])
                    for i in range(len(self.sentiment_classes))
                },
                "processing_time_ms": round((time.time() - start_time) * 1000, 1),
            }

            # Session trend tracking
            if session_id:
                if session_id not in self.session_history:
                    self.session_history[session_id] = deque(maxlen=20)

                self.session_history[session_id].append(valence_score)
                history = list(self.session_history[session_id])

                if len(history) >= 3:
                    # Determine trend direction
                    if history[-1] > history[0]:
                        trend_direction = "improving"
                    elif history[-1] < history[0]:
                        trend_direction = "declining"
                    else:
                        trend_direction = "stable"

                    result["session_trend"] = {
                        "last_n_turns": history[-5:],
                        "trend_direction": trend_direction,
                        "average_valence": float(np.mean(history)),
                    }

            return result

        except Exception as e:
            print(f"[SentimentClassifierService] Error during classification: {e}")
            return None

    def build_prompt_context(self, sentiment_result: Optional[Dict]) -> str:
        """
        Build LLM system prompt context block from sentiment classification.

        Args:
            sentiment_result: Output from classify()

        Returns:
            String block to be appended to LLM system prompt
        """

        if not sentiment_result:
            return ""

        sentiment = sentiment_result.get("sentiment", "unknown")
        valence = sentiment_result.get("valence_score", 0.0)
        trend = sentiment_result.get("session_trend", {})
        trend_dir = trend.get("trend_direction", "unknown")
        avg_valence = trend.get("average_valence", valence)

        block = f"""
## Sentiment Analysis (Coarse-Grained Session Level)
- **Current Message Sentiment**: {sentiment} (valence: {valence:+.2f})
- **Session Trend**: {trend_dir} (session average valence: {avg_valence:+.2f})
"""

        # Add contextual instructions based on sentiment and trend
        if sentiment == "positive" and trend_dir == "improving":
            block += "\n[CONTEXT] Positive Momentum: User is showing clear signs of improvement and relief. Reinforce and celebrate small wins explicitly. Ask: 'I notice you seem lighter—what helped that shift?'\n"

        elif sentiment == "negative" and trend_dir == "declining":
            block += "\n[CONTEXT] Declining Trend: Session sentiment has been consistently worsening. This signals escalating distress. Check in directly: 'I notice things feel heavier as we talk—is there something specific weighing on you right now?'\n"

        elif sentiment == "negative" and trend_dir == "improving":
            block += "\n[CONTEXT] Mixed Signal: Overall session showing improvement but current message is negative. User may be processing difficult material—this is normal therapeutic work. Hold space, validate the difficulty, don't rush to resolution.\n"

        elif sentiment == "neutral":
            block += "\n[CONTEXT] Neutral/Informational: User is providing facts or seeking information. This may indicate intellectualization or avoidance. Gently invite deeper feeling: 'You're giving me the facts—what are you *feeling* beneath that?'\n"

        return block

    def get_session_history(self, session_id: str) -> Optional[List[float]]:
        """
        Get sentiment valence history for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of valence scores in order, or None if session not found
        """

        if session_id in self.session_history:
            return list(self.session_history[session_id])
        return None

    def clear_session(self, session_id: str):
        """
        Clear session history (e.g., when conversation ends).

        Args:
            session_id: Session identifier
        """

        if session_id in self.session_history:
            del self.session_history[session_id]


def get_sentiment_classifier_service() -> SentimentClassifierService:
    """
    Get singleton instance of SentimentClassifierService.
    Recommended usage:
        from sentiment_classifier_service import get_sentiment_classifier_service
        service = get_sentiment_classifier_service()
        result = service.classify("I feel hopeful")
    """
    return SentimentClassifierService()
