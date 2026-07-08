from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import CLINICAL_DOMAIN_CATALOG, GOAL_ACHIEVED_THRESHOLD
from app.core.diagnosis_catalog import diagnosis_labels
from app.core.utils import calculate_age, guardian_label
from app.models.assessment import Assessment, ASSESSMENT_STATUS_COMPLETED
from app.models.caregiver import Caregiver
from app.models.goal import ClinicalDomainSnapshot, Goal
from app.models.patient import Patient
from app.models.session import Session

ANALYTICS_PERIOD_DAYS = {
    "30d": 30,
    "90d": 90,
    "6m": 182,
    "1y": 365,
}


async def get_patient_aggregates(db: AsyncSession, patient_id: UUID) -> dict:
    sessions_count = await db.scalar(
        select(func.count()).select_from(Session).where(Session.patient_id == patient_id)
    )
    protocols_done = await db.scalar(
        select(func.count())
        .select_from(Assessment)
        .where(
            Assessment.patient_id == patient_id,
            Assessment.status == ASSESSMENT_STATUS_COMPLETED,
        )
    )
    goals_result = await db.execute(select(Goal).where(Goal.patient_id == patient_id))
    goals = goals_result.scalars().all()
    total_goals = len(goals)
    goals_achieved = sum(1 for g in goals if g.progress >= GOAL_ACHIEVED_THRESHOLD)
    last_session = await db.scalar(
        select(func.max(Session.date)).where(Session.patient_id == patient_id)
    )
    return {
        "sessions_count": sessions_count or 0,
        "protocols_done": protocols_done or 0,
        "total_goals": total_goals,
        "goals_achieved": goals_achieved,
        "last_session": last_session,
    }


def resolve_analytics_period_start(
    period: str | None,
    *,
    today: date | None = None,
) -> date | None:
    """Return inclusive lower bound for analytics period, or None for all history."""
    if period is None or period == "all":
        return None
    if period not in ANALYTICS_PERIOD_DAYS:
        raise ValueError(f"Invalid period: {period}")
    ref = today or date.today()
    return ref - timedelta(days=ANALYTICS_PERIOD_DAYS[period])


async def build_clinical_domains(db: AsyncSession, patient_id: UUID) -> list[dict]:
    """Legacy shape for PatientDetail / clinical-domains: history as int[]."""
    snapshots_result = await db.execute(
        select(ClinicalDomainSnapshot)
        .where(ClinicalDomainSnapshot.patient_id == patient_id)
        .order_by(ClinicalDomainSnapshot.recorded_at.asc())
    )
    snapshots = snapshots_result.scalars().all()
    by_key: dict[str, list] = {}
    for snap in snapshots:
        by_key.setdefault(snap.key, []).append(snap)

    domains = []
    catalog = {d["key"]: d["label"] for d in CLINICAL_DOMAIN_CATALOG}
    for key, series in by_key.items():
        history = [s.score for s in series]
        score = history[-1] if history else 0
        delta = score - history[-2] if len(history) >= 2 else 0
        domains.append({
            "key": key,
            "label": catalog.get(key, series[-1].label if series else key),
            "score": score,
            "delta": delta,
            "history": history,
        })
    return domains


async def build_development_analytics(
    db: AsyncSession,
    patient_id: UUID,
    period: str = "6m",
    *,
    today: date | None = None,
) -> list[dict]:
    """Analytics shape: history as {date, score}[], filtered by period."""
    start = resolve_analytics_period_start(period, today=today)
    stmt = (
        select(ClinicalDomainSnapshot)
        .where(ClinicalDomainSnapshot.patient_id == patient_id)
        .order_by(ClinicalDomainSnapshot.recorded_at.asc())
    )
    if start is not None:
        stmt = stmt.where(ClinicalDomainSnapshot.recorded_at >= start)
    snapshots_result = await db.execute(stmt)
    snapshots = snapshots_result.scalars().all()
    by_key: dict[str, list] = {}
    for snap in snapshots:
        by_key.setdefault(snap.key, []).append(snap)

    domains = []
    catalog = {d["key"]: d["label"] for d in CLINICAL_DOMAIN_CATALOG}
    for key, series in by_key.items():
        history = [
            {"date": s.recorded_at.isoformat(), "score": s.score}
            for s in series
        ]
        score = history[-1]["score"] if history else 0
        delta = (history[-1]["score"] - history[0]["score"]) if len(history) >= 2 else 0
        domains.append({
            "key": key,
            "label": catalog.get(key, series[-1].label if series else key),
            "score": score,
            "delta": delta,
            "history": history,
        })
    return domains


async def load_patient_with_relations(db: AsyncSession, patient: Patient) -> Patient:
    result = await db.execute(
        select(Patient)
        .where(Patient.id == patient.id)
        .options(
            selectinload(Patient.caregivers),
            selectinload(Patient.goals),
            selectinload(Patient.sessions),
            selectinload(Patient.assessments),
            selectinload(Patient.timeline_events),
            selectinload(Patient.attachments),
        )
    )
    return result.scalar_one()


def patient_to_summary(patient: Patient, aggregates: dict, specialty_key: str = "fono") -> dict:
    caregivers = patient.caregivers if hasattr(patient, "caregivers") and patient.caregivers else []
    keys = patient.diagnosis_keys or []
    return {
        "id": str(patient.id),
        "name": patient.name,
        "age": calculate_age(patient.birth_date),
        "birthDate": patient.birth_date.isoformat(),
        "guardian": guardian_label(caregivers),
        "guardianLabel": guardian_label(caregivers),
        "diagnoses": diagnosis_labels(keys, specialty_key),
        "diagnosisKeys": keys,
        "therapist": patient.professional.name if patient.professional else "",
        "status": patient.status,
        "startDate": patient.start_date.isoformat(),
        "lastSession": aggregates["last_session"].isoformat() if aggregates.get("last_session") else None,
        "sessionsCount": aggregates["sessions_count"],
        "protocolsDone": aggregates["protocols_done"],
        "goalsAchieved": aggregates["goals_achieved"],
        "totalGoals": aggregates["total_goals"],
        "avatarColor": patient.avatar_color,
        "therapyPlanContent": patient.therapy_plan_content,
        "therapyPlanUpdatedAt": patient.therapy_plan_updated_at.isoformat()
        if patient.therapy_plan_updated_at
        else None,
    }
