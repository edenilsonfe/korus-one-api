"""Trial / subscription write access."""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.professional import Professional


class EntitlementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def can_write(self, professional: Professional) -> bool:
        now = datetime.now(UTC)

        if professional.subscription_status == "trialing":
            if professional.trial_ends_at and now > professional.trial_ends_at:
                professional.subscription_status = "trial_expired"
                await self.db.commit()
                return False
            return True

        if professional.subscription_status in ("trial_expired", "canceled", "past_due"):
            return False

        if professional.subscription_status == "active":
            return True

        return False

    async def ensure_write_allowed(self, professional: Professional) -> None:
        if not await self.can_write(professional):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Assinatura ou período de teste indisponível. Renove ou assine um plano para continuar.",
            )
