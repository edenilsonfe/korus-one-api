"""Dispatch WhatsApp appointment notifications.

Compose runs Redis but has no ARQ worker service. Enqueue-only would drop
messages into Redis forever — so we dispatch inline by default.

Set WHATSAPP_USE_ARQ_DISPATCH=true only when `uv run arq worker.WorkerSettings`
(or an equivalent worker container) is actually running.
"""

from __future__ import annotations

import logging
import os
from uuid import UUID

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _use_arq_dispatch() -> bool:
    raw = os.environ.get("WHATSAPP_USE_ARQ_DISPATCH", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


async def enqueue_whatsapp_appointment_event(
    appointment_id: UUID, notification_type: str
) -> None:
    """Dispatch appointment WhatsApp event (inline, or ARQ when explicitly enabled)."""
    if _use_arq_dispatch():
        try:
            from arq import create_pool
            from arq.connections import RedisSettings

            redis = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
            try:
                await redis.enqueue_job(
                    "dispatch_whatsapp_appointment_event",
                    str(appointment_id),
                    notification_type,
                )
                return
            finally:
                close = getattr(redis, "aclose", None) or getattr(redis, "close")
                await close()
        except Exception as exc:
            logger.warning(
                "WhatsApp ARQ enqueue failed (%s); dispatching inline for %s/%s",
                exc,
                appointment_id,
                notification_type,
            )

    from app.services.whatsapp_notification_service import WhatsAppNotificationService

    await WhatsAppNotificationService.dispatch_appointment_event(
        appointment_id, notification_type
    )
