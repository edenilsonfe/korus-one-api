"""In-app notification inbox (product announcements broadcast).

Distinct namespace from the outbound ``notification_*`` tables (clinic -> patient
WhatsApp communication). Backs the unified inbox described in
``docs/notificacoes-in-app-design.md``.

- ``AppNotification`` holds one row per notification. Broadcasts do **not** fan
  out: a single row serves every professional in the target audience.
- ``AppNotificationRead`` materializes only interactions (seen/read) on demand.
  Absence of a row means the notification is unseen and unread for that
  professional.

v1 ships broadcast only; ``kind``/``recipient_professional_id`` are prepared for
a future ``personal`` nature without requiring a migration.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class AppNotification(Base, TimestampMixin):
    __tablename__ = "app_notifications"

    __table_args__ = (
        Index(
            "ix_app_notifications_delivery",
            "kind",
            "status",
            "publish_at",
            "expires_at",
        ),
        Index(
            "ix_app_notifications_recipient_professional_id",
            "recipient_professional_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # 'broadcast' | 'personal'
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text(), nullable=False)  # plain text, no markdown
    deep_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="info", server_default="info"
    )

    # personal only (NULL on broadcast) — prepared for v1.1, unused in v1.
    recipient_professional_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("professionals.id", ondelete="CASCADE"),
        nullable=True,
    )

    # broadcast only (NULL on personal)
    audience: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    publish_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("professionals.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self):
        return (
            f"<AppNotification(id={self.id}, kind='{self.kind}', "
            f"type='{self.type}')>"
        )


class AppNotificationRead(Base, TimestampMixin):
    __tablename__ = "app_notification_reads"

    __table_args__ = (
        UniqueConstraint(
            "notification_id",
            "professional_id",
            name="uq_app_notification_reads_notif_prof",
        ),
        Index("ix_app_notification_reads_notification_id", "notification_id"),
        Index("ix_app_notification_reads_professional_id", "professional_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_notifications.id", ondelete="CASCADE"),
        nullable=False,
    )
    professional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("professionals.id", ondelete="CASCADE"),
        nullable=False,
    )
    seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self):
        return (
            f"<AppNotificationRead(notification_id={self.notification_id}, "
            f"professional_id={self.professional_id})>"
        )
