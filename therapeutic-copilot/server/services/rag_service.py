"""
SAATHI AI — RAG Service (Pinecone vector database)
Per-tenant namespaces for clinic-specific knowledge bases.
Embedding model: all-MiniLM-L6-v2 (384 dimensions)
"""
from typing import List, Dict, Optional
from config import settings
from loguru import logger


class RAGService:
    """Pinecone-backed RAG for per-tenant knowledge retrieval."""

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

    async def query(self, query: str, tenant_id: str, top_k: int = 5) -> List[str]:
        """
        Retrieve top-k relevant passages from the tenant's knowledge base.
        Returns list of text passages for LLM context injection.
        """
        index = self._get_client()
        if not index:
            return []

        embedding = await self._embed(query)
        results = index.query(
            vector=embedding,
            top_k=top_k,
            namespace=tenant_id,
            include_metadata=True,
        )
        return [match["metadata"].get("text", "") for match in results.get("matches", [])]

    async def ingest(self, content: str, tenant_id: str, metadata: Dict) -> Dict:
        """
        Ingest a document into the tenant's Pinecone namespace.
        Chunks content, embeds, and upserts into Pinecone.
        """
        index = self._get_client()
        if not index:
            return {"status": "error", "reason": "Pinecone not configured"}

        import uuid
        embedding = await self._embed(content)
        doc_id = str(uuid.uuid4())
        index.upsert(
            vectors=[(doc_id, embedding, {**metadata, "text": content[:1000]})],
            namespace=tenant_id,
        )
        return {"status": "ingested", "doc_id": doc_id}

    async def _embed(self, text: str) -> List[float]:
        """Generate 384-dim embedding using sentence-transformers."""
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(text).tolist()
