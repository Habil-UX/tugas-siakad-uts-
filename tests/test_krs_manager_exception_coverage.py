
import pytest

from unittest.mock import MagicMock
from types import SimpleNamespace

from app.services.krs_manager import KRSManager


# ==========================================
# HELPER
# ==========================================

def make_manager():
    db = MagicMock()
    manager = KRSManager(db)
    return manager, db


def make_query_result(result):
    query = MagicMock()
    query.filter.return_value = query
    query.with_for_update.return_value = query
    query.first.return_value = result
    return query


# ==========================================
# TEST 1: CREATE KRS DATABASE FAILURE
# ==========================================

def test_get_or_create_krs_commit_failure():

    manager, db = make_manager()

    manager._get_mahasiswa = MagicMock(
        return_value=SimpleNamespace(nim="12345")
    )

    db.query.return_value = make_query_result(None)

    db.commit.side_effect = RuntimeError(
        "Database commit failed"
    )

    with pytest.raises(RuntimeError):
        manager._get_or_create_krs(
            "12345",
            semester=2,
            tahun="2025/2026"
        )

    db.rollback.assert_called_once()


# ==========================================
# TEST 2: SUBMIT KRS DATABASE FAILURE
# ==========================================

def test_submit_krs_commit_failure():

    manager, db = make_manager()

    krs = SimpleNamespace(
        id=1,
        status="DRAFT",
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

    db.commit.side_effect = RuntimeError(
        "Submit commit failed"
    )

    with pytest.raises(RuntimeError):
        manager.submit_krs("12345")

    db.rollback.assert_called_once()

    assert krs.status == "SUBMITTED"



# ==========================================
# TEST 3: APPROVE KRS DATABASE FAILURE
# ==========================================

def test_approve_krs_commit_failure():

    manager, db = make_manager()

    nidn = "198501012010011001"

    krs = SimpleNamespace(
        id=1,
        status="SUBMITTED",
        version=1
    )

    db.query.return_value = make_query_result(krs)

    manager._get_authorized_dosen = MagicMock(
        return_value=SimpleNamespace(nidn=nidn)
    )

    manager._log_transition = MagicMock()

    db.commit.side_effect = RuntimeError(
        "Approve commit failed"
    )

    with pytest.raises(RuntimeError):
        manager.approve_krs(
            "12345",
            nidn
        )

    db.rollback.assert_called_once()

    assert krs.status == "APPROVED"
    assert krs.version == 2


# ==========================================
# TEST 4: REVISE KRS DATABASE FAILURE
# ==========================================

def test_revise_krs_commit_failure():

    manager, db = make_manager()

    nidn = "198501012010011001"

    krs = SimpleNamespace(
        id=1,
        status="SUBMITTED",
        version=1
    )

    db.query.return_value = make_query_result(krs)

    manager._get_authorized_dosen = MagicMock(
        return_value=SimpleNamespace(nidn=nidn)
    )

    manager._log_transition = MagicMock()

    db.commit.side_effect = RuntimeError(
        "Revise commit failed"
    )

    with pytest.raises(RuntimeError):
        manager.revise_krs(
            "12345",
            nidn
        )

    db.rollback.assert_called_once()

    assert krs.status == "REVISION"
    assert krs.version == 2



# ==========================================
# TEST 5: ADD COURSE DATABASE FAILURE
# ==========================================

def test_add_course_commit_failure():

    manager, db = make_manager()

    krs = SimpleNamespace(
        id=1,
        status="DRAFT",
        version=1,
        total_sks=0,
        details=[]
    )

    mk = SimpleNamespace(
        id=10,
        kode_mk="IF101",
        nama_mk="Pemrograman",
        sks=3
    )

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    manager.validator_chain.validate = MagicMock(
        return_value=SimpleNamespace(
            is_valid=True,
            message=""
        )
    )

    db.query.return_value = make_query_result(mk)

    db.commit.side_effect = RuntimeError(
        "Add course commit failed"
    )

    with pytest.raises(RuntimeError):
        manager.add_course(
            "12345",
            "IF101"
        )

    db.rollback.assert_called_once()

    assert krs.total_sks == 3


# ==========================================
# TEST 6: REMOVE COURSE DATABASE FAILURE
# ==========================================

def test_remove_course_commit_failure():

    manager, db = make_manager()

    krs = SimpleNamespace(
        id=1,
        status="DRAFT",
        version=1,
        total_sks=3
    )

    mk = SimpleNamespace(
        id=10,
        kode_mk="IF101",
        nama_mk="Pemrograman",
        sks=3
    )

    detail = SimpleNamespace(
        id=100,
        krs_id=1,
        matakuliah_id=10
    )

    manager._get_or_create_krs = MagicMock(
        return_value=krs
    )

    query_mk = make_query_result(mk)
    query_detail = make_query_result(detail)

    db.query.side_effect = [
        query_mk,
        query_detail
    ]

    db.commit.side_effect = RuntimeError(
        "Remove course commit failed"
    )

    with pytest.raises(RuntimeError):
        manager.remove_course(
            "12345",
            "IF101"
        )

    db.rollback.assert_called_once()

    assert krs.total_sks == 0
