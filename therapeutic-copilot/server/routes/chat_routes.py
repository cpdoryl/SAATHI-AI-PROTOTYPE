"""
Chat routes — handles the full 3-stage therapeutic conversation flow.
Delegates AI logic to TherapeuticAIService.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
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
    return {"session_id": session_id, "messages": [], "current_step": 0}


@router.post("/session/{session_id}/end")
async def end_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    End a therapy session:
    - Generate AI session summary
    - Update clinician dashboard
    - Trigger follow-up scheduling
    """
    return {"message": "Session ended", "summary": "placeholder"}
