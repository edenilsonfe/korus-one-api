"""Proration helpers for subscription plan changes."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.models.billing import Plan, Subscription

MONTHLY_INTERVALS = frozenset({"monthly", "month"})
YEARLY_INTERVALS = frozenset({"yearly", "annual", "year"})


def is_monthly_interval(interval: str | None) -> bool:
    return (interval or "monthly").lower().strip() in MONTHLY_INTERVALS


def is_yearly_interval(interval: str | None) -> bool:
    return (interval or "").lower().strip() in YEARLY_INTERVALS


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day, tzinfo=UTC)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def infer_period_end(subscription: Subscription, plan: Plan, *, now: datetime | None = None) -> datetime:
    if subscription.current_period_end:
        return _ensure_utc(subscription.current_period_end)

    anchor = subscription.last_payment_at or subscription.started_at
    if anchor is None:
        anchor = now or datetime.now(UTC)
    anchor = _ensure_utc(anchor)

    if is_monthly_interval(plan.billing_interval):
        return _add_months(anchor, 1)
    if is_yearly_interval(plan.billing_interval):
        return _add_months(anchor, 12)
    return anchor + timedelta(days=30)


@dataclass(frozen=True)
class UpgradeQuote:
    credit_cents: int
    charge_cents: int
    period_start: datetime
    period_end: datetime
    remaining_days: int
    total_days: int


def calculate_monthly_to_yearly_upgrade(
    *,
    subscription: Subscription,
    current_plan: Plan,
    target_plan: Plan,
    now: datetime | None = None,
) -> UpgradeQuote:
    if not is_monthly_interval(current_plan.billing_interval):
        raise ValueError("Plano atual não é mensal.")
    if not is_yearly_interval(target_plan.billing_interval):
        raise ValueError("Plano alvo não é anual.")

    now = _ensure_utc(now or datetime.now(UTC))
    period_end = infer_period_end(subscription, current_plan, now=now)
    period_start = subscription.last_payment_at or subscription.started_at
    if period_start is None:
        period_start = period_end - timedelta(days=30)
    period_start = _ensure_utc(period_start)

    if period_end <= now:
        credit_cents = 0
        remaining_days = 0
        total_days = max(1, (period_end - period_start).days)
    else:
        remaining_seconds = (period_end - now).total_seconds()
        total_seconds = max(1.0, (period_end - period_start).total_seconds())
        credit_cents = int(current_plan.price_cents * remaining_seconds / total_seconds)
        remaining_days = max(0, int(remaining_seconds // 86400))
        total_days = max(1, int(total_seconds // 86400))

    charge_cents = max(0, target_plan.price_cents - credit_cents)
    return UpgradeQuote(
        credit_cents=credit_cents,
        charge_cents=charge_cents,
        period_start=period_start,
        period_end=period_end,
        remaining_days=remaining_days,
        total_days=total_days,
    )
