from datetime import UTC, date, datetime
from uuid import UUID

from dateutil.relativedelta import relativedelta

from app.core.constants import GOAL_ACHIEVED_THRESHOLD
from app.core.diagnosis_catalog import diagnosis_label as catalog_diagnosis_label


def diagnosis_label(key: str, specialty_key: str = "fono") -> str:
    return catalog_diagnosis_label(key, specialty_key)


def calculate_age(birth_date: date, on_date: date | None = None) -> int:
    ref = on_date or date.today()
    return relativedelta(ref, birth_date).years


def format_time(t) -> str:
    return t.strftime("%H:%M") if t else ""


def goal_status_from_progress(progress: int) -> str:
    if progress >= GOAL_ACHIEVED_THRESHOLD:
        return "Atingida"
    if progress >= 50:
        return "Em andamento"
    return "Inicial"


def utcnow() -> datetime:
    return datetime.now(UTC)


def guardian_label(caregivers: list) -> str:
    if not caregivers:
        return ""
    primary = next((c for c in caregivers if getattr(c, "is_primary", False)), caregivers[0])
    return f"{primary.relation} — {primary.name}" if primary.relation else primary.name


def uuid_str(value: UUID | str) -> str:
    return str(value)
