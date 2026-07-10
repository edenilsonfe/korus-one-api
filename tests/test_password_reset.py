import pytest
from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy import select

from app.api.v1 import auth as auth_router
from app.core.security import verify_password
from app.models.password_reset_token import PasswordResetToken
from app.services.password_reset import (
    GENERIC_FORGOT_MESSAGE,
    change_password,
    hash_token,
    request_password_reset,
    reset_password_with_token,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_type, _compiler, **_kw):
    return "JSON"


def test_hash_token_is_deterministic():
    raw = "token-de-teste"
    assert hash_token(raw) == hash_token(raw)


@pytest.mark.asyncio
async def test_request_password_reset_returns_none_for_unknown_email(db_session):
    result = await request_password_reset(db_session, "naoexiste@exemplo.com")
    assert result is None


@pytest.mark.asyncio
async def test_request_password_reset_creates_token_for_valid_email(db_session, professional):
    result = await request_password_reset(db_session, professional.email)

    assert result is not None
    returned_professional, raw_token = result
    assert returned_professional.id == professional.id
    assert raw_token

    token_result = await db_session.execute(
        select(PasswordResetToken).where(PasswordResetToken.professional_id == professional.id)
    )
    token = token_result.scalar_one_or_none()
    assert token is not None
    assert token.token_hash == hash_token(raw_token)
    assert token.used_at is None


class _FakeRedis:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._data[key] = value


@pytest.mark.asyncio
async def test_request_password_reset_cooldown_blocks_second_request(db_session, professional):
    fake_redis = _FakeRedis()
    first = await request_password_reset(db_session, professional.email, redis_client=fake_redis)
    second = await request_password_reset(db_session, professional.email, redis_client=fake_redis)

    assert first is not None
    assert second is None


@pytest.mark.asyncio
async def test_reset_password_with_token_updates_hash_and_token_version(db_session, professional):
    result = await request_password_reset(db_session, professional.email)
    assert result is not None
    _, raw_token = result
    previous_token_version = professional.token_version

    updated = await reset_password_with_token(db_session, raw_token, "novaSenha@123")
    await db_session.refresh(professional)

    assert updated.id == professional.id
    assert verify_password("novaSenha@123", professional.password_hash) is True
    assert professional.token_version == previous_token_version + 1


@pytest.mark.asyncio
async def test_reset_password_with_invalid_token_raises_400(db_session):
    with pytest.raises(HTTPException) as exc:
        await reset_password_with_token(db_session, "token-invalido", "novaSenha@123")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Token inválido ou expirado"


@pytest.mark.asyncio
async def test_change_password_wrong_current_raises_400(db_session, professional):
    with pytest.raises(HTTPException) as exc:
        await change_password(db_session, professional, "senhaErrada", "novaSenha@123")

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_change_password_success_increments_token_version(db_session, professional):
    previous_token_version = professional.token_version

    updated = await change_password(db_session, professional, "testpass123", "novaSenha@123")
    await db_session.refresh(professional)

    assert updated.id == professional.id
    assert verify_password("novaSenha@123", professional.password_hash) is True
    assert professional.token_version == previous_token_version + 1


@pytest.mark.asyncio
async def test_forgot_password_endpoint_returns_generic_message(api_client, professional, monkeypatch):
    calls = []

    def _fake_send_password_reset_email_task(to_email: str, user_name: str, raw_token: str) -> None:
        calls.append((to_email, user_name, raw_token))

    monkeypatch.setattr(auth_router, "send_password_reset_email_task", _fake_send_password_reset_email_task)

    existing_response = await api_client.post(
        "/api/v1/auth/forgot-password",
        json={"email": professional.email},
    )
    missing_response = await api_client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "naoexiste@example.com"},
    )

    assert existing_response.status_code == 200
    assert missing_response.status_code == 200
    assert existing_response.json() == {"message": GENERIC_FORGOT_MESSAGE}
    assert missing_response.json() == {"message": GENERIC_FORGOT_MESSAGE}
    assert len(calls) == 1
    assert calls[0][0] == professional.email


@pytest.mark.asyncio
async def test_reset_password_endpoint_success(api_client, db_session, professional):
    result = await request_password_reset(db_session, professional.email)
    assert result is not None
    _, raw_token = result

    response = await api_client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "newPassword": "novaSenha@123"},
    )
    await db_session.refresh(professional)

    assert response.status_code == 200
    assert response.json() == {"message": "Senha redefinida com sucesso"}
    assert verify_password("novaSenha@123", professional.password_hash) is True


@pytest.mark.asyncio
async def test_change_password_endpoint_success(api_client, db_session, professional, auth_headers):
    response = await api_client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": "testpass123", "newPassword": "novaSenha@123"},
        headers=auth_headers,
    )
    await db_session.refresh(professional)

    assert response.status_code == 200
    assert response.json() == {"message": "Senha alterada com sucesso"}
    assert verify_password("novaSenha@123", professional.password_hash) is True
