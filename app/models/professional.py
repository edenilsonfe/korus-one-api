import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class Professional(Base, TimestampMixin):
    __tablename__ = "professionals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialty: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    council: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    phone: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    cpf: Mapped[str] = mapped_column(String(14), default="", nullable=False)
    avatar_color: Mapped[str] = mapped_column(String(64), default="oklch(0.58 0.12 205)", nullable=False)
    subscription_status: Mapped[str] = mapped_column(String(32), nullable=False, default="trialing")
    trial_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    patients: Mapped[list["Patient"]] = relationship(back_populates="professional")  # noqa: F821
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="professional")  # noqa: F821
