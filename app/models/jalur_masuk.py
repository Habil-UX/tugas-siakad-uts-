from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .calon_mahasiswa import CalonMahasiswa

class JalurMasuk(Base):
    __tablename__ = "jalur_masuk"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    kode: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    nama: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relasi
    calon_mahasiswa: Mapped[List["CalonMahasiswa"]] = relationship(back_populates="jalur_masuk")