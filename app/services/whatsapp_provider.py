"""WhatsApp provider selection."""

from typing import Protocol, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.evolution_whatsapp_service import EvolutionWhatsAppService
from app.services.meta_whatsapp_service import MetaWhatsAppService
from app.services.whatsapp_types import WhatsAppSendResult

__all__ = [
    "WhatsAppSendResult",
    "WhatsAppProviderService",
    "get_active_whatsapp_provider",
    "whatsapp_can_send",
]


class WhatsAppProviderService(Protocol):
    async def can_send(self, professional_id: UUID) -> bool: ...
    async def get_usage(self, professional_id: UUID) -> dict: ...


WhatsAppService = Union[MetaWhatsAppService, EvolutionWhatsAppService]


def get_active_whatsapp_provider(db: AsyncSession) -> WhatsAppService:
    provider = get_settings().whatsapp_provider
    if provider == "meta":
        return MetaWhatsAppService(db)
    if provider == "evolution":
        return EvolutionWhatsAppService(db)
    raise RuntimeError(f"Unsupported WHATSAPP_PROVIDER: {provider!r}")


async def whatsapp_can_send(db: AsyncSession, professional_id: UUID) -> bool:
    return await get_active_whatsapp_provider(db).can_send(professional_id)
