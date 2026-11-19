
import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace
from fastapi import HTTPException

from app.services.krs_manager import KRSManager


# ==========================================
# HELPER
# ==========================================

def make_manager():
    db = MagicMock()
    manager = KRSManager(db)
    return manager, db


def make_query(result=None, count=0, all_result=None):
    query = MagicMock()
    query.filter.return_value = query
    query.join.return_value = query
    query.with_for_update.return_value = query
    query.first.return_value = result
    query.count.return_value = count
    query.all.return_value = all_result or []
    return query


# ==========================================
# 1. MAHASISWA
# ==========================================

def test_get_mahasiswa_success():
    manager, db = make_manager()
    mahasiswa = SimpleNamespace(nim="12345")
    db.query.return_value = make_query(mahasiswa)

    result = manager._get_mahasiswa("12345")

    assert result == mahasiswa


def test_get_mahasiswa_not_found():
    manager, db = make_manager()
    db.query.return_value = make_query(None)

    with pytest.raises(HTTPException) as exc:
        manager._get_mahasiswa("99999")

    assert exc.value.status_code == 404


# ==========================================
# 2. GET OR CREATE KRS
# ==========================================

def test_get_or_create_krs_existing():
    manager, db = make_manager()
    krs = SimpleNamespace(nim="12345", status="DRAFT")

    db.query.return_value = make_query(krs)

    result = manager._get_or_create_krs("12345")

    assert result == krs
    db.add.assert_not_called()



def test_get_or_create_krs_new():
    manager, db = make_manager()

    manager._get_mahasiswa = MagicMock(
        return_value=SimpleNamespace(nim="12345")
    )

    db.query.return_value = make_query(None)

    def refresh(obj):
        obj.id = 1

    db.refresh.side_effect = refresh

    result = manager._get_or_create_krs(
        "12345",
        semester=2,
        tahun="2025/2026"
    )

    assert result is not None
    assert result.nim == "12345"
    assert result.semester_akademik == 2
    assert result.tahun_akademik == "2025/2026"
    db.add.assert_called_once()
    db.commit.assert_called_once()



# ==========================================
# 3. LOG TRANSITION
# ==========================================

def test_log_transition():
    manager, db = make_manager()

    manager._log_transition(
        1,
        "DRAFT",
        "SUBMITTED",
        "Mahasiswa_12345"
    )

    db.add.assert_called_once()

    log = db.add.call_args[0][0]

    assert log.krs_id == 1
    assert log.from_status == "DRAFT"
    assert log.to_status == "SUBMITTED"
    assert log.changed_by == "Mahasiswa_12345"


# ==========================================
# 4. SUBMIT KRS
# ==========================================

def test_submit_krs_invalid_status():
    manager, db = make_manager()

    krs = SimpleNamespace(status="APPROVED")

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    with pytest.raises(HTTPException) as exc:
        manager.submit_krs("12345")

    assert exc.value.status_code == 400


def test_submit_krs_validation_failed():
    manager, db = make_manager()

    krs = SimpleNamespace(status="DRAFT")

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    manager.validate_krs = MagicMock(
        return_value={
            "is_valid": False,
            "errors": ["SKS melebihi batas"]
        }
    )

    with pytest.raises(HTTPException) as exc:
        manager.submit_krs("12345")

    assert exc.value.status_code == 400
    assert exc.value.detail["message"] == "KRS tidak valid"


def test_submit_krs_success():
    manager, db = make_manager()

    krs = SimpleNamespace(
        id=1,
        status="DRAFT",
        version=0
    )

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    manager.validate_krs = MagicMock(
        return_value={
            "is_valid": True,
            "errors": []
        }
    )

    manager._log_transition = MagicMock()

    result = manager.submit_krs("12345")

    assert result["status"] == "SUBMITTED"
    assert krs.version == 1

    manager._log_transition.assert_called_once()
    db.commit.assert_called_once()


def test_submit_krs_from_revision():
    manager, db = make_manager()

    krs = SimpleNamespace(
        id=2,
        status="REVISION",
        version=1
    )

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    manager.validate_krs = MagicMock(
        return_value={
            "is_valid": True,
            "errors": []
        }
    )

    manager._log_transition = MagicMock()

    result = manager.submit_krs("12345")

    assert result["status"] == "SUBMITTED"
    assert krs.version == 2



# ==========================================
# 5. APPROVE KRS
# ==========================================

NIDN_DOSEN_PA = "198501012010011001"


def test_approve_krs_not_found():
    manager, db = make_manager()
    db.query.return_value = make_query(None)

    with pytest.raises(HTTPException) as exc:
        manager.approve_krs("12345", NIDN_DOSEN_PA)

    assert exc.value.status_code == 404


def test_approve_krs_unauthorized():
    manager, db = make_manager()

    krs = SimpleNamespace(status="SUBMITTED")
    db.query.return_value = make_query(krs)

    manager._get_authorized_dosen = MagicMock(
        side_effect=HTTPException(
            status_code=403,
            detail="Dosen tidak berwenang mengelola KRS mahasiswa ini"
        )
    )

    with pytest.raises(HTTPException) as exc:
        manager.approve_krs("12345", NIDN_DOSEN_PA)

    assert exc.value.status_code == 403


def test_approve_krs_invalid_status():
    manager, db = make_manager()

    krs = SimpleNamespace(status="DRAFT")
    db.query.return_value = make_query(krs)

    manager._get_authorized_dosen = MagicMock(
        return_value=SimpleNamespace(nidn=NIDN_DOSEN_PA)
    )

    with pytest.raises(HTTPException) as exc:
        manager.approve_krs("12345", NIDN_DOSEN_PA)

    assert exc.value.status_code == 400
    assert "Transisi ilegal" in exc.value.detail


def test_approve_krs_success():
    manager, db = make_manager()

    krs = SimpleNamespace(
        id=1,
        status="SUBMITTED",
        version=1
    )

    dosen = SimpleNamespace(nidn=NIDN_DOSEN_PA)

    db.query.return_value = make_query(krs)

    manager._get_authorized_dosen = MagicMock(
        return_value=dosen
    )

    manager._log_transition = MagicMock()

    result = manager.approve_krs(
        "12345",
        NIDN_DOSEN_PA
    )

    assert result["status"] == "APPROVED"
    assert krs.version == 2

    manager._get_authorized_dosen.assert_called_once_with(
        "12345",
        NIDN_DOSEN_PA
    )

    manager._log_transition.assert_called_once_with(
        1,
        "SUBMITTED",
        "APPROVED",
        NIDN_DOSEN_PA
    )

    db.commit.assert_called_once()


# ==========================================
# 6. REVISE KRS
# ==========================================

def test_revise_krs_not_found():
    manager, db = make_manager()

    db.query.return_value = make_query(None)

    with pytest.raises(HTTPException) as exc:
        manager.revise_krs("12345", NIDN_DOSEN_PA)

    assert exc.value.status_code == 404


def test_revise_krs_invalid_status():
    manager, db = make_manager()

    krs = SimpleNamespace(status="APPROVED")

    db.query.return_value = make_query(krs)

    manager._get_authorized_dosen = MagicMock(
        return_value=SimpleNamespace(nidn=NIDN_DOSEN_PA)
    )

    with pytest.raises(HTTPException) as exc:
        manager.revise_krs("12345", NIDN_DOSEN_PA)

    assert exc.value.status_code == 400
    assert "Transisi ilegal" in exc.value.detail


def test_revise_krs_success():
    manager, db = make_manager()

    krs = SimpleNamespace(
        id=1,
        status="SUBMITTED",
        version=1
    )

    dosen = SimpleNamespace(nidn=NIDN_DOSEN_PA)

    db.query.return_value = make_query(krs)

    manager._get_authorized_dosen = MagicMock(
        return_value=dosen
    )

    manager._log_transition = MagicMock()

    result = manager.revise_krs(
        "12345",
        NIDN_DOSEN_PA
    )

    assert result["status"] == "REVISION"
    assert krs.version == 2

    manager._get_authorized_dosen.assert_called_once_with(
        "12345",
        NIDN_DOSEN_PA
    )

    manager._log_transition.assert_called_once_with(
        1,
        "SUBMITTED",
        "REVISION",
        NIDN_DOSEN_PA
    )

    db.commit.assert_called_once()



# ==========================================
# 7. VALIDATE KRS
# ==========================================

def test_validate_krs_empty_details():
    manager, db = make_manager()

    krs = SimpleNamespace(details=[])

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    result = manager.validate_krs("12345")

    assert result["is_valid"] is True
    assert result["errors"] == []


def test_validate_krs_with_errors(monkeypatch):
    import app.services.krs_manager as module

    class FakeValidator:
        def _validate(self, context):
            return SimpleNamespace(
                is_valid=False,
                message="Validasi gagal"
            )

    monkeypatch.setattr(
        module,
        "SKSValidator",
        FakeValidator
    )
    monkeypatch.setattr(
        module,
        "PrerequisiteValidator",
        FakeValidator
    )
    monkeypatch.setattr(
        module,
        "ConflictValidator",
        FakeValidator
    )
    monkeypatch.setattr(
        module,
        "DuplicateValidator",
        FakeValidator
    )

    manager, db = make_manager()

    detail = SimpleNamespace(
        matakuliah=SimpleNamespace(id=1)
    )

    krs = SimpleNamespace(details=[detail])

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    result = manager.validate_krs("12345")

    assert result["is_valid"] is False
    assert "Validasi gagal" in result["errors"]
    assert len(result["errors"]) == 1


# ==========================================
# 8. ADD COURSE
# ==========================================

def test_add_course_invalid_status():
    manager, db = make_manager()

    krs = SimpleNamespace(status="APPROVED")

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    with pytest.raises(HTTPException) as exc:
        manager.add_course("12345", "IF101")

    assert exc.value.status_code == 400


def test_add_course_not_found():
    manager, db = make_manager()

    krs = SimpleNamespace(status="DRAFT")

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    db.query.return_value = make_query(None)

    with pytest.raises(HTTPException) as exc:
        manager.add_course("12345", "IF999")

    assert exc.value.status_code == 404


def test_add_course_validation_failed():
    manager, db = make_manager()

    krs = SimpleNamespace(
        id=1,
        status="DRAFT",
        details=[],
        total_sks=0
    )

    mk = SimpleNamespace(
        id=10,
        kode_mk="IF101",
        sks=3
    )

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    db.query.return_value = make_query(mk)

    manager.validator_chain = MagicMock()

    manager.validator_chain.validate.return_value = (
        SimpleNamespace(
            is_valid=False,
            message="SKS melebihi batas"
        )
    )

    with pytest.raises(HTTPException) as exc:
        manager.add_course("12345", "IF101")

    assert exc.value.status_code == 400


def test_add_course_success():
    manager, db = make_manager()

    krs = SimpleNamespace(
        id=1,
        status="DRAFT",
        details=[],
        total_sks=0
    )

    mk = SimpleNamespace(
        id=10,
        kode_mk="IF101",
        sks=3
    )

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    db.query.return_value = make_query(mk)

    manager.validator_chain = MagicMock()

    manager.validator_chain.validate.return_value = (
        SimpleNamespace(
            is_valid=True,
            message="Valid"
        )
    )

    result = manager.add_course("12345", "IF101")

    assert result["total_sks"] == 3
    assert krs.total_sks == 3
    assert len(krs.details) == 1

    db.commit.assert_called_once()


# ==========================================
# 9. REMOVE COURSE
# ==========================================

def test_remove_course_invalid_status():
    manager, db = make_manager()

    krs = SimpleNamespace(status="APPROVED")

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    with pytest.raises(HTTPException) as exc:
        manager.remove_course("12345", "IF101")

    assert exc.value.status_code == 400


def test_remove_course_not_found():
    manager, db = make_manager()

    krs = SimpleNamespace(status="DRAFT")

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    db.query.return_value = make_query(None)

    with pytest.raises(HTTPException) as exc:
        manager.remove_course("12345", "IF999")

    assert exc.value.status_code == 404


def test_remove_course_detail_not_found():
    manager, db = make_manager()

    krs = SimpleNamespace(
        id=1,
        status="DRAFT",
        total_sks=3
    )

    mk = SimpleNamespace(
        id=10,
        kode_mk="IF101",
        nama_mk="Algoritma",
        sks=3
    )

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    db.query.side_effect = [
        make_query(mk),
        make_query(None)
    ]

    with pytest.raises(HTTPException) as exc:
        manager.remove_course("12345", "IF101")

    assert exc.value.status_code == 404


def test_remove_course_success():
    manager, db = make_manager()

    krs = SimpleNamespace(
        id=1,
        status="DRAFT",
        total_sks=6
    )

    mk = SimpleNamespace(
        id=10,
        kode_mk="IF101",
        nama_mk="Algoritma",
        sks=3
    )

    detail = SimpleNamespace(
        krs_id=1,
        matakuliah_id=10
    )

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    db.query.side_effect = [
        make_query(mk),
        make_query(detail)
    ]

    result = manager.remove_course("12345", "IF101")

    assert result["total_sks"] == 3
    assert krs.total_sks == 3

    db.delete.assert_called_once_with(detail)
    db.commit.assert_called_once()
