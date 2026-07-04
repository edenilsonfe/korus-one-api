from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.mappers import format_size_bytes
from app.core.deps import get_current_professional, get_patient_for_professional
from app.core.utils import utcnow
from app.db.session import get_db
from app.models.anamnese import AnamneseEntry
from app.models.attachment import Attachment
from app.models.evolution import Evolution
from app.models.professional import Professional
from app.schemas.prontuario import AnamneseCreate, AnamneseResponse, EvolutionCreate, EvolutionResponse
from app.services.storage import storage_service
from app.services.timeline import create_timeline_event

router = APIRouter(prefix="/patients/{patient_id}", tags=["prontuario"])


@router.get("/evolutions", response_model=list[EvolutionResponse])
async def list_evolutions(
    patient_id: UUID,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    await get_patient_for_professional(patient_id, professional, db)
    result = await db.execute(
        select(Evolution).where(Evolution.patient_id == patient_id).order_by(Evolution.date.desc())
    )
    return [
        EvolutionResponse(
            id=str(e.id),
            patient_id=str(e.patient_id),
            session_id=str(e.session_id) if e.session_id else None,
            date=e.date.isoformat(),
            title=e.title,
            content=e.content,
            professional=professional.name,
        )
        for e in result.scalars().all()
    ]


@router.post("/evolutions", response_model=EvolutionResponse, status_code=status.HTTP_201_CREATED)
async def create_evolution(
    patient_id: UUID,
    body: EvolutionCreate,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    await get_patient_for_professional(patient_id, professional, db)
    evolution = Evolution(
        patient_id=patient_id,
        session_id=UUID(body.session_id) if body.session_id else None,
        professional_id=professional.id,
        date=utcnow(),
        title=body.title,
        content=body.content,
    )
    db.add(evolution)
    await db.flush()
    await create_timeline_event(
        db,
        patient_id=patient_id,
        professional_id=professional.id,
        event_type="evolucao",
        title=body.title,
        description=body.content[:200],
        source_id=evolution.id,
    )
    return EvolutionResponse(
        id=str(evolution.id),
        patient_id=str(patient_id),
        session_id=body.session_id,
        date=evolution.date.isoformat(),
        title=evolution.title,
        content=evolution.content,
        professional=professional.name,
    )


@router.get("/anamnese", response_model=list[AnamneseResponse])
async def list_anamnese(
    patient_id: UUID,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    await get_patient_for_professional(patient_id, professional, db)
    result = await db.execute(
        select(AnamneseEntry).where(AnamneseEntry.patient_id == patient_id).order_by(AnamneseEntry.section.asc())
    )
    return [
        AnamneseResponse(id=str(a.id), patient_id=str(a.patient_id), section=a.section, value=a.value)
        for a in result.scalars().all()
    ]


@router.post("/anamnese", response_model=AnamneseResponse, status_code=status.HTTP_201_CREATED)
async def upsert_anamnese(
    patient_id: UUID,
    body: AnamneseCreate,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    await get_patient_for_professional(patient_id, professional, db)
    result = await db.execute(
        select(AnamneseEntry).where(AnamneseEntry.patient_id == patient_id, AnamneseEntry.section == body.section)
    )
    entry = result.scalar_one_or_none()
    if entry:
        entry.value = body.value
    else:
        entry = AnamneseEntry(patient_id=patient_id, section=body.section, value=body.value)
        db.add(entry)
    await db.flush()
    return AnamneseResponse(id=str(entry.id), patient_id=str(patient_id), section=entry.section, value=entry.value)


CATEGORY_TIMELINE_MAP = {
    "video": "video",
    "audio": "audio",
    "foto": "foto",
    "relatorio": "documento",
}


@router.get("/attachments")
async def list_attachments(
    patient_id: UUID,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    await get_patient_for_professional(patient_id, professional, db)
    result = await db.execute(
        select(Attachment).where(Attachment.patient_id == patient_id).order_by(Attachment.date.desc())
    )
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "category": a.category,
            "date": a.date.isoformat(),
            "sizeBytes": a.size_bytes,
            "size": format_size_bytes(a.size_bytes),
        }
        for a in result.scalars().all()
    ]


@router.post("/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    patient_id: UUID,
    file: UploadFile = File(...),
    category: str = "relatorio",
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    await get_patient_for_professional(patient_id, professional, db)
    body = await file.read()
    key = storage_service.make_key(patient_id, file.filename or "upload")
    await storage_service.upload(key, body, file.content_type or "application/octet-stream")
    attachment = Attachment(
        patient_id=patient_id,
        professional_id=professional.id,
        name=file.filename or "upload",
        category=category,
        size_bytes=len(body),
        storage_key=key,
        date=utcnow(),
    )
    db.add(attachment)
    await db.flush()
    event_type = CATEGORY_TIMELINE_MAP.get(category, "documento")
    await create_timeline_event(
        db,
        patient_id=patient_id,
        professional_id=professional.id,
        event_type=event_type,
        title=f"Arquivo adicionado: {attachment.name}",
        description=category,
        source_id=attachment.id,
    )
    return {
        "id": str(attachment.id),
        "name": attachment.name,
        "category": attachment.category,
        "date": attachment.date.isoformat(),
        "sizeBytes": attachment.size_bytes,
        "size": format_size_bytes(attachment.size_bytes),
    }


@router.get("/attachments/{attachment_id}/url")
async def get_attachment_url(
    patient_id: UUID,
    attachment_id: UUID,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    await get_patient_for_professional(patient_id, professional, db)
    result = await db.execute(
        select(Attachment).where(Attachment.id == attachment_id, Attachment.patient_id == patient_id)
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Anexo não encontrado")
    url = await storage_service.presigned_url(attachment.storage_key)
    return {"url": url}
