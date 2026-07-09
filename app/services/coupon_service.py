from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coupon import Coupon, CouponRedemption
from app.models.professional import Professional
from app.schemas.admin_billing import (
    ApplyCouponResult,
    CouponCreate,
    CouponItem,
    CouponUpdate,
)
from app.services.admin_audit_service import AdminAuditService


class CouponError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class CouponNotFoundError(CouponError):
    pass


class CouponService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AdminAuditService(db)

    async def list_coupons(self) -> list[CouponItem]:
        result = await self.db.execute(select(Coupon).order_by(Coupon.created_at.desc()))
        coupons = result.scalars().all()
        items: list[CouponItem] = []
        for c in coupons:
            count = int(
                (
                    await self.db.execute(
                        select(func.count())
                        .select_from(CouponRedemption)
                        .where(CouponRedemption.coupon_id == c.id)
                    )
                ).scalar_one()
            )
            items.append(self._to_item(c, count))
        return items

    async def create(self, *, actor: Professional, body: CouponCreate) -> CouponItem:
        code = body.code.strip().upper()
        existing = await self.db.execute(select(Coupon).where(Coupon.code == code))
        if existing.scalar_one_or_none():
            raise CouponError("Código de cupom já existe")
        coupon = Coupon(
            code=code,
            coupon_type=body.coupon_type,
            value=body.value,
            trial_bonus_days=body.trial_bonus_days,
            valid_from=body.valid_from,
            valid_until=body.valid_until,
            max_redemptions=body.max_redemptions,
            max_per_professional=body.max_per_professional,
            plan_slugs=body.plan_slugs,
            is_active=body.is_active,
        )
        self.db.add(coupon)
        await self.audit.log(
            actor_id=actor.id,
            action="create_coupon",
            payload={"code": code, "reason": body.reason},
        )
        await self.db.commit()
        await self.db.refresh(coupon)
        return self._to_item(coupon, 0)

    async def update(self, *, actor: Professional, coupon_id: UUID, body: CouponUpdate) -> CouponItem:
        coupon = await self.db.get(Coupon, coupon_id)
        if coupon is None:
            raise CouponNotFoundError("Cupom não encontrado")
        if body.coupon_type is not None:
            coupon.coupon_type = body.coupon_type
        if body.value is not None:
            coupon.value = body.value
        if body.trial_bonus_days is not None:
            coupon.trial_bonus_days = body.trial_bonus_days
        if body.valid_from is not None:
            coupon.valid_from = body.valid_from
        if body.valid_until is not None:
            coupon.valid_until = body.valid_until
        if body.max_redemptions is not None:
            coupon.max_redemptions = body.max_redemptions
        if body.max_per_professional is not None:
            coupon.max_per_professional = body.max_per_professional
        if body.plan_slugs is not None:
            coupon.plan_slugs = body.plan_slugs
        if body.is_active is not None:
            coupon.is_active = body.is_active
        await self.audit.log(
            actor_id=actor.id,
            action="update_coupon",
            payload={"code": coupon.code, "reason": body.reason},
        )
        await self.db.commit()
        await self.db.refresh(coupon)
        count = int(
            (
                await self.db.execute(
                    select(func.count())
                    .select_from(CouponRedemption)
                    .where(CouponRedemption.coupon_id == coupon.id)
                )
            ).scalar_one()
        )
        return self._to_item(coupon, count)

    async def get_by_code(self, code: str) -> Coupon:
        result = await self.db.execute(select(Coupon).where(Coupon.code == code.strip().upper()))
        coupon = result.scalar_one_or_none()
        if coupon is None:
            raise CouponNotFoundError("Cupom não encontrado")
        return coupon

    async def validate_for_professional(
        self, coupon: Coupon, professional_id: UUID, plan_slug: str | None = None
    ) -> None:
        now = datetime.now(UTC)
        if not coupon.is_active:
            raise CouponError("Cupom inativo")
        if coupon.valid_from and now < coupon.valid_from:
            raise CouponError("Cupom ainda não é válido")
        if coupon.valid_until and now > coupon.valid_until:
            raise CouponError("Cupom expirado")
        if coupon.plan_slugs and plan_slug and plan_slug not in coupon.plan_slugs:
            raise CouponError("Cupom não válido para este plano")

        total = int(
            (
                await self.db.execute(
                    select(func.count())
                    .select_from(CouponRedemption)
                    .where(CouponRedemption.coupon_id == coupon.id)
                )
            ).scalar_one()
        )
        if coupon.max_redemptions is not None and total >= coupon.max_redemptions:
            raise CouponError("Cupom esgotado")

        per_pro = int(
            (
                await self.db.execute(
                    select(func.count())
                    .select_from(CouponRedemption)
                    .where(
                        CouponRedemption.coupon_id == coupon.id,
                        CouponRedemption.professional_id == professional_id,
                    )
                )
            ).scalar_one()
        )
        if per_pro >= coupon.max_per_professional:
            raise CouponError("Limite de uso deste cupom atingido para a conta")

    def discounted_price_cents(self, coupon: Coupon, price_cents: int) -> int:
        if coupon.coupon_type == "percent":
            discount = int(price_cents * (coupon.value / 100.0))
            return max(0, price_cents - discount)
        if coupon.coupon_type == "fixed_cents":
            return max(0, price_cents - coupon.value)
        return price_cents

    async def redeem(
        self,
        *,
        coupon: Coupon,
        professional_id: UUID,
        context: str,
    ) -> CouponRedemption:
        redemption = CouponRedemption(
            coupon_id=coupon.id,
            professional_id=professional_id,
            context=context,
            redeemed_at=datetime.now(UTC),
        )
        self.db.add(redemption)
        await self.db.flush()
        return redemption

    async def apply_admin(
        self, *, actor: Professional, professional_id: UUID, code: str, reason: str | None
    ) -> ApplyCouponResult:
        pro = await self.db.get(Professional, professional_id)
        if pro is None:
            raise CouponNotFoundError("Conta não encontrada")
        coupon = await self.get_by_code(code)
        await self.validate_for_professional(coupon, professional_id)
        await self.redeem(coupon=coupon, professional_id=professional_id, context="admin")

        extended = 0
        if coupon.trial_bonus_days > 0:
            base = pro.trial_ends_at or datetime.now(UTC)
            if base.tzinfo is None:
                base = base.replace(tzinfo=UTC)
            if base < datetime.now(UTC):
                base = datetime.now(UTC)
            pro.trial_ends_at = base + timedelta(days=coupon.trial_bonus_days)
            if pro.subscription_status == "trial_expired":
                pro.subscription_status = "trialing"
            extended = coupon.trial_bonus_days

        await self.audit.log(
            actor_id=actor.id,
            target_professional_id=professional_id,
            action="apply_coupon",
            payload={"code": coupon.code, "trial_bonus_days": extended, "reason": reason},
        )
        await self.db.commit()
        return ApplyCouponResult(
            coupon_code=coupon.code,
            trial_extended_days=extended,
            message=(
                f"Cupom aplicado. Trial estendido em {extended} dia(s)."
                if extended
                else "Cupom registrado (sem bônus de trial)."
            ),
        )

    @staticmethod
    def _to_item(c: Coupon, redemption_count: int) -> CouponItem:
        return CouponItem(
            id=str(c.id),
            code=c.code,
            coupon_type=c.coupon_type,
            value=c.value,
            trial_bonus_days=c.trial_bonus_days,
            valid_from=c.valid_from,
            valid_until=c.valid_until,
            max_redemptions=c.max_redemptions,
            max_per_professional=c.max_per_professional,
            plan_slugs=list(c.plan_slugs) if c.plan_slugs else None,
            is_active=c.is_active,
            external_coupon_id=c.external_coupon_id,
            redemption_count=redemption_count,
        )
