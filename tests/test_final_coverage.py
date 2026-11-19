from app.services.krs_recommender import KRSRecommender
from app.models import SkalaNilai, Prerequisite, RiwayatNilai, CalonMahasiswa, Matakuliah
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services import rescheduling_service as rs_module
from app.services.rescheduling_service import ReschedulingService
from app.services.pmb_service import (
    reject_calon_mahasiswa,
)
from app.models import StatusPendaftaran


# =====================================================
# RESCHEDULING SERVICE TESTS
# =====================================================

def make_rescheduling_db(jadwal, rooms, jumlah=10, existing=None):
    db = MagicMock()

    q_jadwal = MagicMock()
    q_jadwal.filter.return_value = q_jadwal
    q_jadwal.first.return_value = jadwal

    q_krs = MagicMock()
    q_krs.filter.return_value = q_krs
    q_krs.count.return_value = jumlah

    q_rooms = MagicMock()
    q_rooms.filter.return_value = q_rooms
    q_rooms.all.return_value = rooms

    q_existing = MagicMock()
    q_existing.filter.return_value = q_existing
    q_existing.all.return_value = existing or []

    db.query.side_effect = [
        q_jadwal,
        q_krs,
        q_rooms,
        q_existing
    ]

    return db


def make_jadwal():
    return SimpleNamespace(
        id=1,
        matakuliah_id=10,
        dosen_id=20,
        hari="Senin",
        tahun_akademik="2024/2025",
        semester_akademik=1
    )


def make_room():
    return SimpleNamespace(
        id=1,
        kode_ruangan="R01",
        kapasitas=40
    )


def test_rescheduling_returns_empty_when_no_jadwal():
    db = MagicMock()

    query = MagicMock()
    query.filter.return_value = query
    query.first.return_value = None
    db.query.return_value = query

    service = ReschedulingService(db, MagicMock())

    result = service.suggest_alternatives(999)

    assert result == []


def test_rescheduling_skips_conflicting_candidates(monkeypatch):
    jadwal = make_jadwal()
    room = make_room()

    db = make_rescheduling_db(jadwal, [room])

    monkeypatch.setattr(
        rs_module,
        "detect_schedule_conflict",
        lambda candidate, existing: [
            {"type": "ROOM_CONFLICT"}
        ]
    )

    service = ReschedulingService(db, MagicMock())

    result = service.suggest_alternatives(1)

    assert result == []


def test_rescheduling_skips_duplicate_identity(monkeypatch):
    jadwal = make_jadwal()
    room = make_room()

    db = make_rescheduling_db(jadwal, [room])

    monkeypatch.setattr(
        rs_module,
        "detect_schedule_conflict",
        lambda candidate, existing: []
    )

    # Slot sengaja dibuat sama untuk menguji identitas duplikat.
    monkeypatch.setattr(
        ReschedulingService,
        "DEFAULT_TIME_SLOTS",
        [
            (rs_module.time(8, 0), rs_module.time(10, 0)),
            (rs_module.time(8, 0), rs_module.time(10, 0)),
        ]
    )

    service = ReschedulingService(db, MagicMock())

    result = service.suggest_alternatives(1)

    assert len(result) == 1
    assert result[0]["ruangan"] == "R01"



def test_rescheduling_returns_suggestions_after_all_slots(monkeypatch):
    jadwal = make_jadwal()
    room = make_room()

    db = make_rescheduling_db(jadwal, [room])

    monkeypatch.setattr(
        rs_module,
        "detect_schedule_conflict",
        lambda candidate, existing: []
    )

    # Hanya dua slot agar tidak mencapai batas return 3.
    monkeypatch.setattr(
        ReschedulingService,
        "DEFAULT_TIME_SLOTS",
        [
            (rs_module.time(8, 0), rs_module.time(10, 0)),
            (rs_module.time(10, 0), rs_module.time(12, 0)),
        ]
    )

    service = ReschedulingService(db, MagicMock())

    result = service.suggest_alternatives(1)

    assert len(result) == 2
    assert result[-1]["jam_selesai"] == "12:00"



# =====================================================
# PMB SERVICE TESTS
# =====================================================

def test_reject_calon_mahasiswa_already_rejected():
    mahasiswa = SimpleNamespace(
        id=1,
        status=StatusPendaftaran.rejected
    )

    db = MagicMock()

    query = MagicMock()
    query.filter.return_value = query
    query.with_for_update.return_value = query
    query.first.return_value = mahasiswa

    db.query.return_value = query

    result = reject_calon_mahasiswa(db, 1)

    assert result is mahasiswa
    db.commit.assert_not_called()
    db.refresh.assert_not_called()


from app.observers.schedule_subject import Observer
from app.services.krs.validators import Validator
from app.services.conflict_detector import detect_schedule_conflict
from types import SimpleNamespace
from datetime import time


def test_observer_abstract_method_body():
    result = Observer.update(object(), "TEST_EVENT", {})
    assert result is None


def test_validator_abstract_method_body():
    result = Validator._validate(object(), {})
    assert result is None


def test_conflict_detector_skips_different_day():
    new = SimpleNamespace(
        id=2,
        hari="Selasa",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
        ruangan_id=1,
        dosen_id=1
    )

    existing = SimpleNamespace(
        id=1,
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
        ruangan_id=1,
        dosen_id=1
    )

    assert detect_schedule_conflict(new, [existing]) == []


def test_conflict_detector_skips_existing_without_time():
    new = SimpleNamespace(
        id=2,
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
        ruangan_id=1,
        dosen_id=1
    )

    existing = SimpleNamespace(
        id=1,
        hari="Senin",
        jam_mulai=None,
        jam_selesai=None,
        ruangan_id=1,
        dosen_id=1
    )

    assert detect_schedule_conflict(new, [existing]) == []


def test_recommender_prerequisite_not_passed():
    db = MagicMock()

    q1 = MagicMock()
    q1.filter.return_value = q1
    q1.scalar.return_value = 2.0

    q2 = MagicMock()
    q2.filter.return_value = q2
    q2.all.return_value = [
        SimpleNamespace(prerequisite_id=10)
    ]

    q3 = MagicMock()
    q3.join.return_value = q3
    q3.filter.return_value = q3
    q3.first.return_value = None

    db.query.side_effect = [q1, q2, q3]

    recommender = KRSRecommender(db)

    result = recommender._check_prerequisite("12345", 20)

    assert result is False


def test_recommender_without_prerequisites():
    db = MagicMock()

    q1 = MagicMock()
    q1.filter.return_value = q1
    q1.scalar.return_value = 2.0

    q2 = MagicMock()
    q2.filter.return_value = q2
    q2.all.return_value = []

    db.query.side_effect = [q1, q2]

    recommender = KRSRecommender(db)

    result = recommender._check_prerequisite("12345", 20)

    assert result is True


def test_recommender_prerequisite_passed():
    db = MagicMock()

    q1 = MagicMock()
    q1.filter.return_value = q1
    q1.scalar.return_value = 2.0

    q2 = MagicMock()
    q2.filter.return_value = q2
    q2.all.return_value = [
        SimpleNamespace(prerequisite_id=10)
    ]

    q3 = MagicMock()
    q3.join.return_value = q3
    q3.filter.return_value = q3
    q3.first.return_value = SimpleNamespace(id=1)

    db.query.side_effect = [q1, q2, q3]

    recommender = KRSRecommender(db)

    result = recommender._check_prerequisite("12345", 20)

    assert result is True


def test_recommender_records_unfulfilled_prerequisite():
    db = MagicMock()

    mahasiswa_query = MagicMock()
    mahasiswa_query.filter.return_value = mahasiswa_query
    mahasiswa_query.first.return_value = SimpleNamespace(
        nim="12345"
    )

    mk = SimpleNamespace(
        id=20,
        kode_mk="MK001",
        nama_mk="Algoritma",
        jenis_mk="Wajib",
        sks=3,
        hari="Senin",
        jam_mulai=rs_module.time(8, 0),
        jam_selesai=rs_module.time(10, 0)
    )

    mk_query = MagicMock()
    mk_query.all.return_value = [mk]

    db.query.side_effect = [
        mahasiswa_query,
        mk_query
    ]

    recommender = KRSRecommender(db)

    recommender._check_prerequisite = MagicMock(return_value=False)

    result = recommender.generate_recommendation("12345")

    assert result.alasan_tidak_terpilih["MK001"] == (
        "Prasyarat belum terpenuhi"
    )

