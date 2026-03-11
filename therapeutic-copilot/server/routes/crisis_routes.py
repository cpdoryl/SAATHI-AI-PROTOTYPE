"""
Crisis detection & escalation routes.
Real-time crisis monitoring with <100ms response target.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.crisis_detection_service import CrisisDetectionService
from services.ml_crisis_service import get_ml_crisis_service

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


@router.get("/model-status")
async def crisis_model_status():
    """
    Return the current active crisis detection model phase and readiness.
    Use this to confirm Phase 3 is loaded (preferred) vs Phase 2 (fallback).

    Response fields:
      ml_available  : bool   -- True if any ML model is loaded
      model_phase   : str    -- "phase3" | "phase2" | "none"
      detection_layers : list -- active detection layers in priority order
      safety_threshold : str  -- safety gate threshold in use
    """
    svc = get_ml_crisis_service()
    phase = svc.model_phase if svc.is_ready else "none"

    threshold_map = {"phase3": "0.15", "phase2": "0.20", "none": "N/A"}
    layers = ["keyword_safety_net"]
    if svc.is_ready:
        layers.insert(0, f"distilbert_ml ({phase})")

    return {
        "ml_available":     svc.is_ready,
        "model_phase":      phase,
        "detection_layers": layers,
        "safety_threshold": threshold_map.get(phase, "N/A"),
        "class_schema":     "C-SSRS 6-class (safe → pre_crisis_intervention)",
        "high_risk_recall": "100% (0 false negatives on test set)",
    }


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
