import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants.spm import (
    SPM_BATTERY_STATUS_CANCELLED,
    SPM_BATTERY_STATUS_COMPLETED,
    SPM_BATTERY_STATUS_DRAFT,
    SPM_FILLER_EXTERNAL,
    SPM_INSTRUMENT_SLUG,
    SPM_INSTRUMENT_TITLE,
    SPM_INFORMANT_WHATSAPP_MESSAGE,
    SPM_METADATA_KEY,
    SPM_SUBFORM_STATUS_COMPLETED,
    SPM_SUBFORM_STATUS_IN_PROGRESS,
    SPM_SUBFORM_STATUS_PENDING,
)
from app.core.config import get_settings
from app.core.utils import utcnow
from app.models.assessment import Assessment
from app.models.caregiver import Caregiver
from app.models.notification_message_log import MESSAGE_STATUS_SENT, NotificationMessageLog
from app.models.patient import Patient
from app.models.professional import Professional
from app.models.spm import SpmInformantLink, SpmSubformAssessment
from app.schemas.spm import (
    SpmActiveLinkInfo,
    SpmBatteryCreate,
    SpmBatteryResponse,
    SpmBatteryScopeUpdate,
    SpmBatterySummary,
    SpmClinicalReportUpdate,
    SpmInformantLinkCreate,
    SpmInformantLinkCreated,
    SpmInformantLinkWhatsAppSend,
    SpmInformantLinkWhatsAppSent,
    SpmScopeEntry,
    SpmSubformAnswersUpdate,
    SpmSubformResponse,
)
from app.services.spm_content_package import SpmContentPackage, get_spm_content_package
from app.services.spm_scoring_service import (
    build_clinical_report_draft,
    compute_subform_scores,
    spm_scores_to_fields,
    synthesize_battery_scores,
)
from app.services.timeline import create_timeline_event
from app.services.whatsapp_provider import get_active_whatsapp_provider
from app.utils.token_hash import hash_token


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


def _validate_scope(scope: dict[str, SpmScopeEntry], package: SpmContentPackage) -> None:
    if not scope:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selecione ao menos uma sub-forma",
        )
    known = {entry["slug"] for entry in package.list_subforms()}
    unknown = set(scope.keys()) - known
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Sub-formas desconhecidas: {', '.join(sorted(unknown))}",
        )


def _build_informant_url(raw_token: str) -> str:
    settings = get_settings()
    base = settings.frontend_url.rstrip("/")
    return f"{base}/spm/informante/{raw_token}"


def _count_answered(answers: dict[str, Any], total: int) -> int:
    return sum(1 for key in answers if answers.get(key) is not None)


def _first_name(full_name: str | None) -> str:
    if not full_name or not full_name.strip():
        return "Informante"
    return full_name.strip().split()[0]


def _format_expires_at(expires_at: datetime) -> str:
    return expires_at.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M")


def build_informant_whatsapp_message(
    *,
    informant_name: str | None,
    patient_name: str | None,
    subform_title: str,
    link_url: str,
    professional_name: str,
    expires_at: datetime,
) -> str:
    replacements = {
        "{{informantName}}": _first_name(informant_name),
        "{{patientFirstName}}": _first_name(patient_name),
        "{{subformTitle}}": subform_title,
        "{{linkUrl}}": link_url,
        "{{professionalName}}": professional_name or "equipe clínica",
        "{{expiresAt}}": _format_expires_at(expires_at),
    }
    message = SPM_INFORMANT_WHATSAPP_MESSAGE
    for key, value in replacements.items():
        message = message.replace(key, value)
    return message


class SpmBatteryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.package = get_spm_content_package()

    async def _load_battery(
        self,
        battery_id: UUID,
        *,
        professional_id: Optional[UUID] = None,
    ) -> Assessment:
        query = (
            select(Assessment)
            .options(
                selectinload(Assessment.patient),
                selectinload(Assessment.spm_subforms).selectinload(SpmSubformAssessment.informant_links),
            )
            .where(
                Assessment.id == battery_id,
                Assessment.protocol_id == SPM_INSTRUMENT_SLUG,
            )
        )
        if professional_id is not None:
            query = query.where(Assessment.professional_id == professional_id)
        record = (await self.db.execute(query)).scalar_one_or_none()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bateria SPM não encontrada",
            )
        return record

    async def _load_subforms(self, battery_id: UUID) -> list[SpmSubformAssessment]:
        result = await self.db.execute(
            select(SpmSubformAssessment)
            .options(selectinload(SpmSubformAssessment.informant_links))
            .where(SpmSubformAssessment.battery_id == battery_id)
            .order_by(SpmSubformAssessment.subform_slug)
        )
        return list(result.scalars().all())

    def _active_link(self, subform: SpmSubformAssessment) -> Optional[SpmInformantLink]:
        now = _utcnow()
        for link in subform.informant_links:
            if link.revoked_at or link.submitted_at:
                continue
            if link.expires_at <= now:
                continue
            return link
        return None

    def _to_subform_response(self, subform: SpmSubformAssessment) -> SpmSubformResponse:
        config = self.package.get_subform(subform.subform_slug)
        active = self._active_link(subform)
        active_info = None
        if active:
            active_info = SpmActiveLinkInfo(
                id=str(active.id),
                expires_at=active.expires_at,
                url="(link ativo — gere novo link para copiar)",
                inherit_draft=active.inherit_draft,
            )
        return SpmSubformResponse(
            id=str(subform.id),
            subform_slug=subform.subform_slug,
            title=config["title"],
            filler=config["filler"],
            required=subform.required,
            status=subform.status,
            informant_name=subform.informant_name,
            informant_relationship=subform.informant_relationship,
            items_answered=subform.items_answered,
            items_total=subform.items_total,
            scores=subform.scores,
            answers=subform.answers if subform.answers else None,
            completed_at=subform.completed_at,
            active_link=active_info,
        )

    def _battery_metadata(self, record: Assessment) -> dict[str, Any]:
        meta = record.assessment_metadata or {}
        return meta.get(SPM_METADATA_KEY, {})

    def _to_battery_response(
        self,
        record: Assessment,
        subforms: list[SpmSubformAssessment],
    ) -> SpmBatteryResponse:
        meta = self._battery_metadata(record)
        scope_raw = meta.get("scope", {})
        scope = {
            slug: SpmScopeEntry(required=bool(entry.get("required", True)))
            for slug, entry in scope_raw.items()
        }
        return SpmBatteryResponse(
            id=str(record.id),
            patient_id=str(record.patient_id),
            patient_name=record.patient.name if record.patient else None,
            professional_id=str(record.professional_id),
            professional_name=None,
            instrument_slug=SPM_INSTRUMENT_SLUG,
            instrument_title=SPM_INSTRUMENT_TITLE,
            status=record.status,
            scope=scope,
            clinical_report=meta.get("clinical_report"),
            scores=record.scores,
            subforms=[self._to_subform_response(sf) for sf in subforms],
            completed_at=None,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def create_battery(
        self,
        *,
        data: SpmBatteryCreate,
        professional_id: UUID,
    ) -> SpmBatteryResponse:
        _validate_scope(data.scope, self.package)

        patient = (
            await self.db.execute(
                select(Patient).where(
                    Patient.id == data.patient_id,
                    Patient.professional_id == professional_id,
                )
            )
        ).scalar_one_or_none()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paciente não encontrado",
            )

        today = utcnow().date()
        metadata = {
            "engine": "battery",
            "package_id": "spm-br",
            SPM_METADATA_KEY: {
                "scope": {slug: entry.model_dump() for slug, entry in data.scope.items()},
                "clinical_report": None,
            },
        }
        record = Assessment(
            patient_id=data.patient_id,
            professional_id=professional_id,
            protocol_id=SPM_INSTRUMENT_SLUG,
            date=today,
            result="Rascunho SPM",
            percentage=0,
            interpretation="",
            status=SPM_BATTERY_STATUS_DRAFT,
            answers={},
            scores=None,
            assessment_metadata=metadata,
        )
        self.db.add(record)
        await self.db.flush()

        for slug, entry in data.scope.items():
            items = self.package.get_items(slug)
            subform = SpmSubformAssessment(
                battery_id=record.id,
                subform_slug=slug,
                required=entry.required,
                status=SPM_SUBFORM_STATUS_PENDING,
                items_total=len(items),
            )
            self.db.add(subform)

        await self.db.commit()
        await self.db.refresh(record)
        subforms = await self._load_subforms(record.id)
        return self._to_battery_response(record, subforms)

    async def get_battery(
        self,
        battery_id: UUID,
        *,
        professional_id: UUID,
    ) -> SpmBatteryResponse:
        record = await self._load_battery(battery_id, professional_id=professional_id)
        subforms = await self._load_subforms(battery_id)
        return self._to_battery_response(record, subforms)

    async def update_scope(
        self,
        battery_id: UUID,
        data: SpmBatteryScopeUpdate,
        *,
        professional_id: UUID,
    ) -> SpmBatteryResponse:
        record = await self._load_battery(battery_id, professional_id=professional_id)
        if record.status != SPM_BATTERY_STATUS_DRAFT:
            raise HTTPException(status_code=400, detail="Escopo bloqueado após finalização")

        _validate_scope(data.scope, self.package)
        subforms = await self._load_subforms(battery_id)
        existing = {sf.subform_slug: sf for sf in subforms}

        meta = dict(record.assessment_metadata or {})
        spm_meta = dict(meta.get(SPM_METADATA_KEY, {}))
        spm_meta["scope"] = {slug: entry.model_dump() for slug, entry in data.scope.items()}
        meta[SPM_METADATA_KEY] = spm_meta
        record.assessment_metadata = meta

        for slug, entry in data.scope.items():
            if slug in existing:
                existing[slug].required = entry.required
                continue
            items = self.package.get_items(slug)
            self.db.add(
                SpmSubformAssessment(
                    battery_id=battery_id,
                    subform_slug=slug,
                    required=entry.required,
                    status=SPM_SUBFORM_STATUS_PENDING,
                    items_total=len(items),
                )
            )

        for slug, subform in existing.items():
            if slug not in data.scope:
                if subform.status == SPM_SUBFORM_STATUS_COMPLETED:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Não é possível remover sub-forma concluída: {slug}",
                    )
                await self.db.delete(subform)

        await self.db.commit()
        record = await self._load_battery(battery_id, professional_id=professional_id)
        subforms = await self._load_subforms(battery_id)
        return self._to_battery_response(record, subforms)

    async def update_clinical_report(
        self,
        battery_id: UUID,
        data: SpmClinicalReportUpdate,
        *,
        professional_id: UUID,
    ) -> SpmBatteryResponse:
        record = await self._load_battery(battery_id, professional_id=professional_id)
        if record.status == SPM_BATTERY_STATUS_CANCELLED:
            raise HTTPException(status_code=400, detail="Bateria cancelada")

        meta = dict(record.assessment_metadata or {})
        spm_meta = dict(meta.get(SPM_METADATA_KEY, {}))
        spm_meta["clinical_report"] = data.clinical_report
        meta[SPM_METADATA_KEY] = spm_meta
        record.assessment_metadata = meta
        await self.db.commit()
        subforms = await self._load_subforms(battery_id)
        return self._to_battery_response(record, subforms)

    async def update_clinical_subform(
        self,
        battery_id: UUID,
        subform_slug: str,
        data: SpmSubformAnswersUpdate,
        *,
        professional_id: UUID,
        finalize: bool = False,
    ) -> SpmBatteryResponse:
        record = await self._load_battery(battery_id, professional_id=professional_id)
        if record.status != SPM_BATTERY_STATUS_DRAFT:
            raise HTTPException(status_code=400, detail="Bateria não editável")

        subforms = await self._load_subforms(battery_id)
        subform = next((sf for sf in subforms if sf.subform_slug == subform_slug), None)
        if not subform:
            raise HTTPException(status_code=404, detail="Sub-forma não encontrada")

        config = self.package.get_subform(subform_slug)
        if config["filler"] != "clinical":
            raise HTTPException(status_code=400, detail="Sub-forma preenchida via link externo")

        subform.answers = data.answers
        subform.items_answered = _count_answered(data.answers, subform.items_total)
        if data.informant_name:
            subform.informant_name = data.informant_name
        if data.informant_relationship:
            subform.informant_relationship = data.informant_relationship

        if finalize:
            if subform.items_answered < subform.items_total:
                raise HTTPException(
                    status_code=400,
                    detail="Responda todos os itens antes de concluir a sub-forma",
                )
            subform.scores = compute_subform_scores(
                self.package, subform_slug, subform.answers
            )
            subform.status = SPM_SUBFORM_STATUS_COMPLETED
            subform.completed_at = _utcnow()
        elif subform.items_answered > 0:
            subform.status = SPM_SUBFORM_STATUS_IN_PROGRESS

        await self.db.commit()
        record = await self._load_battery(battery_id, professional_id=professional_id)
        subforms = await self._load_subforms(battery_id)
        return self._to_battery_response(record, subforms)

    async def create_informant_link(
        self,
        battery_id: UUID,
        subform_slug: str,
        data: SpmInformantLinkCreate,
        *,
        professional_id: UUID,
    ) -> SpmInformantLinkCreated:
        record = await self._load_battery(battery_id, professional_id=professional_id)
        if record.status != SPM_BATTERY_STATUS_DRAFT:
            raise HTTPException(status_code=400, detail="Bateria não editável")

        subforms = await self._load_subforms(battery_id)
        subform = next((sf for sf in subforms if sf.subform_slug == subform_slug), None)
        if not subform:
            raise HTTPException(status_code=404, detail="Sub-forma não encontrada")

        config = self.package.get_subform(subform_slug)
        if config["filler"] != SPM_FILLER_EXTERNAL:
            raise HTTPException(status_code=400, detail="Sub-forma clínica — preencha no sistema")

        now = _utcnow()
        for link in subform.informant_links:
            if not link.revoked_at and not link.submitted_at:
                link.revoked_at = now

        if not data.inherit_draft:
            subform.answers = {}
            subform.items_answered = 0
            subform.status = SPM_SUBFORM_STATUS_PENDING

        raw_token = secrets.token_urlsafe(32)
        settings = get_settings()
        expires_at = now + timedelta(days=settings.spm_informant_link_expire_days)
        link = SpmInformantLink(
            subform_assessment_id=subform.id,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
            inherit_draft=data.inherit_draft,
        )
        self.db.add(link)
        await self.db.commit()

        return SpmInformantLinkCreated(
            link_id=str(link.id),
            url=_build_informant_url(raw_token),
            expires_at=expires_at,
            inherit_draft=data.inherit_draft,
        )

    async def revoke_active_link(
        self,
        battery_id: UUID,
        subform_slug: str,
        *,
        professional_id: UUID,
    ) -> SpmBatteryResponse:
        record = await self._load_battery(battery_id, professional_id=professional_id)

        subforms = await self._load_subforms(battery_id)
        subform = next((sf for sf in subforms if sf.subform_slug == subform_slug), None)
        if not subform:
            raise HTTPException(status_code=404, detail="Sub-forma não encontrada")

        now = _utcnow()
        for link in subform.informant_links:
            if not link.revoked_at and not link.submitted_at:
                link.revoked_at = now

        await self.db.commit()
        record = await self._load_battery(battery_id, professional_id=professional_id)
        subforms = await self._load_subforms(battery_id)
        return self._to_battery_response(record, subforms)

    async def finalize_battery(
        self,
        battery_id: UUID,
        *,
        professional_id: UUID,
    ) -> SpmBatteryResponse:
        record = await self._load_battery(battery_id, professional_id=professional_id)
        if record.status != SPM_BATTERY_STATUS_DRAFT:
            raise HTTPException(status_code=400, detail="Bateria já finalizada ou cancelada")

        subforms = await self._load_subforms(battery_id)
        meta = self._battery_metadata(record)
        scope = meta.get("scope", {})

        for subform in subforms:
            entry = scope.get(subform.subform_slug, {})
            if entry.get("required", subform.required) and subform.status != SPM_SUBFORM_STATUS_COMPLETED:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sub-forma obrigatória pendente: {subform.subform_slug}",
                )

        subform_score_list = [
            sf.scores
            for sf in subforms
            if sf.scores and sf.status == SPM_SUBFORM_STATUS_COMPLETED
        ]
        battery_scores = synthesize_battery_scores(subform_score_list)
        record.scores = battery_scores
        record.result = battery_scores.get("summary", "SPM concluído")
        record.fields = spm_scores_to_fields(subform_score_list)
        record.answers = {
            sf.subform_slug: sf.answers for sf in subforms if sf.answers
        }
        if subform_score_list:
            avg_t = sum(
                entry.get("overall", {}).get("t_score", 50) for entry in subform_score_list
            ) / len(subform_score_list)
            record.percentage = min(100, max(0, int(round(avg_t))))

        spm_meta = dict(meta)
        if not spm_meta.get("clinical_report"):
            patient_name = record.patient.name if record.patient else "Paciente"
            spm_meta["clinical_report"] = build_clinical_report_draft(
                patient_name, subform_score_list
            )

        full_meta = dict(record.assessment_metadata or {})
        full_meta["engine"] = "battery"
        full_meta["package_id"] = full_meta.get("package_id") or "spm-br"
        full_meta[SPM_METADATA_KEY] = spm_meta
        record.assessment_metadata = full_meta
        record.status = SPM_BATTERY_STATUS_COMPLETED
        record.date = utcnow().date()
        record.interpretation = spm_meta.get("clinical_report") or ""

        now = _utcnow()
        for subform in subforms:
            for link in subform.informant_links:
                if not link.revoked_at and not link.submitted_at:
                    link.revoked_at = now

        await create_timeline_event(
            self.db,
            patient_id=record.patient_id,
            professional_id=professional_id,
            event_type="avaliacao",
            title="Avaliação SPM aplicada",
            description=record.result,
            source_id=record.id,
        )
        await self.db.commit()
        record = await self._load_battery(battery_id, professional_id=professional_id)
        subforms = await self._load_subforms(battery_id)
        return self._to_battery_response(record, subforms)

    async def cancel_battery(
        self,
        battery_id: UUID,
        *,
        professional_id: UUID,
    ) -> SpmBatteryResponse:
        record = await self._load_battery(battery_id, professional_id=professional_id)
        if record.status != SPM_BATTERY_STATUS_DRAFT:
            raise HTTPException(status_code=400, detail="Somente rascunhos podem ser cancelados")

        record.status = SPM_BATTERY_STATUS_CANCELLED
        now = _utcnow()
        subforms = await self._load_subforms(battery_id)
        for subform in subforms:
            for link in subform.informant_links:
                if not link.revoked_at and not link.submitted_at:
                    link.revoked_at = now

        await self.db.commit()
        record = await self._load_battery(battery_id, professional_id=professional_id)
        subforms = await self._load_subforms(battery_id)
        return self._to_battery_response(record, subforms)

    def suggest_scope(self, age_months: Optional[int]) -> dict[str, SpmScopeEntry]:
        raw = self.package.suggest_scope_for_age(age_months)
        return {
            slug: SpmScopeEntry(required=bool(entry.get("required", True)))
            for slug, entry in raw.items()
        }

    async def suggest_scope_for_patient(
        self, patient_id: UUID, professional_id: UUID
    ) -> tuple[dict[str, SpmScopeEntry], Optional[int]]:
        patient = (
            await self.db.execute(
                select(Patient).where(
                    Patient.id == patient_id,
                    Patient.professional_id == professional_id,
                )
            )
        ).scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=404, detail="Paciente não encontrado")
        age = _patient_age_months(patient.birth_date)
        return self.suggest_scope(age), age

    async def _resolve_recipient_phone(
        self,
        patient_id: UUID,
        *,
        phone: str | None,
    ) -> str:
        if phone and phone.strip():
            return phone.strip()
        result = await self.db.execute(
            select(Caregiver)
            .where(Caregiver.patient_id == patient_id)
            .order_by(Caregiver.is_primary.desc(), Caregiver.created_at.asc())
        )
        caregivers = list(result.scalars().all())
        primary = next((c for c in caregivers if c.is_primary), caregivers[0] if caregivers else None)
        if not primary or not primary.phone:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Informe um telefone ou cadastre o responsável com WhatsApp",
            )
        return primary.phone

    async def list_batteries(
        self,
        *,
        professional_id: UUID,
        patient_id: UUID | None = None,
        status_filter: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[SpmBatterySummary], int]:
        query = (
            select(Assessment, Patient)
            .join(Patient, Assessment.patient_id == Patient.id)
            .where(
                Assessment.protocol_id == SPM_INSTRUMENT_SLUG,
                Patient.professional_id == professional_id,
            )
        )
        if patient_id:
            query = query.where(Assessment.patient_id == patient_id)
        if status_filter:
            query = query.where(Assessment.status == status_filter)

        total = await self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        result = await self.db.execute(
            query.order_by(Assessment.updated_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )

        summaries: list[SpmBatterySummary] = []
        for record, patient in result.all():
            subforms = await self._load_subforms(record.id)
            meta = self._battery_metadata(record)
            scope_raw = meta.get("scope", {})
            scope = {
                slug: SpmScopeEntry(required=bool(entry.get("required", True)))
                for slug, entry in scope_raw.items()
            }
            completed = sum(1 for sf in subforms if sf.status == SPM_SUBFORM_STATUS_COMPLETED)
            summaries.append(
                SpmBatterySummary(
                    id=str(record.id),
                    patient_id=str(record.patient_id),
                    patient_name=patient.name,
                    status=record.status,
                    scope=scope,
                    subforms_completed=completed,
                    subforms_total=len(subforms),
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
            )
        return summaries, total

    async def send_informant_link_whatsapp(
        self,
        battery_id: UUID,
        subform_slug: str,
        data: SpmInformantLinkWhatsAppSend,
        *,
        professional_id: UUID,
    ) -> SpmInformantLinkWhatsAppSent:
        link = await self.create_informant_link(
            battery_id,
            subform_slug,
            SpmInformantLinkCreate(inherit_draft=data.inherit_draft),
            professional_id=professional_id,
        )
        record = await self._load_battery(battery_id, professional_id=professional_id)
        professional = await self.db.get(Professional, professional_id)
        phone = await self._resolve_recipient_phone(record.patient_id, phone=data.phone)
        config = self.package.get_subform(subform_slug)

        message = build_informant_whatsapp_message(
            informant_name=data.informant_name,
            patient_name=record.patient.name if record.patient else None,
            subform_title=config["title"],
            link_url=link.url,
            professional_name=professional.name if professional else "",
            expires_at=link.expires_at,
        )

        provider = get_active_whatsapp_provider(self.db)
        if not await provider.can_send(professional_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="WhatsApp não está conectado ou habilitado",
            )

        send_result = await provider.send_text_message(professional_id, phone, message)
        now = _utcnow()
        log = NotificationMessageLog(
            professional_id=professional_id,
            patient_id=record.patient_id,
            channel="whatsapp",
            notification_type="spm_informant_link",
            provider=send_result.provider,
            provider_message_id=send_result.provider_message_id,
            to_phone=phone,
            status=MESSAGE_STATUS_SENT,
            payload={"battery_id": str(battery_id), "subform_slug": subform_slug, "url": link.url},
            sent_at=now,
        )
        self.db.add(log)
        await self.db.commit()

        return SpmInformantLinkWhatsAppSent(
            link_id=link.link_id,
            url=link.url,
            expires_at=link.expires_at,
            inherit_draft=link.inherit_draft,
            phone=phone,
            whatsapp_sent=True,
        )
