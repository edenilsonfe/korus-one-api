"""i9j0k1l2m3n4 — In-app notifications (broadcast) + professional.is_staff."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "i9j0k1l2m3n4"
down_revision = "h8i9j0k1l2m3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. professional.is_staff flag (platform staff gate for announcements admin).
    op.add_column(
        "professionals",
        sa.Column(
            "is_staff",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # 2. app_notifications — one row per notification. Broadcasts do NOT fan out.
    op.create_table(
        "app_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("deep_link", sa.String(length=500), nullable=True),
        sa.Column(
            "severity",
            sa.String(length=20),
            nullable=False,
            server_default="info",
        ),
        # personal only (NULL on broadcast) — prepared for v1.1, unused in v1.
        sa.Column(
            "recipient_professional_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("professionals.id", ondelete="CASCADE"),
            nullable=True,
        ),
        # broadcast only (NULL on personal)
        sa.Column("audience", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("professionals.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_app_notifications_kind",
        "app_notifications",
        ["kind"],
    )
    op.create_index(
        "ix_app_notifications_status",
        "app_notifications",
        ["status"],
    )
    op.create_index(
        "ix_app_notifications_recipient_professional_id",
        "app_notifications",
        ["recipient_professional_id"],
    )
    op.create_index(
        "ix_app_notifications_delivery",
        "app_notifications",
        ["kind", "status", "publish_at", "expires_at"],
    )

    # 3. app_notification_reads — materializes interactions (seen/read) on demand.
    op.create_table(
        "app_notification_reads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "notification_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_notifications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "professional_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("professionals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "notification_id",
            "professional_id",
            name="uq_app_notification_reads_notif_prof",
        ),
    )
    op.create_index(
        "ix_app_notification_reads_notification_id",
        "app_notification_reads",
        ["notification_id"],
    )
    op.create_index(
        "ix_app_notification_reads_professional_id",
        "app_notification_reads",
        ["professional_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_app_notification_reads_professional_id",
        table_name="app_notification_reads",
    )
    op.drop_index(
        "ix_app_notification_reads_notification_id",
        table_name="app_notification_reads",
    )
    op.drop_table("app_notification_reads")
    op.drop_index("ix_app_notifications_delivery", table_name="app_notifications")
    op.drop_index(
        "ix_app_notifications_recipient_professional_id",
        table_name="app_notifications",
    )
    op.drop_index("ix_app_notifications_status", table_name="app_notifications")
    op.drop_index("ix_app_notifications_kind", table_name="app_notifications")
    op.drop_table("app_notifications")
    op.drop_column("professionals", "is_staff")
