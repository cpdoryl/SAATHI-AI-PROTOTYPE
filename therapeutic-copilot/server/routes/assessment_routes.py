"""
Clinical Assessment routes.
Supports: PHQ-9, GAD-7, PCL-5, ISI, OCI-R, SPIN, PSS, WHO-5
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.assessment_service import AssessmentService

router = APIRouter()

SUPPORTED_ASSESSMENTS = ["PHQ-9", "GAD-7", "PCL-5", "ISI", "OCI-R", "SPIN", "PSS", "WHO-5"]


@router.get("/types")
async def list_assessment_types():
    """Return all supported clinical assessment types."""
    return {"assessments": SUPPORTED_ASSESSMENTS}


@router.get("/{assessment_type}/questions")
async def get_questions(assessment_type: str):
    """Return questions for a specific assessment."""
    service = AssessmentService()
    questions = service.get_questions(assessment_type)
    return {"assessment_type": assessment_type, "questions": questions}


@router.post("/{patient_id}/submit")
async def submit_assessment(
    patient_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit completed assessment responses.
    Returns scored result + severity classification.
    """
    service = AssessmentService()
    result = service.score(
        assessment_type=payload.get("assessment_type"),
        responses=payload.get("responses", []),
    )
    return {"patient_id": patient_id, "result": result}


@router.get("/{patient_id}/history")
async def get_assessment_history(patient_id: str, db: AsyncSession = Depends(get_db)):
    """Return all past assessment results for a patient."""
    return {"patient_id": patient_id, "assessments": []}
