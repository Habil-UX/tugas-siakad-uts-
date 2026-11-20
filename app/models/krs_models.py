from sqlalchemy import DateTime
from datetime import datetime, time
from sqlalchemy import (
    String, Integer, ForeignKey, Time,
    UniqueConstraint, CheckConstraint,
    Boolean, DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from typing import List, Optional
from .calon_mahasiswa import CalonMahasiswa

class Matakuliah(Base):
    __tablename__ = "matakuliah"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    kode_mk: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    nama_mk: Mapped[str] = mapped_column(String(100), nullable=False)
    sks: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    jenis_mk: Mapped[str] = mapped_column(String(20), nullable=False) # Wajib / Pilihan
    hari: Mapped[str] = mapped_column(String(10), nullable=False)
    jam_mulai: Mapped[time] = mapped_column(Time, nullable=False)
    jam_selesai: Mapped[time] = mapped_column(Time, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint("sks > 0", name="check_sks_positive"),
        CheckConstraint("jam_selesai > jam_mulai", name="check_time_valid"),
    )

    # Relationships
    prerequisites: Mapped[List["Prerequisite"]] = relationship(
        foreign_keys="[Prerequisite.matakuliah_id]", back_populates="matakuliah"
    )

class KRS(Base):
    __tablename__ = "krs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nim: Mapped[str] = mapped_column(ForeignKey("calon_mahasiswa.nim"), index=True, nullable=False)
    semester_akademik: Mapped[int] = mapped_column(Integer, nullable=False)
    tahun_akademik: Mapped[str] = mapped_column(String(10), nullable=False)
    total_sks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)

    version: Mapped[int] = mapped_column(
    Integer,
    default=1,
    nullable=False
)
    # Relationships
    details: Mapped[List["KRSDetail"]] = relationship(back_populates="krs", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('nim', 'semester_akademik', 'tahun_akademik', name='uq_krs_mahasiswa_semester'),
    )

class KRSDetail(Base):
    __tablename__ = "krs_detail"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    krs_id: Mapped[int] = mapped_column(ForeignKey("krs.id"), index=True, nullable=False)
    matakuliah_id: Mapped[int] = mapped_column(ForeignKey("matakuliah.id"), index=True, nullable=False)
    nilai: Mapped[Optional[str]] = mapped_column(
        String(2),
        ForeignKey("skala_nilai.nilai_huruf"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    krs: Mapped["KRS"] = relationship(back_populates="details")
    matakuliah: Mapped["Matakuliah"] = relationship()

    __table_args__ = (
        UniqueConstraint('krs_id', 'matakuliah_id', name='uq_krs_matakuliah'),
    )

class Prerequisite(Base):
    __tablename__ = "prerequisite"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    matakuliah_id: Mapped[int] = mapped_column(ForeignKey("matakuliah.id"), index=True, nullable=False)
    prerequisite_id: Mapped[int] = mapped_column(ForeignKey("matakuliah.id"), index=True, nullable=False)

    # Relationships
    matakuliah: Mapped["Matakuliah"] = relationship(foreign_keys=[matakuliah_id], back_populates="prerequisites")

    __table_args__ = (
        UniqueConstraint('matakuliah_id', 'prerequisite_id', name='uq_prerequisite'),
        CheckConstraint('matakuliah_id != prerequisite_id', name='check_no_self_prereq'),
    )

class SkalaNilai(Base):
    __tablename__ = "skala_nilai"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nilai_huruf: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    bobot: Mapped[float] = mapped_column(nullable=False)
    lulus: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __init__(self, **kwargs):
        if "lulus" not in kwargs:
            if "bobot" in kwargs and kwargs["bobot"] is not None:
                kwargs["lulus"] = float(kwargs["bobot"]) >= 1.0
            elif kwargs.get("nilai_huruf") == "E":
                kwargs["lulus"] = False
            else:
                kwargs["lulus"] = True
        super().__init__(**kwargs)




class RiwayatNilai(Base):
    __tablename__ = "riwayat_nilai"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    nim: Mapped[str] = mapped_column(
        ForeignKey("calon_mahasiswa.nim"),
        index=True,
        nullable=False
    )

    matakuliah_id: Mapped[int] = mapped_column(
        ForeignKey("matakuliah.id"),
        index=True,
        nullable=False
    )

    skala_nilai_id: Mapped[int] = mapped_column(
        ForeignKey("skala_nilai.id"),
        nullable=False
    )

    semester: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    presensi_persen: Mapped[float] = mapped_column(
        nullable=False
    )

    created_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "nim",
            "matakuliah_id",
            "semester",
            name="uq_riwayat_nilai_mahasiswa_mk_semester"
        ),
    )


# Untuk Optimistic Locking

# Di bagian paling bawah file (class baru):
class KrsTransition(Base):
    __tablename__ = "krs_transition"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    krs_id: Mapped[int] = mapped_column(ForeignKey("krs.id"), index=True)
    from_status: Mapped[str] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    changed_by: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)