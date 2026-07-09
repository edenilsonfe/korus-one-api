from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_audit_log import AdminAuditLog


class AdminAuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        *,
        actor_id: UUID,
        action: str,
        target_professional_id: UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AdminAuditLog:
        entry = AdminAuditLog(
            actor_id=actor_id,
            target_professional_id=target_professional_id,
            action=action,
            payload=payload,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry
