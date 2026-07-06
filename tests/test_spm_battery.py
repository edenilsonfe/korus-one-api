"""SPM battery API and service tests."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.professional import Professional
from app.services.spm_battery_service import (
    SpmBatteryService,
    build_informant_whatsapp_message,
)
from app.services.spm_content_package import get_spm_content_package
from app.services.spm_informant_service import SpmInformantService
from app.services.spm_scoring_service import compute_subform_scores, synthesize_battery_scores
from app.services.whatsapp_types import WhatsAppSendResult


def test_build_informant_whatsapp_message():
    message = build_informant_whatsapp_message(
        informant_name="Maria Silva",
        patient_name="João Silva",
        subform_title="SPM Home",
        link_url="http://localhost:5173/spm/informante/abc",
        professional_name="Dra. Ana",
        expires_at=datetime(2026, 7, 10, 15, 0, tzinfo=timezone.utc),
    )
    assert "Maria" in message
    assert "João" in message
    assert "abc" in message
    assert "Dra. Ana" in message


def test_spm_suggest_scope_for_age():
    package = get_spm_content_package()
    suggested = package.suggest_scope_for_age(48)
    assert len(suggested) >= 1


@pytest.mark.asyncio
async def test_create_battery_and_informant_flow(
    api_client: AsyncClient,
    auth_headers: dict,
    patient: Patient,
):
    package = get_spm_content_package()
    subforms = [e for e in package.list_subforms() if e["item_count"] > 0]
    external = next((s for s in subforms if s["filler"] == "external"), subforms[0])

    create_resp = await api_client.post(
        "/api/v1/spm/batteries",
        headers=auth_headers,
        json={
            "patient_id": str(patient.id),
            "scope": {external["slug"]: {"required": True}},
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    battery = create_resp.json()
    battery_id = battery["id"]

    global_resp = await api_client.get("/api/v1/assessments", headers=auth_headers)
    assert global_resp.status_code == 200
    global_ids = {item["id"] for item in global_resp.json()["items"]}
    assert battery_id in global_ids
    draft_item = next(item for item in global_resp.json()["items"] if item["id"] == battery_id)
    assert draft_item["status"] == "draft"

    list_resp = await api_client.get("/api/v1/spm/batteries", headers=auth_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    link_resp = await api_client.post(
        f"/api/v1/spm/batteries/{battery_id}/subforms/{external['slug']}/links",
        headers=auth_headers,
        json={"inherit_draft": True},
    )
    assert link_resp.status_code == 200, link_resp.text
    token = link_resp.json()["url"].rstrip("/").split("/")[-1]

    session_resp = await api_client.get(f"/api/v1/spm/informant/{token}")
    assert session_resp.status_code == 200
    session = session_resp.json()
    answers = {str(item["id"]): 1 for item in session["items"]}

    submit_resp = await api_client.post(
        f"/api/v1/spm/informant/{token}/submit",
        json={
            "answers": answers,
            "informant_name": "Maria",
            "informant_relationship": "Mãe",
        },
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_finalize_requires_completed_subforms(
    api_client: AsyncClient,
    auth_headers: dict,
    patient: Patient,
):
    package = get_spm_content_package()
    external = next(
        s for s in package.list_subforms() if s["filler"] == "external" and s["item_count"] > 0
    )
    create_resp = await api_client.post(
        "/api/v1/spm/batteries",
        headers=auth_headers,
        json={
            "patient_id": str(patient.id),
            "scope": {external["slug"]: {"required": True}},
        },
    )
    battery_id = create_resp.json()["id"]
    finalize_resp = await api_client.post(
        f"/api/v1/spm/batteries/{battery_id}/finalize",
        headers=auth_headers,
    )
    assert finalize_resp.status_code == 400


@pytest.mark.asyncio
async def test_send_informant_link_whatsapp(
    api_client: AsyncClient,
    auth_headers: dict,
    patient: Patient,
    professional: Professional,
    db_session: AsyncSession,
):
    package = get_spm_content_package()
    external = next(
        s for s in package.list_subforms() if s["filler"] == "external" and s["item_count"] > 0
    )
    create_resp = await api_client.post(
        "/api/v1/spm/batteries",
        headers=auth_headers,
        json={
            "patient_id": str(patient.id),
            "scope": {external["slug"]: {"required": True}},
        },
    )
    battery_id = create_resp.json()["id"]

    mock_provider = AsyncMock()
    mock_provider.can_send = AsyncMock(return_value=True)
    mock_provider.send_text_message = AsyncMock(
        return_value=WhatsAppSendResult(provider="evolution", provider_message_id="msg-1", status="sent")
    )

    with patch(
        "app.services.spm_battery_service.get_active_whatsapp_provider",
        return_value=mock_provider,
    ):
        send_resp = await api_client.post(
            f"/api/v1/spm/batteries/{battery_id}/subforms/{external['slug']}/links/send-whatsapp",
            headers=auth_headers,
            json={"phone": "11988887777", "inherit_draft": True, "informant_name": "Maria"},
        )
    assert send_resp.status_code == 200, send_resp.text
    payload = send_resp.json()
    assert payload["whatsappSent"] is True
    assert "url" in payload
    mock_provider.send_text_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_spm_battery_service_unit(
    db_session: AsyncSession,
    professional: Professional,
    patient: Patient,
):
    service = SpmBatteryService(db_session)
    scope = service.suggest_scope(48)
    assert scope

    from app.schemas.spm import SpmBatteryCreate, SpmScopeEntry

    battery = await service.create_battery(
        data=SpmBatteryCreate(
            patient_id=patient.id,
            scope={next(iter(scope.keys())): SpmScopeEntry(required=True)},
        ),
        professional_id=professional.id,
    )
    assert battery.status == "draft"

    items, total = await service.list_batteries(professional_id=professional.id)
    assert total == 1
    assert items[0].patient_name == patient.name


@pytest.mark.asyncio
async def test_spm_informant_service_invalid_token(db_session):
    service = SpmInformantService(db_session)
    with pytest.raises(HTTPException) as exc:
        await service.get_session("token-invalido")
    assert exc.value.status_code == 404


def test_spm_scoring_pipeline():
    package = get_spm_content_package()
    clinical = next(
        s for s in package.list_subforms() if s["filler"] == "clinical" and s["item_count"] > 0
    )
    items = package.get_items(clinical["slug"])[:3]
    answers = {str(item["id"]): 2 for item in items}
    scores = compute_subform_scores(package, clinical["slug"], answers)
    battery_scores = synthesize_battery_scores([scores])
    assert "summary" in battery_scores
