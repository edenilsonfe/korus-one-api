from pydantic import EmailStr, Field, field_validator

from app.schemas.common import CamelModel


def _normalize_cpf(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


class RegisterRequest(CamelModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str
    specialty: str = ""
    council: str = ""
    phone: str = ""
    cpf: str = Field(min_length=11, max_length=14)

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, value: str) -> str:
        digits = _normalize_cpf(value)
        if len(digits) != 11:
            raise ValueError("CPF deve conter 11 dígitos")
        if digits == digits[0] * 11:
            raise ValueError("CPF inválido")
        return digits


class LoginRequest(CamelModel):
    email: EmailStr
    password: str


class RefreshRequest(CamelModel):
    refresh_token: str


class TokenResponse(CamelModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
