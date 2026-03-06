"""
Crisis detection & escalation routes.
Real-time crisis monitoring with <100ms response target.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.crisis_detection_service import CrisisDetectionService

router = APIRouter()


@router.post("/scan")
async def scan_message(payload: dict, background_tasks: BackgroundTasks):
    """
    Scan a message for crisis indicators.
    Uses 30+ weighted keywords on a 10-point severity scale.
    Returns severity score + recommended action.
    """
    service = CrisisDetectionService()
    result = service.scan(message=payload.get("message", ""))
    return result


@router.post("/escalate")
async def escalate_crisis(
    payload: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger crisis escalation protocol:
    - Alert clinician via WebSocket
    - Send emergency SMS/email
    - Log crisis event
    - Return emergency resources
    """
    service = CrisisDetectionService()
    result = await service.escalate(
        session_id=payload.get("session_id"),
        patient_id=payload.get("patient_id"),
        severity_score=payload.get("severity_score", 0),
        db=db,
    )
    return result


@router.get("/resources")
async def get_crisis_resources(language: str = "en"):
    """Return localised crisis helpline resources."""
    return {
        "en": {
            "iCall": "+91-9152987821",
            "Vandrevala Foundation": "1860-2662-345",
            "iCall": "icallhelpline.org",
        }
    }.get(language, {})
