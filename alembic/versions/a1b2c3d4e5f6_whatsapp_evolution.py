"""whatsapp evolution integration

Revision ID: a1b2c3d4e5f6
Revises: 64acae8f92dc
Create Date: 2026-07-04 06:15:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "64acae8f92dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "caregivers",
        sa.Column("whatsapp_opt_in", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    op.create_table(
        "whatsapp_connections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("professional_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("waba_id", sa.String(length=64), nullable=True),
        sa.Column("phone_number_id", sa.String(length=64), nullable=True),
        sa.Column("display_phone_number", sa.String(length=32), nullable=True),
        sa.Column("verified_name", sa.String(length=255), nullable=True),
        sa.Column("quality_rating", sa.String(length=32), nullable=True),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("evolution_instance_name", sa.String(length=128), nullable=True),
        sa.Column("encrypted_instance_api_key", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("granted_scopes", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_whatsapp_connections_professional_id"), "whatsapp_connections", ["professional_id"])
    op.create_index(
        "ix_whatsapp_connections_professional_provider_status",
        "whatsapp_connections",
        ["professional_id", "provider", "status"],
    )
    op.create_index(
        "ix_whatsapp_connections_evolution_instance_name",
        "whatsapp_connections",
        ["evolution_instance_name"],
    )

    op.create_table(
        "notification_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("professional_id", sa.UUID(), nullable=False),
        sa.Column("whatsapp_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("whatsapp_events", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column(
            "whatsapp_message_templates",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("professional_id"),
    )
    op.create_index(op.f("ix_notification_settings_professional_id"), "notification_settings", ["professional_id"])

    op.create_table(
        "notification_message_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("professional_id", sa.UUID(), nullable=True),
        sa.Column("appointment_id", sa.UUID(), nullable=True),
        sa.Column("patient_id", sa.UUID(), nullable=True),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("notification_type", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_message_id", sa.String(length=128), nullable=True),
        sa.Column("to_phone", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("is_test", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("scheduled_time", sa.Time(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "appointment_id",
            "notification_type",
            "channel",
            "scheduled_date",
            "scheduled_time",
            "is_test",
            name="uq_notification_message_idempotency",
        ),
    )
    op.create_index(op.f("ix_notification_message_logs_professional_id"), "notification_message_logs", ["professional_id"])
    op.create_index(op.f("ix_notification_message_logs_appointment_id"), "notification_message_logs", ["appointment_id"])
    op.create_index(op.f("ix_notification_message_logs_patient_id"), "notification_message_logs", ["patient_id"])
    op.create_index(
        "ix_notification_message_logs_monthly",
        "notification_message_logs",
        ["professional_id", "provider", "notification_type", "created_at"],
    )
    op.create_index(
        "ix_notification_message_logs_provider_message",
        "notification_message_logs",
        ["provider", "provider_message_id"],
    )


def downgrade() -> None:
    op.drop_table("notification_message_logs")
    op.drop_table("notification_settings")
    op.drop_table("whatsapp_connections")
    op.drop_column("caregivers", "whatsapp_opt_in")
