"""Subscription pending plan change fields."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("pending_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("pending_change_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_subscriptions_pending_plan_id",
        "subscriptions",
        "plans",
        ["pending_plan_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_subscriptions_pending_plan_id", "subscriptions", type_="foreignkey")
    op.drop_column("subscriptions", "pending_change_at")
    op.drop_column("subscriptions", "pending_plan_id")
