"""Auth hardening: opaque refresh rotation, rate limits, logout, email normalization."""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.auth_rate_limit import normalize_auth_email


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def test_normalize_auth_email():
    assert normalize_auth_email("  User@Example.COM ") == "user@example.com"


@pytest.mark.asyncio
async def test_login_returns_opaque_refresh_and_cookies(api_client, professional):
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": professional.email, "password": "testpass123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "accessToken" in body
    assert "refreshToken" in body
    assert body["refreshToken"]
    assert "korus_access" in response.cookies
    assert "korus_refresh" in response.cookies


@pytest.mark.asyncio
async def test_refresh_rotates_opaque_token(api_client, professional):
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": professional.email, "password": "testpass123"},
    )
    assert login.status_code == 200
    old_refresh = login.json()["refreshToken"]

    refreshed = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": old_refresh},
    )
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["refreshToken"]
    assert new_refresh != old_refresh

    reuse = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": old_refresh},
    )
    assert reuse.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh(api_client, professional):
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": professional.email, "password": "testpass123"},
    )
    refresh_token = login.json()["refreshToken"]

    logout = await api_client.post(
        "/api/v1/auth/logout",
        json={"refreshToken": refresh_token},
    )
    assert logout.status_code == 200

    refresh = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )
    assert refresh.status_code == 401


@pytest.mark.asyncio
async def test_register_normalizes_email(api_client):
    email = f"MixedCase-{uuid4().hex[:8]}@Test.COM"
    response = await api_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "name": "Mixed Case",
            "specialtyKey": "fono",
        },
    )
    assert response.status_code == 201

    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": email.upper(), "password": "securepass123"},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_login_rate_limit_returns_429(api_client, professional, monkeypatch):
    from app.services import auth_rate_limit

    def _deny(*_args, **_kwargs):
        raise auth_rate_limit.HTTPException(
            status_code=429,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
        )

    monkeypatch.setattr(auth_rate_limit, "enforce_login_rate_limit", _deny)

    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": professional.email, "password": "wrong"},
    )
    assert response.status_code == 429
