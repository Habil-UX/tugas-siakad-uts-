from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AttendanceSession(Base):
    __tablename__ = "attendance_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    schedule_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("jadwal_kuliah.id"),
        nullable=False,
        index=True,
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    session_status: Mapped[str] = mapped_column(
        String(20),
        default="OPEN",
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    schedule: Mapped["JadwalKuliah"] = relationship("JadwalKuliah")
    qr_tokens: Mapped[List["AttendanceQRToken"]] = relationship(
        "AttendanceQRToken",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    records: Mapped[List["AttendanceRecord"]] = relationship(
        "AttendanceRecord",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "schedule_id",
            "session_date",
            name="uq_attendance_session_schedule_date",
        ),
    )


class AttendanceQRToken(Base):
    __tablename__ = "attendance_qr_token"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("attendance_session.id"),
        nullable=False,
        index=True,
    )
    jti: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    phase: Mapped[str] = mapped_column(
        String(20),
        default="NORMAL",
        nullable=False,
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    session: Mapped["AttendanceSession"] = relationship(
        "AttendanceSession",
        back_populates="qr_tokens",
    )
    records: Mapped[List["AttendanceRecord"]] = relationship(
        "AttendanceRecord",
        back_populates="qr_token",
    )


class AttendanceRecord(Base):
    __tablename__ = "attendance_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("attendance_session.id"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("calon_mahasiswa.id"),
        nullable=False,
        index=True,
    )
    nim: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("calon_mahasiswa.nim"),
        nullable=False,
        index=True,
    )
    scanned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    attendance_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    qr_token_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("attendance_qr_token.id"),
        nullable=False,
        index=True,
    )
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    session: Mapped["AttendanceSession"] = relationship(
        "AttendanceSession",
        back_populates="records",
    )
    student: Mapped["CalonMahasiswa"] = relationship(
        "CalonMahasiswa",
        foreign_keys=[student_id],
    )
    qr_token: Mapped["AttendanceQRToken"] = relationship(
        "AttendanceQRToken",
        back_populates="records",
    )

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "student_id",
            name="uq_attendance_record_session_student",
        ),
        UniqueConstraint(
            "session_id",
            "nim",
            name="uq_attendance_record_session_nim",
        ),
    )


class AttendanceScanAttempt(Base):
    __tablename__ = "attendance_scan_attempt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    schedule_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index(
            "ix_attendance_scan_attempt_actor_time",
            "actor_key",
            "attempted_at",
        ),
    )
