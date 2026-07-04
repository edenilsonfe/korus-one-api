from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.spm import SpmInformantDraftUpdate, SpmInformantProgress, SpmInformantSession, SpmInformantSubmit
from app.services.spm_informant_service import SpmInformantService

router = APIRouter(prefix="/spm/informant", tags=["spm-informant"])


@router.get("/{token}", response_model=SpmInformantSession)
async def get_informant_session(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    service = SpmInformantService(db)
    return await service.get_session(token)


@router.put("/{token}/draft", response_model=SpmInformantProgress)
async def save_informant_draft(
    token: str,
    data: SpmInformantDraftUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = SpmInformantService(db)
    return await service.save_draft(token, data.answers)


@router.post("/{token}/submit", response_model=SpmInformantProgress, status_code=status.HTTP_200_OK)
async def submit_informant_form(
    token: str,
    data: SpmInformantSubmit,
    db: AsyncSession = Depends(get_db),
):
    service = SpmInformantService(db)
    return await service.submit(
        token,
        answers=data.answers,
        informant_name=data.informant_name,
        informant_relationship=data.informant_relationship,
    )
