"""Evolution webhook authentication helpers."""

from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import Request

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def normalize_evolution_event(event: str | None) -> str:
    """Normalize Evolution event names to dotted lowercase (CONNECTION_UPDATE → connection.update)."""
    raw = (event or "").strip().lower().replace("-", "_")
    if not raw:
        return ""
    if "." in raw:
        return raw
    if "_" in raw:
        prefix, _, rest = raw.partition("_")
        return f"{prefix}.{rest}" if rest else raw
    return raw


def map_evolution_message_status(status_value: object) -> str | None:
    """Map Evolution/Baileys ack status to our log status."""
    if status_value is None:
        return None
    if isinstance(status_value, int):
        # Baileys: 0 ERROR, 1 PENDING, 2 SERVER_ACK, 3 DELIVERY_ACK, 4 READ, 5 PLAYED
        if status_value >= 4:
            return "read"
        if status_value >= 3:
            return "delivered"
        if status_value >= 2:
            return "sent"
        if status_value == 0:
            return "failed"
        return None

    text = str(status_value).strip().lower()
    aliases = {
        "delivery_ack": "delivered",
        "delivered": "delivered",
        "read": "read",
        "played": "read",
        "server_ack": "sent",
        "sent": "sent",
        "error": "failed",
        "failed": "failed",
    }
    return aliases.get(text, text if text in {"queued", "sent", "delivered", "read", "failed"} else None)


def verify_evolution_webhook_request(request: Request, body: bytes) -> bool:
    """
    Accept either:
    - HMAC-SHA256 of raw body in X-Webhook-Signature (Evolution WEBHOOK_GLOBAL_HMAC_SECRET)
    - static Bearer / X-Webhook-Secret (per-instance custom header we register)
    """
    settings = get_settings()
    secret = (settings.evolution_webhook_secret or "").strip()
    if not secret:
        logger.warning("EVOLUTION_WEBHOOK_SECRET not configured; rejecting webhook")
        return False

    signature = (
        request.headers.get("X-Webhook-Signature")
        or request.headers.get("x-webhook-signature")
        or ""
    ).strip()
    if signature:
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        # Evolution may send raw hex or sha256=<hex>
        provided = signature.removeprefix("sha256=")
        return hmac.compare_digest(expected, provided)

    auth = request.headers.get("Authorization") or ""
    if auth.startswith("Bearer ") and hmac.compare_digest(auth.split(" ", 1)[1], secret):
        return True

    header_secret = request.headers.get("X-Webhook-Secret") or ""
    return bool(header_secret) and hmac.compare_digest(header_secret, secret)
