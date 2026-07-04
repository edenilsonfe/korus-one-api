from fastapi import APIRouter

from app.api.v1 import ai, appointments, auth, clinical, dashboard, me, patients, prontuario, sessions, timeline

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(patients.router)
api_router.include_router(appointments.router)
api_router.include_router(sessions.router)
api_router.include_router(sessions.patient_router)
api_router.include_router(prontuario.router)
api_router.include_router(timeline.router)
api_router.include_router(timeline.patient_router)
api_router.include_router(clinical.router)
api_router.include_router(clinical.patient_router)
api_router.include_router(dashboard.router)
api_router.include_router(ai.router)
