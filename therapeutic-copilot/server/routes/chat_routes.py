"""
Chat routes — handles the full 3-stage therapeutic conversation flow.
Delegates AI logic to TherapeuticAIService.
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from loguru import logger
from database import get_db
from models import TherapySession, ChatMessage
from services.therapeutic_ai_service import TherapeuticAIService

router = APIRouter()


@router.post("/start")
async def start_session(
    payload: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start a new therapy session.
    - Detects patient stage (lead / active / dropout)
    - Loads appropriate LoRA adapter
    - Returns initial AI greeting
    """
    service = TherapeuticAIService(db)
    result = await service.start_session(
        patient_id=payload.get("patient_id"),
        tenant_id=payload.get("tenant_id"),
        widget_token=payload.get("widget_token"),
    )
    return result


@router.post("/message")
async def send_message(
    payload: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Process a patient message through the AI pipeline:
    1. Crisis detection scan
    2. Stage/step routing
    3. RAG context retrieval
    4. LLM inference (Qwen 2.5-7B)
    5. Response streaming
    """
    service = TherapeuticAIService(db)
    result = await service.process_message(
        session_id=payload.get("session_id"),
        message=payload.get("message"),
        stage=payload.get("stage", 1),
    )
    return result


@router.get("/session/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve full session details including messages, step, crisis score."""
    session_result = await db.execute(
        select(TherapySession).where(TherapySession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    msgs_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = msgs_result.scalars().all()
    logger.info(f"Session {session_id} retrieved: {len(messages)} messages")
    return {"session": session, "messages": messages}


@router.post("/session/{session_id}/end")
async def end_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    End a therapy session:
    - Generate AI session summary
    - Update clinician dashboard
    - Trigger follow-up scheduling
    """
    return {"message": "Session ended", "summary": "placeholder"}
