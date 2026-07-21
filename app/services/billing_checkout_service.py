"""In-app checkout session helpers (PIX and credit card)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.billing import PaymentGatewayConfigError, get_payment_gateway
from app.billing.asaas_gateway import AsaasPaymentGateway
from app.billing.errors import PaymentGatewayError
from app.billing.stub_gateway import StubPaymentGateway
from app.models.billing import Subscription
from app.models.professional import Professional
from app.services.billing_customer_service import BillingCustomerService
from app.services.billing_reconciliation_service import BillingReconciliationService
from app.services.plan_change_service import PlanChangeService
from app.services.plan_proration import calculate_monthly_to_yearly_upgrade

_PAYMENT_SUCCESS = frozenset({"RECEIVED", "CONFIRMED", "RECEIVED_IN_CASH"})
_PAYMENT_PENDING = frozenset({"PENDING", "OVERDUE", "AWAITING_RISK_ANALYSIS"})
_ANNUAL_INTERVALS = frozenset({"yearly", "annual"})


def _is_annual_interval(interval: str | None) -> bool:
    return (interval or "monthly").lower().strip() in _ANNUAL_INTERVALS


class BillingCheckoutService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_subscription(
        self, *, session_id: str, professional_id: str
    ) -> Subscription:
        result = await self.db.execute(
            select(Subscription)
            .options(joinedload(Subscription.plan), joinedload(Subscription.pending_plan))
            .where(
                Subscription.professional_id == UUID(str(professional_id)),
                Subscription.external_checkout_id == session_id,
            )
            .order_by(Subscription.updated_at.desc())
        )
        sub = result.scalars().first()
        if not sub or not sub.plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sessão de pagamento não encontrada.",
            )
        return sub

    async def get_session(
        self, *, session_id: str, professional: Professional
    ) -> dict[str, Any]:
        sub = await self._get_subscription(
            session_id=session_id, professional_id=str(professional.id)
        )
        display_plan = sub.pending_plan if sub.pending_plan_id and not sub.pending_change_at else sub.plan
        plan = display_plan or sub.plan
        provider = (sub.provider or "stub").lower()
        payment_status = "pending"
        payment_id = sub.external_checkout_id
        charge_cents: int | None = None
        credit_cents: int | None = None
        change_type: str | None = None

        if sub.pending_plan_id and not sub.pending_change_at and sub.pending_plan and sub.plan:
            change_type = "upgrade"
            try:
                quote = calculate_monthly_to_yearly_upgrade(
                    subscription=sub,
                    current_plan=sub.plan,
                    target_plan=sub.pending_plan,
                )
                credit_cents = quote.credit_cents
                charge_cents = quote.charge_cents
            except ValueError:
                charge_cents = sub.pending_plan.price_cents

        if provider == "asaas" and payment_id:
            try:
                gateway = AsaasPaymentGateway()
                payment = await gateway.get_payment(str(payment_id))
                raw_status = str(payment.get("status", "")).upper()
                if raw_status in _PAYMENT_SUCCESS:
                    payment_status = "paid"
                elif raw_status not in _PAYMENT_PENDING:
                    payment_status = raw_status.lower()
                payment_value = payment.get("value")
                if payment_value is not None:
                    charge_cents = int(round(float(payment_value) * 100))
            except (PaymentGatewayConfigError, PaymentGatewayError):
                payment_status = "pending"

        return {
            "session_id": session_id,
            "provider": provider,
            "status": payment_status,
            "plan": {
                "slug": plan.slug,
                "name": plan.name,
                "description": plan.description,
                "price_cents": charge_cents if charge_cents is not None else plan.price_cents,
                "currency": plan.currency,
                "billing_interval": plan.billing_interval,
            },
            "customer_name": professional.name,
            "customer_email": professional.email,
            "has_cpf": bool(professional.cpf),
            "charge_cents": charge_cents,
            "credit_cents": credit_cents,
            "change_type": change_type,
        }

    async def generate_pix(
        self, *, session_id: str, professional: Professional
    ) -> dict[str, Any]:
        sub = await self._get_subscription(
            session_id=session_id, professional_id=str(professional.id)
        )
        provider = (sub.provider or "stub").lower()
        payment_id = str(sub.external_checkout_id or session_id)

        if provider == "asaas":
            try:
                gateway = AsaasPaymentGateway()
                pix = await gateway.get_pix_qr_code(payment_id)
            except (PaymentGatewayConfigError, PaymentGatewayError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=str(exc),
                ) from exc
        else:
            gateway = StubPaymentGateway()
            pix = await gateway.get_pix_qr_code(payment_id)

        return {
            "session_id": session_id,
            "provider": provider,
            "encoded_image": pix.get("encoded_image"),
            "payload": pix.get("payload"),
            "expiration_date": pix.get("expiration_date"),
        }

    async def pay_credit_card(
        self,
        *,
        session_id: str,
        professional: Professional,
        holder_name: str,
        number: str,
        expiry_month: str,
        expiry_year: str,
        ccv: str,
        postal_code: str,
        address_number: str,
        phone: str,
        installment_count: int = 1,
        remote_ip: str | None = None,
    ) -> dict[str, Any]:
        sub = await self._get_subscription(
            session_id=session_id, professional_id=str(professional.id)
        )
        provider = (sub.provider or "stub").lower()
        payment_id = str(sub.external_checkout_id or session_id)
        plan = sub.plan
        is_annual = _is_annual_interval(plan.billing_interval if plan else None)

        if installment_count < 1 or installment_count > 12:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Número de parcelas inválido. Escolha entre 1x e 12x.",
            )
        if installment_count > 1 and not is_annual:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Parcelamento está disponível apenas no plano anual.",
            )

        document = professional.cpf or ""
        if not document:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Informe seu CPF no cadastro ou checkout antes de pagar com cartão.",
            )

        holder_info = {
            "name": holder_name or professional.name,
            "email": professional.email,
            "cpfCnpj": document,
            "postalCode": postal_code.replace("-", ""),
            "addressNumber": address_number,
            "phone": phone.replace("-", "").replace(" ", ""),
        }
        card_number = number.replace(" ", "")

        response_session_id = session_id

        if provider == "asaas":
            try:
                gateway = AsaasPaymentGateway()
                if installment_count > 1:
                    result = await self._pay_asaas_installments(
                        gateway=gateway,
                        sub=sub,
                        professional=professional,
                        payment_id=payment_id,
                        holder_name=holder_name,
                        number=card_number,
                        expiry_month=expiry_month,
                        expiry_year=expiry_year,
                        ccv=ccv,
                        holder_info=holder_info,
                        remote_ip=remote_ip or "127.0.0.1",
                        installment_count=installment_count,
                    )
                    response_session_id = str(sub.external_checkout_id or session_id)
                else:
                    result = await gateway.pay_with_credit_card(
                        payment_id=payment_id,
                        holder_name=holder_name,
                        number=card_number,
                        expiry_month=expiry_month,
                        expiry_year=expiry_year,
                        ccv=ccv,
                        holder_info=holder_info,
                    )
            except (PaymentGatewayConfigError, PaymentGatewayError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=str(exc),
                ) from exc
        else:
            gateway = StubPaymentGateway()
            result = await gateway.pay_with_credit_card()

        raw_status = str(result.get("status", "")).upper()
        if provider == "stub":
            try:
                gateway = get_payment_gateway()
            except PaymentGatewayConfigError:
                gateway = StubPaymentGateway()
            change_svc = PlanChangeService(self.db, gateway)
            upgrade_applied = await change_svc.apply_pending_upgrade(professional.id)
            if upgrade_applied:
                return {
                    "session_id": response_session_id,
                    "provider": provider,
                    "status": "paid",
                    "message": "Upgrade aplicado com sucesso.",
                }
            reconcile = BillingReconciliationService(self.db)
            sim = await reconcile.simulate_stub_payment(professional.id)
            return {
                "session_id": response_session_id,
                "provider": provider,
                "status": "paid" if sim.get("applied") else "pending",
                "message": sim.get("message", "Pagamento simulado."),
            }
        if raw_status in _PAYMENT_SUCCESS:
            reconcile = BillingReconciliationService(self.db)
            await reconcile.reconcile_professional(professional.id)

        return {
            "session_id": response_session_id,
            "provider": provider,
            "status": "paid" if raw_status in _PAYMENT_SUCCESS else "pending",
            "message": "Pagamento processado com sucesso."
            if raw_status in _PAYMENT_SUCCESS
            else "Pagamento em processamento.",
        }

    async def _pay_asaas_installments(
        self,
        *,
        gateway: AsaasPaymentGateway,
        sub: Subscription,
        professional: Professional,
        payment_id: str,
        holder_name: str,
        number: str,
        expiry_month: str,
        expiry_year: str,
        ccv: str,
        holder_info: dict[str, Any],
        remote_ip: str,
        installment_count: int,
    ) -> dict[str, Any]:
        plan = sub.plan
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Plano da sessão de pagamento não encontrado.",
            )

        customer_svc = BillingCustomerService(self.db)
        customer_id = await customer_svc.get_external_customer_id(
            professional_id=str(professional.id),
            provider="asaas",
        )
        if not customer_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cliente Asaas não encontrado. Reinicie o checkout.",
            )

        await gateway.delete_payment(payment_id)

        result = await gateway.pay_with_credit_card_installments(
            customer_id=customer_id,
            total_value_cents=plan.price_cents,
            installment_count=installment_count,
            holder_name=holder_name,
            number=number,
            expiry_month=expiry_month,
            expiry_year=expiry_year,
            ccv=ccv,
            holder_info=holder_info,
            remote_ip=remote_ip,
            description=f"Assinatura {plan.name} — KorusFono ({installment_count}x)",
            external_reference=f"{professional.id}:{plan.slug}",
        )

        new_payment_id = str(result["id"])
        sub.external_checkout_id = new_payment_id
        await self.db.commit()

        if sub.external_subscription_id:
            next_due = (date.today() + timedelta(days=365)).isoformat()
            try:
                await gateway.defer_subscription_renewal(
                    subscription_id=str(sub.external_subscription_id),
                    next_due_date=next_due,
                )
            except PaymentGatewayError:
                # ponytail: renewal deferral is best-effort; installment already charged
                pass

        return result
