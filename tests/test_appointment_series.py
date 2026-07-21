"""Tests for recurring appointment series slot generation."""

from datetime import date, time, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from app.db.session import get_db
from app.main import app
from app.models.appointment import Appointment
from app.services.appointment_series_slots import (
    MAX_RECURRENT_DAYS,
    AppointmentSlot,
    iter_recurring_child_slots,
    slot_matches,
    validate_recurrent_range,
)


def test_iter_recurring_child_slots_weekly_skips_anchor_day():
    start = date(2026, 1, 5)
    end = date(2026, 1, 19)
    slots = list(
        iter_recurring_child_slots(
            frequency="semanal",
            start_date=start,
            end_date=end,
            start_time=time(10, 0),
            end_time=time(11, 0),
            duration=60,
        )
    )
    assert slots == [
        AppointmentSlot(date(2026, 1, 12), time(10, 0), time(11, 0), 60),
        AppointmentSlot(date(2026, 1, 19), time(10, 0), time(11, 0), 60),
    ]


def test_slot_matches_exact_time():
    slot = AppointmentSlot(date(2026, 1, 12), time(10, 0), time(11, 0), 60)
    assert slot_matches(slot, date(2026, 1, 12), time(10, 0), time(11, 0))
    assert not slot_matches(slot, date(2026, 1, 12), time(10, 30), time(11, 0))


def test_validate_recurrent_range_rejects_over_max_days():
    start = date(2026, 1, 1)
    end = start + timedelta(days=MAX_RECURRENT_DAYS + 1)
    with pytest.raises(ValueError, match=str(MAX_RECURRENT_DAYS)):
        validate_recurrent_range(start, end)


def test_iter_recurring_child_slots_personalizado_weekdays():
    start = date(2026, 1, 5)  # Monday
    end = date(2026, 1, 18)
    slots = list(
        iter_recurring_child_slots(
            frequency="personalizado",
            start_date=start,
            end_date=end,
            start_time=time(10, 0),
            end_time=time(11, 0),
            weekdays=[0, 2],
            duration=60,
        )
    )
    assert slots == [
        AppointmentSlot(date(2026, 1, 7), time(10, 0), time(11, 0), 60),
        AppointmentSlot(date(2026, 1, 12), time(10, 0), time(11, 0), 60),
        AppointmentSlot(date(2026, 1, 14), time(10, 0), time(11, 0), 60),
    ]


def test_iter_recurring_child_slots_personalizado_per_weekday_times():
    from app.services.appointment_series_slots import WeekdaySlotRule

    start = date(2026, 1, 5)  # Monday
    end = date(2026, 1, 14)
    slots = list(
        iter_recurring_child_slots(
            frequency="personalizado",
            start_date=start,
            end_date=end,
            start_time=time(9, 0),
            end_time=time(9, 50),
            weekdays=[0, 2],
            duration=50,
            weekday_rules=[
                WeekdaySlotRule(weekday=0, start_time=time(9, 0), duration=50),
                WeekdaySlotRule(weekday=2, start_time=time(14, 0), duration=30),
            ],
        )
    )
    assert slots == [
        AppointmentSlot(date(2026, 1, 7), time(14, 0), time(14, 30), 30),
        AppointmentSlot(date(2026, 1, 12), time(9, 0), time(9, 50), 50),
        AppointmentSlot(date(2026, 1, 14), time(14, 0), time(14, 30), 30),
    ]


@pytest.mark.asyncio
async def test_create_personalizado_series(
    db_session, professional, patient, auth_headers,
):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    start = date(2026, 6, 1)  # Monday
    end = date(2026, 6, 14)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/appointments",
            headers=auth_headers,
            json={
                "patientId": str(patient.id),
                "date": start.isoformat(),
                "time": "10:00",
                "type": "Terapia individual",
                "duration": 60,
                "status": "confirmado",
                "appointmentType": "recorrente",
                "frequency": "personalizado",
                "endDate": end.isoformat(),
                "weekdays": [0, 2],
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["frequency"] == "personalizado"
    assert body["weekdays"] == [0, 2]


@pytest.mark.asyncio
async def test_create_personalizado_series_with_weekday_slots(
    db_session, professional, patient, auth_headers,
):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    start = date(2026, 6, 1)  # Monday
    end = date(2026, 6, 14)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/appointments",
            headers=auth_headers,
            json={
                "patientId": str(patient.id),
                "date": start.isoformat(),
                "time": "09:00",
                "type": "Terapia individual",
                "duration": 50,
                "status": "confirmado",
                "appointmentType": "recorrente",
                "frequency": "personalizado",
                "endDate": end.isoformat(),
                "weekdaySlots": [
                    {"weekday": 0, "time": "09:00", "duration": 50},
                    {"weekday": 2, "time": "14:00", "duration": 30},
                ],
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["frequency"] == "personalizado"
    assert body["weekdays"] == [0, 2]
    slots = body["weekdaySlots"]
    assert len(slots) == 2
    assert slots[0]["weekday"] == 0 and slots[0]["duration"] == 50
    assert str(slots[0]["time"]).startswith("09:00")
    assert slots[1]["weekday"] == 2 and slots[1]["duration"] == 30
    assert str(slots[1]["time"]).startswith("14:00")

    result = await db_session.execute(
        select(Appointment).where(Appointment.patient_id == patient.id)
    )
    appointments = sorted(result.scalars().all(), key=lambda a: (a.date, a.time))
    by_date = {a.date: a for a in appointments}
    wed = by_date[date(2026, 6, 3)]
    assert wed.time == time(14, 0)
    assert wed.duration == 30
    mon2 = by_date[date(2026, 6, 8)]
    assert mon2.time == time(9, 0)
    assert mon2.duration == 50


@pytest.mark.asyncio
async def test_create_recurring_series_children_keep_recorrente_type(
    db_session, professional, patient, auth_headers,
):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    start = date(2026, 6, 1)
    end = date(2026, 6, 15)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/appointments",
            headers=auth_headers,
            json={
                "patientId": str(patient.id),
                "date": start.isoformat(),
                "time": "10:00",
                "type": "Terapia individual",
                "duration": 60,
                "status": "confirmado",
                "appointmentType": "recorrente",
                "frequency": "semanal",
                "endDate": end.isoformat(),
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["appointmentType"] == "recorrente"
    assert body["childrenCreated"] >= 1

    result = await db_session.execute(
        select(Appointment).where(Appointment.patient_id == patient.id)
    )
    appointments = result.scalars().all()
    assert len(appointments) >= 2
    assert all(a.appointment_type == "recorrente" for a in appointments)
