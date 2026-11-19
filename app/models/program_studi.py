from decimal import Decimal
from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .calon_mahasiswa import CalonMahasiswa

class ProgramStudi(Base):
    __tablename__ = "program_studi"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    kode: Mapped[str] = mapped_column(String(3), unique=True, index=True, nullable=False)
    nama: Mapped[str] = mapped_column(String(100), nullable=False)
    fakultas: Mapped[str] = mapped_column(String(100), nullable=False)
    tarif_spp: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)

    # Relasi
    calon_mahasiswa: Mapped[List["CalonMahasiswa"]] = relationship(back_populates="program_studi")
