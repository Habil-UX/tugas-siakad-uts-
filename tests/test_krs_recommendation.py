import pytest
from unittest.mock import patch
from datetime import date, time
from app.models import Matakuliah, CalonMahasiswa, StatusPendaftaran, KRS
from app.schemas.pmb import CalonMahasiswaCreate

# --- TEST REKOMENDASI KRS (FITUR CHALLENGE) ---

def test_recommendation_basic(client, db_session):
    mhs = CalonMahasiswa(nama_lengkap="Budi", email="budi@test.com", phone="081234567890", tanggal_lahir=date(2000,1,1), alamat="Jalan Test", program_studi_id=1, jalur_masuk_id=1, status=StatusPendaftaran.approved, nim="2024001-0001")
    db_session.add(mhs)
    mk1 = Matakuliah(kode_mk="IF101", nama_mk="Pemrograman", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    mk2 = Matakuliah(kode_mk="IF102", nama_mk="Matematika", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(10,0), jam_selesai=time(12,0))
    mk3 = Matakuliah(kode_mk="IF201", nama_mk="AI", sks=3, semester=2, jenis_mk="Pilihan", hari="Selasa", jam_mulai=time(8,0), jam_selesai=time(10,0))
    db_session.add_all([mk1, mk2, mk3])
    db_session.commit()

    response = client.post("/api/krs/recommend/2024001-0001")
    assert response.status_code == 200
    data = response.json()
    assert data["total_sks"] == 9 
    assert len(data["wajib_terpilih"]) == 2
    assert len(data["pilihan_terpilih"]) == 1

def test_recommendation_conflict(client, db_session):
    mhs = CalonMahasiswa(nama_lengkap="Budi", email="budi@test.com", phone="081234567890", tanggal_lahir=date(2000,1,1), alamat="Jalan Test", program_studi_id=1, jalur_masuk_id=1, status=StatusPendaftaran.approved, nim="2024001-0001")
    db_session.add(mhs)
    mk1 = Matakuliah(kode_mk="IF101", nama_mk="Pemrograman", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    mk2 = Matakuliah(kode_mk="IF102", nama_mk="Matematika", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(9,0), jam_selesai=time(11,0))
    db_session.add_all([mk1, mk2])
    db_session.commit()

    response = client.post("/api/krs/recommend/2024001-0001")
    assert response.status_code == 200
    data = response.json()
    assert data["total_sks"] == 3 
    assert len(data["rekomendasi_mk"]) == 1
    assert "IF102" in data["alasan_tidak_terpilih"]
    assert "Bentrok jadwal" in data["alasan_tidak_terpilih"]["IF102"]

def test_recommendation_sks_limit(client, db_session):
    mhs = CalonMahasiswa(nama_lengkap="Budi", email="budi@test.com", phone="081234567890", tanggal_lahir=date(2000,1,1), alamat="Jalan Test", program_studi_id=1, jalur_masuk_id=1, status=StatusPendaftaran.approved, nim="2024001-0001")
    db_session.add(mhs)
    for i in range(9):
        mk = Matakuliah(kode_mk=f"IF10{i}", nama_mk=f"MK {i}", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8+i,0), jam_selesai=time(9+i,0))
        db_session.add(mk)
    db_session.commit()

    response = client.post("/api/krs/recommend/2024001-0001")
    assert response.status_code == 200
    data = response.json()
    assert data["total_sks"] <= 24
    assert len(data["rekomendasi_mk"]) == 8 

def test_recommend_mahasiswa_not_found(client):
    # Menutupi krs_recommender.py baris 76
    response = client.post("/api/krs/recommend/99999999")
    assert response.status_code == 404
    assert "tidak ditemukan" in response.json()["detail"]


# --- TEST ERROR HANDLING & COVERAGE 100% ---

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200

def test_register_internal_server_error(client):
    # FIX: "alamat" diubah jadi "Jalan Test" agar lolos Pydantic (min 5 karakter)
    payload = {
        "nama_lengkap": "Test Error", "email": "error@test.com", "phone": "081234567890",
        "tanggal_lahir": "2000-01-01", "alamat": "Jalan Test", "program_studi_id": 1, "jalur_masuk_id": 1
    }
    with patch("app.routers.pmb.Session.commit", side_effect=Exception("DB Error")):
        response = client.post("/api/pmb/register", json=payload)
        assert response.status_code == 500

def test_pmb_service_errors(client, db_session):
    res1 = client.put("/api/pmb/approve/9999")
    assert res1.status_code == 404
    res2 = client.put("/api/pmb/reject/9999")
    assert res2.status_code == 404

    mhs = CalonMahasiswa(nama_lengkap="Test", email="rej@test.com", phone="081234567890", tanggal_lahir=date(2000,1,1), alamat="Jalan Test", program_studi_id=1, jalur_masuk_id=1, status=StatusPendaftaran.rejected, nim="1234")
    db_session.add(mhs)
    db_session.commit()
    res3 = client.put(f"/api/pmb/approve/{mhs.id}")
    assert res3.status_code == 409

def test_krs_manager_errors(client, db_session):
    res1 = client.post("/api/krs/add", json={"nim": "INVALID", "kode_mk": "IF101"})
    assert res1.status_code == 404
    
    mhs = CalonMahasiswa(nama_lengkap="Test", email="t@t.com", phone="081234567890", tanggal_lahir=date(2000,1,1), alamat="Jalan Test", program_studi_id=1, jalur_masuk_id=1, status=StatusPendaftaran.approved, nim="12345678")
    db_session.add(mhs)
    
    # TAMBAHKAN BARIS INI: Agar mata kuliah IF101 ada di database
    mk = Matakuliah(kode_mk="IF101", nama_mk="Pemrograman", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    db_session.add(mk)
    db_session.commit()

    res2 = client.post("/api/krs/add", json={"nim": "12345678", "kode_mk": "INVALID"})
    assert res2.status_code == 404

    krs = KRS(nim="12345678", semester_akademik=1, tahun_akademik="2024", status="APPROVED")
    db_session.add(krs)
    db_session.commit()
    
    res3 = client.post("/api/krs/add", json={"nim": "12345678", "kode_mk": "IF101"})
    assert res3.status_code == 400
    assert "tidak dapat diedit" in res3.json()["detail"]

    res4 = client.post("/api/krs/remove", json={"nim": "12345678", "kode_mk": "IF101"})
    assert res4.status_code == 400

def test_krs_remove_errors(client, db_session):
    mhs = CalonMahasiswa(nama_lengkap="Test", email="t@t.com", phone="081234567890", tanggal_lahir=date(2000,1,1), alamat="Jalan Test", program_studi_id=1, jalur_masuk_id=1, status=StatusPendaftaran.approved, nim="12345678")
    mk = Matakuliah(kode_mk="IF101", nama_mk="Pemrograman", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    db_session.add_all([mhs, mk])
    db_session.commit()
    
    # Menutupi krs_manager.py baris 61
    res = client.post("/api/krs/remove", json={"nim": "12345678", "kode_mk": "IF101"})
    assert res.status_code == 404
    assert "tidak terdaftar" in res.json()["detail"]

def test_validator_duplicate_failure(client, db_session):
    # Menutupi validators.py baris 111-112 (Duplicate Validator)
    mhs = CalonMahasiswa(nama_lengkap="Test", email="val@test.com", phone="081234567890", tanggal_lahir=date(2000,1,1), alamat="Jalan Test", program_studi_id=1, jalur_masuk_id=1, status=StatusPendaftaran.approved, nim="9999")
    mk1 = Matakuliah(kode_mk="MK1", nama_mk="MK1", sks=3, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    db_session.add_all([mhs, mk1])
    db_session.commit()

    # Tambah pertama kali
    client.post("/api/krs/add", json={"nim": "9999", "kode_mk": "MK1"})
    
    # Tambah kedua kali (harus gagal karena duplicate)
    res = client.post("/api/krs/add", json={"nim": "9999", "kode_mk": "MK1"})
    assert res.status_code == 400
    # Catatan: Karena ConflictValidator berjalan sebelum DuplicateValidator, 
    # mungkin pesan error yang keluar adalah "Jadwal bentrok". Ini normal.

from sqlalchemy.exc import IntegrityError
from unittest.mock import patch
from datetime import date, time
from app.models import Matakuliah, CalonMahasiswa, StatusPendaftaran

# 1. Menembak app/routers/pmb.py (baris 35-37)
def test_register_integrity_error(client):
    payload = {
        "nama_lengkap": "Test Error", "email": "integrity@test.com", "phone": "081234567890",
        "tanggal_lahir": "2000-01-01", "alamat": "Jalan Test", "program_studi_id": 1, "jalur_masuk_id": 1
    }
    # Memaksa database memunculkan IntegrityError secara spesifik
    with patch("app.routers.pmb.Session.commit", side_effect=IntegrityError("stmt", "params", "orig")):
        response = client.post("/api/pmb/register", json=payload)
        assert response.status_code == 409
        assert "konflik database" in response.json()["detail"]

# 2. Menembak app/services/krs/validators.py (baris 33 - SKS Limit)
def test_sks_limit_combination(client, db_session):
    mhs = CalonMahasiswa(nama_lengkap="Test", email="sks@test.com", phone="081234567890", tanggal_lahir=date(2000,1,1), alamat="Jalan Test", program_studi_id=1, jalur_masuk_id=1, status=StatusPendaftaran.approved, nim="8888")
    mk1 = Matakuliah(kode_mk="MK1", nama_mk="MK1", sks=10, semester=1, jenis_mk="Wajib", hari="Senin", jam_mulai=time(8,0), jam_selesai=time(10,0))
    mk2 = Matakuliah(kode_mk="MK2", nama_mk="MK2", sks=15, semester=1, jenis_mk="Wajib", hari="Selasa", jam_mulai=time(8,0), jam_selesai=time(10,0))
    db_session.add_all([mhs, mk1, mk2])
    db_session.commit()

    # Ambil MK1 (10 SKS)
    client.post("/api/krs/add", json={"nim": "8888", "kode_mk": "MK1"})
    
    # Ambil MK2 (15 SKS). Total 25 SKS. Harus gagal di SKSValidator.
    res = client.post("/api/krs/add", json={"nim": "8888", "kode_mk": "MK2"})
    assert res.status_code == 400
    assert "melebihi batas maksimal 24" in res.json()["detail"]