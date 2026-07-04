import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    professional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professionals.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    diagnosis_key: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="avaliacao")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    avatar_color: Mapped[str] = mapped_column(String(64), nullable=False)

    professional: Mapped["Professional"] = relationship(back_populates="patients")  # noqa: F821
    caregivers: Mapped[list["Caregiver"]] = relationship(back_populates="patient", cascade="all, delete-orphan")  # noqa: F821
    goals: Mapped[list["Goal"]] = relationship(back_populates="patient", cascade="all, delete-orphan")  # noqa: F821
    sessions: Mapped[list["Session"]] = relationship(back_populates="patient", cascade="all, delete-orphan")  # noqa: F821
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="patient", cascade="all, delete-orphan")  # noqa: F821
    evolutions: Mapped[list["Evolution"]] = relationship(back_populates="patient", cascade="all, delete-orphan")  # noqa: F821
    anamnese_entries: Mapped[list["AnamneseEntry"]] = relationship(back_populates="patient", cascade="all, delete-orphan")  # noqa: F821
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="patient", cascade="all, delete-orphan")  # noqa: F821
    timeline_events: Mapped[list["TimelineEvent"]] = relationship(back_populates="patient", cascade="all, delete-orphan")  # noqa: F821
    domain_snapshots: Mapped[list["ClinicalDomainSnapshot"]] = relationship(back_populates="patient", cascade="all, delete-orphan")  # noqa: F821
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient", cascade="all, delete-orphan")  # noqa: F821
    ai_reports: Mapped[list["AIReport"]] = relationship(back_populates="patient", cascade="all, delete-orphan")  # noqa: F821
