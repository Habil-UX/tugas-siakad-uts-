import pytest
from fastapi import HTTPException
from datetime import time, date
from app.models import KRS, JadwalKuliah, Ruangan, Dosen, Matakuliah
from app.services.krs_manager import KRSManager


def test_state_machine_flow(client, db_session):

    # ==========================================
    # 1. SETUP MAHASISWA
    # ==========================================

    from app.models import CalonMahasiswa, StatusPendaftaran

    mhs = CalonMahasiswa(
        nama_lengkap="A",
        email="a@test.com",
        phone="081234567890",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Jl",
        program_studi_id=1,
        jalur_masuk_id=1,
        status=StatusPendaftaran.approved,
        nim="123"
    )

    # Membuat Dosen PA
    dosen = Dosen(
        nidn="DSN_001",
        nama="Dosen Pembimbing Akademik"
    )

    # Membuat mata kuliah untuk KRS
    mk = Matakuliah(
        kode_mk="SM_MK",
        nama_mk="Mata Kuliah State Machine",
        sks=3,
        semester=1,
        jenis_mk="Wajib",
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0)
    )

    db_session.add_all([mhs, dosen, mk])
    db_session.commit()

    # Menetapkan Dosen PA
    mhs.dosen_pa_id = dosen.id
    db_session.commit()

    # ==========================================
    # 2. MEMBUAT KRS
    # ==========================================

    manager = KRSManager(db_session)

    krs = manager._get_or_create_krs("123")

    # Menambahkan mata kuliah
    result_add = manager.add_course(
        "123",
        "SM_MK"
    )

    assert result_add["total_sks"] == 3

    # ==========================================
    # 3. SUBMIT KRS
    # ==========================================

    manager.submit_krs("123")

    assert krs.status == "SUBMITTED"

    # ==========================================
    # 4. APPROVE OLEH DOSEN PA
    # ==========================================

    manager.approve_krs(
        "123",
        "DSN_001"
    )

    assert krs.status == "APPROVED"

    # ==========================================
    # 5. TEST TRANSISI ILEGAL
    # ==========================================

    with pytest.raises(HTTPException) as exc:
        manager.submit_krs("123")

    assert exc.value.status_code == 400
    assert "Transisi ilegal" in exc.value.detail


def test_ai_rescheduling_dynamic(client, db_session):
    from app.services.rescheduling_service import ReschedulingService
    from app.services.scheduling_service import SchedulingService
    
    mk = Matakuliah(kode_mk="X", nama_mk="X", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    dosen = Dosen(nidn="1", nama="D1")
    ruang = Ruangan(kode_ruangan="R1", nama_ruangan="R1", kapasitas=50)
    db_session.add_all([mk, dosen, ruang])
    db_session.commit()

    jadwal = JadwalKuliah(matakuliah_id=mk.id, dosen_id=dosen.id, ruangan_id=ruang.id, hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0), tahun_akademik="2024", semester_akademik=1)
    db_session.add(jadwal)
    db_session.commit()

    sched_service = SchedulingService(db_session)
    rs = ReschedulingService(db_session, sched_service)
    saran = rs.suggest_alternatives(jadwal.id)
    
    # Harus mengembalikan list (walaupun kosong, tidak boleh statis)
    assert isinstance(saran, list)
    if len(saran) > 0:
        assert "hari" in saran[0]
        assert "ruangan" in saran[0]