"""DELETE /patients/{id} — remove patient and cascaded clinical data."""

from datetime import date

import pytest
from uuid import uuid4

from app.core.security import hash_password
from app.models.patient import Patient
from app.models.professional import Professional


@pytest.mark.asyncio
async def test_delete_patient_returns_204(api_client, db_session, professional, monkeypatch):
    monkeypatch.setattr("app.api.v1.auth.enforce_login_rate_limit", lambda *_a, **_k: None)
    patient = Patient(
        professional_id=professional.id,
        name="Para excluir",
        birth_date=date(2020, 1, 1),
        diagnosis_keys=[],
        status="avaliacao",
        start_date=date.today(),
        avatar_color="oklch(0.58 0.12 205)",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": professional.email, "password": "testpass123"},
    )
    assert login.status_code == 200
    assert "korus_access" in login.cookies

    deleted = await api_client.delete(f"/api/v1/patients/{patient.id}")
    assert deleted.status_code == 204

    missing = await api_client.get(f"/api/v1/patients/{patient.id}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_delete_patient_other_professional_returns_404(api_client, db_session, professional, monkeypatch):
    monkeypatch.setattr("app.api.v1.auth.enforce_login_rate_limit", lambda *_a, **_k: None)
    other = Professional(
        email=f"other-{uuid4().hex[:8]}@test.com",
        password_hash=hash_password("testpass123"),
        name="Outra profissional",
        specialty_key="fono",
        specialty="Fonoaudiologia",
    )
    db_session.add(other)
    await db_session.flush()
    foreign = Patient(
        professional_id=other.id,
        name="Paciente alheio",
        birth_date=date(2019, 5, 5),
        diagnosis_keys=[],
        status="avaliacao",
        start_date=date.today(),
        avatar_color="oklch(0.58 0.12 205)",
    )
    db_session.add(foreign)
    await db_session.commit()

    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": professional.email, "password": "testpass123"},
    )
    assert login.status_code == 200
    assert "korus_access" in login.cookies

    response = await api_client.delete(f"/api/v1/patients/{foreign.id}")
    assert response.status_code == 404
