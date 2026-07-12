"""HTTP-level auth matrix for POST /billing/webhooks/{provider}."""

import pytest
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles

from app.core.config import get_settings


# ponytail: sqlite (test DB) has no native JSONB/ARRAY; same shim as
# tests/test_auth_token_version.py so this file's db_session/api_client
# fixtures work when run standalone (not just as part of the full suite).
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_type, _compiler, **_kw):
    return "JSON"


@pytest.fixture(autouse=True)
def _reset_billing_settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "asaas_webhook_token", "")
    monkeypatch.setattr(settings, "debug", False)
    yield


@pytest.mark.asyncio
async def test_asaas_webhook_rejects_when_token_not_configured(api_client):
    response = await api_client.post(
        "/api/v1/billing/webhooks/asaas",
        json={"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_1"}},
        headers={"asaas-access-token": "whatever"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_asaas_webhook_rejects_wrong_header(api_client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "asaas_webhook_token", "correct-token")

    response = await api_client.post(
        "/api/v1/billing/webhooks/asaas",
        json={"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_1"}},
        headers={"asaas-access-token": "wrong-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_asaas_webhook_accepts_correct_header(api_client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "asaas_webhook_token", "correct-token")

    response = await api_client.post(
        "/api/v1/billing/webhooks/asaas",
        json={"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_1"}},
        headers={"asaas-access-token": "correct-token"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stub_webhook_rejects_when_not_debug(api_client):
    response = await api_client.post(
        "/api/v1/billing/webhooks/stub",
        json={"id": "evt-1", "event_type": "payment_succeeded"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stub_webhook_accepts_when_debug(api_client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "debug", True)

    response = await api_client.post(
        "/api/v1/billing/webhooks/stub",
        json={"id": "evt-1", "event_type": "payment_succeeded"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_unknown_provider_webhook_404(api_client):
    response = await api_client.post(
        "/api/v1/billing/webhooks/unknown-provider",
        json={},
    )
    assert response.status_code == 404
