from datetime import date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_professional, get_patient_for_professional
from app.core.utils import utcnow
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.professional import Professional
from app.schemas.appointment import AppointmentCreate, AppointmentResponse, AppointmentUpdate

router = APIRouter(prefix="/appointments", tags=["appointments"])


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


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    body: AppointmentCreate,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    patient = await get_patient_for_professional(UUID(body.patient_id), professional, db)
    await _check_conflict(db, professional.id, body.date, body.time, body.duration)
    appt = Appointment(
        professional_id=professional.id,
        patient_id=patient.id,
        date=body.date,
        time=body.time,
        type=body.type,
        duration=body.duration,
        status=body.status,
    )
    db.add(appt)
    await db.commit()
    await db.refresh(appt)

    from app.services.whatsapp_notification_service import WhatsAppNotificationService

    await WhatsAppNotificationService.dispatch_appointment_event(appt.id, "confirmation")

    return _to_response(appt, patient.name, professional.name)


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: UUID,
    body: AppointmentUpdate,
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

    from app.services.whatsapp_notification_service import WhatsAppNotificationService

    if data.get("status") == "cancelado" and old_status != "cancelado":
        await WhatsAppNotificationService.dispatch_appointment_event(appt.id, "cancelled")
    elif (appt.date != old_date or appt.time != old_time) and appt.status != "cancelado":
        await WhatsAppNotificationService.dispatch_appointment_event(appt.id, "rescheduled")

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
