from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.patient import Patient
from app.models.professional import Professional

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_professional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Professional:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        professional_id = UUID(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from exc

    result = await db.execute(select(Professional).where(Professional.id == professional_id))
    professional = result.scalar_one_or_none()
    if professional is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Profissional não encontrado")
    return professional


async def get_optional_professional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Professional | None:
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            return None
        professional_id = UUID(payload["sub"])
    except Exception:
        return None

    result = await db.execute(select(Professional).where(Professional.id == professional_id))
    return result.scalar_one_or_none()


async def get_patient_for_professional(
    patient_id: UUID,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
) -> Patient:
    result = await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.professional_id == professional.id)
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente não encontrado")
    return patient
