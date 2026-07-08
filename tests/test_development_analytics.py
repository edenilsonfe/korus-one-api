"""Unit tests for development analytics period filtering.

Creates only the tables needed (avoids JSONB ProtocolCatalog on SQLite).
"""

from datetime import date
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.db.base import Base
from app.models.goal import ClinicalDomainSnapshot
from app.models.patient import Patient
from app.models.professional import Professional
from app.services.patient import build_development_analytics, resolve_analytics_period_start

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                bind=sync_conn,
                tables=[
                    Professional.__table__,
                    Patient.__table__,
                    ClinicalDomainSnapshot.__table__,
                ],
            )
        )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def patient_with_snapshots(db_session: AsyncSession):
    pro = Professional(
        email="analytics@example.com",
        password_hash=hash_password("testpass123"),
        name="Dra. Analytics",
        specialty_key="fono",
        specialty="Fonoaudiologia",
        council="CRFa",
        phone="11999990000",
    )
    db_session.add(pro)
    await db_session.flush()
    patient = Patient(
        professional_id=pro.id,
        name="Ana Teste",
        birth_date=date(2020, 1, 1),
        diagnosis_keys=["tea"],
        status="ativo",
        start_date=date(2025, 1, 1),
        avatar_color="oklch(0.58 0.12 205)",
    )
    db_session.add(patient)
    await db_session.flush()

    points = [
        (date(2026, 1, 1), 40),
        (date(2026, 5, 1), 50),
        (date(2026, 6, 15), 60),
        (date(2026, 7, 1), 70),
    ]
    for recorded_at, score in points:
        db_session.add(
            ClinicalDomainSnapshot(
                id=uuid4(),
                patient_id=patient.id,
                key="linguagem",
                label="Linguagem",
                score=score,
                recorded_at=recorded_at,
            )
        )
    await db_session.commit()
    return patient


def test_resolve_analytics_period_start():
    today = date(2026, 7, 8)
    assert resolve_analytics_period_start("30d", today=today) == date(2026, 6, 8)
    assert resolve_analytics_period_start("90d", today=today) == date(2026, 4, 9)
    assert resolve_analytics_period_start(None, today=today) is None
    with pytest.raises(ValueError):
        resolve_analytics_period_start("2y", today=today)


@pytest.mark.asyncio
async def test_build_development_analytics_filters_period(patient_with_snapshots, db_session):
    today = date(2026, 7, 8)
    areas = await build_development_analytics(
        db_session, patient_with_snapshots.id, period="30d", today=today
    )
    assert len(areas) == 1
    area = areas[0]
    assert area["key"] == "linguagem"
    assert [p["date"] for p in area["history"]] == ["2026-06-15", "2026-07-01"]
    assert area["score"] == 70
    assert area["delta"] == 10


@pytest.mark.asyncio
async def test_build_development_analytics_90d_delta(patient_with_snapshots, db_session):
    today = date(2026, 7, 8)
    areas = await build_development_analytics(
        db_session, patient_with_snapshots.id, period="90d", today=today
    )
    area = areas[0]
    assert area["score"] == 70
    assert area["delta"] == 20
    assert len(area["history"]) == 3
