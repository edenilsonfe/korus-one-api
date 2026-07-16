from fastapi import Response

from app.core.config import get_settings

ACCESS_COOKIE = "korus_access"
REFRESH_COOKIE = "korus_refresh"


def _cookie_secure() -> bool:
    return not get_settings().debug


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    secure = _cookie_secure()
    access_max_age = settings.access_token_expire_minutes * 60
    refresh_max_age = settings.refresh_token_expire_days * 24 * 60 * 60
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=access_max_age,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=refresh_max_age,
        path="/api/v1/auth",
    )


def clear_auth_cookies(response: Response) -> None:
    secure = _cookie_secure()
    response.delete_cookie(key=ACCESS_COOKIE, path="/", secure=secure, httponly=True, samesite="lax")
    response.delete_cookie(
        key=REFRESH_COOKIE,
        path="/api/v1/auth",
        secure=secure,
        httponly=True,
        samesite="lax",
    )
