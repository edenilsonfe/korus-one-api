from pydantic import Field

from app.schemas.common import CamelModel


class EvolutionCreate(CamelModel):
    title: str
    content: str
    session_id: str | None = None


class EvolutionResponse(CamelModel):
    id: str
    patient_id: str
    session_id: str | None = None
    date: str
    title: str
    content: str
    professional: str


class AnamneseCreate(CamelModel):
    section: str
    value: str


class AnamneseResponse(CamelModel):
    id: str
    patient_id: str
    section: str
    value: str
