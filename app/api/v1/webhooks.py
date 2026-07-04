import hmac
import logging

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.services.evolution_whatsapp_service import EvolutionWhatsAppService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_evolution_webhook(request: Request) -> bool:
    settings = get_settings()
    secret = (settings.evolution_webhook_secret or "").strip()
    if not secret:
        logger.warning("EVOLUTION_WEBHOOK_SECRET not configured; rejecting webhook")
        return False
    auth = request.headers.get("Authorization") or ""
    if auth.startswith("Bearer ") and hmac.compare_digest(auth.split(" ", 1)[1], secret):
        return True
    header_secret = request.headers.get("X-Webhook-Secret") or ""
    return hmac.compare_digest(header_secret, secret)


@router.post("/evolution/whatsapp")
async def receive_evolution_whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not _verify_evolution_webhook(request):
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    try:
        payload = await request.json()
    except Exception:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    if not isinstance(payload, dict):
        return Response(status_code=status.HTTP_200_OK)

    service = EvolutionWhatsAppService(db)
    await service.handle_webhook_event(payload)
    return Response(status_code=status.HTTP_200_OK)
