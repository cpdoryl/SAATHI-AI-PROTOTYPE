"""
SAATHI AI — RAG Service (Pinecone vector database)
Per-tenant namespaces for clinic-specific knowledge bases.
Embedding model: all-MiniLM-L6-v2 (384 dimensions)
"""
import uuid
from typing import List, Dict

from config import settings
from loguru import logger

# ─── Module-level singleton ───────────────────────────────────────────────────
# Loaded once on first use; shared across all RAGService instances.
# Avoids ~2s model reload penalty on every _embed() call.
_sentence_transformer_model = None


def _get_embedding_model():
    """Return the module-level SentenceTransformer singleton (lazy-init)."""
    global _sentence_transformer_model
    if _sentence_transformer_model is None:
        from sentence_transformers import SentenceTransformer
        _sentence_transformer_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("SentenceTransformer singleton loaded: all-MiniLM-L6-v2")
    return _sentence_transformer_model


class RAGService:
    """Pinecone-backed RAG for per-tenant knowledge retrieval."""

    SIMILARITY_THRESHOLD_TENANT = 0.75
    SIMILARITY_THRESHOLD_DEFAULT = 0.70
    DEFAULT_NAMESPACE = "default"

    def __init__(self):
        self._client = None
        self._index = None

    def _get_client(self):
        """Lazy-initialise Pinecone client."""
        if not self._client:
            try:
                from pinecone import Pinecone
                self._client = Pinecone(api_key=settings.PINECONE_API_KEY)
                self._index = self._client.Index(settings.PINECONE_INDEX)
            except Exception as e:
                logger.warning(f"Pinecone unavailable: {e}. RAG disabled.")
        return self._index

    def _chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks of ~chunk_size tokens.
        Uses character-based approximation (1 token ≈ 4 chars).
        Discards chunks of 50 chars or fewer (too small to be meaningful).
        """
        char_size = chunk_size * 4      # 512 tokens ≈ 2048 chars
        char_overlap = overlap * 4      # 50 tokens  ≈ 200 chars
        stride = char_size - char_overlap

        chunks = []
        start = 0
        while start < len(text):
            end = start + char_size
            chunks.append(text[start:end])
            start += stride

        return [c for c in chunks if len(c.strip()) > 50]

    async def query(self, query: str, tenant_id: str, top_k: int = 5) -> List[str]:
        """
        Retrieve top-k relevant passages from the tenant's knowledge base.

        Similarity thresholds:
          - Tenant namespace: score >= 0.75
          - Default namespace (fallback): score >= 0.70

        Falls back to the 'default' namespace when the tenant namespace
        returns no results above the similarity threshold.

        Returns list of text passages for LLM context injection.
        """
        index = self._get_client()
        if not index:
            return []

        embedding = await self._embed(query)

        # Try tenant namespace first
        results = index.query(
            vector=embedding,
            top_k=top_k,
            namespace=tenant_id,
            include_metadata=True,
        )
        contexts = [
            m.metadata.get("text", "")
            for m in results.matches
            if m.score >= self.SIMILARITY_THRESHOLD_TENANT
        ]

        # Fallback: if tenant has no high-confidence results, query default namespace
        if not contexts and tenant_id != self.DEFAULT_NAMESPACE:
            logger.debug(
                f"RAG: no results for tenant '{tenant_id}' "
                f"(threshold={self.SIMILARITY_THRESHOLD_TENANT}), "
                f"falling back to '{self.DEFAULT_NAMESPACE}' namespace"
            )
            results = index.query(
                vector=embedding,
                top_k=top_k,
                namespace=self.DEFAULT_NAMESPACE,
                include_metadata=True,
            )
            contexts = [
                m.metadata.get("text", "")
                for m in results.matches
                if m.score >= self.SIMILARITY_THRESHOLD_DEFAULT
            ]

        return contexts

    async def ingest(self, content: str, tenant_id: str, metadata: Dict) -> Dict:
        """
        Ingest a document into the tenant's Pinecone namespace.

        Pipeline:
          1. Chunk content into ~512-token segments with 50-token overlap.
          2. Embed each chunk with all-MiniLM-L6-v2.
          3. Upsert all vectors to Pinecone in batches of 100.

        Returns a summary dict with chunk count and tenant_id.
        """
        index = self._get_client()
        if not index:
            return {"status": "error", "reason": "Pinecone not configured"}

        chunks = self._chunk_text(content)
        if not chunks:
            return {"status": "error", "reason": "No valid chunks produced from content"}

        source = metadata.get("source", "doc")
        vectors = []
        for i, chunk in enumerate(chunks):
            embedding = await self._embed(chunk)
            chunk_id = f"{source}_{tenant_id}_{i}_{uuid.uuid4().hex[:8]}"
            vectors.append({
                "id": chunk_id,
                "values": embedding,
                "metadata": {
                    "text": chunk,
                    "tenant_id": tenant_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    **metadata,
                },
            })

        # Batch upsert — Pinecone limit is 100 vectors per call
        for batch in [vectors[i:i + 100] for i in range(0, len(vectors), 100)]:
            index.upsert(vectors=batch, namespace=tenant_id)

        logger.info(
            f"RAG: ingested {len(chunks)} chunks for tenant '{tenant_id}' "
            f"source='{source}'"
        )
        return {
            "status": "ingested",
            "chunks_ingested": len(chunks),
            "tenant_id": tenant_id,
        }

    async def _embed(self, text: str) -> List[float]:
        """Generate 384-dim embedding using the module-level singleton model."""
        model = _get_embedding_model()
        return model.encode(text).tolist()
