from datetime import datetime, date
from sqlalchemy import String, Date, DateTime, Enum, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .program_studi import ProgramStudi
    from .jalur_masuk import JalurMasuk
    from .jadwal_models import Dosen

class StatusPendaftaran(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class CalonMahasiswa(Base):
    __tablename__ = "calon_mahasiswa"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nama_lengkap: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    tanggal_lahir: Mapped[date] = mapped_column(Date, nullable=False)
    alamat: Mapped[str] = mapped_column(Text, nullable=False)
    
    program_studi_id: Mapped[int] = mapped_column(ForeignKey("program_studi.id"), nullable=False)
    jalur_masuk_id: Mapped[int] = mapped_column(ForeignKey("jalur_masuk.id"), nullable=False)
    dosen_pa_id: Mapped[Optional[int]] = mapped_column(
    ForeignKey("dosen.id"),
    nullable=True,
    index=True
)
    
    status: Mapped[StatusPendaftaran] = mapped_column(
        Enum(StatusPendaftaran), default=StatusPendaftaran.pending, nullable=False
    )
    nim: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relasi
    program_studi: Mapped["ProgramStudi"] = relationship(back_populates="calon_mahasiswa")
    jalur_masuk: Mapped["JalurMasuk"] = relationship(back_populates="calon_mahasiswa")
    dosen_pa: Mapped[Optional["Dosen"]] = relationship(
    "Dosen",
    foreign_keys=[dosen_pa_id]
)

    # Constraint tambahan di level database (SQLite/MySQL compatible)
    __table_args__ = (
        CheckConstraint("length(phone) >= 9", name="check_phone_length"),
    )