
from datetime import date, datetime
from decimal import Decimal
from typing import List

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from .calon_mahasiswa import CalonMahasiswa


# ==========================================
# BILLING MODEL
# ==========================================

class Billing(Base):
    __tablename__ = "billing"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    nim: Mapped[str] = mapped_column(
        ForeignKey("calon_mahasiswa.nim"),
        nullable=False,
        index=True
    )

    semester_akademik: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    tahun_akademik: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    due_date: Mapped[date] = mapped_column(
    Date,
    nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="unpaid",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    mahasiswa: Mapped["CalonMahasiswa"] = relationship()

    payments: Mapped[List["Payment"]] = relationship(
        back_populates="billing"
    )

    __table_args__ = (
        UniqueConstraint(
            "nim",
            "semester_akademik",
            "tahun_akademik",
            name="uq_billing_mahasiswa_semester"
        ),
        CheckConstraint(
            "amount > 0",
            name="check_billing_amount_positive"
        ),
        CheckConstraint(
            "status IN ('unpaid', 'partial', 'paid', 'overdue')",
            name="check_billing_status"
        ),
    )


# ==========================================
# PAYMENT METHOD MODEL
# ==========================================

class PaymentMethod(Base):
    __tablename__ = "payment_method"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
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


# ==========================================
# PAYMENT MODEL
# ==========================================

class Payment(Base):
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    billing_id: Mapped[int] = mapped_column(
        ForeignKey("billing.id"),
        nullable=False,
        index=True
    )

    payment_method_id: Mapped[int] = mapped_column(
        ForeignKey("payment_method.id"),
        nullable=False
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False
    )

    reference_number: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    billing: Mapped["Billing"] = relationship(
        back_populates="payments"
    )

    payment_method: Mapped["PaymentMethod"] = relationship()

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="check_payment_amount_positive"
        ),
        CheckConstraint(
            "status IN ('pending', 'success', 'failed')",
            name="check_payment_status"
        ),
    )
