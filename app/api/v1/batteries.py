from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_professional
from app.db.session import get_db
from app.models.professional import Professional
from app.schemas.battery import (
    BatteryCreate,
    BatteryResponse,
    BatterySubformAnswersUpdate,
    BatterySubformFormResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.battery_report_service import export_battery_pdf
from app.services.battery_service import BatteryService
from app.services.instrument_content_package import get_instrument_content_package

router = APIRouter(prefix="/batteries", tags=["batteries"])


@router.post("", response_model=BatteryResponse, status_code=status.HTTP_201_CREATED)
async def create_battery(
    data: BatteryCreate,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    service = BatteryService(db)
    return await service.create_battery(data=data, professional_id=professional.id)


@router.get("", response_model=PaginatedResponse)
async def list_batteries(
    instrument_slug: str | None = Query(None, alias="instrumentSlug"),
    patient_id: UUID | None = Query(None, alias="patientId"),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    service = BatteryService(db)
    items, total = await service.list_batteries(
        professional_id=professional.id,
        instrument_slug=instrument_slug,
        patient_id=patient_id,
        status_filter=status_filter,
        page=page,
        limit=limit,
    )
    return PaginatedResponse(items=items, total=total, page=page, limit=limit)


@router.get("/{battery_id}", response_model=BatteryResponse)
async def get_battery(
    battery_id: UUID,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    service = BatteryService(db)
    return await service.get_battery(battery_id, professional_id=professional.id)


@router.get("/{battery_id}/subforms/{subform_slug}/form", response_model=BatterySubformFormResponse)
async def get_battery_subform_form(
    battery_id: UUID,
    subform_slug: str,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    service = BatteryService(db)
    return await service.get_subform_form(
        battery_id, subform_slug, professional_id=professional.id
    )


@router.patch("/{battery_id}/subforms/{subform_slug}", response_model=BatteryResponse)
async def update_battery_subform(
    battery_id: UUID,
    subform_slug: str,
    data: BatterySubformAnswersUpdate,
    finalize: bool = Query(False),
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    service = BatteryService(db)
    return await service.update_subform(
        battery_id,
        subform_slug,
        data,
        professional_id=professional.id,
        finalize=finalize,
    )


@router.post("/{battery_id}/finalize", response_model=BatteryResponse)
async def finalize_battery(
    battery_id: UUID,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    service = BatteryService(db)
    return await service.finalize_battery(battery_id, professional_id=professional.id)


@router.post("/{battery_id}/cancel", response_model=BatteryResponse)
async def cancel_battery(
    battery_id: UUID,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    service = BatteryService(db)
    return await service.cancel_battery(battery_id, professional_id=professional.id)


@router.get("/{battery_id}/report")
async def download_battery_report(
    battery_id: UUID,
    format: str = Query("pdf", pattern="^(pdf)$"),
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    service = BatteryService(db)
    battery = await service.get_battery(battery_id, professional_id=professional.id)
    if battery.status != "completed":
        raise HTTPException(status_code=400, detail="Relatório disponível apenas para baterias finalizadas")
    try:
        package = get_instrument_content_package(battery.instrument_slug)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Pacote não encontrado") from exc
    pdf_bytes = export_battery_pdf(battery, package)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="abfw-{battery_id}.pdf"'},
    )
