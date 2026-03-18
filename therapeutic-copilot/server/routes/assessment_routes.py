"""
Clinical Assessment Routes — SAATHI AI
Supports: PHQ-9, GAD-7, PCL-5, ISI, OCI-R, SPIN, PSS, WHO-5

Endpoints:
  GET  /api/v1/assessments/                         — All assessment metadata (dashboard)
  GET  /api/v1/assessments/types                    — Assessment type list
  GET  /api/v1/assessments/{type}/questions         — Questions for one assessment
  POST /api/v1/assessments/{patient_id}/submit      — Submit + score responses
  GET  /api/v1/assessments/{patient_id}/history     — Patient assessment history
  GET  /api/v1/assessments/{patient_id}/report/{id} — Full clinical report
  POST /api/v1/assessments/score                    — Score without saving (demo/preview)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Optional
from loguru import logger
from database import get_db
from models import Assessment
from services.assessment_service import AssessmentService

router = APIRouter()
service = AssessmentService()

SUPPORTED_ASSESSMENTS = ["PHQ-9", "GAD-7", "PCL-5", "ISI", "OCI-R", "SPIN", "PSS", "WHO-5"]


# ─── Request/Response Models ───────────────────────────────────────────────────

class SubmitAssessmentRequest(BaseModel):
    assessment_type: str
    responses: List[int]
    patient_name: Optional[str] = None


class QuickScoreRequest(BaseModel):
    assessment_type: str
    responses: List[int]
    patient_name: Optional[str] = None
    generate_report: bool = True


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/")
async def list_all_assessments():
    """Return full metadata for all assessments — used to populate the dashboard."""
    return {
        "assessments": service.get_all_assessments(),
        "total": len(SUPPORTED_ASSESSMENTS),
    }


@router.get("/types")
async def list_assessment_types():
    """Return supported assessment type codes."""
    return {"assessments": SUPPORTED_ASSESSMENTS}


@router.get("/{assessment_type}/questions")
async def get_questions(assessment_type: str):
    """Return full question bank and scale labels for an assessment."""
    questions = service.get_questions(assessment_type.upper())
    if not questions:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_type}' not found")

    # Return assessment metadata alongside questions
    all_meta = {a["id"]: a for a in service.get_all_assessments()}
    meta = all_meta.get(assessment_type.upper(), {})

    return {
        "assessment_type": assessment_type.upper(),
        "assessment_name": meta.get("name", assessment_type),
        "condition": meta.get("condition", ""),
        "description": meta.get("description", ""),
        "question_count": len(questions),
        "max_score": meta.get("max_score", 0),
        "questions": questions,
    }


@router.post("/score")
async def quick_score(payload: QuickScoreRequest):
    """
    Score an assessment and optionally generate a clinical report.
    Does NOT persist to database — for demo/preview use.
    """
    result = service.score(
        assessment_type=payload.assessment_type.upper(),
        responses=payload.responses,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    response = {"score_result": result}

    if payload.generate_report:
        report = service.generate_report(
            assessment_type=payload.assessment_type.upper(),
            score_result=result,
            patient_name=payload.patient_name,
        )
        response["report"] = report

    return response


@router.post("/{patient_id}/submit")
async def submit_assessment(
    patient_id: str,
    payload: SubmitAssessmentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit completed assessment. Score, generate report, save to DB.
    Returns full scored result + clinical report.
    """
    assessment_type = payload.assessment_type.upper()

    result = service.score(
        assessment_type=assessment_type,
        responses=payload.responses,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    report = service.generate_report(
        assessment_type=assessment_type,
        score_result=result,
        patient_name=payload.patient_name,
    )

    # ── Persist to DB ─────────────────────────────────────────────────────────
    try:
        import json
        from datetime import datetime

        db_record = Assessment(
            patient_id=patient_id,
            assessment_type=assessment_type,
            responses=json.dumps(payload.responses),
            total_score=result["total_score"],
            severity=result["severity"],
            crisis_flag=result["crisis_flag"],
            administered_at=datetime.utcnow(),
        )
        db.add(db_record)
        await db.commit()
        await db.refresh(db_record)
        record_id = str(db_record.id)
        logger.info(
            f"Assessment saved: patient={patient_id} type={assessment_type} "
            f"score={result['total_score']} severity={result['severity']}"
        )
    except Exception as exc:
        logger.error(f"Failed to save assessment for patient {patient_id}: {exc}")
        record_id = None

    if result.get("crisis_flag"):
        logger.warning(
            f"CRISIS FLAG in assessment: patient={patient_id} "
            f"type={assessment_type} details={result.get('crisis_details')}"
        )

    return {
        "patient_id": patient_id,
        "record_id": record_id,
        "score_result": result,
        "report": report,
    }


@router.get("/{patient_id}/history")
async def get_assessment_history(patient_id: str, db: AsyncSession = Depends(get_db)):
    """Return all past assessment results for a patient, most recent first."""
    try:
        result = await db.execute(
            select(Assessment)
            .where(Assessment.patient_id == patient_id)
            .order_by(Assessment.administered_at.desc())
        )
        assessments = result.scalars().all()
        logger.info(f"Assessment history for {patient_id}: {len(assessments)} records")
        return {
            "patient_id": patient_id,
            "total": len(assessments),
            "assessments": [
                {
                    "id": str(a.id),
                    "assessment_type": a.assessment_type,
                    "total_score": a.total_score,
                    "severity": a.severity,
                    "crisis_flag": a.crisis_flag,
                    "administered_at": a.administered_at.isoformat() if a.administered_at else None,
                }
                for a in assessments
            ],
        }
    except Exception as exc:
        logger.error(f"Assessment history fetch failed for {patient_id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to retrieve assessment history")


@router.get("/{patient_id}/report/{record_id}")
async def get_assessment_report(
    patient_id: str,
    record_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a full clinical report for a specific past assessment."""
    try:
        import json

        result = await db.execute(
            select(Assessment).where(
                Assessment.id == int(record_id),
                Assessment.patient_id == patient_id,
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail="Assessment record not found")

        responses = json.loads(record.responses) if record.responses else []
        score_result = service.score(
            assessment_type=record.assessment_type,
            responses=responses,
        )
        report = service.generate_report(
            assessment_type=record.assessment_type,
            score_result=score_result,
        )
        return {
            "patient_id": patient_id,
            "record_id": record_id,
            "report": report,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Report generation failed for record {record_id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to generate report")
