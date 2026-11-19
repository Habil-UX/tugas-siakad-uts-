
import pytest
from datetime import time
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.models import JadwalKuliah
from app.services.scheduling_service import SchedulingService


# ==========================================
# HELPER
# ==========================================

def make_service():
    db = MagicMock()
    service = SchedulingService(db)
    return service, db


def make_query(first=None, all_data=None, count=0):
    query = MagicMock()
    query.filter.return_value = query
    query.join.return_value = query
    query.with_for_update.return_value = query
    query.first.return_value = first
    query.all.return_value = all_data or []
    query.count.return_value = count
    return query


def valid_data():
    return {
        "matakuliah_id": 1,
        "dosen_id": 1,
        "ruangan_id": 1,
        "hari": "Senin",
        "jam_mulai": "08:00:00",
        "jam_selesai": "10:00:00",
        "tahun_akademik": "2024",
        "semester_akademik": 1
    }


def fake_entities():
    mk = SimpleNamespace(
        id=1,
        nama_mk="Algoritma",
        kode_mk="IF101",
        sks=3
    )

    room = SimpleNamespace(
        id=1,
        is_active=True,
        kapasitas=50
    )

    dosen = SimpleNamespace(
        id=1,
        nama="Dosen A"
    )

    return mk, room, dosen


# ==========================================
# 1. PARSE TIME
# ==========================================

def test_parse_time_object():
    service, _ = make_service()

    result = service._parse_time(time(8, 30))

    assert result == time(8, 30)


def test_parse_time_hms():
    service, _ = make_service()

    result = service._parse_time("08:30:00")

    assert result == time(8, 30)


def test_parse_time_hm():
    service, _ = make_service()

    result = service._parse_time("08:30")

    assert result == time(8, 30)


def test_parse_time_invalid_type():
    service, _ = make_service()

    with pytest.raises(ValueError):
        service._parse_time(12345)


def test_parse_time_invalid_string():
    service, _ = make_service()

    with pytest.raises(ValueError):
        service._parse_time("25:90:90")


# ==========================================
# 2. INVALIDATE KRS
# ==========================================

def test_invalidate_krs_empty():
    service, db = make_service()
    db.query.return_value = make_query(all_data=[])

    result = service._invalidate_krs(1)

    assert result == []


def test_invalidate_krs_non_approved():
    service, db = make_service()

    krs1 = SimpleNamespace(
        status="DRAFT",
        needs_review=False
    )
    krs2 = SimpleNamespace(
        status="SUBMITTED",
        needs_review=False
    )

    db.query.return_value = make_query(
        all_data=[krs1, krs2]
    )

    result = service._invalidate_krs(1)

    assert len(result) == 2
    assert krs1.needs_review is True
    assert krs2.needs_review is True


def test_invalidate_krs_approved_unchanged():
    service, db = make_service()

    approved = SimpleNamespace(
        status="APPROVED",
        needs_review=False
    )

    draft = SimpleNamespace(
        status="DRAFT",
        needs_review=False
    )

    db.query.return_value = make_query(
        all_data=[approved, draft]
    )

    result = service._invalidate_krs(1)

    assert len(result) == 2
    assert approved.needs_review is False
    assert draft.needs_review is True


# ==========================================
# 3. OBSERVER
# ==========================================

def test_trigger_observers_with_students(monkeypatch):
    import app.services.scheduling_service as module

    subject = MagicMock()
    monkeypatch.setattr(
        module,
        "ScheduleSubject",
        lambda: subject
    )

    monkeypatch.setattr(
        module,
        "AdminObserver",
        lambda db: "ADMIN"
    )

    monkeypatch.setattr(
        module,
        "LecturerObserver",
        lambda db, dosen_id: "LECTURER"
    )

    monkeypatch.setattr(
        module,
        "StudentObserver",
        lambda db, nims: ("STUDENT", nims)
    )

    service, db = make_service()

    db.query.return_value = make_query(
        all_data=[
            SimpleNamespace(nim="123"),
            SimpleNamespace(nim="456"),
            SimpleNamespace(nim="123")
        ]
    )

    jadwal = SimpleNamespace(id=10)
    mk = SimpleNamespace(
        id=1,
        nama_mk="Algoritma"
    )

    service._trigger_observers(
        "SCHEDULE_CREATED",
        jadwal,
        mk,
        5
    )

    assert subject.attach.call_count == 3
    subject.notify.assert_called_once()

    args = subject.notify.call_args[0]

    assert args[0] == "SCHEDULE_CREATED"
    assert args[1]["nama_mk"] == "Algoritma"
    assert args[1]["id"] == 10


def test_trigger_observers_without_students(monkeypatch):
    import app.services.scheduling_service as module

    subject = MagicMock()

    monkeypatch.setattr(
        module,
        "ScheduleSubject",
        lambda: subject
    )

    monkeypatch.setattr(
        module,
        "AdminObserver",
        lambda db: "ADMIN"
    )

    monkeypatch.setattr(
        module,
        "LecturerObserver",
        lambda db, dosen_id: "LECTURER"
    )

    service, db = make_service()

    db.query.return_value = make_query(all_data=[])

    jadwal = SimpleNamespace(id=20)
    mk = SimpleNamespace(
        id=2,
        nama_mk="Basis Data"
    )

    service._trigger_observers(
        "SCHEDULE_UPDATED",
        jadwal,
        mk,
        7
    )

    assert subject.attach.call_count == 2
    subject.notify.assert_called_once()


# ==========================================
# 4. VALIDATE SCHEDULE
# ==========================================

def test_validate_schedule_success(monkeypatch):
    import app.services.scheduling_service as module

    mk, room, dosen = fake_entities()

    service, db = make_service()

    db.query.return_value = make_query()
    db.query.return_value.first.side_effect = [
        mk,
        room,
        dosen
    ]

    db.query.return_value.count.return_value = 10
    db.query.return_value.all.return_value = []

    monkeypatch.setattr(
        module,
        "detect_schedule_conflict",
        lambda candidate, existing: []
    )

    candidate, result_mk = service._validate_schedule(
        valid_data()
    )

    assert candidate.hari == "Senin"
    assert candidate.jam_mulai == time(8, 0)
    assert candidate.jam_selesai == time(10, 0)
    assert result_mk == mk


@pytest.mark.parametrize(
    "field",
    [
        "matakuliah_id",
        "dosen_id",
        "ruangan_id",
        "hari",
        "jam_mulai",
        "jam_selesai"
    ]
)
def test_validate_required_field(field):
    service, _ = make_service()

    data = valid_data()
    data[field] = None

    with pytest.raises(HTTPException) as exc:
        service._validate_schedule(data)

    assert exc.value.status_code == 422


def test_validate_missing_field():
    service, _ = make_service()

    data = valid_data()
    del data["hari"]

    with pytest.raises(HTTPException) as exc:
        service._validate_schedule(data)

    assert exc.value.status_code == 422


def test_validate_invalid_time():
    service, _ = make_service()

    data = valid_data()
    data["jam_mulai"] = "waktu-salah"

    with pytest.raises(HTTPException) as exc:
        service._validate_schedule(data)

    assert exc.value.status_code == 422


def test_validate_start_after_end():
    service, _ = make_service()

    data = valid_data()
    data["jam_mulai"] = "11:00"
    data["jam_selesai"] = "09:00"

    with pytest.raises(HTTPException) as exc:
        service._validate_schedule(data)

    assert exc.value.status_code == 422


def test_validate_start_equal_end():
    service, _ = make_service()

    data = valid_data()
    data["jam_mulai"] = "08:00"
    data["jam_selesai"] = "08:00"

    with pytest.raises(HTTPException):
        service._validate_schedule(data)


@pytest.mark.parametrize(
    "missing_index",
    [0, 1, 2]
)
def test_validate_entities_not_found(missing_index):
    service, db = make_service()

    entities = list(fake_entities())
    entities[missing_index] = None

    db.query.return_value = make_query()
    db.query.return_value.first.side_effect = entities

    with pytest.raises(HTTPException) as exc:
        service._validate_schedule(valid_data())

    assert exc.value.status_code == 404


def test_validate_inactive_room():
    service, db = make_service()

    mk, room, dosen = fake_entities()
    room.is_active = False

    db.query.return_value = make_query()
    db.query.return_value.first.side_effect = [
        mk,
        room,
        dosen
    ]

    with pytest.raises(HTTPException) as exc:
        service._validate_schedule(valid_data())

    assert exc.value.status_code == 400


def test_validate_room_capacity_exceeded():
    service, db = make_service()

    mk, room, dosen = fake_entities()

    db.query.return_value = make_query()
    db.query.return_value.first.side_effect = [
        mk,
        room,
        dosen
    ]

    db.query.return_value.count.return_value = 60

    with pytest.raises(HTTPException) as exc:
        service._validate_schedule(valid_data())

    assert exc.value.status_code == 400


def test_validate_schedule_conflict(monkeypatch):
    import app.services.scheduling_service as module

    mk, room, dosen = fake_entities()

    service, db = make_service()

    db.query.return_value = make_query()
    db.query.return_value.first.side_effect = [
        mk,
        room,
        dosen
    ]

    db.query.return_value.count.return_value = 0

    monkeypatch.setattr(
        module,
        "detect_schedule_conflict",
        lambda candidate, existing: [
            {
                "type": "ROOM_CONFLICT",
                "description": "Ruangan bentrok"
            }
        ]
    )

    with pytest.raises(HTTPException) as exc:
        service._validate_schedule(valid_data())

    assert exc.value.status_code == 409


def test_validate_exclude_id(monkeypatch):
    import app.services.scheduling_service as module

    mk, room, dosen = fake_entities()

    service, db = make_service()

    query = make_query()
    db.query.return_value = query
    query.first.side_effect = [mk, room, dosen]
    query.count.return_value = 0

    monkeypatch.setattr(
        module,
        "detect_schedule_conflict",
        lambda candidate, existing: []
    )

    service._validate_schedule(
        valid_data(),
        exclude_id=10
    )

    # Filter tambahan untuk mengecualikan jadwal sendiri.
    assert query.filter.call_count >= 2


# ==========================================
# 5. CREATE SCHEDULE
# ==========================================

def test_create_schedule_success(monkeypatch):
    service, db = make_service()

    candidate = SimpleNamespace(
        id=10,
        dosen_id=1
    )
    mk = SimpleNamespace(nama_mk="Algoritma")

    service._validate_schedule = MagicMock(
        return_value=(candidate, mk)
    )
    service._trigger_observers = MagicMock()

    result = service.create_schedule(valid_data())

    assert result == candidate
    db.add.assert_called()
    db.flush.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(candidate)

    service._trigger_observers.assert_called_once()


def test_create_schedule_rollback(monkeypatch):
    service, db = make_service()

    candidate = SimpleNamespace(
        id=10,
        dosen_id=1
    )
    mk = SimpleNamespace(nama_mk="Algoritma")

    service._validate_schedule = MagicMock(
        return_value=(candidate, mk)
    )

    db.add.side_effect = RuntimeError("Database error")

    with pytest.raises(RuntimeError):
        service.create_schedule(valid_data())

    db.rollback.assert_called_once()


# ==========================================
# 6. UPDATE SCHEDULE
# ==========================================

def make_existing_schedule():
    return SimpleNamespace(
        id=10,
        matakuliah_id=1,
        dosen_id=1,
        ruangan_id=1,
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
        tahun_akademik="2024",
        semester_akademik=1,
        status="ACTIVE"
    )


def test_update_schedule_not_found():
    service, db = make_service()

    db.query.return_value = make_query(None)

    with pytest.raises(HTTPException) as exc:
        service.update_schedule(10, {})

    assert exc.value.status_code == 404


def test_update_schedule_success_same_course():
    service, db = make_service()

    jadwal = make_existing_schedule()
    candidate = make_existing_schedule()
    mk = SimpleNamespace(id=1)

    db.query.return_value = make_query(jadwal)

    service._validate_schedule = MagicMock(
        return_value=(candidate, mk)
    )

    service._invalidate_krs = MagicMock()
    service._trigger_observers = MagicMock()

    result = service.update_schedule(
        10,
        {"hari": "Selasa"}
    )

    assert result == jadwal
    assert jadwal.hari == "Selasa"

    service._invalidate_krs.assert_called_once_with(1)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(jadwal)
    service._trigger_observers.assert_called_once()


def test_update_schedule_course_changed():
    service, db = make_service()

    jadwal = make_existing_schedule()
    candidate = make_existing_schedule()
    mk = SimpleNamespace(id=2)

    db.query.return_value = make_query(jadwal)

    service._validate_schedule = MagicMock(
        return_value=(candidate, mk)
    )

    service._invalidate_krs = MagicMock()
    service._trigger_observers = MagicMock()

    service.update_schedule(
        10,
        {"matakuliah_id": 2}
    )

    assert jadwal.matakuliah_id == 2

    assert service._invalidate_krs.call_count == 2
    service._invalidate_krs.assert_any_call(1)
    service._invalidate_krs.assert_any_call(2)


def test_update_schedule_rollback():
    service, db = make_service()

    jadwal = make_existing_schedule()
    candidate = make_existing_schedule()
    mk = SimpleNamespace(id=1)

    db.query.return_value = make_query(jadwal)

    service._validate_schedule = MagicMock(
        return_value=(candidate, mk)
    )

    service._invalidate_krs = MagicMock()

    db.commit.side_effect = RuntimeError("Commit gagal")

    with pytest.raises(RuntimeError):
        service.update_schedule(
            10,
            {"hari": "Selasa"}
        )

    db.rollback.assert_called_once()


# ==========================================
# 7. DELETE SCHEDULE
# ==========================================

def test_delete_schedule_not_found():
    service, db = make_service()

    db.query.return_value = make_query(None)

    with pytest.raises(HTTPException) as exc:
        service.delete_schedule(10)

    assert exc.value.status_code == 404


def test_delete_schedule_success_with_course():
    service, db = make_service()

    jadwal = make_existing_schedule()
    mk = SimpleNamespace(
        id=1,
        nama_mk="Algoritma"
    )

    db.query.side_effect = [
        make_query(jadwal),
        make_query(mk)
    ]

    service._invalidate_krs = MagicMock()
    service._trigger_observers = MagicMock()

    result = service.delete_schedule(10)

    assert result["id"] == 10
    assert result["message"] == "Jadwal berhasil dihapus"

    service._invalidate_krs.assert_called_once_with(1)
    db.delete.assert_called_once_with(jadwal)
    db.commit.assert_called_once()
    service._trigger_observers.assert_called_once()


def test_delete_schedule_without_course():
    service, db = make_service()

    jadwal = make_existing_schedule()

    db.query.side_effect = [
        make_query(jadwal),
        make_query(None)
    ]

    service._invalidate_krs = MagicMock()
    service._trigger_observers = MagicMock()

    result = service.delete_schedule(10)

    assert result["id"] == 10

    service._trigger_observers.assert_not_called()
    db.delete.assert_called_once_with(jadwal)


def test_delete_schedule_rollback():
    service, db = make_service()

    jadwal = make_existing_schedule()
    mk = SimpleNamespace(id=1)

    db.query.side_effect = [
        make_query(jadwal),
        make_query(mk)
    ]

    service._invalidate_krs = MagicMock()

    db.commit.side_effect = RuntimeError("Commit gagal")

    with pytest.raises(RuntimeError):
        service.delete_schedule(10)

    db.rollback.assert_called_once()
