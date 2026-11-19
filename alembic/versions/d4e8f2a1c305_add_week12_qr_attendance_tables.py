"""add week12 qr attendance tables

Revision ID: d4e8f2a1c305
Revises: b7e4c1d9a204
Create Date: 2026-11-18 18:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e8f2a1c305"
down_revision: Union[str, None] = "b7e4c1d9a204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "attendance_session" not in existing_tables:
        op.create_table(
            "attendance_session",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "schedule_id",
                sa.Integer(),
                sa.ForeignKey("jadwal_kuliah.id"),
                nullable=False,
            ),
            sa.Column("session_date", sa.Date(), nullable=False),
            sa.Column(
                "session_status",
                sa.String(20),
                nullable=False,
                server_default="OPEN",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.UniqueConstraint(
                "schedule_id",
                "session_date",
                name="uq_attendance_session_schedule_date",
            ),
        )
        op.create_index("ix_attendance_session_id", "attendance_session", ["id"])
        op.create_index(
            "ix_attendance_session_schedule_id",
            "attendance_session",
            ["schedule_id"],
        )
        op.create_index(
            "ix_attendance_session_session_date",
            "attendance_session",
            ["session_date"],
        )
        op.create_index(
            "ix_attendance_session_session_status",
            "attendance_session",
            ["session_status"],
        )

    if "attendance_qr_token" not in existing_tables:
        op.create_table(
            "attendance_qr_token",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "session_id",
                sa.Integer(),
                sa.ForeignKey("attendance_session.id"),
                nullable=False,
            ),
            sa.Column("jti", sa.String(64), nullable=False),
            sa.Column(
                "phase",
                sa.String(20),
                nullable=False,
                server_default="NORMAL",
            ),
            sa.Column("generated_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("jti", name="uq_attendance_qr_token_jti"),
        )
        op.create_index(
            "ix_attendance_qr_token_id",
            "attendance_qr_token",
            ["id"],
        )
        op.create_index(
            "ix_attendance_qr_token_session_id",
            "attendance_qr_token",
            ["session_id"],
        )
        op.create_index(
            "ix_attendance_qr_token_jti",
            "attendance_qr_token",
            ["jti"],
            unique=True,
        )
        op.create_index(
            "ix_attendance_qr_token_expires_at",
            "attendance_qr_token",
            ["expires_at"],
        )

    if "attendance_record" not in existing_tables:
        op.create_table(
            "attendance_record",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "session_id",
                sa.Integer(),
                sa.ForeignKey("attendance_session.id"),
                nullable=False,
            ),
            sa.Column(
                "student_id",
                sa.Integer(),
                sa.ForeignKey("calon_mahasiswa.id"),
                nullable=False,
            ),
            sa.Column(
                "nim",
                sa.String(20),
                sa.ForeignKey("calon_mahasiswa.nim"),
                nullable=False,
            ),
            sa.Column("scanned_at", sa.DateTime(), nullable=False),
            sa.Column("attendance_status", sa.String(20), nullable=False),
            sa.Column(
                "qr_token_id",
                sa.Integer(),
                sa.ForeignKey("attendance_qr_token.id"),
                nullable=False,
            ),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.UniqueConstraint(
                "session_id",
                "student_id",
                name="uq_attendance_record_session_student",
            ),
            sa.UniqueConstraint(
                "session_id",
                "nim",
                name="uq_attendance_record_session_nim",
            ),
        )
        op.create_index("ix_attendance_record_id", "attendance_record", ["id"])
        op.create_index(
            "ix_attendance_record_session_id",
            "attendance_record",
            ["session_id"],
        )
        op.create_index(
            "ix_attendance_record_student_id",
            "attendance_record",
            ["student_id"],
        )
        op.create_index(
            "ix_attendance_record_nim",
            "attendance_record",
            ["nim"],
        )
        op.create_index(
            "ix_attendance_record_attendance_status",
            "attendance_record",
            ["attendance_status"],
        )
        op.create_index(
            "ix_attendance_record_qr_token_id",
            "attendance_record",
            ["qr_token_id"],
        )

    if "attendance_scan_attempt" not in existing_tables:
        op.create_table(
            "attendance_scan_attempt",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("actor_key", sa.String(100), nullable=False),
            sa.Column("schedule_id", sa.Integer(), nullable=True),
            sa.Column(
                "attempted_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("outcome", sa.String(50), nullable=False),
            sa.Column("detail", sa.String(255), nullable=True),
        )
        op.create_index(
            "ix_attendance_scan_attempt_id",
            "attendance_scan_attempt",
            ["id"],
        )
        op.create_index(
            "ix_attendance_scan_attempt_actor_key",
            "attendance_scan_attempt",
            ["actor_key"],
        )
        op.create_index(
            "ix_attendance_scan_attempt_schedule_id",
            "attendance_scan_attempt",
            ["schedule_id"],
        )
        op.create_index(
            "ix_attendance_scan_attempt_attempted_at",
            "attendance_scan_attempt",
            ["attempted_at"],
        )
        op.create_index(
            "ix_attendance_scan_attempt_actor_time",
            "attendance_scan_attempt",
            ["actor_key", "attempted_at"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "attendance_scan_attempt" in existing_tables:
        op.drop_table("attendance_scan_attempt")
    if "attendance_record" in existing_tables:
        op.drop_table("attendance_record")
    if "attendance_qr_token" in existing_tables:
        op.drop_table("attendance_qr_token")
    if "attendance_session" in existing_tables:
        op.drop_table("attendance_session")
