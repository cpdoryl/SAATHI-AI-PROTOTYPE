"""RAG (Retrieval-Augmented Generation) routes — Pinecone per-tenant knowledge base."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.rag_service import RAGService

router = APIRouter()


@router.post("/query")
async def query_knowledge_base(payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Query the tenant's RAG knowledge base.
    Returns top-k relevant documents for AI context augmentation.
    """
    service = RAGService()
    results = await service.query(
        query=payload.get("query"),
        tenant_id=payload.get("tenant_id"),
        top_k=payload.get("top_k", 5),
    )
    return {"results": results}


@router.post("/ingest")
async def ingest_document(payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Ingest a document into the tenant's Pinecone namespace.
    Accepts: FAQ content, therapy protocols, clinic-specific info.
    """
    service = RAGService()
    result = await service.ingest(
        content=payload.get("content"),
        tenant_id=payload.get("tenant_id"),
        metadata=payload.get("metadata", {}),
    )
    return result
