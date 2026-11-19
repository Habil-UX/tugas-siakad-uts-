from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class NimSequence(Base):
    __tablename__ = "nim_sequences"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tahun: Mapped[int] = mapped_column(Integer, nullable=False)
    program_studi_id: Mapped[int] = mapped_column(ForeignKey("program_studi.id"), nullable=False)
    last_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint('tahun', 'program_studi_id', name='uq_nim_tahun_prodi'),
    )