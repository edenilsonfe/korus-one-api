from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import FIDELITY_BADGES, ProtocolCatalog
from app.models.professional import Professional
from app.schemas.admin_product import AdminProtocolItem, AdminProtocolUpdate
from app.services.admin_audit_service import AdminAuditService
from app.services.assessment_scoring import get_protocol_scoring_mode


class AdminProtocolNotFoundError(Exception):
    pass


class AdminProtocolConflictError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class AdminProtocolService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AdminAuditService(db)

    async def list_all(self) -> list[AdminProtocolItem]:
        result = await self.db.execute(
            select(ProtocolCatalog).order_by(
                ProtocolCatalog.sort_order.asc(), ProtocolCatalog.name.asc()
            )
        )
        return [self._to_item(p) for p in result.scalars().all()]

    async def update(
        self, *, actor: Professional, protocol_id: str, body: AdminProtocolUpdate
    ) -> AdminProtocolItem:
        proto = await self.db.get(ProtocolCatalog, protocol_id)
        if proto is None:
            raise AdminProtocolNotFoundError()

        before = {
            "is_active": proto.is_active,
            "sort_order": proto.sort_order,
            "fidelity_badge": proto.fidelity_badge,
        }
        if body.is_active is not None:
            proto.is_active = body.is_active
        if body.sort_order is not None:
            proto.sort_order = body.sort_order
        if body.clear_fidelity_badge:
            proto.fidelity_badge = None
        elif body.fidelity_badge is not None:
            if body.fidelity_badge not in FIDELITY_BADGES:
                raise AdminProtocolConflictError("Badge de fidelidade inválido")
            proto.fidelity_badge = body.fidelity_badge

        await self.audit.log(
            actor_id=actor.id,
            action="update_protocol",
            payload={
                "protocol_id": protocol_id,
                "before": before,
                "after": {
                    "is_active": proto.is_active,
                    "sort_order": proto.sort_order,
                    "fidelity_badge": proto.fidelity_badge,
                },
                "reason": body.reason,
            },
        )
        await self.db.commit()
        await self.db.refresh(proto)
        return self._to_item(proto)

    @staticmethod
    def _to_item(p: ProtocolCatalog) -> AdminProtocolItem:
        return AdminProtocolItem(
            id=p.id,
            name=p.name,
            full_name=p.full_name,
            age_range=p.age_range,
            is_active=p.is_active,
            sort_order=p.sort_order,
            fidelity_badge=p.fidelity_badge,
            scoring_mode=get_protocol_scoring_mode(p.id),
        )
