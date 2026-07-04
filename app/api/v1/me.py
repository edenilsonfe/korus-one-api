from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_professional
from app.db.session import get_db
from app.models.professional import Professional
from app.schemas.professional import ProfessionalResponse, ProfessionalUpdate

router = APIRouter(prefix="/me", tags=["me"])


def _to_response(p: Professional) -> ProfessionalResponse:
    return ProfessionalResponse(
        id=str(p.id),
        name=p.name,
        specialty=p.specialty,
        council=p.council,
        email=p.email,
        phone=p.phone,
        cpf=p.cpf or "",
        avatar_color=p.avatar_color,
    )


@router.get("", response_model=ProfessionalResponse)
async def get_me(professional: Professional = Depends(get_current_professional)):
    return _to_response(professional)


@router.patch("", response_model=ProfessionalResponse)
async def update_me(
    body: ProfessionalUpdate,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(professional, field, value)
    await db.flush()
    return _to_response(professional)
