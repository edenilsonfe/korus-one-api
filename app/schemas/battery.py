from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import CamelModel


class BatterySetupMetadata(CamelModel):
    assessment_date: Optional[str] = None
    examiner_name: Optional[str] = None
    initial_notes: Optional[str] = None


class BatteryCreate(CamelModel):
    instrument_slug: str = Field(..., min_length=1, max_length=64)
    patient_id: UUID
    setup: Optional[BatterySetupMetadata] = None


class BatterySubformAnswersUpdate(CamelModel):
    answers: dict[str, Any] = Field(default_factory=dict)


class BatteryFinalizeRequest(CamelModel):
    clinical_conclusion: str = ""


class BatteryEvidenceCreate(CamelModel):
    kind: Literal["note"] = "note"
    note_text: str = Field(..., min_length=1)
    subform_slug: Optional[str] = None
    item_id: Optional[str] = None
    recorded_at: Optional[datetime] = None


class BatteryEventCreate(CamelModel):
    text: str = Field(..., min_length=1)
    occurred_at: Optional[datetime] = None
    subform_slug: Optional[str] = None
    item_id: Optional[str] = None
    evidence_id: Optional[UUID] = None


class BatteryEventUpdate(CamelModel):
    text: Optional[str] = None
    occurred_at: Optional[datetime] = None
    subform_slug: Optional[str] = None
    item_id: Optional[str] = None


class BatterySubformItem(CamelModel):
    id: str
    text: str
    target: Optional[str] = None
    category: Optional[str] = None
    category_title: Optional[str] = None
    stimulus_type: Optional[str] = None
    input_type: Optional[str] = None
    options: list[dict[str, Any]] = Field(default_factory=list)
    age_start_months: Optional[int] = None
    age_end_months: Optional[int] = None
    material: Optional[str] = None
    examiner_instructions: Optional[str] = None
    section: Optional[str] = None
    response_type: Optional[str] = None


class BatterySubformFormResponse(CamelModel):
    subform_slug: str
    title: str
    module_kind: str
    domain: Optional[str] = None
    categories: list[dict[str, Any]] = Field(default_factory=list)
    classifications: list[dict[str, Any]] = Field(default_factory=list)
    phonological_processes: list[dict[str, Any]] = Field(default_factory=list)
    target_syllables: Optional[int] = None
    scale: list[dict[str, Any]] = Field(default_factory=list)
    input_type: str = "scale"
    items: list[BatterySubformItem]
    filler: str = "clinician"
    administration_rules: Optional[dict[str, Any]] = None


class BatterySubformResponse(CamelModel):
    id: str
    subform_slug: str
    title: str
    module_kind: str
    domain: Optional[str] = None
    required: bool
    status: str
    items_answered: int
    items_total: int
    scores: Optional[dict[str, Any]] = None
    answers: Optional[dict[str, Any]] = None
    completed_at: Optional[datetime] = None


class BatteryResponse(CamelModel):
    id: str
    patient_id: str
    patient_name: Optional[str] = None
    professional_id: str
    instrument_slug: str
    instrument_title: str
    status: str
    scores: Optional[dict[str, Any]] = None
    percentage: int = 0
    interpretation: str = ""
    subforms: list[BatterySubformResponse]
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_minutes: Optional[float] = None
    setup: Optional[BatterySetupMetadata] = None
    created_at: datetime
    updated_at: datetime


class BatterySummary(CamelModel):
    id: str
    patient_id: str
    patient_name: Optional[str] = None
    instrument_slug: str
    status: str
    subforms_completed: int
    subforms_total: int
    percentage: int
    created_at: datetime
    updated_at: datetime
