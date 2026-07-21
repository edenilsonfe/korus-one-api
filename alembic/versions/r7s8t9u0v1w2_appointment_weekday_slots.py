"""appointment weekday_slots + duration default 50

Revision ID: r7s8t9u0v1w2
Revises: q6r7s8t9u0v1
Create Date: 2026-07-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "r7s8t9u0v1w2"
down_revision: Union[str, None] = "q6r7s8t9u0v1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("appointments", sa.Column("weekday_slots", sa.JSON(), nullable=True))
    op.alter_column(
        "appointments",
        "duration",
        existing_type=sa.Integer(),
        server_default="50",
        existing_nullable=False,
    )
    op.alter_column(
        "sessions",
        "duration",
        existing_type=sa.Integer(),
        server_default="50",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "sessions",
        "duration",
        existing_type=sa.Integer(),
        server_default="45",
        existing_nullable=False,
    )
    op.alter_column(
        "appointments",
        "duration",
        existing_type=sa.Integer(),
        server_default="45",
        existing_nullable=False,
    )
    op.drop_column("appointments", "weekday_slots")
