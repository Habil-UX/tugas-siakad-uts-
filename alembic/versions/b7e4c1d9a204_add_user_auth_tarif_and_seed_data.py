"""add user auth tarif and seed data

Revision ID: b7e4c1d9a204
Revises: a8c2d6e9f103
Create Date: 2026-11-16 19:50:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e4c1d9a204"
down_revision: Union[str, None] = "a8c2d6e9f103"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. Tabel app_user untuk autentikasi HMAC dan RBAC
    if "app_user" not in inspector.get_table_names():
        op.create_table(
            "app_user",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(50), nullable=False),
            sa.Column("password_hash", sa.String(128), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column(
                "nim",
                sa.String(20),
                sa.ForeignKey("calon_mahasiswa.nim"),
                nullable=True,
            ),
            sa.Column(
                "nidn",
                sa.String(20),
                sa.ForeignKey("dosen.nidn"),
                nullable=True,
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("username", name="uq_app_user_username"),
        )
        op.create_index("ix_app_user_id", "app_user", ["id"])
        op.create_index("ix_app_user_username", "app_user", ["username"], unique=True)
        op.create_index("ix_app_user_nim", "app_user", ["nim"])
        op.create_index("ix_app_user_nidn", "app_user", ["nidn"])

    # 2. Kolom tarif_spp pada program_studi
    prodi_cols = [c["name"] for c in inspector.get_columns("program_studi")]
    if "tarif_spp" not in prodi_cols:
        op.add_column(
            "program_studi",
            sa.Column("tarif_spp", sa.Numeric(12, 2), nullable=True),
        )

    # 3. Composite index pada riwayat_nilai untuk optimasi query prasyarat
    rn_indexes = [idx["name"] for idx in inspector.get_indexes("riwayat_nilai")]
    if "ix_riwayat_nilai_nim_mk_skala" not in rn_indexes:
        op.create_index(
            "ix_riwayat_nilai_nim_mk_skala",
            "riwayat_nilai",
            ["nim", "matakuliah_id", "skala_nilai_id"],
            unique=False,
        )

    # 4. Seed data referensi (non-destruktif menggunakan INSERT OR IGNORE)
    for huruf, bobot in [("A", 4.0), ("B", 3.0), ("C", 2.0), ("D", 1.0), ("E", 0.0)]:
        conn.execute(
            sa.text(
                "INSERT OR IGNORE INTO skala_nilai (nilai_huruf, bobot) VALUES (:h, :b)"
            ),
            {"h": huruf, "b": bobot},
        )

    for kode, nama in [
        ("SNBP", "Seleksi Nasional Berdasarkan Prestasi"),
        ("SNBT", "Seleksi Nasional Berdasarkan Tes"),
        ("MANDIRI", "Seleksi Mandiri Universitas"),
    ]:
        conn.execute(
            sa.text(
                "INSERT OR IGNORE INTO jalur_masuk (kode, nama) VALUES (:k, :n)"
            ),
            {"k": kode, "n": nama},
        )

    conn.execute(
        sa.text(
            """
            INSERT OR IGNORE INTO program_studi (kode, nama, fakultas, tarif_spp)
            VALUES
                ('TIF', 'Teknik Informatika', 'Fakultas Teknik', 5000000.00),
                ('EKO', 'Manajemen', 'Fakultas Ekonomi', 4000000.00)
            """
        )
    )
    conn.execute(
        sa.text(
            "UPDATE program_studi SET tarif_spp = 5000000.00 WHERE lower(fakultas) LIKE '%teknik%' AND tarif_spp IS NULL"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE program_studi SET tarif_spp = 4000000.00 WHERE lower(fakultas) LIKE '%ekonomi%' AND tarif_spp IS NULL"
        )
    )

    for code, name in [
        ("BANK_TRANSFER", "Transfer Bank"),
        ("CASH", "Pembayaran Tunai"),
        ("VIRTUAL_ACCOUNT", "Virtual Account"),
        ("EWALLET", "E-Wallet / QRIS"),
    ]:
        conn.execute(
            sa.text(
                """
                INSERT OR IGNORE INTO payment_method (code, name, is_active, created_at)
                VALUES (:c, :n, 1, CURRENT_TIMESTAMP)
                """
            ),
            {"c": code, "n": name},
        )

    from app.utils.security import hash_password

    for uname, pwd, role in [
        ("admin", "admin123", "admin"),
        ("dosen_pa", "dosen123", "dosen"),
        ("mahasiswa1", "mhs123", "mahasiswa"),
    ]:
        conn.execute(
            sa.text(
                """
                INSERT OR IGNORE INTO app_user (username, password_hash, role, is_active, created_at)
                VALUES (:u, :p, :r, 1, CURRENT_TIMESTAMP)
                """
            ),
            {"u": uname, "p": hash_password(pwd, salt="siakadsalt202600"), "r": role},
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    rn_indexes = [idx["name"] for idx in inspector.get_indexes("riwayat_nilai")]
    if "ix_riwayat_nilai_nim_mk_skala" in rn_indexes:
        op.drop_index("ix_riwayat_nilai_nim_mk_skala", table_name="riwayat_nilai")

    prodi_cols = [c["name"] for c in inspector.get_columns("program_studi")]
    if "tarif_spp" in prodi_cols:
        with op.batch_alter_table("program_studi") as batch_op:
            batch_op.drop_column("tarif_spp")

    if "app_user" in inspector.get_table_names():
        op.drop_index("ix_app_user_nidn", table_name="app_user")
        op.drop_index("ix_app_user_nim", table_name="app_user")
        op.drop_index("ix_app_user_username", table_name="app_user")
        op.drop_index("ix_app_user_id", table_name="app_user")
        op.drop_table("app_user")
