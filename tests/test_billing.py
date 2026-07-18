"""Billing webhook and reconciliation tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.billing.types import InternalBillingEventType
from app.billing.webhook_normalizer import StubWebhookNormalizer
from app.models.billing import Plan, Subscription
from app.models.professional import Professional
from app.services.billing_checkout_service import BillingCheckoutService
from app.services.plan_catalog_seed import COMMERCIAL_PLAN_SEEDS
from app.services.saas_billing_service import SaasBillingService


@pytest.mark.asyncio
async def test_stub_webhook_activates_subscription(db_session):
    plan = Plan(**COMMERCIAL_PLAN_SEEDS[0])
    professional = Professional(
        email="billing@test.com",
        password_hash="hash",
        name="Billing User",
        subscription_status="trialing",
        trial_started_at=datetime.now(UTC),
        trial_ends_at=datetime.now(UTC),
    )
    db_session.add_all([plan, professional])
    await db_session.flush()

    sub = Subscription(
        professional_id=professional.id,
        plan_id=plan.id,
        status="incomplete",
        provider="stub",
        external_subscription_id="stub_sub_test",
        external_checkout_id="stub_pay_test",
    )
    db_session.add(sub)
    await db_session.commit()

    professional_id = str(professional.id)
    normalizer = StubWebhookNormalizer()
    events = normalizer.normalize(
        {
            "id": "evt-1",
            "event_type": InternalBillingEventType.PAYMENT_SUCCEEDED.value,
            "professional_id": professional_id,
            "plan_slug": plan.slug,
            "provider": "stub",
            "external_subscription_id": "stub_sub_test",
            "subscription_status": "active",
        },
        {},
    )

    billing = SaasBillingService(db_session)
    row = await billing.record_webhook_raw(
        provider="stub",
        external_event_id=events[0].external_event_id,
        event_type=events[0].event_type.value,
        payload=events[0].payload,
        professional_id=professional_id,
    )
    assert row is not None
    await billing.apply_normalized_events(events)

    await db_session.refresh(professional)
    await db_session.refresh(sub)
    assert professional.subscription_status == "active"
    assert sub.status == "active"


def _card_kwargs() -> dict:
    return {
        "holder_name": "Test User",
        "number": "5162306219378829",
        "expiry_month": "05",
        "expiry_year": "2030",
        "ccv": "123",
        "postal_code": "01310100",
        "address_number": "100",
        "phone": "11999990000",
    }


@pytest.mark.asyncio
async def test_credit_card_installments_rejected_on_monthly(db_session):
    plan = Plan(**{**COMMERCIAL_PLAN_SEEDS[0], "billing_interval": "monthly"})
    professional = Professional(
        email="installments-monthly@test.com",
        password_hash="hash",
        name="Monthly User",
        cpf="24971563792",
        subscription_status="trialing",
        trial_started_at=datetime.now(UTC),
        trial_ends_at=datetime.now(UTC),
    )
    db_session.add_all([plan, professional])
    await db_session.flush()

    sub = Subscription(
        professional_id=professional.id,
        plan_id=plan.id,
        status="incomplete",
        provider="stub",
        external_subscription_id="stub_sub_monthly",
        external_checkout_id="stub_pay_monthly",
    )
    db_session.add(sub)
    await db_session.commit()

    service = BillingCheckoutService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.pay_credit_card(
            session_id="stub_pay_monthly",
            professional=professional,
            installment_count=10,
            **_card_kwargs(),
        )
    assert exc_info.value.status_code == 422
    assert "anual" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_credit_card_installments_accepts_range_on_yearly_stub(db_session):
    yearly = next(p for p in COMMERCIAL_PLAN_SEEDS if p["billing_interval"] == "yearly")
    plan = Plan(**yearly)
    professional = Professional(
        email="installments-range@test.com",
        password_hash="hash",
        name="Range User",
        cpf="24971563792",
        subscription_status="trialing",
        trial_started_at=datetime.now(UTC),
        trial_ends_at=datetime.now(UTC),
    )
    db_session.add_all([plan, professional])
    await db_session.flush()

    sub = Subscription(
        professional_id=professional.id,
        plan_id=plan.id,
        status="incomplete",
        provider="stub",
        external_subscription_id="stub_sub_range",
        external_checkout_id="stub_pay_range",
    )
    db_session.add(sub)
    await db_session.commit()

    service = BillingCheckoutService(db_session)
    with (
        patch(
            "app.services.billing_checkout_service.PlanChangeService.apply_pending_upgrade",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "app.services.billing_checkout_service.BillingReconciliationService.simulate_stub_payment",
            new_callable=AsyncMock,
            return_value={"applied": True, "message": "Pagamento simulado."},
        ),
    ):
        result = await service.pay_credit_card(
            session_id="stub_pay_range",
            professional=professional,
            installment_count=3,
            **_card_kwargs(),
        )
    assert result["status"] == "paid"


@pytest.mark.asyncio
async def test_credit_card_installments_accepted_on_yearly_stub(db_session):
    yearly = next(p for p in COMMERCIAL_PLAN_SEEDS if p["billing_interval"] == "yearly")
    plan = Plan(**yearly)
    professional = Professional(
        email="installments-yearly@test.com",
        password_hash="hash",
        name="Yearly User",
        cpf="24971563792",
        subscription_status="trialing",
        trial_started_at=datetime.now(UTC),
        trial_ends_at=datetime.now(UTC),
    )
    db_session.add_all([plan, professional])
    await db_session.flush()

    sub = Subscription(
        professional_id=professional.id,
        plan_id=plan.id,
        status="incomplete",
        provider="stub",
        external_subscription_id="stub_sub_yearly",
        external_checkout_id="stub_pay_yearly",
    )
    db_session.add(sub)
    await db_session.commit()

    service = BillingCheckoutService(db_session)
    # Stub reconcile hits sqlite UUID binding quirks; mock post-pay path.
    with (
        patch(
            "app.services.billing_checkout_service.PlanChangeService.apply_pending_upgrade",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "app.services.billing_checkout_service.BillingReconciliationService.simulate_stub_payment",
            new_callable=AsyncMock,
            return_value={"applied": True, "message": "Pagamento simulado."},
        ),
    ):
        result = await service.pay_credit_card(
            session_id="stub_pay_yearly",
            professional=professional,
            installment_count=10,
            **_card_kwargs(),
        )
    assert result["status"] == "paid"
    assert result["provider"] == "stub"
