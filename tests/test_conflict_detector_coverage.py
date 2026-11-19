
from datetime import time
from types import SimpleNamespace

from app.services.conflict_detector import detect_schedule_conflict


# ==========================================
# HELPER
# ==========================================

def make_schedule(**overrides):
    data = {
        "id": 1,
        "hari": "Senin",
        "jam_mulai": time(8, 0),
        "jam_selesai": time(10, 0),
        "ruangan_id": 1,
        "dosen_id": 1,
        "status": "AKTIF",
        "tahun_akademik": "2026/2027",
        "semester_akademik": 1,
    }

    data.update(overrides)

    return SimpleNamespace(**data)


# ==========================================
# TEST 1: INACTIVE SCHEDULE
# Coverage line 38
# ==========================================

def test_ignore_inactive_schedule():

    new_jadwal = make_schedule(id=1)

    existing = make_schedule(
        id=2,
        status="DIBATALKAN"
    )

    result = detect_schedule_conflict(
        new_jadwal,
        [existing]
    )

    assert result == []


# ==========================================
# TEST 2: DIFFERENT ACADEMIC YEAR
# Coverage line 45
# ==========================================

def test_ignore_different_academic_year():

    new_jadwal = make_schedule(id=1)

    existing = make_schedule(
        id=2,
        tahun_akademik="2025/2026"
    )

    result = detect_schedule_conflict(
        new_jadwal,
        [existing]
    )

    assert result == []


# ==========================================
# TEST 3: DIFFERENT ACADEMIC SEMESTER
# Coverage line 51
# ==========================================

def test_ignore_different_academic_semester():

    new_jadwal = make_schedule(id=1)

    existing = make_schedule(
        id=2,
        semester_akademik=2
    )

    result = detect_schedule_conflict(
        new_jadwal,
        [existing]
    )

    assert result == []
