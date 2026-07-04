"""Build absolute checkout return URLs for PSP redirects."""

from urllib.parse import urlencode

from app.core.config import get_settings


def get_frontend_base_url() -> str:
    settings = get_settings()
    if settings.billing_frontend_base_url:
        return settings.billing_frontend_base_url.rstrip("/")
    origins = settings.cors_origin_list
    for port in ("5173", "3000", "8080"):
        for origin in origins:
            if f":{port}" in origin:
                return origin.rstrip("/")
    if origins:
        return origins[0].rstrip("/")
    return "http://localhost:5173"


def build_checkout_return_urls() -> tuple[str, str]:
    base = get_frontend_base_url()
    success = f"{base}/planos/retorno?{urlencode({'status': 'pending'})}"
    cancel = f"{base}/planos?{urlencode({'checkout': 'cancel'})}"
    return success, cancel


def build_in_app_payment_url(session_id: str) -> str:
    base = get_frontend_base_url()
    return f"{base}/planos/pagamento?{urlencode({'sessionId': session_id})}"
