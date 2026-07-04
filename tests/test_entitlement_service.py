"""Entitlement / trial write access tests."""

from datetime import UTC, datetime, timedelta

import pytest

from app.models.professional import Professional
from app.services.entitlement_service import EntitlementService


@pytest.mark.asyncio
async def test_can_write_trialing_future(db_session):
    professional = Professional(
        email="trial@test.com",
        password_hash="hash",
        name="Trial User",
        subscription_status="trialing",
        trial_started_at=datetime.now(UTC),
        trial_ends_at=datetime.now(UTC) + timedelta(days=3),
    )
    db_session.add(professional)
    await db_session.commit()

    svc = EntitlementService(db_session)
    assert await svc.can_write(professional) is True


@pytest.mark.asyncio
async def test_can_write_trialing_expired_sets_trial_expired(db_session):
    professional = Professional(
        email="expired@test.com",
        password_hash="hash",
        name="Expired User",
        subscription_status="trialing",
        trial_started_at=datetime.now(UTC) - timedelta(days=10),
        trial_ends_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(professional)
    await db_session.commit()

    svc = EntitlementService(db_session)
    assert await svc.can_write(professional) is False
    assert professional.subscription_status == "trial_expired"


@pytest.mark.asyncio
async def test_can_write_active(db_session):
    professional = Professional(
        email="active@test.com",
        password_hash="hash",
        name="Active User",
        subscription_status="active",
    )
    db_session.add(professional)
    await db_session.commit()

    svc = EntitlementService(db_session)
    assert await svc.can_write(professional) is True
