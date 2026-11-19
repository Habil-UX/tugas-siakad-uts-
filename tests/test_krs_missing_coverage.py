
import pytest
from datetime import date
from fastapi import HTTPException

from app.models import (
    CalonMahasiswa,
    Dosen,
    StatusPendaftaran
)

from app.services.krs_manager import KRSManager
import app.routers.krs as krs_router


# ==========================================
# HELPER: MEMBUAT MAHASISWA
# ==========================================

def create_mahasiswa(
    db_session,
    nim,
    email,
    dosen_pa_id=None
):
    mahasiswa = CalonMahasiswa(
        nama_lengkap="Mahasiswa Coverage",
        email=email,
        phone="081234567890",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Jl. Testing",
        program_studi_id=1,
        jalur_masuk_id=1,
        status=StatusPendaftaran.approved,
        nim=nim,
        dosen_pa_id=dosen_pa_id
    )

    db_session.add(mahasiswa)
    db_session.commit()

    return mahasiswa


# ==========================================
# 1. DOSEN PA BELUM DITETAPKAN
# COVERAGE KRS_MANAGER BARIS 67
# ==========================================

def test_authorized_dosen_not_assigned(db_session):

    mahasiswa = create_mahasiswa(
        db_session,
        "COV001",
        "cov001@test.com"
    )

    manager = KRSManager(db_session)

    with pytest.raises(HTTPException) as exc:

        manager._get_authorized_dosen(
            mahasiswa.nim,
            "198501012010011001"
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Dosen PA mahasiswa belum ditetapkan"


# ==========================================
# 2. NIDN DOSEN TIDAK DITEMUKAN
# COVERAGE KRS_MANAGER BARIS 79
# ==========================================

def test_authorized_dosen_not_found(db_session):

    dosen = Dosen(
        nidn="COV_NIDN_01",
        nama="Dosen Coverage"
    )

    db_session.add(dosen)
    db_session.commit()

    mahasiswa = create_mahasiswa(
        db_session,
        "COV002",
        "cov002@test.com",
        dosen_pa_id=dosen.id
    )

    manager = KRSManager(db_session)

    with pytest.raises(HTTPException) as exc:

        manager._get_authorized_dosen(
            mahasiswa.nim,
            "NIDN_TIDAK_ADA"
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Dosen dengan NIDN tersebut tidak ditemukan"


# ==========================================
# 3. DOSEN TIDAK BERWENANG
# COVERAGE KRS_MANAGER BARIS 85
# ==========================================

def test_authorized_dosen_forbidden(db_session):

    dosen_pa = Dosen(
        nidn="COV_PA_01",
        nama="Dosen PA Mahasiswa"
    )

    dosen_lain = Dosen(
        nidn="COV_PA_02",
        nama="Dosen Lain"
    )

    db_session.add_all([
        dosen_pa,
        dosen_lain
    ])

    db_session.commit()

    mahasiswa = create_mahasiswa(
        db_session,
        "COV003",
        "cov003@test.com",
        dosen_pa_id=dosen_pa.id
    )

    manager = KRSManager(db_session)

    with pytest.raises(HTTPException) as exc:

        manager._get_authorized_dosen(
            mahasiswa.nim,
            dosen_lain.nidn
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Dosen tidak berwenang mengelola KRS mahasiswa ini"


# ==========================================
# 4. TEST ENDPOINT SUBMIT KRS
# COVERAGE ROUTER BARIS 81-83
# ==========================================

def test_submit_krs_router(client, monkeypatch):

    def fake_submit(self, nim):
        return {
            "message": "KRS berhasil disubmit",
            "status": "SUBMITTED"
        }

    monkeypatch.setattr(
        krs_router.KRSManager,
        "submit_krs",
        fake_submit
    )

    response = client.post(
        "/api/krs/submit/COV001"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "SUBMITTED"


# ==========================================
# 5. TEST ENDPOINT APPROVE KRS
# COVERAGE ROUTER BARIS 96-98
# ==========================================

def test_approve_krs_router(client, monkeypatch):

    def fake_approve(
        self,
        nim,
        nidn_dosen_pa
    ):
        return {
            "message": "KRS berhasil disetujui",
            "status": "APPROVED"
        }

    monkeypatch.setattr(
        krs_router.KRSManager,
        "approve_krs",
        fake_approve
    )

    response = client.post(
        "/api/krs/approve/COV001",
        json={
            "nidn_dosen_pa": "198501012010011001"
        }
    )

    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"


# ==========================================
# 6. TEST ENDPOINT REVISE KRS
# COVERAGE ROUTER BARIS 114-116
# ==========================================

def test_revise_krs_router(client, monkeypatch):

    def fake_revise(
        self,
        nim,
        nidn_dosen_pa
    ):
        return {
            "message": "KRS dikembalikan untuk revisi",
            "status": "REVISION"
        }

    monkeypatch.setattr(
        krs_router.KRSManager,
        "revise_krs",
        fake_revise
    )

    response = client.post(
        "/api/krs/revise/COV001",
        json={
            "nidn_dosen_pa": "198501012010011001"
        }
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REVISION"
