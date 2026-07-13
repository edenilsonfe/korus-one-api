"""Equivalence tests for get_patient_aggregates_batch vs sequential get_patient_aggregates.

Standalone setup: creates only the tables needed on an in-memory SQLite DB,
mirroring the pattern in test_session_evolutions_idor.py (Session.objectives
is a Postgres ARRAY column that needs a sqlite DDL fallback).
"""

import json
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.core.constants import GOAL_ACHIEVED_THRESHOLD
from app.db.base import Base
from app.models.assessment import ASSESSMENT_STATUS_COMPLETED, Assessment, ProtocolCatalog
from app.models.goal import Goal
from app.models.patient import Patient
from app.models.professional import Professional
from app.models.session import Session
from app.services.patient import get_patient_aggregates, get_patient_aggregates_batch


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(element, compiler, **kw):
    return "JSON"


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                bind=sync_conn,
                tables=[
                    Professional.__table__,
                    Patient.__table__,
                    Session.__table__,
                    Goal.__table__,
                    ProtocolCatalog.__table__,
                    Assessment.__table__,
                ],
            )
        )
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


async def _make_professional(db):
    pro = Professional(
        email=f"{uuid.uuid4()}@example.com",
        password_hash="x",
        name="Dra. Teste",
        specialty_key="fono",
        specialty="Fonoaudiologia",
        council="CRFa",
        phone="11999990000",
    )
    db.add(pro)
    await db.commit()
    await db.refresh(pro)
    return pro


async def _make_patient(db, professional, *, name):
    p = Patient(
        professional_id=professional.id,
        name=name,
        birth_date=date.today().replace(year=date.today().year - 4),
        diagnosis_keys=["tea"],
        status="ativo",
        start_date=date.today() - timedelta(days=90),
        avatar_color="oklch(0.58 0.12 205)",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def _make_session(db, patient, professional, *, when):
    # Session.objectives is a Postgres ARRAY column; insert via raw SQL to
    # avoid SQLAlchemy's lack of a bind processor for it on SQLite.
    session_id = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO sessions "
            "(id, patient_id, professional_id, date, duration, type, objectives, notes, created_at, updated_at) "
            "VALUES (:id, :patient_id, :professional_id, :date, :duration, :type, :objectives, :notes, :created_at, :updated_at)"
        ),
        {
            "id": session_id.hex,
            "patient_id": patient.id.hex,
            "professional_id": professional.id.hex,
            "date": when.isoformat(),
            "duration": 45,
            "type": "atendimento",
            "objectives": json.dumps([]),
            "notes": "",
            "created_at": when.isoformat(),
            "updated_at": when.isoformat(),
        },
    )
    await db.commit()


async def _make_goal(db, patient, professional, *, progress):
    g = Goal(
        patient_id=patient.id,
        professional_id=professional.id,
        title="Meta",
        area="linguagem",
        progress=progress,
        start_date=date.today() - timedelta(days=30),
        status="Em andamento",
    )
    db.add(g)
    await db.commit()


async def _make_protocol(db, protocol_id="protocolo-teste"):
    protocol = ProtocolCatalog(
        id=protocol_id,
        name="Protocolo Teste",
        full_name="Protocolo Teste Completo",
        description="Teste",
        age_range="0-99",
        field_templates=[],
    )
    db.add(protocol)
    await db.commit()
    return protocol


async def _make_assessment(db, patient, professional, protocol, *, status):
    a = Assessment(
        patient_id=patient.id,
        professional_id=professional.id,
        protocol_id=protocol.id,
        date=date.today(),
        result="ok",
        percentage=80,
        status=status,
    )
    db.add(a)
    await db.commit()


async def test_batch_matches_sequential_for_multiple_patients(db):
    pro = await _make_professional(db)
    protocol = await _make_protocol(db)

    empty_patient = await _make_patient(db, pro, name="Sem dados")

    active_patient = await _make_patient(db, pro, name="Com dados")
    now = datetime.now(timezone.utc)
    await _make_session(db, active_patient, pro, when=now - timedelta(days=5))
    await _make_session(db, active_patient, pro, when=now)
    await _make_goal(db, active_patient, pro, progress=GOAL_ACHIEVED_THRESHOLD)
    await _make_goal(db, active_patient, pro, progress=GOAL_ACHIEVED_THRESHOLD - 1)
    await _make_assessment(db, active_patient, pro, protocol, status=ASSESSMENT_STATUS_COMPLETED)
    await _make_assessment(db, active_patient, pro, protocol, status="draft")

    boundary_patient = await _make_patient(db, pro, name="No limite")
    await _make_goal(db, boundary_patient, pro, progress=GOAL_ACHIEVED_THRESHOLD)

    patient_ids = [empty_patient.id, active_patient.id, boundary_patient.id]

    batch = await get_patient_aggregates_batch(db, patient_ids)
    sequential = {pid: await get_patient_aggregates(db, pid) for pid in patient_ids}

    assert batch == sequential

    assert batch[empty_patient.id] == {
        "sessions_count": 0,
        "protocols_done": 0,
        "total_goals": 0,
        "goals_achieved": 0,
        "last_session": None,
    }
    assert batch[active_patient.id]["sessions_count"] == 2
    assert batch[active_patient.id]["protocols_done"] == 1
    assert batch[active_patient.id]["total_goals"] == 2
    assert batch[active_patient.id]["goals_achieved"] == 1
    assert batch[boundary_patient.id]["goals_achieved"] == 1


async def test_batch_empty_patient_ids_returns_empty_dict(db):
    assert await get_patient_aggregates_batch(db, []) == {}
