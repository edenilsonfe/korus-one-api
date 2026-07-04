"""Tests for Evolution WhatsApp phone normalization and webhook security."""

import uuid

import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import app
from app.services.evolution_whatsapp_service import (
    format_reminder_text,
    normalize_whatsapp_number,
    whatsapp_number_candidates,
)
from app.utils import credential_encryption as cred


def test_normalize_whatsapp_number_mobile():
    assert normalize_whatsapp_number("11999990000") == "5511999990000"


def test_whatsapp_number_candidates_adds_ninth_digit():
    candidates = whatsapp_number_candidates("1188887777")
    assert "551188887777" in candidates
    assert any(len(c) == 13 for c in candidates)


def test_format_reminder_text():
    text = format_reminder_text(["Ana", "Dra. Silva", "10/07/2026", "14:00", "Clínica"])
    assert "Ana" in text
    assert "14:00" in text


@pytest.fixture
def evolution_env(monkeypatch):
    key = Fernet.generate_key().decode()
    settings = get_settings()
    monkeypatch.setattr(settings, "whatsapp_provider", "evolution")
    monkeypatch.setattr(settings, "whatsapp_credential_encryption_key", key)
    monkeypatch.setattr(settings, "evolution_api_base_url", "http://evolution.test")
    monkeypatch.setattr(settings, "evolution_global_api_key", "global-key")
    monkeypatch.setattr(settings, "evolution_webhook_secret", "evo-webhook-secret")
    monkeypatch.setattr(settings, "app_public_url", "https://api.test")
    cred._get_fernet.cache_clear()
    yield
    cred._get_fernet.cache_clear()


@pytest.mark.asyncio
async def test_evolution_webhook_rejects_without_secret(evolution_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/evolution/whatsapp",
            json={"event": "connection.update", "instance": "korus-test"},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_evolution_webhook_accepts_bearer_secret(evolution_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/evolution/whatsapp",
            json={"event": "connection.update", "instance": str(uuid.uuid4())},
            headers={"Authorization": "Bearer evo-webhook-secret"},
        )
    assert response.status_code == 200
