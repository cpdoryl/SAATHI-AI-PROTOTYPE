"""
SAATHI AI — Analytics Service
Aggregates session, patient, crisis, and assessment data for the dashboard.
"""
from datetime import datetime, timedelta
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from models import Patient, TherapySession, Assessment, PatientStage


class AnalyticsService:
    """Compute analytics aggregates from the database."""

    async def get_summary(self, db: AsyncSession) -> dict:
        """
        Return full analytics summary:
          - weekly_sessions: session counts per day for the last 7 days
          - crisis_rate: fraction of sessions with crisis_score > 0.5, per week, last 4 weeks
          - patient_stages: count per stage (LEAD / ACTIVE / DROPOUT)
          - assessment_scores: average score per assessment type
          - kpi: total_active, total_sessions_this_week, crisis_alerts_this_week
        """
        now = datetime.utcnow()
        seven_days_ago = now - timedelta(days=7)
        four_weeks_ago = now - timedelta(weeks=4)

        weekly_sessions = await self._weekly_sessions(db, seven_days_ago, now)
        crisis_rate = await self._crisis_rate_by_week(db, four_weeks_ago, now)
        patient_stages = await self._patient_stage_counts(db)
        assessment_scores = await self._assessment_score_distribution(db)
        kpis = await self._kpis(db, seven_days_ago)

        return {
            "weekly_sessions": weekly_sessions,
            "crisis_rate": crisis_rate,
            "patient_stages": patient_stages,
            "assessment_scores": assessment_scores,
            **kpis,
        }

    # ─── Private helpers ───────────────────────────────────────────────────────

    async def _weekly_sessions(
        self, db: AsyncSession, since: datetime, until: datetime
    ) -> list[dict]:
        """Count sessions per calendar day for the last 7 days."""
        result = await db.execute(
            select(
                func.date(TherapySession.started_at).label("day"),
                func.count(TherapySession.id).label("count"),
            )
            .where(TherapySession.started_at >= since)
            .where(TherapySession.started_at <= until)
            .group_by(func.date(TherapySession.started_at))
            .order_by(func.date(TherapySession.started_at))
        )
        rows = result.all()

        # Build a full 7-day map so days with 0 sessions still appear
        day_map: dict[str, int] = {}
        for i in range(7):
            d = (since + timedelta(days=i)).strftime("%a")
            day_map[d] = 0
        for row in rows:
            label = datetime.strptime(str(row.day), "%Y-%m-%d").strftime("%a")
            day_map[label] = day_map.get(label, 0) + row.count

        return [{"day": d, "sessions": c} for d, c in day_map.items()]

    async def _crisis_rate_by_week(
        self, db: AsyncSession, since: datetime, until: datetime
    ) -> list[dict]:
        """
        For each of the last 4 weeks compute crisis rate = (sessions with
        crisis_score > 0.5) / total_sessions.
        """
        output = []
        for week_index in range(4):
            week_start = since + timedelta(weeks=week_index)
            week_end = week_start + timedelta(weeks=1)

            total_result = await db.execute(
                select(func.count(TherapySession.id))
                .where(TherapySession.started_at >= week_start)
                .where(TherapySession.started_at < week_end)
            )
            total = total_result.scalar() or 0

            crisis_result = await db.execute(
                select(func.count(TherapySession.id))
                .where(TherapySession.started_at >= week_start)
                .where(TherapySession.started_at < week_end)
                .where(TherapySession.crisis_score > 0.5)
            )
            crisis_count = crisis_result.scalar() or 0

            rate = round(crisis_count / total, 3) if total > 0 else 0.0
            output.append({
                "week": f"Wk {week_index + 1}",
                "crisisRate": rate,
                "total": total,
                "crisisCount": crisis_count,
            })

        return output

    async def _patient_stage_counts(self, db: AsyncSession) -> list[dict]:
        """Count patients per stage (LEAD, ACTIVE, DROPOUT)."""
        result = await db.execute(
            select(Patient.stage, func.count(Patient.id).label("count"))
            .where(Patient.stage.in_([PatientStage.LEAD, PatientStage.ACTIVE, PatientStage.DROPOUT]))
            .group_by(Patient.stage)
        )
        rows = result.all()
        stage_map = {PatientStage.LEAD: 0, PatientStage.ACTIVE: 0, PatientStage.DROPOUT: 0}
        for row in rows:
            stage_map[row.stage] = row.count
        return [
            {"stage": "LEAD", "count": stage_map[PatientStage.LEAD]},
            {"stage": "ACTIVE", "count": stage_map[PatientStage.ACTIVE]},
            {"stage": "DROPOUT", "count": stage_map[PatientStage.DROPOUT]},
        ]

    async def _assessment_score_distribution(self, db: AsyncSession) -> list[dict]:
        """Average score and submission count per assessment type."""
        result = await db.execute(
            select(
                Assessment.assessment_type,
                func.avg(Assessment.score).label("avg_score"),
                func.count(Assessment.id).label("count"),
            )
            .where(Assessment.score.isnot(None))
            .group_by(Assessment.assessment_type)
            .order_by(Assessment.assessment_type)
        )
        rows = result.all()
        return [
            {
                "type": row.assessment_type,
                "avgScore": round(float(row.avg_score), 1),
                "count": row.count,
            }
            for row in rows
        ]

    async def _kpis(self, db: AsyncSession, since: datetime) -> dict:
        """High-level KPI counts."""
        active_result = await db.execute(
            select(func.count(Patient.id)).where(Patient.stage == PatientStage.ACTIVE)
        )
        total_active = active_result.scalar() or 0

        sessions_result = await db.execute(
            select(func.count(TherapySession.id))
            .where(TherapySession.started_at >= since)
        )
        total_sessions_week = sessions_result.scalar() or 0

        crisis_result = await db.execute(
            select(func.count(TherapySession.id))
            .where(TherapySession.started_at >= since)
            .where(TherapySession.crisis_score > 0.5)
        )
        crisis_alerts_week = crisis_result.scalar() or 0

        logger.info(
            f"[analytics] active={total_active} sessions_7d={total_sessions_week} "
            f"crisis_7d={crisis_alerts_week}"
        )
        return {
            "total_active_patients": total_active,
            "total_sessions_this_week": total_sessions_week,
            "crisis_alerts_this_week": crisis_alerts_week,
        }
