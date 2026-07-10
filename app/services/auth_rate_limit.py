from __future__ import annotations

import logging

from fastapi import HTTPException, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _redis_allow(key: str, max_requests: int, window_seconds: int) -> bool:
    import redis

    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds, nx=True)
        current, _ = pipe.execute()
        return int(current) <= max_requests
    finally:
        client.close()


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def enforce_forgot_rate_limit(ip: str, email: str) -> None:
    key = f"auth:forgot:{ip}:{_normalize_email(email)}"
    try:
        allowed = _redis_allow(key=key, max_requests=3, window_seconds=3600)
    except Exception as exc:  # pragma: no cover - defensive fail-open path
        logger.warning("Forgot-password rate limit unavailable (fail-open): %s", exc)
        return
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Tente novamente mais tarde.",
            headers={"Retry-After": "3600"},
        )


def enforce_reset_rate_limit(ip: str) -> None:
    key = f"auth:reset:{ip}"
    try:
        allowed = _redis_allow(key=key, max_requests=10, window_seconds=60)
    except Exception as exc:  # pragma: no cover - defensive fail-open path
        logger.warning("Reset-password rate limit unavailable (fail-open): %s", exc)
        return
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Tente novamente em instantes.",
            headers={"Retry-After": "60"},
        )
