"""Clínico, agenda recorrente e ferramentas IA — specialty, diagnosis_keys, therapy plan, appointments series."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "professionals",
        sa.Column("specialty_key", sa.String(length=32), nullable=False, server_default="fono"),
    )

    op.add_column(
        "patients",
        sa.Column("diagnosis_keys", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.execute(
        "UPDATE patients SET diagnosis_keys = jsonb_build_array(diagnosis_key) WHERE diagnosis_key IS NOT NULL"
    )
    op.alter_column("patients", "diagnosis_keys", nullable=False)
    op.drop_column("patients", "diagnosis_key")

    op.add_column("patients", sa.Column("therapy_plan_content", sa.Text(), nullable=True))
    op.add_column(
        "patients",
        sa.Column("therapy_plan_updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "appointments",
        sa.Column("appointment_type", sa.String(length=32), nullable=False, server_default="avulso"),
    )
    op.add_column(
        "appointments",
        sa.Column("series_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_appointments_series_id",
        "appointments",
        "appointments",
        ["series_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_appointments_series_id", "appointments", ["series_id"])
    op.add_column("appointments", sa.Column("frequency", sa.String(length=32), nullable=True))
    op.add_column("appointments", sa.Column("end_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("appointments", "end_date")
    op.drop_column("appointments", "frequency")
    op.drop_index("ix_appointments_series_id", table_name="appointments")
    op.drop_constraint("fk_appointments_series_id", "appointments", type_="foreignkey")
    op.drop_column("appointments", "series_id")
    op.drop_column("appointments", "appointment_type")

    op.drop_column("patients", "therapy_plan_updated_at")
    op.drop_column("patients", "therapy_plan_content")

    op.add_column("patients", sa.Column("diagnosis_key", sa.String(length=32), nullable=True))
    op.execute(
        "UPDATE patients SET diagnosis_key = diagnosis_keys->>0 WHERE diagnosis_keys IS NOT NULL"
    )
    op.alter_column("patients", "diagnosis_key", nullable=False)
    op.drop_column("patients", "diagnosis_keys")

    op.drop_column("professionals", "specialty_key")
