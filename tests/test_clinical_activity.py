"""C4 ClinicalActivity — timeline emission without callers building title/description."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.evolution import Evolution
from app.models.patient import Patient
from app.models.professional import Professional
from app.models.session import Session
from app.models.timeline import TimelineEvent
from app.services import clinical_activity


async def _insert_session(db: AsyncSession, *, patient_id, professional_id, notes="") -> Session:
    sid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    await db.execute(
        text(
            "INSERT INTO sessions "
            "(id, patient_id, professional_id, date, duration, type, objectives, notes, created_at, updated_at) "
            "VALUES (:id, :patient_id, :professional_id, :date, :duration, :type, :objectives, :notes, :created_at, :updated_at)"
        ),
        {
            "id": sid.hex,
            "patient_id": patient_id.hex,
            "professional_id": professional_id.hex,
            "date": now.isoformat(),
            "duration": 45,
            "type": "Avaliação",
            "objectives": json.dumps([]),
            "notes": notes,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
    )
    await db.flush()
    return (await db.execute(select(Session).where(Session.id == sid))).scalar_one()


@pytest.mark.asyncio
async def test_record_session_builds_title(
    db_session: AsyncSession,
    professional: Professional,
    patient: Patient,
):
    session = await _insert_session(
        db_session,
        patient_id=patient.id,
        professional_id=professional.id,
        notes="Notas longas " * 30,
    )

    event = await clinical_activity.record_session(db_session, session=session, professional=professional)
    assert event.type == "sessao"
    assert event.title == "Sessão de Avaliação"
    assert len(event.description) <= 200
    assert event.source_id == session.id


@pytest.mark.asyncio
async def test_record_assessment_builds_title(
    db_session: AsyncSession,
    professional: Professional,
    patient: Patient,
):
    assessment = Assessment(
        patient_id=patient.id,
        professional_id=professional.id,
        protocol_id="fois",
        date=date.today(),
        result="FOIS nível 5",
        percentage=71,
        status="completed",
    )
    db_session.add(assessment)
    await db_session.flush()

    event = await clinical_activity.record_assessment(
        db_session,
        assessment=assessment,
        protocol_name="FOIS",
        professional=professional,
    )
    assert event.type == "avaliacao"
    assert event.title == "Avaliação FOIS aplicada"
    assert event.description == "FOIS nível 5"
    assert event.source_id == assessment.id


@pytest.mark.asyncio
async def test_record_evolution_builds_title(
    db_session: AsyncSession,
    professional: Professional,
    patient: Patient,
):
    evolution = Evolution(
        patient_id=patient.id,
        professional_id=professional.id,
        date=datetime.now(timezone.utc),
        title="Evolução semanal",
        content="A" * 300,
    )
    db_session.add(evolution)
    await db_session.flush()

    event = await clinical_activity.record_evolution(
        db_session, evolution=evolution, professional=professional
    )
    assert event.type == "evolucao"
    assert event.title == "Evolução semanal"
    assert len(event.description) == 200
    assert event.source_id == evolution.id


@pytest.mark.asyncio
async def test_deletion_event_survives_source_delete(
    db_session: AsyncSession,
    professional: Professional,
    patient: Patient,
):
    """Deletion test: timeline event persists after source entity is deleted."""
    session = await _insert_session(
        db_session, patient_id=patient.id, professional_id=professional.id
    )
    event = await clinical_activity.record_session(db_session, session=session, professional=professional)
    await db_session.commit()
    source_id = session.id
    event_id = event.id

    await db_session.delete(session)
    await db_session.commit()

    remaining = (
        await db_session.execute(select(TimelineEvent).where(TimelineEvent.id == event_id))
    ).scalar_one()
    assert remaining.source_id == source_id
    assert remaining.type == "sessao"
