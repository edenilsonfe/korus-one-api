"""Public billing plan and checkout schemas."""

from typing import Any

from pydantic import Field

from app.schemas.common import CamelModel


class PlanPublicResponse(CamelModel):
    id: str
    slug: str
    name: str
    description: str | None = None
    limits: dict[str, Any] | None = None
    price_cents: int = 0
    currency: str = "BRL"
    billing_interval: str = "monthly"
    features: list[Any] = Field(default_factory=list)
    badge: str | None = None
    highlighted: bool = False
    display_order: int = 0
    is_active: bool = True


class CheckoutRequest(CamelModel):
    plan_slug: str
    cpf: str | None = None
    coupon_code: str | None = None


class CheckoutResponse(CamelModel):
    checkout_url: str | None = None
    session_id: str | None = None
    status: str | None = None
    provider: str | None = None
    message: str | None = None
    change_type: str | None = None
    charge_cents: int | None = None
    credit_cents: int | None = None
    scheduled_at: str | None = None


class PlanChangePreviewResponse(CamelModel):
    change_type: str
    message: str
    current_plan_slug: str | None = None
    target_plan_slug: str | None = None
    credit_cents: int | None = None
    charge_cents: int | None = None
    target_price_cents: int | None = None
    scheduled_at: str | None = None
    period_end: str | None = None
    remaining_days: int | None = None


class ReconcileResponse(CamelModel):
    applied: bool
    message: str
    payments_checked: int = 0
    subscription_status: str | None = None
    professional_status: str | None = None
    plan_slug: str | None = None


class PlanSummary(CamelModel):
    id: str
    slug: str
    name: str
    billing_interval: str = "monthly"


class PendingPlanSummary(CamelModel):
    id: str
    slug: str
    name: str
    billing_interval: str = "monthly"


class SubscriptionSummary(CamelModel):
    id: str
    status: str
    plan: PlanSummary
    started_at: str | None = None
    last_payment_at: str | None = None
    current_period_end: str | None = None
    pending_plan: PendingPlanSummary | None = None
    pending_change_at: str | None = None


class BillingMeResponse(CamelModel):
    subscription_status: str
    trial_started_at: str | None = None
    trial_ends_at: str | None = None
    can_write: bool
    subscription: SubscriptionSummary | None = None


class PaymentSessionPlan(CamelModel):
    slug: str
    name: str
    description: str | None = None
    price_cents: int
    currency: str = "BRL"
    billing_interval: str = "monthly"


class PaymentSessionResponse(CamelModel):
    session_id: str
    provider: str
    status: str
    plan: PaymentSessionPlan
    customer_name: str
    customer_email: str
    has_cpf: bool = False
    charge_cents: int | None = None
    change_type: str | None = None
    credit_cents: int | None = None


class PixCheckoutResponse(CamelModel):
    session_id: str
    provider: str
    encoded_image: str | None = None
    payload: str | None = None
    expiration_date: str | None = None


class CreditCardPaymentRequest(CamelModel):
    holder_name: str
    number: str
    expiry_month: str
    expiry_year: str
    ccv: str
    postal_code: str
    address_number: str
    phone: str


class CreditCardPaymentResponse(CamelModel):
    session_id: str
    provider: str
    status: str
    message: str
