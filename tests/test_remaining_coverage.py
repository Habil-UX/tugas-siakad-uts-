
import pytest
from datetime import time
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.conflict_detector import detect_schedule_conflict
from app.observers.schedule_subject import ScheduleSubject
from app.services.krs.validators import (
    ValidationResult,
    SKSValidator,
    ConflictValidator,
    DuplicateValidator,
    PrerequisiteValidator,
    build_chain,
)


# ==========================================
# 1. CONFLICT DETECTOR
# ==========================================

def make_schedule(
    id=1,
    hari="Senin",
    start=time(8),
    end=time(10),
    room=1,
    dosen=1
):
    return SimpleNamespace(
        id=id,
        hari=hari,
        jam_mulai=start,
        jam_selesai=end,
        ruangan_id=room,
        dosen_id=dosen
    )


def test_conflict_new_schedule_none():
    assert detect_schedule_conflict(None, []) == []


@pytest.mark.parametrize("start,end", [
    (None, time(10)),
    (time(8), None),
    (time(10), time(8)),
    (time(8), time(8)),
])
def test_conflict_invalid_time(start, end):
    new = make_schedule(start=start, end=end)
    assert detect_schedule_conflict(new, []) == []


def test_conflict_existing_none():
    new = make_schedule()
    assert detect_schedule_conflict(new, [None]) == []


def test_conflict_same_schedule_id():
    new = make_schedule(id=1)
    old = make_schedule(id=1)
    assert detect_schedule_conflict(new, [old]) == []


def test_conflict_different_day():
    new = make_schedule()
    old = make_schedule(hari="Selasa")
    assert detect_schedule_conflict(new, [old]) == []


def test_conflict_existing_invalid_time():
    new = make_schedule()
    old = make_schedule(start=None)
    assert detect_schedule_conflict(new, [old]) == []


def test_conflict_room_and_lecturer():
    new = make_schedule(room=1, dosen=1)
    old = make_schedule(id=2, room=1, dosen=1)

    result = detect_schedule_conflict(new, [old])

    assert len(result) == 2
    assert {x["type"] for x in result} == {
        "ROOM_CONFLICT",
        "LECTURER_CONFLICT"
    }


def test_conflict_room_only():
    new = make_schedule(room=1, dosen=1)
    old = make_schedule(id=2, room=1, dosen=2)

    result = detect_schedule_conflict(new, [old])

    assert len(result) == 1
    assert result[0]["type"] == "ROOM_CONFLICT"


def test_conflict_lecturer_only():
    new = make_schedule(room=1, dosen=1)
    old = make_schedule(id=2, room=2, dosen=1)

    result = detect_schedule_conflict(new, [old])

    assert len(result) == 1
    assert result[0]["type"] == "LECTURER_CONFLICT"


def test_conflict_empty_existing():
    assert detect_schedule_conflict(make_schedule(), None) == []


# ==========================================
# 2. SCHEDULE SUBJECT
# ==========================================

class FakeObserver:
    def __init__(self):
        self.events = []

    def update(self, event_type, data):
        self.events.append((event_type, data))


class FailingObserver:
    def update(self, event_type, data):
        raise RuntimeError("Observer gagal")


def test_subject_attach_and_notify():
    subject = ScheduleSubject()
    observer = FakeObserver()

    subject.attach(observer)
    subject.notify("CREATED", {"id": 1})

    assert len(observer.events) == 1
    assert observer.events[0][0] == "CREATED"


def test_subject_duplicate_attach():
    subject = ScheduleSubject()
    observer = FakeObserver()

    subject.attach(observer)
    subject.attach(observer)

    assert len(subject._observers) == 1


def test_subject_detach():
    subject = ScheduleSubject()
    observer = FakeObserver()

    subject.attach(observer)
    subject.detach(observer)

    assert observer not in subject._observers


def test_subject_detach_missing_observer():
    subject = ScheduleSubject()

    with pytest.raises(ValueError):
        subject.detach(FakeObserver())


def test_subject_observer_failure_does_not_stop_others():
    subject = ScheduleSubject()
    failing = FailingObserver()
    working = FakeObserver()

    subject.attach(failing)
    subject.attach(working)

    subject.notify("UPDATED", {"id": 10})

    assert len(working.events) == 1


# ==========================================
# 3. VALIDATORS
# ==========================================

def test_sks_validator_success():
    validator = SKSValidator()

    context = {
        "db": MagicMock(),
        "krs": SimpleNamespace(details=[]),
        "new_mk": SimpleNamespace(sks=3)
    }

    result = validator._validate(context)

    assert result.is_valid is True


def test_sks_validator_exceeded():
    validator = SKSValidator()

    details = [
        SimpleNamespace(
            matakuliah=SimpleNamespace(sks=24)
        )
    ]

    context = {
        "db": MagicMock(),
        "krs": SimpleNamespace(details=details),
        "new_mk": SimpleNamespace(sks=3)
    }

    result = validator._validate(context)

    assert result.is_valid is False
    assert result.validator_name == "SKSValidator"


def test_conflict_validator_success():
    validator = ConflictValidator()

    context = {
        "krs": SimpleNamespace(details=[]),
        "new_mk": SimpleNamespace(
            hari="Selasa",
            jam_mulai=time(8),
            jam_selesai=time(10)
        )
    }

    assert validator._validate(context).is_valid is True


def test_conflict_validator_different_day():
    validator = ConflictValidator()

    existing = SimpleNamespace(
        hari="Senin",
        jam_mulai=time(8),
        jam_selesai=time(10),
        nama_mk="Algoritma"
    )

    new = SimpleNamespace(
        hari="Selasa",
        jam_mulai=time(9),
        jam_selesai=time(11)
    )

    result = validator._validate({
        "krs": SimpleNamespace(
            details=[SimpleNamespace(matakuliah=existing)]
        ),
        "new_mk": new
    })

    assert result.is_valid is True


def test_conflict_validator_detected():
    validator = ConflictValidator()

    existing = SimpleNamespace(
        hari="Senin",
        jam_mulai=time(8),
        jam_selesai=time(10),
        nama_mk="Algoritma"
    )

    new = SimpleNamespace(
        hari="Senin",
        jam_mulai=time(9),
        jam_selesai=time(11)
    )

    result = validator._validate({
        "krs": SimpleNamespace(
            details=[SimpleNamespace(matakuliah=existing)]
        ),
        "new_mk": new
    })

    assert result.is_valid is False
    assert "Algoritma" in result.message


def test_duplicate_validator_success():
    validator = DuplicateValidator()

    result = validator._validate({
        "krs": SimpleNamespace(details=[]),
        "new_mk": SimpleNamespace(id=10, nama_mk="Algoritma")
    })

    assert result.is_valid is True


def test_duplicate_validator_detected():
    validator = DuplicateValidator()

    detail = SimpleNamespace(matakuliah_id=10)

    result = validator._validate({
        "krs": SimpleNamespace(details=[detail]),
        "new_mk": SimpleNamespace(id=10, nama_mk="Algoritma")
    })

    assert result.is_valid is False
    assert result.validator_name == "DuplicateValidator"


def test_validator_chain_stops_on_failure():
    chain = build_chain()

    context = {
        "db": MagicMock(),
        "nim": "12345",
        "krs": SimpleNamespace(
            details=[
                SimpleNamespace(
                    matakuliah=SimpleNamespace(sks=24)
                )
            ]
        ),
        "new_mk": SimpleNamespace(
            id=1,
            sks=3,
            nama_mk="Algoritma"
        )
    }

    result = chain.validate(context)

    assert result.is_valid is False
    assert result.validator_name == "SKSValidator"


def test_validation_result_defaults():
    result = ValidationResult(is_valid=True)

    assert result.message == ""
    assert result.validator_name == ""
    assert result.detail is None


# ==========================================
# 4. PREREQUISITE VALIDATOR
# ==========================================

def test_prerequisite_validator_no_missing_prerequisite():
    validator = PrerequisiteValidator()

    db = MagicMock()
    db.query.return_value.filter.return_value.scalar.return_value = 2.0
    db.execute.return_value.all.return_value = []

    result = validator._validate({
        "db": db,
        "nim": "12345",
        "new_mk": SimpleNamespace(id=10)
    })

    assert result.is_valid is True


def test_prerequisite_validator_missing_prerequisite():
    validator = PrerequisiteValidator()

    db = MagicMock()
    db.query.return_value.filter.return_value.scalar.return_value = 2.0
    db.execute.return_value.all.return_value = [
        ("Matematika Dasar",),
        ("Algoritma",)
    ]

    result = validator._validate({
        "db": db,
        "nim": "12345",
        "new_mk": SimpleNamespace(id=10)
    })

    assert result.is_valid is False
    assert result.validator_name == "PrerequisiteValidator"
    assert len(result.detail["missing"]) == 2
