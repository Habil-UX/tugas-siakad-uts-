from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.finance import (
    BillingGenerateRequest,
    BillingSemesterGenerateRequest,
)
from app.services.billing_service import BillingService
from app.services.scheduler_service import billing_scheduler
from app.utils.security import require_roles

router = APIRouter(
    prefix="/api/billing",
    tags=["Billing Management"],
)


@router.post("/generate")
def generate_billing(
    data: BillingGenerateRequest,
    db: Session = Depends(get_db),
    _user: Optional[dict] = Depends(require_roles(["admin"])),
):
    service = BillingService(db)

    return service.generate_billing(
        nim=data.nim,
        semester=data.semester,
        tahun=data.tahun,
        semester_start_date=data.semester_start_date,
    )


@router.post("/generate-semester")
def generate_semester_billing(
    data: BillingSemesterGenerateRequest,
    db: Session = Depends(get_db),
    _user: Optional[dict] = Depends(require_roles(["admin"])),
):
    service = BillingService(db)
    return service.generate_semester_billing(
        semester=data.semester,
        tahun=data.tahun,
        semester_start_date=data.semester_start_date,
    )


@router.post("/reminders/run")
def run_overdue_reminders(
    as_of_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: Optional[dict] = Depends(require_roles(["admin"])),
):
    return billing_scheduler.run_overdue_reminder_job(
        db=db,
        as_of_date=as_of_date,
    )


@router.get("/scheduler/status")
def get_scheduler_status():
    return billing_scheduler.get_status()


@router.get("/dashboard")
def get_finance_dashboard(
    as_of_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    service = BillingService(db)
    return service.get_financial_dashboard_data(as_of_date=as_of_date)


@router.get("/ai-report")
def get_ai_financial_report(
    as_of_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    service = BillingService(db)
    return service.generate_ai_financial_report(as_of_date=as_of_date)


@router.get("/{billing_id}/late-fee")
def calculate_late_fee(
    billing_id: int = Path(ge=1),
    as_of_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    service = BillingService(db)

    return service.calculate_late_fee(
        billing_id=billing_id,
        as_of_date=as_of_date,
    )


@router.put("/{billing_id}/status")
def update_billing_status(
    billing_id: int = Path(ge=1),
    as_of_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    service = BillingService(db)

    return service.update_billing_status(
        billing_id=billing_id,
        as_of_date=as_of_date,
    )
