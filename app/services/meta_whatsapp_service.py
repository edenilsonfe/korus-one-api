"""Meta WhatsApp provider stub for future implementation."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.whatsapp_types import WhatsAppSendResult


class MetaWhatsAppService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def can_send(self, professional_id: UUID) -> bool:
        return False

    async def get_usage(self, professional_id: UUID) -> dict:
        return {"month": "", "used": 0, "limit": 0, "remaining": 0}

    async def disconnect(self, professional_id: UUID):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Provider Meta ainda não implementado no Korus Fono.",
        )

    async def send_text_message(
        self, professional_id: UUID, recipient_phone: str, text: str
    ) -> WhatsAppSendResult:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Provider Meta ainda não implementado no Korus Fono.",
        )

    async def send_appointment_reminder(
        self, professional_id: UUID, recipient_phone: str, variables: list[str]
    ) -> WhatsAppSendResult:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Provider Meta ainda não implementado no Korus Fono.",
        )
