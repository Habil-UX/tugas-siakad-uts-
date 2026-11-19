
from alembic import op
import sqlalchemy as sa


revision = "a8c2d6e9f103"
down_revision = "50747fbd5ef0"
branch_labels = None
depends_on = None


def upgrade():

    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # ======================================
    # 1. MEMBERSIHKAN TABEL SEMENTARA
    # ======================================

    if "_alembic_tmp_calon_mahasiswa" in inspector.get_table_names():

        count = conn.execute(
            sa.text(
                "SELECT COUNT(*) FROM _alembic_tmp_calon_mahasiswa"
            )
        ).scalar_one()

        if count > 0:
            raise RuntimeError(
                "Tabel sementara berisi data. "
                "Migration dihentikan untuk melindungi data."
            )

        op.execute(
            "DROP TABLE _alembic_tmp_calon_mahasiswa"
        )

    # ======================================
    # 2. MENAMBAHKAN KOLOM DOSEN PA
    # ======================================

    inspector = sa.inspect(conn)

    columns = [
        column["name"]
        for column in inspector.get_columns("calon_mahasiswa")
    ]

    if "dosen_pa_id" not in columns:

        op.execute("""
            ALTER TABLE calon_mahasiswa
            ADD COLUMN dosen_pa_id INTEGER
            REFERENCES dosen(id)
        """)

    # ======================================
    # 3. MEMBUAT INDEX
    # ======================================

    inspector = sa.inspect(conn)

    indexes = [
        index["name"]
        for index in inspector.get_indexes("calon_mahasiswa")
    ]

    if "ix_calon_mahasiswa_dosen_pa_id" not in indexes:

        op.create_index(
            "ix_calon_mahasiswa_dosen_pa_id",
            "calon_mahasiswa",
            ["dosen_pa_id"],
            unique=False
        )


def downgrade():

    conn = op.get_bind()

    # Simpan definisi VIEW sebelum perubahan tabel.
    view_sql = conn.execute(
        sa.text("""
            SELECT sql
            FROM sqlite_master
            WHERE type = 'view'
            AND name = 'v_grade_history'
        """)
    ).scalar()

    # VIEW harus dilepas sebelum tabel dibangun ulang.
    if view_sql:
        op.execute("DROP VIEW v_grade_history")

    inspector = sa.inspect(conn)

    indexes = [
        index["name"]
        for index in inspector.get_indexes("calon_mahasiswa")
    ]

    if "ix_calon_mahasiswa_dosen_pa_id" in indexes:
        op.drop_index(
            "ix_calon_mahasiswa_dosen_pa_id",
            table_name="calon_mahasiswa"
        )

    columns = [
        column["name"]
        for column in sa.inspect(conn).get_columns("calon_mahasiswa")
    ]

    if "dosen_pa_id" in columns:
        fk_names = {
            fk.get("name")
            for fk in sa.inspect(conn).get_foreign_keys("calon_mahasiswa")
            if fk.get("name")
        }

        with op.batch_alter_table("calon_mahasiswa") as batch_op:
            if "fk_calon_mahasiswa_dosen_pa_id_dosen" in fk_names:
                batch_op.drop_constraint(
                    "fk_calon_mahasiswa_dosen_pa_id_dosen",
                    type_="foreignkey"
                )

            batch_op.drop_column("dosen_pa_id")

    # Pulihkan VIEW dengan definisi SQL aslinya.
    if view_sql:
        op.execute(view_sql)
