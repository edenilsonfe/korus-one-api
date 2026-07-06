import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class BatterySubformAssessment(Base, TimestampMixin):
    __tablename__ = "battery_subform_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    battery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    instrument_slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subform_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    required: Mapped[bool] = mapped_column(nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    items_answered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    battery: Mapped["Assessment"] = relationship(back_populates="battery_subforms")  # noqa: F821
