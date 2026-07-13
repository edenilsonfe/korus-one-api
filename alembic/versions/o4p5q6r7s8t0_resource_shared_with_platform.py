"""o4p5q6r7s8t0 — Resources shared_with_platform flag."""

from alembic import op
import sqlalchemy as sa

revision = "o4p5q6r7s8t0"
down_revision = "n4o5p6q7r8s9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resources",
        sa.Column(
            "shared_with_platform",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("resources", "shared_with_platform")
