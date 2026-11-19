
from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models import (
    Billing,
    Payment,
    PaymentMethod,
    CalonMahasiswa,
    ProgramStudi,
    JalurMasuk,
    StatusPendaftaran,
)

from app.services.payment_service import PaymentService


# ==========================================
# TEST HELPERS
# ==========================================

def create_student(db):

    prodi = db.query(ProgramStudi).filter(
        ProgramStudi.kode == "TIF"
    ).first()

    jalur = db.query(JalurMasuk).filter(
        JalurMasuk.kode == "SNBT"
    ).first()

    mahasiswa = CalonMahasiswa(
        nama_lengkap="Payment Testing",
        email="payment@test.com",
        phone="081234567890",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Jalan Testing",
        program_studi_id=prodi.id,
        jalur_masuk_id=jalur.id,
        status=StatusPendaftaran.approved,
        nim="251635099",
    )

    db.add(mahasiswa)
    db.commit()
    db.refresh(mahasiswa)

    return mahasiswa


def create_billing(
    db,
    nim,
    amount=Decimal("5000000"),
    due_date=date(2026, 12, 31),
):

    billing = Billing(
        nim=nim,
        semester_akademik=1,
        tahun_akademik="2026/2027",
        amount=amount,
        due_date=due_date,
        status="unpaid",
    )

    db.add(billing)
    db.commit()
    db.refresh(billing)

    return billing


def create_method(
    db,
    active=True,
):

    method = PaymentMethod(
        code="TEST_TRANSFER",
        name="Transfer Bank",
        is_active=active,
    )

    db.add(method)
    db.commit()
    db.refresh(method)

    return method


def create_payment(
    db,
    billing,
    method,
    amount=Decimal("2000000"),
    status="pending",
    reference=None,
):

    payment = Payment(
        billing_id=billing.id,
        payment_method_id=method.id,
        amount=amount,
        status=status,
        reference_number=reference,
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return payment


def setup_payment(db):

    mahasiswa = create_student(db)
    billing = create_billing(db, mahasiswa.nim)
    method = create_method(db)

    return mahasiswa, billing, method


# ==========================================
# NORMALIZE AMOUNT
# ==========================================

def test_normalize_amount_success(db_session):

    service = PaymentService(db_session)

    result = service._normalize_amount("150000.50")

    assert result == Decimal("150000.50")


@pytest.mark.parametrize(
    "amount",
    [None, "abc", "NaN", "Infinity"]
)
def test_normalize_amount_invalid(db_session, amount):

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service._normalize_amount(amount)

    assert exc.value.status_code == 400


@pytest.mark.parametrize(
    "amount",
    [0, -100]
)
def test_normalize_amount_not_positive(db_session, amount):

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service._normalize_amount(amount)

    assert exc.value.status_code == 400


def test_normalize_amount_more_than_two_decimals(db_session):

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service._normalize_amount("100.123")

    assert exc.value.status_code == 400


# ==========================================
# GET BILLING
# ==========================================

def test_get_billing_success(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    service = PaymentService(db_session)

    result = service._get_billing(billing.id)

    assert result.id == billing.id


def test_get_billing_not_found(db_session):

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service._get_billing(99999)

    assert exc.value.status_code == 404


# ==========================================
# GET PAYMENT METHOD
# ==========================================

def test_get_payment_method_success(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    service = PaymentService(db_session)

    result = service._get_payment_method(method.id)

    assert result.id == method.id


def test_get_payment_method_not_found(db_session):

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service._get_payment_method(99999)

    assert exc.value.status_code == 404


def test_get_payment_method_inactive(db_session):

    mahasiswa = create_student(db_session)
    billing = create_billing(db_session, mahasiswa.nim)
    method = create_method(db_session, active=False)

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service._get_payment_method(method.id)

    assert exc.value.status_code == 400


# ==========================================
# GET PAYMENT
# ==========================================

def test_get_payment_success(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(
        db_session,
        billing,
        method
    )

    service = PaymentService(db_session)

    result = service._get_payment(payment.id)

    assert result.id == payment.id


def test_get_payment_not_found(db_session):

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service._get_payment(99999)

    assert exc.value.status_code == 404


# ==========================================
# TOTAL PAYMENT
# ==========================================

def test_get_total_amount_empty(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    service = PaymentService(db_session)

    result = service._get_total_amount(
        billing.id,
        ["success"]
    )

    assert result == Decimal("0")


def test_get_total_amount_success(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    create_payment(
        db_session,
        billing,
        method,
        amount=Decimal("1000000"),
        status="success"
    )

    create_payment(
        db_session,
        billing,
        method,
        amount=Decimal("500000"),
        status="pending"
    )

    service = PaymentService(db_session)

    result = service._get_total_amount(
        billing.id,
        ["success"]
    )

    assert result == Decimal("1000000")


# ==========================================
# CREATE PAYMENT
# ==========================================

def test_create_payment_success(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    service = PaymentService(db_session)

    result = service.create_payment(
        billing.id,
        method.id,
        "2000000"
    )

    assert result["status"] == "pending"
    assert result["amount"] == "2000000.00"
    assert result["billing_id"] == billing.id


def test_create_payment_billing_not_found(db_session):

    method = create_method(db_session)

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.create_payment(
            99999,
            method.id,
            1000000
        )

    assert exc.value.status_code == 404


def test_create_payment_method_not_found(db_session):

    mahasiswa = create_student(db_session)
    billing = create_billing(db_session, mahasiswa.nim)

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.create_payment(
            billing.id,
            99999,
            1000000
        )

    assert exc.value.status_code == 404


def test_create_payment_inactive_method(db_session):

    mahasiswa = create_student(db_session)
    billing = create_billing(db_session, mahasiswa.nim)
    method = create_method(db_session, active=False)

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.create_payment(
            billing.id,
            method.id,
            1000000
        )

    assert exc.value.status_code == 400


def test_create_payment_invalid_amount(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.create_payment(
            billing.id,
            method.id,
            -1000
        )

    assert exc.value.status_code == 400


def test_create_payment_already_paid(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    create_payment(
        db_session,
        billing,
        method,
        amount=Decimal("5000000"),
        status="success"
    )

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.create_payment(
            billing.id,
            method.id,
            100000
        )

    assert exc.value.status_code == 409


def test_create_payment_pending_reservation(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    create_payment(
        db_session,
        billing,
        method,
        amount=Decimal("5000000"),
        status="pending"
    )

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.create_payment(
            billing.id,
            method.id,
            100000
        )

    assert exc.value.status_code == 409


def test_create_payment_exceeds_outstanding(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.create_payment(
            billing.id,
            method.id,
            6000000
        )

    assert exc.value.status_code == 400


def test_create_payment_commit_exception(
    db_session,
    monkeypatch
):

    mahasiswa, billing, method = setup_payment(db_session)

    service = PaymentService(db_session)

    rollback_called = []

    def fail_commit():
        raise RuntimeError("Commit failed")

    def fake_rollback():
        rollback_called.append(True)

    monkeypatch.setattr(
        db_session,
        "commit",
        fail_commit
    )

    monkeypatch.setattr(
        db_session,
        "rollback",
        fake_rollback
    )

    with pytest.raises(RuntimeError):

        service.create_payment(
            billing.id,
            method.id,
            1000000
        )

    assert rollback_called


# ==========================================
# SYNC BILLING STATUS
# ==========================================

@pytest.mark.parametrize(
    "paid,as_of,expected",
    [
        (5000000, date(2026, 12, 1), "paid"),
        (1000000, date(2026, 12, 1), "partial"),
        (0, date(2027, 1, 1), "overdue"),
        (0, date(2026, 12, 1), "unpaid"),
    ]
)
def test_sync_billing_status(
    db_session,
    paid,
    as_of,
    expected
):

    mahasiswa, billing, method = setup_payment(db_session)

    service = PaymentService(db_session)

    service._sync_billing_status(
        billing,
        Decimal(str(paid)),
        as_of
    )

    assert billing.status == expected


def test_sync_billing_status_default_date(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    service = PaymentService(db_session)

    service._sync_billing_status(
        billing,
        Decimal("0")
    )

    assert billing.status in ["unpaid", "overdue"]


# ==========================================
# CONFIRM PAYMENT
# ==========================================

def test_confirm_payment_success(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(
        db_session,
        billing,
        method
    )

    service = PaymentService(db_session)

    result = service.confirm_payment(
        payment.id,
        "REF-CONFIRM-001",
        datetime(2026, 12, 1, 10, 0),
        date(2026, 12, 1)
    )

    assert result["payment_status"] == "success"
    assert result["billing_status"] == "partial"
    assert result["reference_number"] == "REF-CONFIRM-001"


def test_confirm_payment_reference_not_string(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(db_session, billing, method)

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.confirm_payment(
            payment.id,
            None
        )

    assert exc.value.status_code == 400


@pytest.mark.parametrize(
    "reference",
    ["", " "]
)
def test_confirm_payment_empty_reference(db_session, reference):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(db_session, billing, method)

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.confirm_payment(
            payment.id,
            reference
        )

    assert exc.value.status_code == 400


def test_confirm_payment_reference_too_long(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(db_session, billing, method)

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.confirm_payment(
            payment.id,
            "R" * 101
        )

    assert exc.value.status_code == 400


def test_confirm_payment_not_found(db_session):

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.confirm_payment(
            99999,
            "REF-999"
        )

    assert exc.value.status_code == 404


def test_confirm_payment_idempotent(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(
        db_session,
        billing,
        method,
        status="success",
        reference="REF-EXISTING"
    )

    service = PaymentService(db_session)

    result = service.confirm_payment(
        payment.id,
        "REF-EXISTING"
    )

    assert result["idempotent"] is True


def test_confirm_payment_different_reference(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(
        db_session,
        billing,
        method,
        status="success",
        reference="REF-OLD"
    )

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.confirm_payment(
            payment.id,
            "REF-NEW"
        )

    assert exc.value.status_code == 409


def test_confirm_payment_failed_status(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(
        db_session,
        billing,
        method,
        status="failed"
    )

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.confirm_payment(
            payment.id,
            "REF-FAILED"
        )

    assert exc.value.status_code == 409


def test_confirm_payment_duplicate_reference(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    create_payment(
        db_session,
        billing,
        method,
        status="failed",
        reference="REF-DUPLICATE"
    )

    payment = create_payment(
        db_session,
        billing,
        method
    )

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.confirm_payment(
            payment.id,
            "REF-DUPLICATE"
        )

    assert exc.value.status_code == 409


def test_confirm_payment_exceeds_billing(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(
        db_session,
        billing,
        method,
        amount=Decimal("6000000")
    )

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.confirm_payment(
            payment.id,
            "REF-OVERPAY",
            as_of_date=date(2026, 12, 1)
        )

    assert exc.value.status_code == 409


def test_confirm_payment_fully_paid(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(
        db_session,
        billing,
        method,
        amount=Decimal("5000000")
    )

    service = PaymentService(db_session)

    result = service.confirm_payment(
        payment.id,
        "REF-FULL",
        as_of_date=date(2026, 12, 1)
    )

    assert result["billing_status"] == "paid"


def test_confirm_payment_overdue(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(
        db_session,
        billing,
        method,
        amount=Decimal("1000000")
    )

    service = PaymentService(db_session)

    result = service.confirm_payment(
        payment.id,
        "REF-OVERDUE",
        as_of_date=date(2027, 1, 1)
    )

    assert result["billing_status"] == "overdue"


def test_confirm_payment_default_datetime(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(
        db_session,
        billing,
        method
    )

    service = PaymentService(db_session)

    result = service.confirm_payment(
        payment.id,
        "REF-DEFAULT",
        as_of_date=date(2026, 12, 1)
    )

    assert result["payment_status"] == "success"


def test_confirm_payment_integrity_error(
    db_session,
    monkeypatch
):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(db_session, billing, method)

    service = PaymentService(db_session)

    rollback_called = []

    def fail_commit():
        raise IntegrityError(
            "statement",
            {},
            Exception("Duplicate reference")
        )

    def fake_rollback():
        rollback_called.append(True)

    monkeypatch.setattr(
        db_session,
        "commit",
        fail_commit
    )

    monkeypatch.setattr(
        db_session,
        "rollback",
        fake_rollback
    )

    with pytest.raises(HTTPException) as exc:

        service.confirm_payment(
            payment.id,
            "REF-INTEGRITY"
        )

    assert exc.value.status_code == 409
    assert rollback_called


def test_confirm_payment_generic_exception(
    db_session,
    monkeypatch
):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(db_session, billing, method)

    service = PaymentService(db_session)

    rollback_called = []

    def fail_commit():
        raise RuntimeError("Unexpected database error")

    def fake_rollback():
        rollback_called.append(True)

    monkeypatch.setattr(
        db_session,
        "commit",
        fail_commit
    )

    monkeypatch.setattr(
        db_session,
        "rollback",
        fake_rollback
    )

    with pytest.raises(RuntimeError):

        service.confirm_payment(
            payment.id,
            "REF-ERROR"
        )

    assert rollback_called


# ==========================================
# FAIL PAYMENT
# ==========================================

def test_fail_payment_success(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(
        db_session,
        billing,
        method
    )

    service = PaymentService(db_session)

    result = service.fail_payment(
        payment.id,
        date(2026, 12, 1)
    )

    assert result["payment_status"] == "failed"
    assert result["billing_status"] == "unpaid"


def test_fail_payment_overdue(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(
        db_session,
        billing,
        method
    )

    service = PaymentService(db_session)

    result = service.fail_payment(
        payment.id,
        date(2027, 1, 1)
    )

    assert result["billing_status"] == "overdue"


def test_fail_payment_partial(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    create_payment(
        db_session,
        billing,
        method,
        amount=Decimal("1000000"),
        status="success",
        reference="REF-PAID"
    )

    payment = create_payment(
        db_session,
        billing,
        method
    )

    service = PaymentService(db_session)

    result = service.fail_payment(
        payment.id,
        date(2026, 12, 1)
    )

    assert result["billing_status"] == "partial"


def test_fail_payment_not_found(db_session):

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.fail_payment(99999)

    assert exc.value.status_code == 404


def test_fail_payment_idempotent(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(
        db_session,
        billing,
        method,
        status="failed"
    )

    service = PaymentService(db_session)

    result = service.fail_payment(payment.id)

    assert result["idempotent"] is True


def test_fail_payment_already_success(db_session):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(
        db_session,
        billing,
        method,
        status="success",
        reference="REF-SUCCESS"
    )

    service = PaymentService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.fail_payment(payment.id)

    assert exc.value.status_code == 409


def test_fail_payment_commit_exception(
    db_session,
    monkeypatch
):

    mahasiswa, billing, method = setup_payment(db_session)

    payment = create_payment(
        db_session,
        billing,
        method
    )

    service = PaymentService(db_session)

    rollback_called = []

    def fail_commit():
        raise RuntimeError("Commit failed")

    def fake_rollback():
        rollback_called.append(True)

    monkeypatch.setattr(
        db_session,
        "commit",
        fail_commit
    )

    monkeypatch.setattr(
        db_session,
        "rollback",
        fake_rollback
    )

    with pytest.raises(RuntimeError):

        service.fail_payment(payment.id)

    assert rollback_called
