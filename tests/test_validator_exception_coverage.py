
from datetime import time
from types import SimpleNamespace

from app.services.krs.validators import ConflictValidator


def test_conflict_validator_skips_incomplete_schedule():

    validator = ConflictValidator()

    existing_mk = SimpleNamespace(
        id=1,
        nama_mk="Pemrograman",
        hari="Senin",
        jam_mulai=None,
        jam_selesai=time(10, 0)
    )

    new_mk = SimpleNamespace(
        id=2,
        nama_mk="Basis Data",
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0)
    )

    existing_detail = SimpleNamespace(
        matakuliah=existing_mk
    )

    krs = SimpleNamespace(
        details=[existing_detail]
    )

    result = validator._validate({
        "krs": krs,
        "new_mk": new_mk
    })

    assert result.is_valid is True
    assert result.validator_name == ""
