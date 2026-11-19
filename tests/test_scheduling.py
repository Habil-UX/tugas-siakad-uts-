import pytest
from datetime import time
from app.models import JadwalKuliah, Ruangan, Dosen, Matakuliah
from app.services.conflict_detector import detect_schedule_conflict

def test_room_conflict():
    # Setup jadwal existing
    j1 = JadwalKuliah(id=1, hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0), ruangan_id=1, dosen_id=1)
    
    # New jadwal bentrok di ruangan yang sama
    j2 = JadwalKuliah(id=2, hari="Senin", jam_mulai=time(9,0), jam_selesai=time(11,0), ruangan_id=1, dosen_id=2)
    
    conflicts = detect_schedule_conflict(j2, [j1])
    assert len(conflicts) == 1
    assert conflicts[0]["type"] == "ROOM_CONFLICT"

def test_no_conflict_adjacent_time():
    j1 = JadwalKuliah(id=1, hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0), ruangan_id=1, dosen_id=1)
    # Jadwal tepat setelahnya (10:00 - 12:00) tidak boleh dianggap bentrok
    j2 = JadwalKuliah(id=2, hari="Senin", jam_mulai=time(10,0), jam_selesai=time(12,0), ruangan_id=1, dosen_id=1)
    
    conflicts = detect_schedule_conflict(j2, [j1])
    assert len(conflicts) == 0