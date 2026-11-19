import pytest
from datetime import time
from fastapi import HTTPException
from app.models import Matakuliah, Dosen, Ruangan, JadwalKuliah
from app.services.scheduling_service import SchedulingService

def test_create_schedule_success(db_session):
    # Setup data
    mk = Matakuliah(kode_mk="MK01", nama_mk="Test", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    dosen = Dosen(nidn="111", nama="Dosen A")
    ruangan = Ruangan(kode_ruangan="R01", nama_ruangan="Ruang 1", kapasitas=50)
    db_session.add_all([mk, dosen, ruangan])
    db_session.commit()

    service = SchedulingService(db_session)
    data = {
        "matakuliah_id": mk.id,
        "dosen_id": dosen.id,
        "ruangan_id": ruangan.id,
        "hari": "Rabu",
        "jam_mulai": "08:00:00",
        "jam_selesai": "10:00:00",
        "tahun_akademik": "2024",
        "semester_akademik": 1
    }
    
    jadwal = service.create_schedule(data)
    assert jadwal.id is not None
    assert jadwal.hari == "Rabu"

def test_create_schedule_room_conflict(db_session):
    mk = Matakuliah(kode_mk="MK02", nama_mk="Test", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    d1 = Dosen(nidn="222", nama="Dosen B")
    d2 = Dosen(nidn="333", nama="Dosen C")
    r1 = Ruangan(kode_ruangan="R02", nama_ruangan="Ruang 2", kapasitas=50)
    db_session.add_all([mk, d1, d2, r1])
    db_session.commit()

    service = SchedulingService(db_session)
    
    # Jadwal 1
    service.create_schedule({
        "matakuliah_id": mk.id, "dosen_id": d1.id, "ruangan_id": r1.id,
        "hari": "Kamis", "jam_mulai": "08:00:00", "jam_selesai": "10:00:00",
        "tahun_akademik": "2024", "semester_akademik": 1
    })

    # Jadwal 2 (Bentrok Ruangan & Waktu)
    with pytest.raises(HTTPException) as excinfo:
        service.create_schedule({
            "matakuliah_id": mk.id, "dosen_id": d2.id, "ruangan_id": r1.id, # Ruangan sama
            "hari": "Kamis", "jam_mulai": "09:00:00", "jam_selesai": "11:00:00", # Overlap
            "tahun_akademik": "2024", "semester_akademik": 1
        })
    assert excinfo.value.status_code == 409
    assert "Konflik terdeteksi" in excinfo.value.detail["message"]