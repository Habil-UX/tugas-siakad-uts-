"""add version column to krs

Revision ID: 50747fbd5ef0
Revises: 9fb882e2b5ae
Create Date: 2026-11-15 14:37:42.746067

Catatan perbaikan (audit 2026-11-16):
- Kolom ``krs.version`` sudah ditambahkan oleh revisi 95417f7b9188. Menambahkannya
  lagi membuat ``alembic upgrade head`` dari database kosong gagal
  ("duplicate column name: version"). Upgrade sekarang memeriksa keberadaan kolom
  secara idempotent.
- Dua fungsi ``downgrade`` sebelumnya saling menimpa. Kolom ``version`` dimiliki
  oleh revisi 95417f7b9188 yang akan menghapusnya saat downgrade ke base.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50747fbd5ef0'
down_revision: Union[str, None] = '9fb882e2b5ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = [c["name"] for c in inspector.get_columns("krs")]

    if "version" not in columns:
        op.add_column(
            "krs",
            sa.Column(
                "version",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1")
            )
        )


def downgrade() -> None:
    # Kolom krs.version dihapus pada downgrade revisi 95417f7b9188.
    pass
