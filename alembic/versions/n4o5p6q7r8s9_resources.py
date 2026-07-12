"""n4o5p6q7r8s9 — Resources library (global catalog + personal uploads)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "n4o5p6q7r8s9"
down_revision = "m3n4o5p6q7r8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_professional_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("professionals.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("categories", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("pages", sa.Integer(), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("downloads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("accent", sa.String(length=32), nullable=False, server_default="primary"),
        sa.Column("objective", sa.String(length=500), nullable=True),
        sa.Column("age_range", sa.String(length=120), nullable=True),
        sa.Column("skill", sa.String(length=255), nullable=True),
        sa.Column("related_protocol", sa.String(length=255), nullable=True),
        sa.Column("difficulty", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_resources_owner_professional_id",
        "resources",
        ["owner_professional_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_resources_owner_professional_id", table_name="resources")
    op.drop_table("resources")
