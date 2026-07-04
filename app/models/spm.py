import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class SpmSubformAssessment(Base, TimestampMixin):
    __tablename__ = "spm_subform_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    battery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subform_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    informant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    informant_relationship: Mapped[str | None] = mapped_column(String(128), nullable=True)
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    items_answered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    battery: Mapped["Assessment"] = relationship(back_populates="spm_subforms")  # noqa: F821
    informant_links: Mapped[list["SpmInformantLink"]] = relationship(
        back_populates="subform_assessment",
        cascade="all, delete-orphan",
    )


class SpmInformantLink(Base):
    __tablename__ = "spm_informant_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    subform_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("spm_subform_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inherit_draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    subform_assessment: Mapped["SpmSubformAssessment"] = relationship(back_populates="informant_links")
