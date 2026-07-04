from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import GOAL_ACHIEVED_THRESHOLD
from app.models.appointment import Appointment
from app.models.assessment import Assessment
from app.models.patient import Patient
from app.models.session import Session
from app.models.ai import AIReport


async def build_dashboard(db: AsyncSession, professional_id) -> dict:
    today = date.today()
    month_start = today.replace(day=1)

    active_patients = await db.scalar(
        select(func.count()).select_from(Patient).where(
            Patient.professional_id == professional_id, Patient.status == "ativo"
        )
    )
    new_this_month = await db.scalar(
        select(func.count()).select_from(Patient).where(
            Patient.professional_id == professional_id, Patient.start_date >= month_start
        )
    )
    sessions_done = await db.scalar(
        select(func.count())
        .select_from(Session)
        .join(Patient, Session.patient_id == Patient.id)
        .where(Patient.professional_id == professional_id)
    )
    sessions_pending = await db.scalar(
        select(func.count()).select_from(Appointment).where(
            Appointment.professional_id == professional_id,
            Appointment.status.in_(["pendente", "confirmado"]),
            Appointment.date >= today,
        )
    )
    ai_reports = await db.scalar(
        select(func.count()).select_from(AIReport).where(AIReport.professional_id == professional_id)
    )

    # Monthly growth - last 6 months
    monthly_growth = []
    for i in range(5, -1, -1):
        ref = today.replace(day=1) - timedelta(days=i * 30)
        month_start_i = ref.replace(day=1)
        if month_start_i.month == 12:
            month_end = month_start_i.replace(year=month_start_i.year + 1, month=1)
        else:
            month_end = month_start_i.replace(month=month_start_i.month + 1)
        count = await db.scalar(
            select(func.count()).select_from(Patient).where(
                Patient.professional_id == professional_id,
                Patient.start_date >= month_start_i,
                Patient.start_date < month_end,
            )
        )
        month_names = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        monthly_growth.append({"month": month_names[month_start_i.month - 1], "pacientes": count or 0})

    # Protocols applied
    protocols_result = await db.execute(
        select(Assessment.protocol_id, func.count())
        .join(Patient, Assessment.patient_id == Patient.id)
        .where(Patient.professional_id == professional_id)
        .group_by(Assessment.protocol_id)
        .order_by(func.count().desc())
        .limit(10)
    )
    protocols_applied = [{"name": row[0].upper(), "value": row[1]} for row in protocols_result.all()]

    # Upcoming appointments today
    appts_result = await db.execute(
        select(Appointment, Patient)
        .join(Patient, Appointment.patient_id == Patient.id)
        .where(
            Appointment.professional_id == professional_id,
            Appointment.date == today,
            Appointment.status.in_(["pendente", "confirmado"]),
        )
        .order_by(Appointment.time.asc())
        .limit(10)
    )
    upcoming = []
    for appt, patient in appts_result.all():
        upcoming.append({
            "id": str(appt.id),
            "time": appt.time.strftime("%H:%M"),
            "patientName": patient.name,
            "type": appt.type,
            "therapist": "",
        })

    # Patient evolution placeholder from domain snapshots avg
    patient_evolution = [
        {"month": "Jan", "vocabulario": 42, "pragmatica": 30},
        {"month": "Fev", "vocabulario": 48, "pragmatica": 35},
        {"month": "Mar", "vocabulario": 55, "pragmatica": 41},
        {"month": "Abr", "vocabulario": 61, "pragmatica": 50},
        {"month": "Mai", "vocabulario": 68, "pragmatica": 58},
        {"month": "Jun", "vocabulario": 74, "pragmatica": 65},
    ]

    return {
        "kpis": {
            "activePatients": active_patients or 0,
            "newThisMonth": new_this_month or 0,
            "sessionsDone": sessions_done or 0,
            "sessionsPending": sessions_pending or 0,
            "aiReports": ai_reports or 0,
        },
        "patientEvolution": patient_evolution,
        "monthlyGrowth": monthly_growth,
        "upcomingAppointments": upcoming,
        "protocolsApplied": protocols_applied,
    }
