"""Analytics API — summary endpoint for the ClinicianDashboard analytics tab."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database import get_db
from services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/summary")
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    """
    Return aggregated analytics data:
      - weekly_sessions (7-day bar chart data)
      - crisis_rate (4-week area chart data)
      - patient_stages (LEAD/ACTIVE/DROPOUT pie chart data)
      - assessment_scores (per-type average + count bar chart data)
      - KPIs: total_active_patients, total_sessions_this_week, crisis_alerts_this_week
    """
    try:
        service = AnalyticsService()
        summary = await service.get_summary(db)
        return summary
    except Exception as exc:
        logger.error(f"Analytics summary failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to compute analytics summary")
