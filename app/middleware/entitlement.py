"""Block mutating API calls when trial/subscription does not allow writes."""

from collections.abc import Callable

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.professional import Professional
from app.services.entitlement_service import EntitlementService
from sqlalchemy import select

EXEMPT_PATH_PREFIXES: tuple[str, ...] = (
    "/api/v1/auth",
    "/api/v1/billing/checkout",
    "/api/v1/billing/reconcile",
    "/api/v1/billing/webhooks",
    "/api/v1/webhooks",
    # Notifications (seen/read) and announcements admin (staff) are not
    # clinical data mutations — exempt from entitlement gating.
    "/api/v1/notifications",
    "/api/v1/announcements",
)
EXEMPT_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json"})


class EntitlementMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        path = request.url.path
        if path in EXEMPT_PATHS:
            return await call_next(request)
        if any(path.startswith(prefix) for prefix in EXEMPT_PATH_PREFIXES):
            return await call_next(request)
        if not path.startswith("/api/v1/"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return await call_next(request)

        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                raise HTTPException(status_code=401, detail="Token inválido")
            from uuid import UUID

            professional_id = UUID(payload["sub"])
        except Exception:
            return await call_next(request)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Professional).where(Professional.id == professional_id)
            )
            professional = result.scalar_one_or_none()
            if not professional:
                return await call_next(request)

            ent = EntitlementService(db)
            if not await ent.can_write(professional):
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Assinatura ou período de teste indisponível. Renove ou assine um plano para continuar.",
                        "type": "entitlement_error",
                    },
                )

        return await call_next(request)
