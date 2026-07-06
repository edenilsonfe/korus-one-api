"""g7h8i9j0k1l2 — Generic battery subform assessments."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "g7h8i9j0k1l2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "battery_subform_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "battery_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("instrument_slug", sa.String(length=64), nullable=False),
        sa.Column("subform_slug", sa.String(length=64), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column(
            "answers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("items_answered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_battery_subform_battery_slug",
        "battery_subform_assessments",
        ["battery_id", "subform_slug"],
        unique=True,
    )
    op.create_index(
        "ix_battery_subform_instrument",
        "battery_subform_assessments",
        ["instrument_slug"],
    )


def downgrade() -> None:
    op.drop_index("ix_battery_subform_instrument", table_name="battery_subform_assessments")
    op.drop_index("ix_battery_subform_battery_slug", table_name="battery_subform_assessments")
    op.drop_table("battery_subform_assessments")
