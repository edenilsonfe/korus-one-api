import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class ProtocolCatalog(Base, TimestampMixin):
    __tablename__ = "protocol_catalog"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    age_range: Mapped[str] = mapped_column(String(64), nullable=False)
    field_templates: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)


class Assessment(Base, TimestampMixin):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    professional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professionals.id"), nullable=False, index=True
    )
    protocol_id: Mapped[str] = mapped_column(String(64), ForeignKey("protocol_catalog.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    result: Mapped[str] = mapped_column(String(255), nullable=False)
    percentage: Mapped[int] = mapped_column(Integer, nullable=False)
    interpretation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    fields: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    patient: Mapped["Patient"] = relationship(back_populates="assessments")  # noqa: F821
    protocol: Mapped["ProtocolCatalog"] = relationship()
