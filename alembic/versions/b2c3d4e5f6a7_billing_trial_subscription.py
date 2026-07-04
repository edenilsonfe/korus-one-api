"""Billing trial and subscription tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "professionals",
        sa.Column("cpf", sa.String(length=14), server_default="", nullable=False),
    )
    op.add_column(
        "professionals",
        sa.Column("subscription_status", sa.String(length=32), server_default="trialing", nullable=False),
    )
    op.add_column(
        "professionals",
        sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "professionals",
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("limits", sa.JSON(), nullable=True),
        sa.Column("price_cents", sa.Integer(), server_default="0", nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="BRL", nullable=False),
        sa.Column("billing_interval", sa.String(length=32), server_default="monthly", nullable=False),
        sa.Column("features", sa.JSON(), nullable=True),
        sa.Column("badge", sa.String(length=64), nullable=True),
        sa.Column("highlighted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plans_slug"), "plans", ["slug"], unique=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professional_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="incomplete", nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("external_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("external_checkout_id", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_payment_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subscriptions_professional_id"), "subscriptions", ["professional_id"], unique=False)
    op.create_index(op.f("ix_subscriptions_plan_id"), "subscriptions", ["plan_id"], unique=False)
    op.create_index(
        op.f("ix_subscriptions_external_subscription_id"),
        "subscriptions",
        ["external_subscription_id"],
        unique=False,
    )

    op.create_table(
        "billing_customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professional_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("external_customer_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("professional_id", "provider", name="uq_billing_customer_professional_provider"),
    )
    op.create_index(op.f("ix_billing_customers_professional_id"), "billing_customers", ["professional_id"], unique=False)
    op.create_index(op.f("ix_billing_customers_provider"), "billing_customers", ["provider"], unique=False)

    op.create_table(
        "billing_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("external_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="received", nullable=False),
        sa.Column("professional_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "external_event_id", name="uq_billing_event_provider_external"),
    )
    op.create_index(op.f("ix_billing_events_provider"), "billing_events", ["provider"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_billing_events_provider"), table_name="billing_events")
    op.drop_table("billing_events")
    op.drop_index(op.f("ix_billing_customers_provider"), table_name="billing_customers")
    op.drop_index(op.f("ix_billing_customers_professional_id"), table_name="billing_customers")
    op.drop_table("billing_customers")
    op.drop_index(op.f("ix_subscriptions_external_subscription_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_plan_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_professional_id"), table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index(op.f("ix_plans_slug"), table_name="plans")
    op.drop_table("plans")
    op.drop_column("professionals", "trial_ends_at")
    op.drop_column("professionals", "trial_started_at")
    op.drop_column("professionals", "subscription_status")
    op.drop_column("professionals", "cpf")
