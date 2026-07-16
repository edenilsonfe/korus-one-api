from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote_plus
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.models.password_reset_token import PURPOSE_PASSWORD_RESET, PasswordResetToken
from app.models.professional import Professional
from app.services.email.resend_client import send_email
from app.services.email.templates import password_reset_email
from app.services.refresh_token_service import revoke_all_refresh_sessions
from app.utils.token_hash import hash_token

logger = logging.getLogger(__name__)

GENERIC_FORGOT_MESSAGE = (
    "Se o e-mail informado estiver cadastrado e ativo, você receberá um link para redefinir sua senha."
)


def _redis_client() -> Any | None:
    try:
        import redis

        return redis.from_url(get_settings().redis_url, decode_responses=True)
    except Exception as exc:  # pragma: no cover - fail-open when Redis unavailable
        logger.warning("Password reset Redis unavailable (fail-open): %s", exc)
        return None


async def create_password_token(
    db: AsyncSession,
    professional_id: UUID,
    purpose: str = PURPOSE_PASSWORD_RESET,
) -> str:
    now = datetime.now(UTC)
    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)

    await db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.professional_id == professional_id,
            PasswordResetToken.purpose == purpose,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    db.add(
        PasswordResetToken(
            professional_id=professional_id,
            token_hash=hash_token(raw_token),
            purpose=purpose,
            expires_at=now + timedelta(minutes=settings.password_token_expire_minutes),
        )
    )
    await db.commit()
    return raw_token


async def request_password_reset(
    db: AsyncSession,
    email: str,
    redis_client: Any = None,
) -> tuple[Professional, str] | None:
    normalized_email = (email or "").strip().lower()
    if not normalized_email:
        return None

    result = await db.execute(select(Professional).where(Professional.email == normalized_email))
    professional = result.scalar_one_or_none()
    if professional is None or professional.is_disabled:
        return None

    client = redis_client if redis_client is not None else _redis_client()
    cooldown_key = f"pwreset_cooldown:{professional.id}"
    if client is not None:
        try:
            if client.get(cooldown_key):
                return None
        except Exception as exc:  # pragma: no cover - defensive fail-open path
            logger.warning("Password reset cooldown read failed (fail-open): %s", exc)

    raw_token = await create_password_token(db, professional.id, PURPOSE_PASSWORD_RESET)

    if client is not None:
        settings = get_settings()
        try:
            client.set(cooldown_key, "1", ex=settings.password_reset_cooldown_seconds)
        except Exception as exc:  # pragma: no cover - defensive fail-open path
            logger.warning("Password reset cooldown write failed (fail-open): %s", exc)

    return professional, raw_token


def send_password_reset_email_sync(to_email: str, user_name: str, raw_token: str) -> None:
    settings = get_settings()
    base_url = (settings.frontend_url or "").rstrip("/")
    reset_url = f"{base_url}/reset-password?token={quote_plus(raw_token)}"

    if not settings.email_sending_enabled:
        logger.info(
            "Email sending disabled; password reset token created for professional (email omitted from logs)"
        )
        return

    rendered = password_reset_email(
        user_name=user_name,
        reset_url=reset_url,
        expires_minutes=settings.password_token_expire_minutes,
    )
    try:
        send_email(
            to_email=to_email,
            subject=rendered.subject,
            html=rendered.html,
            text=rendered.text,
        )
    except Exception as exc:
        logger.exception("Failed to send password reset email to %s: %s", to_email, exc)


async def reset_password_with_token(
    db: AsyncSession,
    raw_token: str,
    new_password: str,
) -> Professional:
    now = datetime.now(UTC)
    token_hash = hash_token(raw_token)
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.purpose == PURPOSE_PASSWORD_RESET,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
    )
    token = result.scalar_one_or_none()
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado",
        )

    professional = await db.get(Professional, token.professional_id)
    if professional is None or professional.is_disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado",
        )

    professional.password_hash = hash_password(new_password)
    await revoke_all_refresh_sessions(db, professional)
    token.used_at = now

    await db.commit()
    await db.refresh(professional)
    return professional


async def change_password(
    db: AsyncSession,
    professional: Professional,
    current_password: str,
    new_password: str,
) -> Professional:
    if not verify_password(current_password, professional.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual inválida",
        )

    professional.password_hash = hash_password(new_password)
    await revoke_all_refresh_sessions(db, professional)

    await db.commit()
    await db.refresh(professional)
    return professional
