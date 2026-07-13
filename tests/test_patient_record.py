"""C3 PatientRecord — sectioned read of the patient chart."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, ProtocolCatalog
from app.models.patient import Patient
from app.models.professional import Professional
from app.models.session import Session
from app.services.patient_record import build_patient_detail, map_assessment


async def _insert_session(db: AsyncSession, *, patient_id, professional_id) -> Session:
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
            "type": "Terapia individual",
            "objectives": json.dumps([]),
            "notes": "",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
    )
    await db.commit()
    return (await db.execute(select(Session).where(Session.id == sid))).scalar_one()


@pytest.mark.asyncio
async def test_include_sessions_only_leaves_assessments_empty(
    db_session: AsyncSession,
    professional: Professional,
    patient: Patient,
):
    await _insert_session(db_session, patient_id=patient.id, professional_id=professional.id)

    detail = await build_patient_detail(db_session, patient, professional, {"sessions"})
    assert len(detail.sessions) == 1
    assert detail.assessments == []
    assert detail.goals == []


@pytest.mark.asyncio
async def test_map_assessment_includes_answers_and_scores(
    db_session: AsyncSession,
    professional: Professional,
    patient: Patient,
):
    proto = await db_session.get(ProtocolCatalog, "fois")
    assert proto is not None
    assessment = Assessment(
        patient_id=patient.id,
        professional_id=professional.id,
        protocol_id="fois",
        date=date.today(),
        result="FOIS 5",
        percentage=71,
        interpretation="ok",
        fields=[],
        answers={"fois_level": 5},
        scores={"total": 5, "engine": "scaled_sum"},
        status="completed",
    )
    db_session.add(assessment)
    await db_session.commit()
    await db_session.refresh(assessment)

    mapped = map_assessment(assessment, proto.name, professional.name)
    assert mapped["answers"] == {"fois_level": 5}
    assert mapped["scores"]["total"] == 5
    assert mapped["protocolId"] == "fois"


@pytest.mark.asyncio
async def test_include_assessments_uses_unified_mapper(
    db_session: AsyncSession,
    professional: Professional,
    patient: Patient,
):
    assessment = Assessment(
        patient_id=patient.id,
        professional_id=professional.id,
        protocol_id="fois",
        date=date.today(),
        result="FOIS 5",
        percentage=71,
        interpretation="ok",
        fields=[],
        answers={"fois_level": 5},
        scores={"total": 5},
        status="completed",
    )
    db_session.add(assessment)
    await db_session.commit()

    detail = await build_patient_detail(db_session, patient, professional, {"assessments"})
    assert len(detail.assessments) == 1
    assert detail.assessments[0].answers == {"fois_level": 5}
    assert detail.sessions == []
