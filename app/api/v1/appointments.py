from datetime import date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_professional, get_patient_for_professional
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.professional import Professional
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentCreateResponse,
    AppointmentResponse,
    AppointmentUpdate,
)
from app.services.appointment_series_slots import (
    iter_recurring_child_slots,
    validate_recurrent_range,
)
from app.services.whatsapp_queue import enqueue_whatsapp_appointment_event

router = APIRouter(prefix="/appointments", tags=["appointments"])

VALID_FREQUENCIES = {"semanal", "quinzenal", "mensal"}


def _end_time_from_duration(start: time, duration: int) -> time:
    start_dt = datetime.combine(date.today(), start)
    return (start_dt + timedelta(minutes=duration)).time()


def _to_response(appt: Appointment, patient_name: str, therapist: str) -> AppointmentResponse:
    return AppointmentResponse(
        id=str(appt.id),
        patient_id=str(appt.patient_id),
        patient=patient_name,
        date=appt.date.isoformat(),
        time=appt.time.strftime("%H:%M"),
        type=appt.type,
        therapist=therapist,
        duration=appt.duration,
        status=appt.status,
        appointment_type=appt.appointment_type,
        series_id=str(appt.series_id) if appt.series_id else None,
        frequency=appt.frequency,
        end_date=appt.end_date.isoformat() if appt.end_date else None,
    )


async def _check_conflict(
    db: AsyncSession,
    professional_id: UUID,
    appt_date: date,
    appt_time: time,
    duration: int,
    exclude_id: UUID | None = None,
) -> None:
    start = datetime.combine(appt_date, appt_time)
    end = start + timedelta(minutes=duration)
    result = await db.execute(
        select(Appointment).where(
            Appointment.professional_id == professional_id,
            Appointment.date == appt_date,
            Appointment.status.notin_(["cancelado"]),
        )
    )
    for existing in result.scalars().all():
        if exclude_id and existing.id == exclude_id:
            continue
        ex_start = datetime.combine(existing.date, existing.time)
        ex_end = ex_start + timedelta(minutes=existing.duration)
        if start < ex_end and end > ex_start:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflito de horário")


@router.get("", response_model=list[AppointmentResponse])
async def list_appointments(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Appointment, Patient)
        .join(Patient, Appointment.patient_id == Patient.id)
        .where(
            Appointment.professional_id == professional.id,
            Appointment.date >= from_date,
            Appointment.date <= to_date,
        )
        .order_by(Appointment.date.asc(), Appointment.time.asc())
    )
    return [_to_response(a, p.name, professional.name) for a, p in result.all()]


@router.post("", response_model=AppointmentCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    body: AppointmentCreate,
    background_tasks: BackgroundTasks,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    patient = await get_patient_for_professional(UUID(body.patient_id), professional, db)
    appointment_type = body.appointment_type or "avulso"

    if appointment_type == "recorrente":
        if not body.frequency or body.frequency not in VALID_FREQUENCIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Frequência inválida para compromisso recorrente",
            )
        if not body.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data fim é obrigatória para compromisso recorrente",
            )
        try:
            validate_recurrent_range(body.date, body.end_date)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await _check_conflict(db, professional.id, body.date, body.time, body.duration)

    end_time = _end_time_from_duration(body.time, body.duration)
    anchor = Appointment(
        professional_id=professional.id,
        patient_id=patient.id,
        date=body.date,
        time=body.time,
        type=body.type,
        duration=body.duration,
        status=body.status,
        appointment_type=appointment_type,
        frequency=body.frequency if appointment_type == "recorrente" else None,
        end_date=body.end_date if appointment_type == "recorrente" else None,
    )
    db.add(anchor)
    await db.flush()

    children_created = 0
    if appointment_type == "recorrente" and body.end_date:
        for slot in iter_recurring_child_slots(
            body.frequency,
            body.date,
            body.end_date,
            body.time,
            end_time,
        ):
            await _check_conflict(db, professional.id, slot.start_date, slot.start_time, body.duration)
            child = Appointment(
                professional_id=professional.id,
                patient_id=patient.id,
                date=slot.start_date,
                time=slot.start_time,
                type=body.type,
                duration=body.duration,
                status=body.status,
                appointment_type="recorrente",
                series_id=anchor.id,
                frequency=body.frequency,
                end_date=body.end_date,
            )
            db.add(child)
            children_created += 1

    await db.commit()
    await db.refresh(anchor)

    # Após a response — não bloquear o modal da agenda na Evolution.
    background_tasks.add_task(
        enqueue_whatsapp_appointment_event, anchor.id, "confirmation"
    )

    response = _to_response(anchor, patient.name, professional.name)
    return AppointmentCreateResponse(**response.model_dump(by_alias=False), children_created=children_created)


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: UUID,
    body: AppointmentUpdate,
    background_tasks: BackgroundTasks,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Appointment, Patient)
        .join(Patient, Appointment.patient_id == Patient.id)
        .where(Appointment.id == appointment_id, Appointment.professional_id == professional.id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    appt, patient = row
    data = body.model_dump(exclude_unset=True)
    old_date = appt.date
    old_time = appt.time
    old_status = appt.status
    new_date = data.get("date", appt.date)
    new_time = data.get("time", appt.time)
    new_duration = data.get("duration", appt.duration)
    if any(k in data for k in ("date", "time", "duration")):
        await _check_conflict(db, professional.id, new_date, new_time, new_duration, appt.id)
    for field, value in data.items():
        setattr(appt, field, value)
    await db.commit()
    await db.refresh(appt)

    if data.get("status") == "cancelado" and old_status != "cancelado":
        background_tasks.add_task(
            enqueue_whatsapp_appointment_event, appt.id, "cancelled"
        )
    elif (appt.date != old_date or appt.time != old_time) and appt.status != "cancelado":
        background_tasks.add_task(
            enqueue_whatsapp_appointment_event, appt.id, "rescheduled"
        )

    return _to_response(appt, patient.name, professional.name)


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: UUID,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id, Appointment.professional_id == professional.id)
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    await db.delete(appt)
