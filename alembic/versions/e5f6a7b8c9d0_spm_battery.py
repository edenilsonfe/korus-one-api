"""SPM battery — sub-form assessments and informant links."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "spm_subform_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "battery_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subform_slug", sa.String(length=64), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("informant_name", sa.String(length=255), nullable=True),
        sa.Column("informant_relationship", sa.String(length=128), nullable=True),
        sa.Column(
            "answers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("items_answered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_spm_subform_battery_slug",
        "spm_subform_assessments",
        ["battery_id", "subform_slug"],
        unique=True,
    )

    op.create_table(
        "spm_informant_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "subform_assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("spm_subform_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inherit_draft", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_spm_informant_links_subform_active",
        "spm_informant_links",
        ["subform_assessment_id", "revoked_at", "submitted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_spm_informant_links_subform_active", table_name="spm_informant_links")
    op.drop_table("spm_informant_links")
    op.drop_index("ix_spm_subform_battery_slug", table_name="spm_subform_assessments")
    op.drop_table("spm_subform_assessments")
