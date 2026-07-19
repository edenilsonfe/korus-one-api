from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants.spm import (
    SPM_BATTERY_STATUS_DRAFT,
    SPM_SUBFORM_STATUS_COMPLETED,
    SPM_SUBFORM_STATUS_IN_PROGRESS,
    SPM_SUBFORM_STATUS_PENDING,
)
from app.models.assessment import Assessment
from app.models.spm import SpmInformantLink, SpmSubformAssessment
from app.schemas.spm import SpmInformantProgress, SpmInformantSession
from app.services.spm_content_package import get_spm_content_package
from app.services.spm_scoring_service import compute_subform_scores
from app.utils.token_hash import hash_token


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _count_answered(answers: dict[str, Any], total: int) -> int:
    return sum(1 for key in answers if answers.get(key) is not None)


class SpmInformantService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.package = get_spm_content_package()

    async def _resolve_link(self, raw_token: str) -> tuple[SpmInformantLink, SpmSubformAssessment]:
        token_hash = hash_token(raw_token)
        result = await self.db.execute(
            select(SpmInformantLink)
            .options(
                selectinload(SpmInformantLink.subform_assessment).selectinload(
                    SpmSubformAssessment.battery
                )
            )
            .where(SpmInformantLink.token_hash == token_hash)
        )
        link = result.scalar_one_or_none()
        if not link:
            raise HTTPException(status_code=404, detail="Link inválido")

        now = _utcnow()
        if link.revoked_at:
            raise HTTPException(status_code=410, detail="Link revogado")
        if link.submitted_at:
            raise HTTPException(status_code=410, detail="Link já utilizado")
        if link.expires_at <= now:
            raise HTTPException(status_code=410, detail="Link expirado")

        subform = link.subform_assessment
        battery = subform.battery
        if battery.status != SPM_BATTERY_STATUS_DRAFT:
            raise HTTPException(status_code=410, detail="Bateria não está mais aberta")

        return link, subform

    def _patient_first_name(self, battery: Assessment) -> str:
        if battery.patient and battery.patient.name:
            return battery.patient.name.split()[0]
        return "Paciente"

    async def get_session(self, raw_token: str) -> SpmInformantSession:
        link, subform = await self._resolve_link(raw_token)
        battery = (
            await self.db.execute(
                select(Assessment)
                .options(selectinload(Assessment.patient))
                .where(Assessment.id == subform.battery_id)
            )
        ).scalar_one()
        config = self.package.get_subform(subform.subform_slug)

        return SpmInformantSession(
            subform_slug=subform.subform_slug,
            subform_title=config["title"],
            patient_first_name=self._patient_first_name(battery),
            scale=self.package.scale,
            domains=self.package.domains,
            items=self.package.public_items_payload(subform.subform_slug),
            items_answered=subform.items_answered,
            items_total=subform.items_total,
            status=subform.status,
            draft_answers=subform.answers or {},
            expires_at=link.expires_at,
        )

    async def save_draft(
        self, raw_token: str, answers: dict[str, Any]
    ) -> SpmInformantProgress:
        _link, subform = await self._resolve_link(raw_token)
        subform.answers = answers
        subform.items_answered = _count_answered(answers, subform.items_total)
        subform.status = (
            SPM_SUBFORM_STATUS_IN_PROGRESS
            if subform.items_answered > 0
            else SPM_SUBFORM_STATUS_PENDING
        )
        await self.db.commit()
        return SpmInformantProgress(
            items_answered=subform.items_answered,
            items_total=subform.items_total,
            status=subform.status,
        )

    async def submit(
        self,
        raw_token: str,
        *,
        answers: dict[str, Any],
        informant_name: str,
        informant_relationship: str,
    ) -> SpmInformantProgress:
        link, subform = await self._resolve_link(raw_token)
        subform.answers = answers
        subform.items_answered = _count_answered(answers, subform.items_total)
        if subform.items_answered < subform.items_total:
            raise HTTPException(
                status_code=400,
                detail="Responda todos os itens antes de enviar",
            )

        subform.informant_name = informant_name
        subform.informant_relationship = informant_relationship
        subform.scores = compute_subform_scores(
            self.package, subform.subform_slug, answers
        )
        subform.status = SPM_SUBFORM_STATUS_COMPLETED
        subform.completed_at = _utcnow()
        link.submitted_at = _utcnow()

        await self.db.commit()

        # Refresh hub label (may clear "Aguardando informante").
        from app.services.spm_battery_service import SpmBatteryService

        await SpmBatteryService(self.db).refresh_draft_result_label(subform.battery_id)

        return SpmInformantProgress(
            items_answered=subform.items_answered,
            items_total=subform.items_total,
            status=subform.status,
        )
