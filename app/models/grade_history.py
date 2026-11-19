
from datetime import datetime

from sqlalchemy import (
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GradeHistory(Base):
    __tablename__ = "grade_history"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    grade_id: Mapped[int] = mapped_column(
        ForeignKey("riwayat_nilai.id"),
        nullable=False,
        index=True
    )

    old_value: Mapped[str] = mapped_column(
        String(2),
        nullable=False
    )

    new_value: Mapped[str] = mapped_column(
        String(2),
        nullable=False
    )

    changed_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
