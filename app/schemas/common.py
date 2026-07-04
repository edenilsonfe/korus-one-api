from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        ser_json_by_alias=True,
    )


T = TypeVar("T")


class PaginatedResponse(CamelModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    limit: int


class MessageResponse(CamelModel):
    message: str


class ProfessionalRef(CamelModel):
    id: str
    name: str


class PatientRef(CamelModel):
    id: str
    name: str
    avatar_color: str = Field(alias="avatarColor")


class ErrorDetail(CamelModel):
    detail: str
