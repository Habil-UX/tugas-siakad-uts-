
"""add unique constraint riwayat nilai

Revision ID: 8d2fbf7e4c2b
Revises: 95417f7b9188
Create Date: 2026-11-10 14:24:25.821777
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8d2fbf7e4c2b'
down_revision: Union[str, None] = '95417f7b9188'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table(
        "riwayat_nilai",
        recreate="always"
    ) as batch_op:

        batch_op.create_unique_constraint(
            "uq_riwayat_nilai_mahasiswa_mk_semester",
            ["nim", "matakuliah_id", "semester"]
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "riwayat_nilai",
        recreate="always"
    ) as batch_op:

        batch_op.drop_constraint(
            "uq_riwayat_nilai_mahasiswa_mk_semester",
            type_="unique"
        )
