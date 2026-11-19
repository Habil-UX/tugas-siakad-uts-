from datetime import date, time
import pytest
from hypothesis import given, settings, strategies as st
from app.models import CalonMahasiswa, KRS, Matakuliah, StatusPendaftaran
from app.services.krs.validators import SKSValidator


# 1. Unit & Integration Test Bentrok Jadwal KRS
def test_schedule_conflict(client, db_session):
    mhs = CalonMahasiswa(
        nama_lengkap="Mahasiswa Konflik",
        email="konflik_krs@test.com",
        phone="081234567890",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Jl. Merdeka 10",
        program_studi_id=1,
        jalur_masuk_id=1,
        status=StatusPendaftaran.approved,
        nim="2025001-0099",
    )
    mk1 = Matakuliah(
        kode_mk="IF101",
        nama_mk="Kalkulus I",
        sks=3,
        semester=1,
        jenis_mk="Wajib",
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
    )
    mk2 = Matakuliah(
        kode_mk="IF102",
        nama_mk="Fisika Dasar",
        sks=3,
        semester=1,
        jenis_mk="Wajib",
        hari="Senin",
        jam_mulai=time(9, 0),
        jam_selesai=time(11, 0),
    )
    db_session.add_all([mhs, mk1, mk2])
    db_session.commit()

    res1 = client.post(
        "/api/krs/add",
        json={"nim": "2025001-0099", "kode_mk": "IF101"},
    )
    assert res1.status_code == 200

    res2 = client.post(
        "/api/krs/add",
        json={"nim": "2025001-0099", "kode_mk": "IF102"},
    )
    assert res2.status_code == 400
    assert "Jadwal bentrok dengan mata kuliah Kalkulus I" in res2.json()["detail"]


# 2. Hypothesis Property-Based Testing (1000 examples)
@settings(max_examples=1000)
@given(
    st.lists(
        st.integers(min_value=1, max_value=4),
        min_size=1,
        max_size=10,
    )
)
def test_total_sks_never_exceeds_limit(sks_list):
    """
    Property: Berapapun kombinasi SKS yang dimasukkan (1000 kombinasi),
    SKSValidator harus selalu menolak jika akumulasi > 24 SKS.
    """
    validator = SKSValidator()

    class MockMK:
        def __init__(self, sks):
            self.sks = sks

    class MockDetail:
        def __init__(self, sks):
            self.matakuliah = MockMK(sks)

    class MockKRS:
        def __init__(self, items):
            self.details = [MockDetail(s) for s in items]

    accepted_sks = []
    for sks in sks_list:
        context = {
            "db": None,
            "krs": MockKRS(accepted_sks),
            "new_mk": MockMK(sks),
        }
        result = validator.validate(context)
        if sum(accepted_sks) + sks > 24:
            assert result.is_valid is False
            assert "melebihi batas maksimal 24 SKS" in result.message
        else:
            assert result.is_valid is True
            accepted_sks.append(sks)

    assert sum(accepted_sks) <= 24


# 3. Test Endpoint Router dan Chain Validator
def test_krs_endpoints(client, db_session):
    mhs = CalonMahasiswa(
        nama_lengkap="Test",
        email="krs@test.com",
        phone="08123456789",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Jl. Test",
        program_studi_id=1,
        jalur_masuk_id=1,
        status=StatusPendaftaran.approved,
        nim="2024001-0001",
    )
    mk = Matakuliah(
        kode_mk="IF101",
        nama_mk="Dasar Pemrograman",
        sks=3,
        semester=1,
        jenis_mk="Wajib",
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
    )
    db_session.add(mhs)
    db_session.add(mk)
    db_session.commit()

    payload = {"nim": "2024001-0001", "kode_mk": "IF101"}
    response = client.post("/api/krs/add", json=payload)
    assert response.status_code == 200
    assert response.json()["total_sks"] == 3

    # Test Endpoint ADD Duplikat -> Ditangkap oleh DuplicateValidator
    response_dup = client.post("/api/krs/add", json=payload)
    assert response_dup.status_code == 400
    assert "sudah terdaftar di KRS" in response_dup.json()["detail"]

    # Test Endpoint REMOVE
    response_del = client.post("/api/krs/remove", json=payload)
    assert response_del.status_code == 200
    assert response_del.json()["total_sks"] == 0

    # Test Endpoint VALIDATE
    response_val = client.get("/api/krs/validate/2024001-0001")
    assert response_val.status_code == 200
