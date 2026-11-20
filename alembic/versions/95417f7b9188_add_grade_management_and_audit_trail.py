
"""add grade management and audit trail"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "95417f7b9188"
down_revision: Union[str, None] = "c0b4e3a8c963"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # 1. Tambahkan kolom Grade Management ke riwayat_nilai
    op.add_column(
        "riwayat_nilai",
        sa.Column("presensi_persen", sa.Float(), nullable=True)
    )

    op.add_column(
        "riwayat_nilai",
        sa.Column("created_by", sa.String(100), nullable=True)
    )

    op.add_column(
        "riwayat_nilai",
        sa.Column("updated_at", sa.DateTime(), nullable=True)
    )

    op.add_column(
        "riwayat_nilai",
        sa.Column("version", sa.Integer(), nullable=True)
    )

    # Isi nilai awal untuk data yang sudah tersedia
    op.execute("""
        UPDATE riwayat_nilai
        SET presensi_persen = 100,
            created_by = 'SYSTEM',
            updated_at = CURRENT_TIMESTAMP,
            version = 1
    """)

    with op.batch_alter_table("riwayat_nilai") as batch_op:
        batch_op.alter_column(
            "presensi_persen",
            existing_type=sa.Float(),
            nullable=False
        )
        batch_op.alter_column(
            "created_by",
            existing_type=sa.String(100),
            nullable=False
        )
        batch_op.alter_column(
            "updated_at",
            existing_type=sa.DateTime(),
            nullable=False
        )
        batch_op.alter_column(
            "version",
            existing_type=sa.Integer(),
            nullable=False
        )

    # 2. Tambahkan optimistic locking pada KRS
    op.add_column(
        "krs",
        sa.Column("version", sa.Integer(), nullable=True)
    )

    op.execute("""
        UPDATE krs SET version = 1
    """)

    with op.batch_alter_table("krs") as batch_op:
        batch_op.alter_column(
            "version",
            existing_type=sa.Integer(),
            nullable=False
        )

    # 3. Tabel Grade History
    op.create_table(
        "grade_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "grade_id",
            sa.Integer(),
            sa.ForeignKey("riwayat_nilai.id"),
            nullable=False
        ),
        sa.Column("old_value", sa.String(2), nullable=False),
        sa.Column("new_value", sa.String(2), nullable=False),
        sa.Column("changed_by", sa.String(100), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False)
    )

    op.create_index(
        "ix_grade_history_id",
        "grade_history",
        ["id"]
    )

    op.create_index(
        "ix_grade_history_grade_id",
        "grade_history",
        ["grade_id"]
    )

    # 4. Tabel KRS Transition
    op.create_table(
        "krs_transition",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "krs_id",
            sa.Integer(),
            sa.ForeignKey("krs.id"),
            nullable=False
        ),
        sa.Column("from_status", sa.String(20), nullable=False),
        sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column("changed_by", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False)
    )

    op.create_index(
        "ix_krs_transition_id",
        "krs_transition",
        ["id"]
    )

    op.create_index(
        "ix_krs_transition_krs_id",
        "krs_transition",
        ["krs_id"]
    )

    # 5. Minggu 9: skala_nilai.lulus & krs_detail.nilai (FK skala_nilai.nilai_huruf)
    op.add_column(
        "skala_nilai",
        sa.Column("lulus", sa.Boolean(), nullable=False, server_default=sa.text("1"))
    )
    op.execute("UPDATE skala_nilai SET lulus = CASE WHEN bobot >= 1.0 THEN 1 ELSE 0 END")

    with op.batch_alter_table("krs_detail") as batch_op:
        batch_op.add_column(sa.Column("nilai", sa.String(2), nullable=True))
        batch_op.create_foreign_key(
            "fk_krs_detail_nilai_skala_nilai",
            "skala_nilai",
            ["nilai"],
            ["nilai_huruf"]
        )


def downgrade() -> None:
    with op.batch_alter_table("krs_detail") as batch_op:
        batch_op.drop_constraint("fk_krs_detail_nilai_skala_nilai", type_="foreignkey")
        batch_op.drop_column("nilai")

    with op.batch_alter_table("skala_nilai") as batch_op:
        batch_op.drop_column("lulus")

    # Hapus tabel transition dan history
    op.drop_index(
        "ix_krs_transition_krs_id",
        table_name="krs_transition"
    )
    op.drop_index(
        "ix_krs_transition_id",
        table_name="krs_transition"
    )
    op.drop_table("krs_transition")

    op.drop_index(
        "ix_grade_history_grade_id",
        table_name="grade_history"
    )
    op.drop_index(
        "ix_grade_history_id",
        table_name="grade_history"
    )
    op.drop_table("grade_history")

    # Hapus optimistic locking KRS
    with op.batch_alter_table("krs") as batch_op:
        batch_op.drop_column("version")

    # Hapus kolom Grade Management
    with op.batch_alter_table("riwayat_nilai") as batch_op:
        batch_op.drop_column("version")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_by")
        batch_op.drop_column("presensi_persen")
