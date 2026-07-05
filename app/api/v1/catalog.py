from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_optional_professional
from app.core.diagnosis_catalog import list_diagnoses
from app.core.specialty_catalog import is_valid_specialty_key
from app.db.session import get_db
from app.models.professional import Professional
from app.schemas.catalog import DiagnosisCatalogItem

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/diagnoses", response_model=list[DiagnosisCatalogItem])
async def get_diagnoses(
    specialty_key: str | None = Query(None, alias="specialtyKey"),
    professional: Professional | None = Depends(get_optional_professional),
    db: AsyncSession = Depends(get_db),
):
    del db  # reserved for future catalog persistence
    key = specialty_key
    if key is None:
        if professional is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe specialtyKey ou autentique-se",
            )
        key = professional.specialty_key
    if not is_valid_specialty_key(key):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Especialidade inválida")
    return [DiagnosisCatalogItem(**item) for item in list_diagnoses(key)]
