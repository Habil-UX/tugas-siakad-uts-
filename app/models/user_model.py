from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="mahasiswa"
    )
    nim: Mapped[Optional[str]] = mapped_column(
        String(20),
        ForeignKey("calon_mahasiswa.nim"),
        nullable=True,
        index=True
    )
    nidn: Mapped[Optional[str]] = mapped_column(
        String(20),
        ForeignKey("dosen.nidn"),
        nullable=True,
        index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
