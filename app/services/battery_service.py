from datetime import date, datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants.battery import (
    BATTERY_METADATA_KEY,
    BATTERY_STATUS_CANCELLED,
    BATTERY_STATUS_COMPLETED,
    BATTERY_STATUS_DRAFT,
    BATTERY_SUBFORM_STATUS_COMPLETED,
    BATTERY_SUBFORM_STATUS_IN_PROGRESS,
    BATTERY_SUBFORM_STATUS_PENDING,
)
from app.core.utils import utcnow
from app.models.assessment import Assessment
from app.models.battery import BatterySubformAssessment
from app.models.patient import Patient
from app.schemas.battery import (
    BatteryCreate,
    BatteryResponse,
    BatterySubformAnswersUpdate,
    BatterySubformFormResponse,
    BatterySubformResponse,
    BatterySummary,
)
from app.services.assessment_scoring import build_assessment_from_scores
from app.services.battery_scoring_service import (
    battery_scores_to_fields,
    score_battery_subform,
    synthesize_battery_scores,
)
from app.services.instrument_content_package import InstrumentContentPackage, get_instrument_content_package
from app.services.timeline import create_timeline_event


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _patient_age_months(birth_date: date | None) -> Optional[int]:
    if not birth_date:
        return None
    today = _utcnow().date()
    months = (today.year - birth_date.year) * 12 + (today.month - birth_date.month)
    if today.day < birth_date.day:
        months -= 1
    return max(0, months)


def _count_answered(answers: dict[str, Any], item_ids: list[str]) -> int:
    count = 0
    for item_id in item_ids:
        raw = answers.get(item_id)
        if raw is None:
            continue
        if isinstance(raw, dict):
            response = raw.get("response")
            if response is not None and str(response).strip() != "":
                count += 1
            elif raw.get("classification"):
                count += 1
            elif raw.get("count") is not None:
                count += 1
            elif raw.get("duration_seconds") or raw.get("syllable_count"):
                count += 1
            elif raw.get("value") is not None:
                count += 1
            elif raw.get("selected"):
                count += 1
            elif raw.get("notes") or raw.get("text"):
                count += 1
        else:
            count += 1
    return count


class BatteryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_package(self, instrument_slug: str) -> InstrumentContentPackage:
        try:
            return get_instrument_content_package(instrument_slug)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Pacote do instrumento não encontrado") from exc

    async def _load_battery(
        self,
        battery_id: UUID,
        *,
        professional_id: Optional[UUID] = None,
        instrument_slug: Optional[str] = None,
    ) -> Assessment:
        query = (
            select(Assessment)
            .options(
                selectinload(Assessment.patient),
                selectinload(Assessment.battery_subforms),
            )
            .where(Assessment.id == battery_id)
        )
        if professional_id is not None:
            query = query.where(Assessment.professional_id == professional_id)
        record = (await self.db.execute(query)).scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail="Bateria não encontrada")
        if instrument_slug and record.protocol_id != instrument_slug:
            raise HTTPException(status_code=404, detail="Bateria não encontrada")
        return record

    def _battery_metadata(self, record: Assessment) -> dict[str, Any]:
        meta = record.assessment_metadata or {}
        return meta.get(BATTERY_METADATA_KEY, {})

    def _to_subform_response(
        self, subform: BatterySubformAssessment, package: InstrumentContentPackage
    ) -> BatterySubformResponse:
        mod = package.get_module_config(subform.subform_slug)
        return BatterySubformResponse(
            id=str(subform.id),
            subform_slug=subform.subform_slug,
            title=mod.get("title", subform.subform_slug),
            module_kind=mod.get("module_kind", "generic"),
            domain=mod.get("domain"),
            required=subform.required,
            status=subform.status,
            items_answered=subform.items_answered,
            items_total=subform.items_total,
            scores=subform.scores,
            answers=subform.answers if subform.answers else None,
            completed_at=subform.completed_at,
        )

    def _to_battery_response(self, record: Assessment, package: InstrumentContentPackage) -> BatteryResponse:
        meta = self._battery_metadata(record)
        subforms = sorted(record.battery_subforms, key=lambda s: s.subform_slug)
        return BatteryResponse(
            id=str(record.id),
            patient_id=str(record.patient_id),
            patient_name=record.patient.name if record.patient else None,
            professional_id=str(record.professional_id),
            instrument_slug=record.protocol_id,
            instrument_title=package.instrument_title,
            status=record.status,
            scores=record.scores,
            percentage=record.percentage,
            interpretation=record.interpretation,
            subforms=[self._to_subform_response(sf, package) for sf in subforms],
            started_at=meta.get("started_at"),
            completed_at=meta.get("completed_at"),
            duration_minutes=meta.get("duration_minutes"),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def create_battery(
        self,
        *,
        data: BatteryCreate,
        professional_id: UUID,
    ) -> BatteryResponse:
        package = self._get_package(data.instrument_slug)
        if not package.modules:
            raise HTTPException(status_code=400, detail="Instrumento não possui módulos de bateria")

        patient = (
            await self.db.execute(
                select(Patient).where(
                    Patient.id == data.patient_id,
                    Patient.professional_id == professional_id,
                )
            )
        ).scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=404, detail="Paciente não encontrado")

        today = utcnow().date()
        metadata = {
            "engine": "battery",
            "package_id": package.package_id,
            BATTERY_METADATA_KEY: {
                "started_at": _utcnow().isoformat(),
                "completed_at": None,
                "duration_minutes": None,
            },
        }
        record = Assessment(
            patient_id=data.patient_id,
            professional_id=professional_id,
            protocol_id=data.instrument_slug,
            date=today,
            result="Rascunho",
            percentage=0,
            interpretation="",
            status=BATTERY_STATUS_DRAFT,
            answers={},
            scores=None,
            assessment_metadata=metadata,
        )
        self.db.add(record)
        await self.db.flush()

        for slug in package.modules:
            mod = package.get_module_config(slug)
            items = package.get_module_items(slug)
            subform = BatterySubformAssessment(
                battery_id=record.id,
                instrument_slug=data.instrument_slug,
                subform_slug=slug,
                required=mod.get("required", True),
                status=BATTERY_SUBFORM_STATUS_PENDING,
                items_total=len(items),
            )
            self.db.add(subform)

        await self.db.commit()
        await self.db.refresh(record, ["battery_subforms", "patient"])
        return self._to_battery_response(record, package)

    async def get_battery(self, battery_id: UUID, *, professional_id: UUID) -> BatteryResponse:
        record = await self._load_battery(battery_id, professional_id=professional_id)
        package = self._get_package(record.protocol_id)
        return self._to_battery_response(record, package)

    async def list_batteries(
        self,
        *,
        professional_id: UUID,
        instrument_slug: Optional[str] = None,
        patient_id: Optional[UUID] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[BatterySummary], int]:
        query = select(Assessment).where(Assessment.professional_id == professional_id)
        if instrument_slug:
            query = query.where(Assessment.protocol_id == instrument_slug)
        if patient_id:
            query = query.where(Assessment.patient_id == patient_id)
        if status_filter:
            query = query.where(Assessment.status == status_filter)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        query = (
            query.options(selectinload(Assessment.patient), selectinload(Assessment.battery_subforms))
            .order_by(Assessment.updated_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        records = list((await self.db.execute(query)).scalars().all())

        summaries: list[BatterySummary] = []
        for record in records:
            completed = sum(1 for sf in record.battery_subforms if sf.status == BATTERY_SUBFORM_STATUS_COMPLETED)
            summaries.append(
                BatterySummary(
                    id=str(record.id),
                    patient_id=str(record.patient_id),
                    patient_name=record.patient.name if record.patient else None,
                    instrument_slug=record.protocol_id,
                    status=record.status,
                    subforms_completed=completed,
                    subforms_total=len(record.battery_subforms),
                    percentage=record.percentage,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
            )
        return summaries, total

    async def get_subform_form(
        self,
        battery_id: UUID,
        subform_slug: str,
        *,
        professional_id: UUID,
    ) -> BatterySubformFormResponse:
        record = await self._load_battery(battery_id, professional_id=professional_id)
        package = self._get_package(record.protocol_id)
        payload = package.public_module_form(subform_slug)
        return BatterySubformFormResponse(**payload)

    async def update_subform(
        self,
        battery_id: UUID,
        subform_slug: str,
        data: BatterySubformAnswersUpdate,
        *,
        professional_id: UUID,
        finalize: bool = False,
    ) -> BatteryResponse:
        record = await self._load_battery(battery_id, professional_id=professional_id)
        if record.status != BATTERY_STATUS_DRAFT:
            raise HTTPException(status_code=400, detail="Bateria não está em rascunho")

        package = self._get_package(record.protocol_id)
        subform = next((sf for sf in record.battery_subforms if sf.subform_slug == subform_slug), None)
        if not subform:
            raise HTTPException(status_code=404, detail="Subforma não encontrada")

        merged = {**subform.answers, **data.answers}
        subform.answers = merged
        items = package.get_module_items(subform_slug)
        item_ids = [item["id"] for item in items]
        subform.items_answered = _count_answered(merged, item_ids)

        if subform.status == BATTERY_SUBFORM_STATUS_PENDING:
            subform.status = BATTERY_SUBFORM_STATUS_IN_PROGRESS
            subform.started_at = subform.started_at or _utcnow()

        if finalize:
            age = _patient_age_months(record.patient.birth_date if record.patient else None)
            scores = score_battery_subform(
                package, subform_slug, merged, patient_age_months=age
            )
            subform.scores = scores
            subform.status = BATTERY_SUBFORM_STATUS_COMPLETED
            subform.completed_at = _utcnow()

        await self.db.commit()
        await self.db.refresh(record, ["battery_subforms", "patient"])
        return self._to_battery_response(record, package)

    async def finalize_battery(
        self,
        battery_id: UUID,
        *,
        professional_id: UUID,
        clinical_conclusion: str = "",
    ) -> BatteryResponse:
        record = await self._load_battery(battery_id, professional_id=professional_id)
        if record.status != BATTERY_STATUS_DRAFT:
            raise HTTPException(status_code=400, detail="Bateria já finalizada ou cancelada")

        package = self._get_package(record.protocol_id)
        pending_required = [
            sf.subform_slug
            for sf in record.battery_subforms
            if sf.required and sf.status != BATTERY_SUBFORM_STATUS_COMPLETED
        ]
        if pending_required:
            raise HTTPException(
                status_code=400,
                detail=f"Módulos pendentes: {', '.join(pending_required)}",
            )

        subform_scores = [sf.scores for sf in record.battery_subforms if sf.scores]
        synthesized = synthesize_battery_scores(package, subform_scores)
        derived = build_assessment_from_scores(synthesized)

        meta = record.assessment_metadata or {}
        battery_meta = meta.get(BATTERY_METADATA_KEY, {})
        started_at = battery_meta.get("started_at")
        duration_minutes = None
        if started_at:
            try:
                start_dt = datetime.fromisoformat(started_at)
                duration_minutes = round((_utcnow() - start_dt).total_seconds() / 60, 1)
            except ValueError:
                pass
        battery_meta["completed_at"] = _utcnow().isoformat()
        battery_meta["duration_minutes"] = duration_minutes
        if clinical_conclusion:
            battery_meta["clinical_conclusion"] = clinical_conclusion
        meta[BATTERY_METADATA_KEY] = battery_meta

        if clinical_conclusion:
            synthesized["clinical_conclusion"] = clinical_conclusion

        record.status = BATTERY_STATUS_COMPLETED
        record.scores = synthesized
        record.answers = {sf.subform_slug: sf.answers for sf in record.battery_subforms}
        record.result = derived["result"]
        record.percentage = derived["percentage"]
        record.interpretation = derived["interpretation"]
        record.fields = battery_scores_to_fields(synthesized)
        record.assessment_metadata = meta

        await create_timeline_event(
            self.db,
            patient_id=record.patient_id,
            professional_id=professional_id,
            event_type="avaliacao",
            title=f"{package.instrument_title}",
            description=derived["interpretation"] or derived["result"],
            source_id=record.id,
        )

        await self.db.commit()
        await self.db.refresh(record, ["battery_subforms", "patient"])
        return self._to_battery_response(record, package)

    async def cancel_battery(self, battery_id: UUID, *, professional_id: UUID) -> BatteryResponse:
        record = await self._load_battery(battery_id, professional_id=professional_id)
        if record.status != BATTERY_STATUS_DRAFT:
            raise HTTPException(status_code=400, detail="Somente rascunhos podem ser cancelados")
        record.status = BATTERY_STATUS_CANCELLED
        package = self._get_package(record.protocol_id)
        await self.db.commit()
        await self.db.refresh(record, ["battery_subforms", "patient"])
        return self._to_battery_response(record, package)
