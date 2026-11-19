from datetime import datetime, time
from sqlalchemy import String, Integer, ForeignKey, Time, Boolean, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from typing import List

# Tabel Dosen (Jika belum ada)
class Dosen(Base):
    __tablename__ = "dosen"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nidn: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nama: Mapped[str] = mapped_column(String(100))
    
    jadwal: Mapped[List["JadwalKuliah"]] = relationship(back_populates="dosen")

class Ruangan(Base):
    __tablename__ = "ruangan"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    kode_ruangan: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    nama_ruangan: Mapped[str] = mapped_column(String(50))
    kapasitas: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    jadwal: Mapped[List["JadwalKuliah"]] = relationship(back_populates="ruangan")

class JadwalKuliah(Base):
    __tablename__ = "jadwal_kuliah"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    matakuliah_id: Mapped[int] = mapped_column(ForeignKey("matakuliah.id"), index=True)
    dosen_id: Mapped[int] = mapped_column(ForeignKey("dosen.id"), index=True)
    ruangan_id: Mapped[int] = mapped_column(ForeignKey("ruangan.id"), index=True)
    
    hari: Mapped[str] = mapped_column(String(10))
    jam_mulai: Mapped[time] = mapped_column(Time)
    jam_selesai: Mapped[time] = mapped_column(Time)
    tahun_akademik: Mapped[str] = mapped_column(String(10))
    semester_akademik: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="AKTIF")

    matakuliah: Mapped["Matakuliah"] = relationship()
    dosen: Mapped["Dosen"] = relationship(back_populates="jadwal")
    ruangan: Mapped["Ruangan"] = relationship(back_populates="jadwal")

class NotificationLog(Base):
    __tablename__ = "notification_log"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    recipient_type: Mapped[str] = mapped_column(String(20))
    recipient_id: Mapped[str] = mapped_column(String(50))
    channel: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ScheduleChangeLog(Base):
    __tablename__ = "schedule_change_log"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    jadwal_id: Mapped[int] = mapped_column(Integer)
    action_type: Mapped[str] = mapped_column(String(20))
    old_data: Mapped[str] = mapped_column(Text, nullable=True)
    new_data: Mapped[str] = mapped_column(Text, nullable=True)
    changed_by: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)