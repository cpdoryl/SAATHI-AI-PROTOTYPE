"""Chat API — delegates to TherapeuticAIService."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db

router = APIRouter()


@router.post("/message")
async def send_message(payload: dict, db: AsyncSession = Depends(get_db)):
    """Send a patient message and receive AI therapeutic response."""
    return {"response": "placeholder", "session_id": "placeholder"}


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve full chat history for a therapy session."""
    return {"messages": []}
