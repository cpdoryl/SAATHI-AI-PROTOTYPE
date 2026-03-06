"""SAATHI AI — Embedding Service (384-dim sentence embeddings for RAG)."""
from typing import List
from loguru import logger


class EmbeddingService:
    """Generates 384-dimensional sentence embeddings using all-MiniLM-L6-v2."""

    def __init__(self):
        self._model = None

    def _get_model(self):
        if not self._model:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Embedding model loaded: all-MiniLM-L6-v2")
        return self._model

    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text string."""
        model = self._get_model()
        return model.encode(text).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        model = self._get_model()
        return model.encode(texts).tolist()
