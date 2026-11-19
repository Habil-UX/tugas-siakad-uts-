import pytest
from datetime import time, date
from fastapi import HTTPException
from unittest.mock import patch
from app.models import (
    CalonMahasiswa, Matakuliah, KRS, KRSDetail, StatusPendaftaran, 
    Dosen, Ruangan, JadwalKuliah
)
from app.services.krs_manager import KRSManager
from app.services.scheduling_service import SchedulingService
from app.services.conflict_detector import detect_schedule_conflict
from app.services.rescheduling_service import ReschedulingService
from app.observers.schedule_subject import ScheduleSubject, Observer
from app.services.krs.validators import PrerequisiteValidator

# ==========================================
# 1. KRS MANAGER (State Machine & Errors)
# ==========================================

def test_krs_manager_exhaustive(db_session):
    # ==========================================
    # SETUP DATA
    # ==========================================

    mhs = CalonMahasiswa(
        nama_lengkap="A",
        email="a@ex.com",
        phone="081234567890",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Jl",
        program_studi_id=1,
        jalur_masuk_id=1,
        status=StatusPendaftaran.approved,
        nim="EX1"
    )

    mk1 = Matakuliah(
        kode_mk="MK_A",
        nama_mk="A",
        sks=3,
        semester=1,
        jenis_mk="Wajib",
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0)
    )

    mk2 = Matakuliah(
        kode_mk="MK_B",
        nama_mk="B",
        sks=22,
        semester=1,
        jenis_mk="Wajib",
        hari="Selasa",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0)
    )

    # Membuat Dosen PA
    dosen = Dosen(
        nidn="DSN_01",
        nama="Dosen PA"
    )

    db_session.add_all([
        mhs,
        mk1,
        mk2,
        dosen
    ])

    db_session.commit()

    # Menetapkan Dosen PA kepada mahasiswa
    mhs.dosen_pa_id = dosen.id
    db_session.commit()

    manager = KRSManager(db_session)

    # ==========================================
    # TEST 1: NIM TIDAK DITEMUKAN
    # ==========================================

    with pytest.raises(HTTPException) as exc:
        manager.submit_krs("INVALID")

    assert exc.value.status_code == 404

    # ==========================================
    # TEST 2: ADD COURSE
    # ==========================================

    manager.add_course("EX1", "MK_A")

    # Error tambah mata kuliah duplikat
    with pytest.raises(HTTPException) as exc:
        manager.add_course("EX1", "MK_A")

    assert exc.value.status_code == 400

    # ==========================================
    # TEST 3: VALIDASI BATAS SKS
    # ==========================================

    krs = (
        db_session.query(KRS)
        .filter(KRS.nim == "EX1")
        .first()
    )

    krs.details.append(
        KRSDetail(matakuliah_id=mk2.id)
    )

    krs.total_sks += 22
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        manager.submit_krs("EX1")

    assert exc.value.status_code == 400

    # Menghapus MK 22 SKS
    detail = (
        db_session.query(KRSDetail)
        .filter_by(
            krs_id=krs.id,
            matakuliah_id=mk2.id
        )
        .first()
    )

    db_session.delete(detail)
    krs.total_sks -= 22
    db_session.commit()

    # ==========================================
    # TEST 4: SUBMIT KRS
    # ==========================================

    result = manager.submit_krs("EX1")

    assert result["status"] == "SUBMITTED"

    # ==========================================
    # TEST 5: REVISE KRS
    # ==========================================

    result = manager.revise_krs(
        "EX1",
        "DSN_01"
    )

    assert result["status"] == "REVISION"

    # ==========================================
    # TEST 6: SUBMIT ULANG
    # ==========================================

    result = manager.submit_krs("EX1")

    assert result["status"] == "SUBMITTED"

    # ==========================================
    # TEST 7: APPROVE KRS
    # ==========================================

    result = manager.approve_krs(
        "EX1",
        "DSN_01"
    )

    assert result["status"] == "APPROVED"

    # ==========================================
    # TEST 8: TRANSISI ILEGAL
    # ==========================================

    with pytest.raises(HTTPException) as exc:
        manager.submit_krs("EX1")

    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        manager.approve_krs("EX1", "DSN_01")

    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        manager.revise_krs("EX1", "DSN_01")

    assert exc.value.status_code == 400


# ==========================================
# 2. SCHEDULING SERVICE (Bentrok & CRUD)
# ==========================================
def test_scheduling_exhaustive(db_session):
    mk = Matakuliah(kode_mk="MK_S", nama_mk="S", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    dosen = Dosen(nidn="D1", nama="Dosen")
    r1 = Ruangan(kode_ruangan="R1", nama_ruangan="R1", kapasitas=10) # Kapasitas kecil
    r2 = Ruangan(kode_ruangan="R2", nama_ruangan="R2", kapasitas=50)
    mhs = CalonMahasiswa(nama_lengkap="B", email="b@ex.com", phone="081234567890", tanggal_lahir=date(2000,1,1), alamat="Jl", program_studi_id=1, jalur_masuk_id=1, status=StatusPendaftaran.approved, nim="EX2")
    db_session.add_all([mk, dosen, r1, r2, mhs])
    db_session.commit()

    # Buat 15 Mahasiswa dummy untuk nge-test kapasitas R1 (max 10)
    for i in range(15):
        m = CalonMahasiswa(nama_lengkap=f"M{i}", email=f"m{i}@ex.com", phone="081234567890", tanggal_lahir=date(2000,1,1), alamat="Jl", program_studi_id=1, jalur_masuk_id=1, status=StatusPendaftaran.approved, nim=f"M{i}")
        db_session.add(m)
        db_session.commit()
        k = KRS(nim=f"M{i}", semester_akademik=1, tahun_akademik="2024", status="DRAFT", total_sks=3)
        db_session.add(k)
        db_session.commit()
        db_session.add(KRSDetail(krs_id=k.id, matakuliah_id=mk.id))
        db_session.commit()

    service = SchedulingService(db_session)
    
    # Error: MK tidak ada
    with pytest.raises(HTTPException) as exc: service.create_schedule({"matakuliah_id": 999, "ruangan_id": 999})
    assert exc.value.status_code == 404
    
    # Error: Kapasitas kurang (15 mhs > 10 kapasitas)
    with pytest.raises(HTTPException) as exc: 
        service.create_schedule({"matakuliah_id": mk.id, "dosen_id": dosen.id, "ruangan_id": r1.id, "hari": "Rabu", "jam_mulai": "08:00", "jam_selesai": "10:00", "tahun_akademik": "2024", "semester_akademik": 1})
    assert exc.value.status_code == 400

    # Sukses create di R2
    jadwal = service.create_schedule({"matakuliah_id": mk.id, "dosen_id": dosen.id, "ruangan_id": r2.id, "hari": "Rabu", "jam_mulai": "08:00", "jam_selesai": "10:00", "tahun_akademik": "2024", "semester_akademik": 1})
    
    # Error update bentrok
    service.create_schedule({"matakuliah_id": mk.id, "dosen_id": dosen.id, "ruangan_id": r2.id, "hari": "Kamis", "jam_mulai": "08:00", "jam_selesai": "10:00", "tahun_akademik": "2024", "semester_akademik": 1})
    with pytest.raises(HTTPException) as exc: 
        service.update_schedule(jadwal.id, {"hari": "Kamis", "jam_mulai": "09:00", "jam_selesai": "11:00"})
    assert exc.value.status_code == 409

    # Delete jadwal
    service.delete_schedule(jadwal.id)
    with pytest.raises(HTTPException) as exc: service.delete_schedule(jadwal.id)
    assert exc.value.status_code == 404

# ==========================================
# 3. CONFLICT DETECTOR (Boundary Time)
# ==========================================
def test_conflict_detector_boundary():
    mk = Matakuliah(kode_mk="X", nama_mk="X", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    # Jadwal berurutan tepat (10:00 - 12:00) TIDAK BOLEH bentrok
    j1 = JadwalKuliah(id=1, hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0), ruangan_id=1, dosen_id=1)
    j2 = JadwalKuliah(id=2, hari="Senin", jam_mulai=time(10,0), jam_selesai=time(12,0), ruangan_id=1, dosen_id=1)
    conflicts = detect_schedule_conflict(j2, [j1])
    assert len(conflicts) == 0

# ==========================================
# 4. OBSERVER PATTERN (Detach & Error)
# ==========================================
def test_observer_pattern_coverage():
    subject = ScheduleSubject()
    
    class DummyObserver(Observer):
        def update(self, event_type, data): pass

    class ErrorObserver(Observer):
        def update(self, event_type, data): raise Exception("Simulasi Gagal")

    obs = DummyObserver()
    subject.attach(obs)
    subject.detach(obs) # Mencakup fungsi detach
    
    subject.attach(ErrorObserver())
    # Memastikan error di observer tidak menghentikan program (tertangkap try-except)
    subject.notify("TEST", {}) 

# ==========================================
# 5. RESCHEDULING SERVICE (Empty Slot)
# ==========================================
def test_rescheduling_no_slots(db_session):
    mk = Matakuliah(kode_mk="X", nama_mk="X", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    dosen = Dosen(nidn="1", nama="D1")
    r1 = Ruangan(kode_ruangan="R1", nama_ruangan="R1", kapasitas=50)
    db_session.add_all([mk, dosen, r1])
    db_session.commit()

    jadwal = JadwalKuliah(matakuliah_id=mk.id, dosen_id=dosen.id, ruangan_id=r1.id, hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0), tahun_akademik="2024", semester_akademik=1)
    db_session.add(jadwal)
    db_session.commit()

    rs = ReschedulingService(db_session, SchedulingService(db_session))
    saran = rs.suggest_alternatives(jadwal.id)
    assert isinstance(saran, list) # Mencakup kondisi jika list kosong atau ada isinya