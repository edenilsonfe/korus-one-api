"""GET /assessments — filtros de listagem global."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.patient import Patient
from app.models.professional import Professional


@pytest.mark.asyncio
async def test_list_assessments_filters_by_status(
    api_client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    professional: Professional,
    patient: Patient,
):
    db_session.add_all(
        [
            Assessment(
                patient_id=patient.id,
                professional_id=professional.id,
                protocol_id="fois",
                date=date.today(),
                result="Rascunho",
                percentage=0,
                interpretation="",
                fields=[],
                status="draft",
            ),
            Assessment(
                patient_id=patient.id,
                professional_id=professional.id,
                protocol_id="fois",
                date=date.today(),
                result="FOIS 5",
                percentage=71,
                interpretation="ok",
                fields=[],
                status="completed",
            ),
            Assessment(
                patient_id=patient.id,
                professional_id=professional.id,
                protocol_id="fois",
                date=date.today(),
                result="Cancelada",
                percentage=0,
                interpretation="",
                fields=[],
                status="cancelled",
            ),
        ]
    )
    await db_session.commit()

    draft = await api_client.get("/api/v1/assessments?status=draft", headers=auth_headers)
    assert draft.status_code == 200
    assert draft.json()["total"] >= 1
    assert all(item["status"] == "draft" for item in draft.json()["items"])

    done = await api_client.get("/api/v1/assessments?status=completed", headers=auth_headers)
    assert done.status_code == 200
    assert done.json()["total"] >= 1
    assert all(item["status"] == "completed" for item in done.json()["items"])

    bad = await api_client.get("/api/v1/assessments?status=foo", headers=auth_headers)
    assert bad.status_code == 400
