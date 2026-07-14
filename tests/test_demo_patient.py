"""ponytail: assert demo birth date stays in M-CHAT age window (~16–30 months)."""

from datetime import date

from app.core.demo_patient import DEMO_PATIENT_NAME, demo_patient_birth_date


def test_demo_patient_name_constant():
    assert DEMO_PATIENT_NAME == "Paciente demonstração"


def test_demo_birth_date_about_20_months():
    today = date(2026, 7, 14)
    birth = demo_patient_birth_date(today)
    days = (today - birth).days
    months = days / 30.44
    assert 16 <= months <= 30
