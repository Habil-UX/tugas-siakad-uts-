
"""add finance billing payment tables

Revision ID: 9fb882e2b5ae
Revises: 0f9e48bbab1f
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9fb882e2b5ae"
down_revision: Union[str, None] = "0f9e48bbab1f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ======================================
    # PAYMENT METHOD
    # ======================================

    op.create_table(
        "payment_method",

        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),

        sa.UniqueConstraint("code")
    )

    op.create_index(
        "ix_payment_method_id",
        "payment_method",
        ["id"]
    )

    # ======================================
    # BILLING
    # ======================================

    op.create_table(
        "billing",

        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nim", sa.String(20), nullable=False),
        sa.Column("semester_akademik", sa.Integer(), nullable=False),
        sa.Column("tahun_akademik", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),

        sa.ForeignKeyConstraint(
            ["nim"],
            ["calon_mahasiswa.nim"]
        ),

        sa.UniqueConstraint(
            "nim",
            "semester_akademik",
            "tahun_akademik",
            name="uq_billing_mahasiswa_semester"
        ),

        sa.CheckConstraint(
            "amount > 0",
            name="check_billing_amount_positive"
        ),

        sa.CheckConstraint(
            "status IN ('unpaid', 'partial', 'paid', 'overdue')",
            name="check_billing_status"
        )
    )

    op.create_index(
        "ix_billing_id",
        "billing",
        ["id"]
    )

    op.create_index(
        "ix_billing_nim",
        "billing",
        ["nim"]
    )

    # ======================================
    # PAYMENT
    # ======================================

    op.create_table(
        "payment",

        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("billing_id", sa.Integer(), nullable=False),
        sa.Column("payment_method_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reference_number", sa.String(100), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),

        sa.ForeignKeyConstraint(
            ["billing_id"],
            ["billing.id"]
        ),

        sa.ForeignKeyConstraint(
            ["payment_method_id"],
            ["payment_method.id"]
        ),

        sa.UniqueConstraint("reference_number"),

        sa.CheckConstraint(
            "amount > 0",
            name="check_payment_amount_positive"
        ),

        sa.CheckConstraint(
            "status IN ('pending', 'success', 'failed')",
            name="check_payment_status"
        )
    )

    op.create_index(
        "ix_payment_id",
        "payment",
        ["id"]
    )

    op.create_index(
        "ix_payment_billing_id",
        "payment",
        ["billing_id"]
    )


def downgrade() -> None:

    # Hapus tabel dalam urutan terbalik
    op.drop_index(
        "ix_payment_id",
        table_name="payment"
    )

    op.drop_index(
        "ix_payment_billing_id",
        table_name="payment"
    )

    op.drop_table("payment")

    op.drop_index(
        "ix_billing_id",
        table_name="billing"
    )

    op.drop_index(
        "ix_billing_nim",
        table_name="billing"
    )

    op.drop_table("billing")

    op.drop_index(
        "ix_payment_method_id",
        table_name="payment_method"
    )

    op.drop_table("payment_method")
