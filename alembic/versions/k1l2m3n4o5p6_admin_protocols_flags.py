"""k1l2m3n4o5p6 — Admin protocols publication fields + feature flags."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "k1l2m3n4o5p6"
down_revision = "j0k1l2m3n4o5"
branch_labels = None
depends_on = None

SEED_FLAGS = [
    ("ai_assistant", "Assistente de IA unificado"),
    ("spm", "Bateria SPM"),
    ("abllsr", "ABLLS-R"),
    ("whatsapp", "WhatsApp Evolution"),
]


def upgrade() -> None:
    op.add_column(
        "protocol_catalog",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "protocol_catalog",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "protocol_catalog",
        sa.Column("fidelity_badge", sa.String(length=32), nullable=True),
    )

    op.create_table(
        "feature_flags",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("enabled_global", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("audience", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "feature_flag_overrides",
        sa.Column(
            "flag_key",
            sa.String(length=64),
            sa.ForeignKey("feature_flags.key", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "professional_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("professionals.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_feature_flag_overrides_professional_id",
        "feature_flag_overrides",
        ["professional_id"],
    )

    flags = sa.table(
        "feature_flags",
        sa.column("key", sa.String),
        sa.column("description", sa.String),
        sa.column("enabled_global", sa.Boolean),
    )
    op.bulk_insert(
        flags,
        [
            {"key": key, "description": desc, "enabled_global": True}
            for key, desc in SEED_FLAGS
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_feature_flag_overrides_professional_id", table_name="feature_flag_overrides")
    op.drop_table("feature_flag_overrides")
    op.drop_table("feature_flags")
    op.drop_column("protocol_catalog", "fidelity_badge")
    op.drop_column("protocol_catalog", "sort_order")
    op.drop_column("protocol_catalog", "is_active")
