
import pytest

from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.services.grade_service import GradeService


def make_query(result):
    query = MagicMock()
    query.filter.return_value = query
    query.with_for_update.return_value = query
    query.first.return_value = result
    return query


# ==========================================
# TEST 1: SKALA NILAI LAMA TIDAK DITEMUKAN
# ==========================================

def test_update_grade_old_scale_not_found():

    db = MagicMock()
    service = GradeService(db)

    grade = SimpleNamespace(
        id=1,
        skala_nilai_id=10,
        version=1
    )

    new_scale = SimpleNamespace(
        id=20,
        nilai_huruf="A",
        bobot=4.0
    )

    db.query.side_effect = [
        make_query(grade),
        make_query(new_scale),
        make_query(None)
    ]

    with pytest.raises(HTTPException) as exc:

        service.update_grade(
            grade_id=1,
            nilai_huruf="A",
            changed_by="admin",
            reason="Koreksi nilai mahasiswa"
        )

    assert exc.value.status_code == 500
    assert exc.value.detail == "Skala nilai lama tidak ditemukan"


# ==========================================
# TEST 2: UPDATE GRADE DATABASE FAILURE
# ==========================================

def test_update_grade_database_failure():

    db = MagicMock()
    service = GradeService(db)

    grade = SimpleNamespace(
        id=1,
        skala_nilai_id=10,
        version=1,
        updated_at=None
    )

    new_scale = SimpleNamespace(
        id=20,
        nilai_huruf="A",
        bobot=4.0
    )

    old_scale = SimpleNamespace(
        id=10,
        nilai_huruf="B",
        bobot=3.0
    )

    db.query.side_effect = [
        make_query(grade),
        make_query(new_scale),
        make_query(old_scale)
    ]

    db.execute.side_effect = RuntimeError(
        "Database update failed"
    )

    with pytest.raises(RuntimeError):

        service.update_grade(
            grade_id=1,
            nilai_huruf="A",
            changed_by="admin",
            reason="Koreksi nilai mahasiswa"
        )

    db.rollback.assert_called_once()
