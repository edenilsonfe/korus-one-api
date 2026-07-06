from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import CamelModel


class BatteryCreate(CamelModel):
    instrument_slug: str = Field(..., min_length=1, max_length=64)
    patient_id: UUID


class BatterySubformAnswersUpdate(CamelModel):
    answers: dict[str, Any] = Field(default_factory=dict)


class BatterySubformItem(CamelModel):
    id: str
    text: str
    target: Optional[str] = None
    category: Optional[str] = None
    category_title: Optional[str] = None
    stimulus_type: Optional[str] = None


class BatterySubformFormResponse(CamelModel):
    subform_slug: str
    title: str
    module_kind: str
    domain: Optional[str] = None
    categories: list[dict[str, Any]] = Field(default_factory=list)
    classifications: list[dict[str, Any]] = Field(default_factory=list)
    phonological_processes: list[dict[str, Any]] = Field(default_factory=list)
    target_syllables: Optional[int] = None
    items: list[BatterySubformItem]
    filler: str = "clinician"


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
