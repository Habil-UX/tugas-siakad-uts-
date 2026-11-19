from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Union

from pydantic import BaseModel, Field


# ==========================================
# BILLING SCHEMAS
# ==========================================

class BillingGenerateRequest(BaseModel):
    nim: str = Field(min_length=1, max_length=20)
    semester: int = Field(ge=1)
    tahun: str = Field(min_length=1, max_length=10)
    semester_start_date: date


class BillingSemesterGenerateRequest(BaseModel):
    semester: int = Field(ge=1)
    tahun: str = Field(min_length=1, max_length=10)
    semester_start_date: Optional[date] = None


class BillingLateFeeRequest(BaseModel):
    as_of_date: date | None = None


class BillingStatusRequest(BaseModel):
    as_of_date: date | None = None


# ==========================================
# PAYMENT SCHEMAS
# ==========================================

class PaymentCreateRequest(BaseModel):
    billing_id: int = Field(ge=1)
    payment_method_id: int = Field(ge=1)
    amount: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )


class PaymentProcessRequest(BaseModel):
    billing_id: int = Field(ge=1)
    amount: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    method: Union[int, str]
    reference_number: Optional[str] = Field(default=None, max_length=100)
    paid_at: Optional[datetime] = None
    as_of_date: Optional[date] = None


class PaymentConfirmRequest(BaseModel):
    reference_number: str = Field(
        min_length=1,
        max_length=100,
    )
    paid_at: datetime | None = None
    as_of_date: date | None = None


class PaymentFailRequest(BaseModel):
    as_of_date: date | None = None
