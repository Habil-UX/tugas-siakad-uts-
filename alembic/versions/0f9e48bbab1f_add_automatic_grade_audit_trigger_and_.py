
"""add automatic grade audit trigger and history view"""

from typing import Sequence, Union

from alembic import op


revision: str = "0f9e48bbab1f"
down_revision: Union[str, None] = "8d2fbf7e4c2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.execute("""
        CREATE TABLE grade_audit_context (
            grade_id INTEGER PRIMARY KEY,
            changed_by VARCHAR(100) NOT NULL,
            reason TEXT NOT NULL
        )
    """)

    op.execute("""
        CREATE TRIGGER trg_grade_history_update
        AFTER UPDATE OF skala_nilai_id ON riwayat_nilai
        FOR EACH ROW
        WHEN OLD.skala_nilai_id != NEW.skala_nilai_id
        BEGIN

            INSERT INTO grade_history (
                grade_id,
                old_value,
                new_value,
                changed_by,
                changed_at,
                reason
            )
            SELECT
                NEW.id,
                old_scale.nilai_huruf,
                new_scale.nilai_huruf,
                COALESCE(ctx.changed_by, 'SYSTEM'),
                CURRENT_TIMESTAMP,
                COALESCE(ctx.reason, 'Perubahan nilai')
            FROM skala_nilai AS old_scale
            JOIN skala_nilai AS new_scale
            LEFT JOIN grade_audit_context AS ctx
                ON ctx.grade_id = NEW.id
            WHERE old_scale.id = OLD.skala_nilai_id
              AND new_scale.id = NEW.skala_nilai_id;

            DELETE FROM grade_audit_context
            WHERE grade_id = NEW.id;

        END
    """)

    op.execute("""
        CREATE VIEW v_grade_history AS
        SELECT
            gh.id AS history_id,
            rn.nim AS nim,
            cm.nama_lengkap AS nama_mahasiswa,
            mk.kode_mk AS kode_mk,
            mk.nama_mk AS nama_mk,
            rn.semester AS semester,
            gh.grade_id AS grade_id,
            gh.old_value AS nilai_lama,
            gh.new_value AS nilai_baru,
            gh.changed_by AS changed_by,
            gh.changed_at AS changed_at,
            gh.reason AS reason
        FROM grade_history gh
        JOIN riwayat_nilai rn
            ON rn.id = gh.grade_id
        JOIN calon_mahasiswa cm
            ON cm.nim = rn.nim
        JOIN matakuliah mk
            ON mk.id = rn.matakuliah_id
    """)


def downgrade() -> None:

    op.execute("DROP VIEW IF EXISTS v_grade_history")

    op.execute(
        "DROP TRIGGER IF EXISTS trg_grade_history_update"
    )

    op.execute(
        "DROP TABLE IF EXISTS grade_audit_context"
    )
