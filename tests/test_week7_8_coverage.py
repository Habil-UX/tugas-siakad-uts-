import pytest
from datetime import time
from app.models import Matakuliah, Dosen, Ruangan, JadwalKuliah, KRS, KRSDetail, CalonMahasiswa, StatusPendaftaran
from datetime import date

def test_dashboard_endpoint(client):
    # Menutupi app/routers/dashboard.py
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Conflict Resolver Dashboard" in response.text

def test_create_schedule_success(client, db_session):
    # 1. Setup Data
    from app.models import JadwalKuliah # Pastikan diimport
    mhs = CalonMahasiswa(nama_lengkap="Test", email="sched@test.com", phone="081234567890", tanggal_lahir=date(2000,1,1), alamat="Jalan Test", program_studi_id=1, jalur_masuk_id=1, status=StatusPendaftaran.approved, nim="2024001-0001")
    mk = Matakuliah(kode_mk="IF101", nama_mk="Pemrograman", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    dosen = Dosen(nidn="12345", nama="Dosen Test")
    ruangan = Ruangan(kode_ruangan="A101", nama_ruangan="Ruang A", kapasitas=50, is_active=True)
    
    db_session.add_all([mhs, mk, dosen, ruangan])
    db_session.commit()

    # Tambahkan KRS Detail agar kapasitas terhitung
    krs = KRS(nim="2024001-0001", semester_akademik=1, tahun_akademik="2024", total_sks=3, status="DRAFT")
    db_session.add(krs)
    db_session.commit()
    detail = KRSDetail(krs_id=krs.id, matakuliah_id=mk.id)
    db_session.add(detail)
    db_session.commit()

    # 2. Request Create Schedule
    payload = {
        "matakuliah_id": mk.id,
        "dosen_id": dosen.id,
        "ruangan_id": ruangan.id,
        "hari": "Rabu",
        "jam_mulai": "08:00:00",
        "jam_selesai": "10:00:00",
        "tahun_akademik": "2024",
        "semester_akademik": 1
    }
    
    response = client.post("/api/schedules", json=payload)
    assert response.status_code == 200
    
    # FIX: Cek langsung ke database, bukan ke response JSON
    jadwal_db = db_session.query(JadwalKuliah).filter(JadwalKuliah.hari == "Rabu").first()
    assert jadwal_db is not None
    assert jadwal_db.hari == "Rabu"

def test_create_schedule_conflict(client, db_session):
    # Menutupi app/services/conflict_detector.py (bagian error)
    mk = Matakuliah(kode_mk="IF102", nama_mk="Algoritma", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    dosen1 = Dosen(nidn="111", nama="Dosen 1")
    dosen2 = Dosen(nidn="222", nama="Dosen 2")
    ruangan = Ruangan(kode_ruangan="A102", nama_ruangan="Ruang B", kapasitas=50, is_active=True)
    db_session.add_all([mk, dosen1, dosen2, ruangan])
    db_session.commit()

    # Buat jadwal pertama
    jadwal1 = JadwalKuliah(matakuliah_id=mk.id, dosen_id=dosen1.id, ruangan_id=ruangan.id, hari="Kamis", jam_mulai=time(8,0), jam_selesai=time(10,0), tahun_akademik="2024", semester_akademik=1)
    db_session.add(jadwal1)
    db_session.commit()

    # Request jadwal kedua (bentrok ruangan & waktu)
    payload = {
        "matakuliah_id": mk.id,
        "dosen_id": dosen2.id,
        "ruangan_id": ruangan.id, # Ruangan sama
        "hari": "Kamis",          # Hari sama
        "jam_mulai": "09:00:00",  # Overlap
        "jam_selesai": "11:00:00",
        "tahun_akademik": "2024",
        "semester_akademik": 1
    }
    
    response = client.post("/api/schedules", json=payload)
    assert response.status_code == 409
    assert "Konflik terdeteksi" in response.json()["detail"]["message"]

def test_get_schedules_and_suggestions(client, db_session):
    # Menutupi app/routers/schedules.py (GET dan Suggestions)
    mk = Matakuliah(kode_mk="IF103", nama_mk="Basis Data", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    dosen = Dosen(nidn="333", nama="Dosen 3")
    ruangan = Ruangan(kode_ruangan="A103", nama_ruangan="Ruang C", kapasitas=50, is_active=True)
    db_session.add_all([mk, dosen, ruangan])
    db_session.commit()

    jadwal = JadwalKuliah(matakuliah_id=mk.id, dosen_id=dosen.id, ruangan_id=ruangan.id, hari="Jumat", jam_mulai=time(8,0), jam_selesai=time(10,0), tahun_akademik="2024", semester_akademik=1)
    db_session.add(jadwal)
    db_session.commit()

    # Test GET
    res_get = client.get("/api/schedules")
    assert res_get.status_code == 200
    assert len(res_get.json()) > 0

    # Test POST Suggestions (AI)
    res_sug = client.post(f"/api/schedules/{jadwal.id}/suggestions")
    assert res_sug.status_code == 200
    assert len(res_sug.json()) > 0
    assert "reason" in res_sug.json()[0]


# ==========================================
# ADDITIONAL SCHEDULE API TESTS
# ==========================================

def test_create_schedule_missing_required_field(client):
    """API harus menolak request tanpa field wajib."""

    response = client.post(
        "/api/schedules",
        json={}
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Field matakuliah_id wajib diisi"
    )


def test_create_schedule_matakuliah_not_found(client):
    """API harus mengembalikan 404 jika MK tidak ditemukan."""

    payload = {
        "matakuliah_id": 999999,
        "dosen_id": 1,
        "ruangan_id": 1,
        "hari": "Senin",
        "jam_mulai": "08:00",
        "jam_selesai": "10:00",
        "tahun_akademik": "2024",
        "semester_akademik": 1
    }

    response = client.post(
        "/api/schedules",
        json=payload
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Mata kuliah tidak ditemukan"
    )


def test_suggestions_schedule_not_found(client):
    """Menguji AI suggestions ketika jadwal tidak ditemukan."""

    response = client.post(
        "/api/schedules/999999/suggestions"
    )

    assert response.status_code == 200
    assert response.json() == []


def test_schedule_notifications_saved_to_database(client, db_session):
    from datetime import date, time
    from app.models import (
        CalonMahasiswa,
        Matakuliah,
        Dosen,
        Ruangan,
        KRS,
        KRSDetail,
        StatusPendaftaran,
        NotificationLog
    )

    # Setup mahasiswa
    mhs = CalonMahasiswa(
        nama_lengkap="Test Notification",
        email="notif@test.com",
        phone="081234567890",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Jl. Test",
        program_studi_id=1,
        jalur_masuk_id=1,
        status=StatusPendaftaran.approved,
        nim="NOTIF001"
    )

    mk = Matakuliah(
        kode_mk="NTF101",
        nama_mk="Testing Notification",
        sks=3,
        semester=1,
        jenis_mk="Wajib",
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0)
    )

    dosen = Dosen(nidn="NTF001", nama="Dosen Notification")

    ruangan = Ruangan(
        kode_ruangan="NTF01",
        nama_ruangan="Ruang Notification",
        kapasitas=50,
        is_active=True
    )

    db_session.add_all([mhs, mk, dosen, ruangan])
    db_session.commit()

    # Setup KRS mahasiswa
    krs = KRS(
        nim="NOTIF001",
        semester_akademik=1,
        tahun_akademik="2024",
        total_sks=3,
        status="DRAFT"
    )

    db_session.add(krs)
    db_session.commit()

    db_session.add(
        KRSDetail(
            krs_id=krs.id,
            matakuliah_id=mk.id
        )
    )
    db_session.commit()

    # Panggil Scheduling API
    response = client.post(
        "/api/schedules",
        json={
            "matakuliah_id": mk.id,
            "dosen_id": dosen.id,
            "ruangan_id": ruangan.id,
            "hari": "Rabu",
            "jam_mulai": "08:00:00",
            "jam_selesai": "10:00:00",
            "tahun_akademik": "2024",
            "semester_akademik": 1
        }
    )

    assert response.status_code == 200

    # Verifikasi Notification Database
    logs = (
        db_session.query(NotificationLog)
        .filter(
            NotificationLog.event_type == "SCHEDULE_CHANGE"
        )
        .all()
    )

    assert len(logs) == 3

    assert {
        log.recipient_type for log in logs
    } == {"ADMIN", "DOSEN", "MAHASISWA"}

    assert {
        log.channel for log in logs
    } == {"push", "sms", "email"}

    assert all(log.status == "SENT" for log in logs)
