from typing import Any, Literal

from pydantic import Field

from app.schemas.common import CamelModel

FidelityBadge = Literal[
    "official-structure",
    "partial-norms",
    "draft-knowledge",
    "DEV-SAMPLE",
    "structure-only",

]


class AdminProtocolItem(CamelModel):
    id: str
    name: str
    full_name: str
    age_range: str
    is_active: bool
    sort_order: int
    fidelity_badge: str | None = None
    scoring_mode: str = "manual"


class AdminProtocolUpdate(CamelModel):
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=10_000)
    fidelity_badge: FidelityBadge | None = None
    clear_fidelity_badge: bool = False
    reason: str | None = None


class FeatureFlagItem(CamelModel):
    key: str
    description: str
    enabled_global: bool
    audience: dict[str, Any] | None = None


class FeatureFlagCreate(CamelModel):
    key: str = Field(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    description: str = ""
    enabled_global: bool = True
    audience: dict[str, Any] | None = None
    reason: str | None = None


class FeatureFlagUpdate(CamelModel):
    description: str | None = None
    enabled_global: bool | None = None
    audience: dict[str, Any] | None = None
    clear_audience: bool = False
    reason: str | None = None


class ProfessionalFlagState(CamelModel):
    key: str
    description: str
    enabled_global: bool
    override: bool | None = None
    resolved: bool


class SetFlagOverrideBody(CamelModel):
    enabled: bool | None = None
    reason: str | None = None
