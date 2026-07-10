import pytest
from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy import select

from app.core.security import verify_password
from app.models.password_reset_token import PasswordResetToken
from app.services.password_reset import (
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
