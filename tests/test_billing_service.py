
from datetime import timedelta
from types import SimpleNamespace
from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models import (
    Billing,
    Payment,
    PaymentMethod,
    CalonMahasiswa,
    ProgramStudi,
    JalurMasuk,
    StatusPendaftaran,
)

from app.services.billing_service import BillingService


def create_student(db, nim="251635099", program=None):

    if program is None:
        program = db.query(ProgramStudi).filter(
            ProgramStudi.kode == "TIF"
        ).first()

    jalur = db.query(JalurMasuk).filter(
        JalurMasuk.kode == "SNBT"
    ).first()

    mahasiswa = CalonMahasiswa(
        nama_lengkap="Mahasiswa Testing",
        email=f"{nim}@test.com",
        phone="081234567890",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Jalan Testing",
        program_studi_id=program.id,
        jalur_masuk_id=jalur.id,
        status=StatusPendaftaran.approved,
        nim=nim,
    )

    db.add(mahasiswa)
    db.commit()
    db.refresh(mahasiswa)

    return mahasiswa


def create_billing(db, nim, due_date=date(2026, 1, 1)):

    billing = Billing(
        nim=nim,
        semester_akademik=1,
        tahun_akademik="2025/2026",
        amount=Decimal("5000000"),
        due_date=due_date,
        status="unpaid",
    )

    db.add(billing)
    db.commit()
    db.refresh(billing)

    return billing


def create_payment(db, billing, amount):

    method = PaymentMethod(
        code="TEST_TRANSFER",
        name="Transfer Bank",
        is_active=True,
    )

    db.add(method)
    db.flush()

    payment = Payment(
        billing_id=billing.id,
        payment_method_id=method.id,
        amount=Decimal(str(amount)),
        status="success",
        reference_number=f"REF-{billing.id}",
        paid_at=datetime(2026, 1, 10),
    )

    db.add(payment)
    db.commit()

    return payment


# ==========================================
# GENERATE BILLING
# ==========================================

def test_generate_billing_success(db_session):

    mahasiswa = create_student(db_session)
    service = BillingService(db_session)

    result = service.generate_billing(
        nim=mahasiswa.nim,
        semester=1,
        tahun="2026/2027",
        semester_start_date=date(2026, 8, 1),
    )

    assert result["status"] == "unpaid"
    assert Decimal(result["amount"]) == Decimal("5000000")
    assert result["due_date"] == "2026-08-15"


def test_generate_billing_student_not_found(db_session):

    service = BillingService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.generate_billing(
            "INVALID",
            1,
            "2026/2027",
            date(2026, 8, 1),
        )

    assert exc.value.status_code == 404


def test_generate_billing_invalid_semester(db_session):

    service = BillingService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.generate_billing(
            "INVALID",
            0,
            "2026/2027",
            date(2026, 8, 1),
        )

    assert exc.value.status_code == 400


def test_generate_billing_duplicate(db_session):

    mahasiswa = create_student(db_session)
    service = BillingService(db_session)

    service.generate_billing(
        mahasiswa.nim,
        1,
        "2026/2027",
        date(2026, 8, 1),
    )

    with pytest.raises(HTTPException) as exc:

        service.generate_billing(
            mahasiswa.nim,
            1,
            "2026/2027",
            date(2026, 8, 1),
        )

    assert exc.value.status_code == 409


def test_generate_billing_economy_tariff(db_session):

    program = ProgramStudi(
        kode="EKO",
        nama="Manajemen",
        fakultas="Fakultas Ekonomi",
    )

    db_session.add(program)
    db_session.commit()

    mahasiswa = create_student(
        db_session,
        nim="251635098",
        program=program,
    )

    service = BillingService(db_session)

    result = service.generate_billing(
        mahasiswa.nim,
        1,
        "2026/2027",
        date(2026, 8, 1),
    )

    assert Decimal(result["amount"]) == Decimal("4000000")


def test_generate_billing_unknown_tariff(db_session):

    program = ProgramStudi(
        kode="SENI",
        nama="Seni Rupa",
        fakultas="Fakultas Seni",
    )

    db_session.add(program)
    db_session.commit()

    mahasiswa = create_student(
        db_session,
        nim="251635097",
        program=program,
    )

    service = BillingService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.generate_billing(
            mahasiswa.nim,
            1,
            "2026/2027",
            date(2026, 8, 1),
        )

    assert exc.value.status_code == 400


# ==========================================
# LATE FEE
# ==========================================

def test_calculate_late_fee_success(db_session):

    mahasiswa = create_student(db_session)
    billing = create_billing(db_session, mahasiswa.nim)

    create_payment(
        db_session,
        billing,
        2000000,
    )

    service = BillingService(db_session)

    result = service.calculate_late_fee(
        billing.id,
        date(2026, 3, 2),
    )

    assert result["outstanding"] == "3000000.00"
    assert result["months_late"] == 2
    assert result["late_fee"] == "60000.00"
    assert result["total_due"] == "3060000.00"


def test_calculate_late_fee_before_30_days(db_session):

    mahasiswa = create_student(db_session)
    billing = create_billing(db_session, mahasiswa.nim)

    service = BillingService(db_session)

    result = service.calculate_late_fee(
        billing.id,
        date(2026, 1, 30),
    )

    assert result["overdue_days"] == 29
    assert result["late_fee"] == "0.00"


def test_calculate_late_fee_paid_in_full(db_session):

    mahasiswa = create_student(db_session)
    billing = create_billing(db_session, mahasiswa.nim)

    create_payment(
        db_session,
        billing,
        5000000,
    )

    service = BillingService(db_session)

    result = service.calculate_late_fee(
        billing.id,
        date(2026, 3, 2),
    )

    assert result["outstanding"] == "0.00"
    assert result["late_fee"] == "0.00"


def test_calculate_late_fee_billing_not_found(db_session):

    service = BillingService(db_session)

    with pytest.raises(HTTPException) as exc:
        service.calculate_late_fee(99999)

    assert exc.value.status_code == 404


# ==========================================
# UPDATE BILLING STATUS
# ==========================================

@pytest.mark.parametrize(
    "paid,as_of,expected",
    [
        (0, date(2026, 1, 1), "unpaid"),
        (2000000, date(2026, 1, 1), "partial"),
        (0, date(2026, 1, 2), "overdue"),
        (5000000, date(2026, 1, 2), "paid"),
    ],
)
def test_update_billing_status(
    db_session,
    paid,
    as_of,
    expected,
):

    mahasiswa = create_student(db_session)
    billing = create_billing(db_session, mahasiswa.nim)

    if paid > 0:
        create_payment(db_session, billing, paid)

    service = BillingService(db_session)

    result = service.update_billing_status(
        billing.id,
        as_of,
    )

    assert result["status"] == expected


def test_update_billing_status_not_found(db_session):

    service = BillingService(db_session)

    with pytest.raises(HTTPException) as exc:
        service.update_billing_status(99999)

    assert exc.value.status_code == 404


# ==========================================
# ADDITIONAL COVERAGE TESTS
# ==========================================

def test_get_tariff_without_program(db_session):

    service = BillingService(db_session)

    mahasiswa = SimpleNamespace(
        program_studi=None
    )

    with pytest.raises(HTTPException) as exc:

        service._get_tariff(mahasiswa)

    assert exc.value.status_code == 400


def test_generate_billing_commit_exception(
    db_session,
    monkeypatch
):

    mahasiswa = create_student(db_session)
    service = BillingService(db_session)

    rollback_called = []

    def fail_commit():
        raise RuntimeError("Database commit failed")

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

        service.generate_billing(
            mahasiswa.nim,
            1,
            "2026/2027",
            date(2026, 8, 1)
        )

    assert rollback_called


def test_calculate_late_fee_default_date(db_session):

    mahasiswa = create_student(db_session)

    billing = create_billing(
        db_session,
        mahasiswa.nim,
        date.today() - timedelta(days=60)
    )

    service = BillingService(db_session)

    result = service.calculate_late_fee(
        billing.id
    )

    assert result["overdue_days"] == 60
    assert result["months_late"] == 2


def test_update_billing_status_default_date(db_session):

    mahasiswa = create_student(db_session)

    billing = create_billing(
        db_session,
        mahasiswa.nim,
        date.today() - timedelta(days=1)
    )

    service = BillingService(db_session)

    result = service.update_billing_status(
        billing.id
    )

    assert result["status"] == "overdue"


def test_update_billing_status_commit_exception(
    db_session,
    monkeypatch
):

    mahasiswa = create_student(db_session)

    billing = create_billing(
        db_session,
        mahasiswa.nim
    )

    service = BillingService(db_session)

    rollback_called = []

    def fail_commit():
        raise RuntimeError("Database commit failed")

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

        service.update_billing_status(
            billing.id,
            date(2026, 1, 2)
        )

    assert rollback_called
