"""Canonical demo patient created on register for first-run activation."""

from datetime import date, timedelta

DEMO_PATIENT_NAME = "Paciente demonstração"
DEMO_AVATAR_COLOR = "oklch(0.58 0.12 205)"


def demo_patient_birth_date(today: date | None = None) -> date:
    """~20 months old — inside M-CHAT 16–30 months window."""
    base = today or date.today()
    return base - timedelta(days=608)
