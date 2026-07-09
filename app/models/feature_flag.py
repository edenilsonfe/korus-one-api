from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin


class FeatureFlag(Base, TimestampMixin):
    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    enabled_global: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    audience: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class FeatureFlagOverride(Base, TimestampMixin):
    __tablename__ = "feature_flag_overrides"

    flag_key: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("feature_flags.key", ondelete="CASCADE"),
        primary_key=True,
    )
    professional_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("professionals.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
