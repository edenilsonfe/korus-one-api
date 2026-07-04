from pydantic import Field

from app.schemas.common import CamelModel


class ProtocolFieldTemplate(CamelModel):
    key: str
    label: str


class ProtocolResponse(CamelModel):
    id: str
    name: str
    full_name: str
    description: str
    age_range: str
    fields: list[ProtocolFieldTemplate]
    applications: int = 0
    avg_result: float = 0
    last_applied: str | None = None


class AssessmentFieldInput(CamelModel):
    label: str
    value: str


class AssessmentCreate(CamelModel):
    protocol_id: str
    date: str | None = None
    result: str
    percentage: int
    interpretation: str = ""
    fields: list[AssessmentFieldInput] = Field(default_factory=list)


class GoalCreate(CamelModel):
    title: str
    area: str
    progress: int = 0
    start_date: str | None = None
    status: str | None = None


class GoalUpdate(CamelModel):
    title: str | None = None
    area: str | None = None
    progress: int | None = None
    status: str | None = None
