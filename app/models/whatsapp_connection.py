import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid

CONNECTION_STATUS_NOT_CONNECTED = "not_connected"
CONNECTION_STATUS_CONNECTING = "connecting"
CONNECTION_STATUS_SETUP_INCOMPLETE = "setup_incomplete"
CONNECTION_STATUS_TEMPLATE_PENDING = "template_pending"
CONNECTION_STATUS_TEMPLATE_REJECTED = "template_rejected"
CONNECTION_STATUS_ACTIVE = "active"
CONNECTION_STATUS_NEEDS_RECONNECT = "needs_reconnect"
CONNECTION_STATUS_DISCONNECTED = "disconnected"
CONNECTION_STATUS_ERROR = "error"


class WhatsAppConnection(Base, TimestampMixin):
    __tablename__ = "whatsapp_connections"
    __table_args__ = (
        Index("ix_whatsapp_connections_professional_provider_status", "professional_id", "provider", "status"),
        Index("ix_whatsapp_connections_evolution_instance_name", "evolution_instance_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    professional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professionals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="evolution")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=CONNECTION_STATUS_SETUP_INCOMPLETE)
    waba_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone_number_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    verified_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quality_rating: Mapped[str | None] = mapped_column(String(32), nullable=True)
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    evolution_instance_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    encrypted_instance_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    granted_scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
