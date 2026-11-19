import pytest
from datetime import time, date
from fastapi import HTTPException
from app.models import CalonMahasiswa, Matakuliah, KRS, KRSDetail, StatusPendaftaran, Dosen, Ruangan, JadwalKuliah
from app.services.krs_manager import KRSManager
from app.services.scheduling_service import SchedulingService

def test_ultimate_coverage(db_session):
    # --- SETUP DATA ---
    mhs = CalonMahasiswa(nama_lengkap="Coverage", email="cov@test.com", phone="081234567890", tanggal_lahir=date(2000,1,1), alamat="Jl", program_studi_id=1, jalur_masuk_id=1, status=StatusPendaftaran.approved, nim="COV1")
    mk1 = Matakuliah(kode_mk="COV_MK1", nama_mk="MK 1", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    mk2 = Matakuliah(kode_mk="COV_MK2", nama_mk="MK 2", sks=25, semester=1, jenis_mk="Wajib", hari="Selasa", jam_mulai=time(8,0), jam_selesai=time(10,0))
    dosen = Dosen(nidn="COV_D", nama="Dosen Cov")
    r1 = Ruangan(kode_ruangan="COV_R1", nama_ruangan="R1", kapasitas=50)
    r2 = Ruangan(kode_ruangan="COV_R2", nama_ruangan="R2", kapasitas=50)
    db_session.add_all([mhs, mk1, mk2, dosen, r1, r2])
    db_session.commit()

# Tetapkan Dosen PA kepada mahasiswa
    mhs.dosen_pa_id = dosen.id
    db_session.commit()

    # ==========================================
    # KRS MANAGER COVERAGE (STATE MACHINE)
    # ==========================================
    krs_mgr = KRSManager(db_session)

    # 1. Test add_course (memicu _get_mahasiswa)
    res = krs_mgr.add_course("COV1", "COV_MK1")
    assert res["total_sks"] == 3

    # 2. Test add_course error duplicate
    with pytest.raises(HTTPException) as exc:
        krs_mgr.add_course("COV1", "COV_MK1")
    assert exc.value.status_code == 400

    # 3. Test add_course error SKS > 24
    with pytest.raises(HTTPException) as exc:
        krs_mgr.add_course("COV1", "COV_MK2")
    assert exc.value.status_code == 400

    # 4. Test submit_krs dengan error validasi (Paksa SKS > 24)
    krs = db_session.query(KRS).filter(KRS.nim == "COV1").first()
    krs.details.append(KRSDetail(matakuliah_id=mk2.id))
    krs.total_sks += 25
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        krs_mgr.submit_krs("COV1")
    assert exc.value.status_code == 400
    
    # Bersihkan kembali
    krs.details.pop()
    krs.total_sks -= 25
    db_session.commit()

    # 5. Test submit_krs sukses
    res_submit = krs_mgr.submit_krs("COV1")
    assert res_submit["status"] == "SUBMITTED"

    # 6. Test revise_krs
    res_revise = krs_mgr.revise_krs("COV1", "COV_D")
    assert res_revise["status"] == "REVISION"

    # 7. Test submit_krs lagi dari REVISION
    res_submit2 = krs_mgr.submit_krs("COV1")
    assert res_submit2["status"] == "SUBMITTED"

    # 8. Test approve_krs
    res_approve = krs_mgr.approve_krs("COV1", "COV_D")
    assert res_approve["status"] == "APPROVED"

    # 9. Test add_course error karena status APPROVED
    with pytest.raises(HTTPException) as exc:
        krs_mgr.add_course("COV1", "COV_MK1")
    assert exc.value.status_code == 400


    # ==========================================
    # SCHEDULING SERVICE COVERAGE (CRUD)
    # ==========================================
    sched_mgr = SchedulingService(db_session)

    # 1. Create Schedule (format jam tanpa detik untuk test _parse_time)
    payload = {
        "matakuliah_id": mk1.id, "dosen_id": dosen.id, "ruangan_id": r1.id,
        "hari": "Rabu", "jam_mulai": "08:00", "jam_selesai": "10:00",
        "tahun_akademik": "2024", "semester_akademik": 1
    }
    jadwal = sched_mgr.create_schedule(payload)
    assert jadwal.jam_mulai == time(8, 0)

    # 2. Update Schedule (memicu _invalidate_krs)
    update_payload = {
        "ruangan_id": r2.id,
        "jam_mulai": "13:00",
        "jam_selesai": "15:00"
    }
    updated = sched_mgr.update_schedule(jadwal.id, update_payload)
    assert updated.ruangan_id == r2.id

    # 3. Update Schedule error bentrok
    payload_dummy = {
        "matakuliah_id": mk1.id, "dosen_id": dosen.id, "ruangan_id": r1.id,
        "hari": "Kamis", "jam_mulai": "08:00", "jam_selesai": "10:00",
        "tahun_akademik": "2024", "semester_akademik": 1
    }
    sched_mgr.create_schedule(payload_dummy)

    with pytest.raises(HTTPException) as exc:
        sched_mgr.update_schedule(jadwal.id, {"hari": "Kamis", "jam_mulai": "09:00", "jam_selesai": "11:00"})
    assert exc.value.status_code == 409

    # 4. Delete Schedule
    sched_mgr.delete_schedule(jadwal.id)
    assert db_session.query(JadwalKuliah).get(jadwal.id) is None

    # 5. Error Handling not found
    with pytest.raises(HTTPException):
        sched_mgr.delete_schedule(99999)