"""Add structured answers and scores to assessments."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
    )
    op.add_column("assessments", sa.Column("scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column(
        "assessments",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
    )
    op.add_column("assessments", sa.Column("informant", sa.String(length=255), nullable=True))
    op.add_column("assessments", sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("assessments", "metadata")
    op.drop_column("assessments", "informant")
    op.drop_column("assessments", "status")
    op.drop_column("assessments", "scores")
    op.drop_column("assessments", "answers")
