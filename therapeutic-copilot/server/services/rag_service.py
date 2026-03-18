"""
SAATHI AI — RAG Service
Dual-backend: Pinecone (production) + ChromaDB (local dev/demo fallback).

Backend selection:
  - If PINECONE_API_KEY is set → Pinecone (per-tenant namespaces)
  - Otherwise               → ChromaDB persistent local store

Embedding model: all-MiniLM-L6-v2 (384 dimensions, cosine similarity)
"""
import asyncio
import uuid
from typing import List, Dict, Optional

from config import settings
from loguru import logger

# ── Module-level singletons ──
_sentence_transformer_model = None
_chroma_client = None


def _get_embedding_model():
    """Return the module-level SentenceTransformer singleton (lazy-init)."""
    global _sentence_transformer_model
    if _sentence_transformer_model is None:
        from sentence_transformers import SentenceTransformer
        _sentence_transformer_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("SentenceTransformer singleton loaded: all-MiniLM-L6-v2")
    return _sentence_transformer_model


def _get_chroma_client():
    """Return persistent ChromaDB client (lazy-init)."""
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        db_path = getattr(settings, "LOCAL_RAG_DB_PATH", "./chroma_db")
        _chroma_client = chromadb.PersistentClient(path=str(db_path))
        logger.info(f"ChromaDB client initialised at: {db_path}")
    return _chroma_client


# ─── Normalise namespace → valid ChromaDB collection name ────────────────────
def _safe_collection_name(namespace: str) -> str:
    """ChromaDB names: 3-63 chars, alphanumeric + hyphens only."""
    safe = "".join(
        c if c.isalnum() or c == "-" else "_" for c in namespace
    )
    safe = safe[:63]
    if len(safe) < 3:
        safe = safe + "_kb"
    return safe


class RAGService:
    """
    Unified RAG service with Pinecone (prod) and ChromaDB (local dev) backends.

    Automatic backend selection:
      • PINECONE_API_KEY set → Pinecone (namespaced per tenant)
      • PINECONE_API_KEY empty → ChromaDB persistent local store

    Ingestion pipeline:
      1. Chunk text into ~512-token segments (50-token overlap)
      2. Embed each chunk with all-MiniLM-L6-v2 (384-dim)
      3. Upsert vectors + metadata to chosen backend

    Query pipeline:
      1. Embed query
      2. Similarity search in tenant namespace (top-k=5)
      3. Filter by similarity threshold (0.75 tenant / 0.70 default)
      4. Fallback to 'default' namespace when tenant returns nothing
    """

    SIMILARITY_THRESHOLD_TENANT  = 0.75
    SIMILARITY_THRESHOLD_DEFAULT = 0.70
    DEFAULT_NAMESPACE            = "default"

    def __init__(self):
        self._pinecone_client = None
        self._pinecone_index  = None
        self._use_pinecone: Optional[bool] = None   # resolved on first access

    # ── Backend selection ──

    def _backend(self) -> str:
        """Return 'pinecone' or 'chroma' based on config."""
        if self._use_pinecone is None:
            self._use_pinecone = bool(settings.PINECONE_API_KEY)
            backend_name = "Pinecone" if self._use_pinecone else "ChromaDB"
            logger.info(f"RAG backend: {backend_name}")
        return "pinecone" if self._use_pinecone else "chroma"

    def _get_pinecone_index(self):
        """Lazy-initialise Pinecone client and return the index."""
        if self._pinecone_index:
            return self._pinecone_index
        try:
            from pinecone import Pinecone
            self._pinecone_client = Pinecone(
                api_key=settings.PINECONE_API_KEY
            )
            self._pinecone_index = self._pinecone_client.Index(
                settings.PINECONE_INDEX
            )
            return self._pinecone_index
        except Exception as e:
            logger.warning(f"Pinecone init failed: {e}. Using ChromaDB.")
            self._use_pinecone = False
            return None

    def _get_chroma_collection(self, namespace: str):
        """Get-or-create a ChromaDB collection for the given namespace."""
        client = _get_chroma_client()
        name   = _safe_collection_name(namespace)
        return client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    # ── Chunking ──

    def _chunk_text(
        self, text: str, chunk_size: int = 512, overlap: int = 50
    ) -> List[str]:
        """
        Split text into overlapping chunks (~512 tokens, 50-token overlap).
        Uses 1 token ≈ 4 chars approximation.
        """
        char_size    = chunk_size * 4   # ≈ 2048 chars
        char_overlap = overlap * 4      # ≈ 200 chars
        stride       = char_size - char_overlap

        chunks, start = [], 0
        while start < len(text):
            chunks.append(text[start:start + char_size])
            start += stride

        return [c for c in chunks if len(c.strip()) > 50]

    # ── Embedding ──

    async def _embed(self, text: str) -> List[float]:
        """Generate 384-dim embedding via the singleton SentenceTransformer.

        Runs in a thread pool executor so the synchronous CPU-bound
        SentenceTransformer.encode() call does not block the event loop.
        """
        model = _get_embedding_model()
        loop = asyncio.get_event_loop()
        vector = await loop.run_in_executor(
            None,
            lambda: model.encode(text, normalize_embeddings=True).tolist(),
        )
        return vector

    # ── Query ──

    async def query(
        self, query: str, tenant_id: str, top_k: int = 5
    ) -> List[str]:
        """
        Retrieve top-k relevant passages.

        1. Try tenant namespace with threshold 0.75
        2. Fallback to 'default' namespace with threshold 0.70
        """
        backend = self._backend()

        if backend == "pinecone":
            return await self._query_pinecone(query, tenant_id, top_k)
        else:
            return await self._query_chroma(query, tenant_id, top_k)

    async def _query_pinecone(
        self, query: str, tenant_id: str, top_k: int
    ) -> List[str]:
        index = self._get_pinecone_index()
        if not index:
            return await self._query_chroma(query, tenant_id, top_k)

        embedding = await self._embed(query)

        # Tenant namespace
        results  = index.query(
            vector=embedding, top_k=top_k,
            namespace=tenant_id, include_metadata=True,
        )
        contexts = [
            m.metadata.get("text", "")
            for m in results.matches
            if m.score >= self.SIMILARITY_THRESHOLD_TENANT
        ]

        # Fallback to default
        if not contexts and tenant_id != self.DEFAULT_NAMESPACE:
            logger.debug(
                f"RAG Pinecone: tenant '{tenant_id}' miss → default"
            )
            results  = index.query(
                vector=embedding, top_k=top_k,
                namespace=self.DEFAULT_NAMESPACE, include_metadata=True,
            )
            contexts = [
                m.metadata.get("text", "")
                for m in results.matches
                if m.score >= self.SIMILARITY_THRESHOLD_DEFAULT
            ]
        return contexts

    async def _query_chroma(
        self, query: str, tenant_id: str, top_k: int
    ) -> List[str]:
        try:
            embedding   = await self._embed(query)
            collection  = self._get_chroma_collection(tenant_id)
            count       = collection.count()

            contexts = []
            if count > 0:
                results = collection.query(
                    query_embeddings=[embedding],
                    n_results=min(top_k, count),
                    include=["documents", "distances"],
                )
                # ChromaDB cosine distance: 0 = identical, 2 = opposite.
                # Convert to similarity: sim = 1 - (distance / 2)
                docs      = results["documents"][0]
                distances = results["distances"][0]
                contexts  = [
                    doc for doc, dist in zip(docs, distances)
                    if (1 - dist / 2) >= self.SIMILARITY_THRESHOLD_TENANT
                ]

            # Fallback to default namespace
            if not contexts and tenant_id != self.DEFAULT_NAMESPACE:
                logger.debug(
                    f"RAG ChromaDB: '{tenant_id}' miss → default"
                )
                default_col = self._get_chroma_collection(
                    self.DEFAULT_NAMESPACE
                )
                default_count = default_col.count()
                if default_count > 0:
                    results = default_col.query(
                        query_embeddings=[embedding],
                        n_results=min(top_k, default_count),
                        include=["documents", "distances"],
                    )
                    docs      = results["documents"][0]
                    distances = results["distances"][0]
                    contexts  = [
                        doc for doc, dist in zip(docs, distances)
                        if (1 - dist / 2) >= self.SIMILARITY_THRESHOLD_DEFAULT
                    ]
            return contexts

        except Exception as e:
            logger.warning(f"RAG ChromaDB query error: {e}")
            return []

    # ── Ingest ──

    async def ingest(
        self, content: str, tenant_id: str, metadata: Dict
    ) -> Dict:
        """
        Ingest a document into the tenant's vector store.

        Pipeline:
          1. Chunk into ~512-token segments with 50-token overlap
          2. Embed each chunk
          3. Upsert to Pinecone (prod) or ChromaDB (local)
        """
        backend = self._backend()

        if backend == "pinecone":
            return await self._ingest_pinecone(content, tenant_id, metadata)
        else:
            return await self._ingest_chroma(content, tenant_id, metadata)

    async def _ingest_pinecone(
        self, content: str, tenant_id: str, metadata: Dict
    ) -> Dict:
        index = self._get_pinecone_index()
        if not index:
            return await self._ingest_chroma(content, tenant_id, metadata)

        chunks = self._chunk_text(content)
        if not chunks:
            return {"status": "error", "reason": "No valid chunks produced"}

        source  = metadata.get("source", "doc")
        vectors = []
        for i, chunk in enumerate(chunks):
            embedding  = await self._embed(chunk)
            chunk_id   = f"{source}_{tenant_id}_{i}_{uuid.uuid4().hex[:8]}"
            vectors.append({
                "id":     chunk_id,
                "values": embedding,
                "metadata": {
                    "text":         chunk,
                    "tenant_id":    tenant_id,
                    "chunk_index":  i,
                    "total_chunks": len(chunks),
                    **metadata,
                },
            })

        for batch in [vectors[i:i + 100] for i in range(0, len(vectors), 100)]:
            index.upsert(vectors=batch, namespace=tenant_id)

        logger.info(
            f"RAG Pinecone: ingested {len(chunks)} chunks | "
            f"tenant='{tenant_id}' source='{source}'"
        )
        return {
            "status":          "ingested",
            "backend":         "pinecone",
            "chunks_ingested": len(chunks),
            "tenant_id":       tenant_id,
        }

    async def _ingest_chroma(
        self, content: str, tenant_id: str, metadata: Dict
    ) -> Dict:
        try:
            chunks = self._chunk_text(content)
            if not chunks:
                return {
                    "status": "error",
                    "reason": "No valid chunks produced",
                }

            source     = metadata.get("source", "doc")
            collection = self._get_chroma_collection(tenant_id)

            ids, embeddings, documents, metadatas = [], [], [], []
            for i, chunk in enumerate(chunks):
                embedding = await self._embed(chunk)
                chunk_id  = f"{source}_{tenant_id}_{i}_{uuid.uuid4().hex[:8]}"
                ids.append(chunk_id)
                embeddings.append(embedding)
                documents.append(chunk)
                metadatas.append({
                    "tenant_id":    tenant_id,
                    "chunk_index":  i,
                    "total_chunks": len(chunks),
                    "source":       source,
                    **{k: str(v) for k, v in metadata.items()},
                })

            # ChromaDB upsert in batches of 100
            for start in range(0, len(ids), 100):
                collection.upsert(
                    ids=ids[start:start + 100],
                    embeddings=embeddings[start:start + 100],
                    documents=documents[start:start + 100],
                    metadatas=metadatas[start:start + 100],
                )

            logger.info(
                f"RAG ChromaDB: ingested {len(chunks)} chunks | "
                f"tenant='{tenant_id}' source='{source}'"
            )
            return {
                "status":          "ingested",
                "backend":         "chroma",
                "chunks_ingested": len(chunks),
                "tenant_id":       tenant_id,
            }
        except Exception as e:
            logger.error(f"RAG ChromaDB ingest error: {e}")
            return {"status": "error", "reason": str(e)}

    # ── Stats / Health ──

    def stats(self, tenant_id: str = "default") -> Dict:
        """Return document count and backend info for a namespace."""
        backend = self._backend()
        try:
            if backend == "chroma":
                col   = self._get_chroma_collection(tenant_id)
                count = col.count()
                return {
                    "backend": "chroma",
                    "namespace": tenant_id,
                    "chunk_count": count,
                }
            else:
                return {"backend": "pinecone", "namespace": tenant_id}
        except Exception as e:
            return {"backend": backend, "error": str(e)}
