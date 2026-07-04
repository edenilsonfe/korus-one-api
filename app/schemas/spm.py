from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import CamelModel


class SpmCatalogSubform(CamelModel):
    slug: str
    title: str
    filler: Literal["external", "clinical"]
    min_age_months: int
    max_age_months: int
    item_count: int
    import_pending: bool = False


class SpmSubformItem(CamelModel):
    id: int
    domain: str
    text: str


class SpmSubformFormResponse(CamelModel):
    subform_slug: str
    title: str
    scale: list[dict[str, Any]]
    domains: list[dict[str, str]]
    items: list[SpmSubformItem]
    filler: str


class SpmSubformScoreRequest(CamelModel):
    answers: dict[str, Any] = Field(default_factory=dict)


class SpmBatteryScoreRequest(CamelModel):
    subforms: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Lista de { slug, answers }",
    )


class SpmScopeEntry(CamelModel):
    required: bool = True


class SpmBatteryCreate(CamelModel):
    patient_id: UUID
    scope: dict[str, SpmScopeEntry]


class SpmBatteryScopeUpdate(CamelModel):
    scope: dict[str, SpmScopeEntry]


class SpmClinicalReportUpdate(CamelModel):
    clinical_report: str


class SpmSubformAnswersUpdate(CamelModel):
    answers: dict[str, Any]
    informant_name: Optional[str] = None
    informant_relationship: Optional[str] = None


class SpmInformantLinkCreate(CamelModel):
    inherit_draft: bool = True


class SpmInformantDraftUpdate(CamelModel):
    answers: dict[str, Any]


class SpmInformantSubmit(CamelModel):
    answers: dict[str, Any]
    informant_name: str = Field(..., min_length=1, max_length=255)
    informant_relationship: str = Field(..., min_length=1, max_length=128)


class SpmActiveLinkInfo(CamelModel):
    id: str
    expires_at: datetime
    url: str
    inherit_draft: bool


class SpmSubformResponse(CamelModel):
    id: str
    subform_slug: str
    title: str
    filler: Literal["external", "clinical"]
    required: bool
    status: str
    informant_name: Optional[str] = None
    informant_relationship: Optional[str] = None
    items_answered: int
    items_total: int
    scores: Optional[dict[str, Any]] = None
    answers: Optional[dict[str, Any]] = None
    completed_at: Optional[datetime] = None
    active_link: Optional[SpmActiveLinkInfo] = None


class SpmBatteryResponse(CamelModel):
    id: str
    patient_id: str
    patient_name: Optional[str] = None
    professional_id: str
    professional_name: Optional[str] = None
    instrument_slug: str
    instrument_title: str
    status: str
    scope: dict[str, SpmScopeEntry]
    clinical_report: Optional[str] = None
    scores: Optional[dict[str, Any]] = None
    subforms: list[SpmSubformResponse]
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SpmInformantLinkCreated(CamelModel):
    link_id: str
    url: str
    expires_at: datetime
    inherit_draft: bool


class SpmInformantLinkWhatsAppSend(CamelModel):
    phone: Optional[str] = None
    inherit_draft: bool = True
    informant_name: Optional[str] = None


class SpmInformantLinkWhatsAppSent(CamelModel):
    link_id: str
    url: str
    expires_at: datetime
    inherit_draft: bool
    phone: str
    whatsapp_sent: bool = True


class SpmBatterySummary(CamelModel):
    id: str
    patient_id: str
    patient_name: Optional[str] = None
    status: str
    scope: dict[str, SpmScopeEntry]
    subforms_completed: int
    subforms_total: int
    created_at: datetime
    updated_at: datetime


class SpmSuggestScopeResponse(CamelModel):
    suggested: dict[str, SpmScopeEntry]
    age_months: Optional[int] = None


class SpmInformantSession(CamelModel):
    subform_slug: str
    subform_title: str
    patient_first_name: str
    scale: list[dict[str, Any]]
    domains: list[dict[str, str]]
    items: list[SpmSubformItem]
    items_answered: int
    items_total: int
    status: str
    draft_answers: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime


class SpmInformantProgress(CamelModel):
    items_answered: int
    items_total: int
    status: str
