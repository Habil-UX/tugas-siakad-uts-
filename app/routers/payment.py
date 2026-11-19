import json
from typing import Optional

from fastapi import APIRouter, Depends, Header, Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.finance import (
    PaymentConfirmRequest,
    PaymentCreateRequest,
    PaymentFailRequest,
    PaymentProcessRequest,
)
from app.services.payment_service import PaymentService
from app.utils.security import compute_webhook_signature

router = APIRouter(
    prefix="/api/payments",
    tags=["Payment Management"],
)


@router.post("/create")
def create_payment(
    data: PaymentCreateRequest,
    db: Session = Depends(get_db),
):
    service = PaymentService(db)

    return service.create_payment(
        billing_id=data.billing_id,
        payment_method_id=data.payment_method_id,
        amount=data.amount,
    )


@router.post("/process")
def process_payment(
    data: PaymentProcessRequest,
    db: Session = Depends(get_db),
):
    service = PaymentService(db)
    return service.process_payment(
        billing_id=data.billing_id,
        amount=data.amount,
        method=data.method,
        reference_number=data.reference_number,
        paid_at=data.paid_at,
        as_of_date=data.as_of_date,
    )


@router.post("/webhook")
def payment_webhook(
    payload: dict,
    x_webhook_signature: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    service = PaymentService(db)
    return service.handle_webhook(
        payload=payload,
        signature=x_webhook_signature,
    )


@router.post("/webhook/simulate-signature")
def simulate_gateway_signature(payload: dict):
    canonical_data = {
        k: v for k, v in payload.items() if k != "signature"
    }
    canonical_str = json.dumps(
        canonical_data,
        separators=(",", ":"),
        sort_keys=True,
    )
    signature = compute_webhook_signature(canonical_str)
    return {
        "payload": canonical_data,
        "signature": signature,
    }


@router.post("/{payment_id}/confirm")
def confirm_payment(
    data: PaymentConfirmRequest,
    payment_id: int = Path(ge=1),
    db: Session = Depends(get_db),
):
    service = PaymentService(db)

    return service.confirm_payment(
        payment_id=payment_id,
        reference_number=data.reference_number,
        paid_at=data.paid_at,
        as_of_date=data.as_of_date,
    )


@router.post("/{payment_id}/fail")
def fail_payment(
    data: PaymentFailRequest,
    payment_id: int = Path(ge=1),
    db: Session = Depends(get_db),
):
    service = PaymentService(db)

    return service.fail_payment(
        payment_id=payment_id,
        as_of_date=data.as_of_date,
    )
