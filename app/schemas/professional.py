from pydantic import EmailStr, Field

from app.schemas.common import CamelModel


class ProfessionalResponse(CamelModel):
    id: str
    name: str
    specialty: str
    council: str
    email: EmailStr
    phone: str
    avatar_color: str


class ProfessionalUpdate(CamelModel):
    name: str | None = None
    specialty: str | None = None
    council: str | None = None
    phone: str | None = None
    avatar_color: str | None = None
