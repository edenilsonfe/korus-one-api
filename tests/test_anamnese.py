"""Anamnese draft save + complete lock."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.anamnese import AnamneseEntry
from app.models.patient import Patient


@pytest.fixture(autouse=True)
def patch_entitlement_session(db_engine, monkeypatch):
    """EntitlementMiddleware uses AsyncSessionLocal, not get_db — bind to test engine."""
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr("app.middleware.entitlement.AsyncSessionLocal", factory)


@pytest.mark.asyncio
async def test_get_anamnese_includes_draft_status(
    api_client: AsyncClient,
    auth_headers: dict,
    patient: Patient,
):
    resp = await api_client.get(f"/api/v1/patients/{patient.id}/anamnese", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft"
    assert data["completedAt"] is None
    assert data["entries"] == []


@pytest.mark.asyncio
async def test_put_saves_entries_in_batch(
    api_client: AsyncClient,
    auth_headers: dict,
    patient: Patient,
):
    resp = await api_client.put(
        f"/api/v1/patients/{patient.id}/anamnese",
        headers=auth_headers,
        json={
            "entries": [
                {"section": "Gestação", "value": "Pré-natal ok"},
                {"section": "Parto", "value": "Cesárea"},
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft"
    assert {e["section"]: e["value"] for e in data["entries"]} == {
        "Gestação": "Pré-natal ok",
        "Parto": "Cesárea",
    }


@pytest.mark.asyncio
async def test_complete_requires_at_least_one_section(
    api_client: AsyncClient,
    auth_headers: dict,
    patient: Patient,
):
    resp = await api_client.post(
        f"/api/v1/patients/{patient.id}/anamnese/complete",
        headers=auth_headers,
        json={"entries": [{"section": "Gestação", "value": "   "}]},
    )
    assert resp.status_code == 422
    assert "pelo menos uma" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_complete_locks_writes(
    api_client: AsyncClient,
    auth_headers: dict,
    patient: Patient,
):
    complete = await api_client.post(
        f"/api/v1/patients/{patient.id}/anamnese/complete",
        headers=auth_headers,
        json={"entries": [{"section": "Gestação", "value": "Ok"}]},
    )
    assert complete.status_code == 200
    body = complete.json()
    assert body["status"] == "completed"
    assert body["completedAt"] is not None

    put = await api_client.put(
        f"/api/v1/patients/{patient.id}/anamnese",
        headers=auth_headers,
        json={"entries": [{"section": "Gestação", "value": "Alterado"}]},
    )
    assert put.status_code == 409

    post = await api_client.post(
        f"/api/v1/patients/{patient.id}/anamnese",
        headers=auth_headers,
        json={"section": "Parto", "value": "Novo"},
    )
    assert post.status_code == 409

    again = await api_client.post(
        f"/api/v1/patients/{patient.id}/anamnese/complete",
        headers=auth_headers,
        json={},
    )
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_complete_uses_existing_entries_without_body(
    api_client: AsyncClient,
    auth_headers: dict,
    patient: Patient,
    db_session: AsyncSession,
):
    # Commit so EntitlementMiddleware's session rollback (shared SQLite conn) can't wipe it.
    db_session.add(
        AnamneseEntry(patient_id=patient.id, section="Observações", value="Família engajada")
    )
    await db_session.commit()
    resp = await api_client.post(
        f"/api/v1/patients/{patient.id}/anamnese/complete",
        headers=auth_headers,
        json={},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "completed"
