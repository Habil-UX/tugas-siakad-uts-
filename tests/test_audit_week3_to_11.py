from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    AppUser,
    Billing,
    CalonMahasiswa,
    Dosen,
    JadwalKuliah,
    JalurMasuk,
    KRS,
    KRSDetail,
    KrsTransition,
    Matakuliah,
    NotificationLog,
    Payment,
    PaymentMethod,
    Prerequisite,
    ProgramStudi,
    RiwayatNilai,
    Ruangan,
    SkalaNilai,
    StatusPendaftaran,
)
from app.services.billing_service import BillingService
from app.services.conflict_detector import (
    detect_all_schedule_conflicts,
    detect_schedule_conflict,
)
from app.services.gpa_calculator import GPACalculator
from app.services.krs.validators import (
    PrerequisiteValidator,
    ValidationResult,
    build_chain,
)
from app.services.krs_manager import KRSManager
from app.services.payment_service import PaymentService
from app.services.pmb_service import approve_calon_mahasiswa, generate_nim
from app.services.scheduler_service import billing_scheduler
from app.utils.security import (
    compute_webhook_signature,
    create_access_token,
    hash_password,
    verify_access_token,
    verify_password,
    verify_webhook_signature,
)


# =====================================================
# 1. AUTHENTICATION, SECURITY & RBAC TESTS
# =====================================================

def test_password_hashing_and_token_lifecycle():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed) is True
    assert verify_password("wrong", hashed) is False
    assert verify_password("secret123", "malformed_hash") is False

    token = create_access_token({"sub": 1, "role": "admin"}, expires_in=3600)
    claims = verify_access_token(token)
    assert claims["sub"] == 1
    assert claims["role"] == "admin"

    with pytest.raises(HTTPException) as exc1:
        verify_access_token("invalid_token_without_dot")
    assert exc1.value.status_code == 401

    with pytest.raises(HTTPException) as exc2:
        verify_access_token(token + "tampered")
    assert exc2.value.status_code == 401

    with pytest.raises(HTTPException) as exc3:
        bad_b64 = "!!!not_base64!!!"
        sig = compute_webhook_signature(bad_b64, secret="siakad-default-hmac-secret-key-2026")
        verify_access_token(f"{bad_b64}.{sig}")
    assert exc3.value.status_code == 401

    expired_token = create_access_token({"sub": 1, "role": "admin"}, expires_in=-10)
    with pytest.raises(HTTPException) as exc4:
        verify_access_token(expired_token)
    assert exc4.value.status_code == 401


def test_auth_router_and_rbac_enforcement(client, db_session):
    reg_res = client.post(
        "/api/auth/register",
        json={
            "username": "mhs_user",
            "password": "password123",
            "role": "mahasiswa",
            "nim": None,
        },
    )
    assert reg_res.status_code == 201

    dup_res = client.post(
        "/api/auth/register",
        json={
            "username": "mhs_user",
            "password": "password123",
            "role": "mahasiswa",
        },
    )
    assert dup_res.status_code == 409

    bad_login = client.post(
        "/api/auth/login",
        json={"username": "mhs_user", "password": "wrongpassword"},
    )
    assert bad_login.status_code == 401

    login_res = client.post(
        "/api/auth/login",
        json={"username": "mhs_user", "password": "password123"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    me_unauth = client.get("/api/auth/me")
    assert me_unauth.status_code == 401

    me_bad_header = client.get(
        "/api/auth/me",
        headers={"Authorization": "Basic 123"},
    )
    assert me_bad_header.status_code == 401

    me_ok = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_ok.status_code == 200
    assert me_ok.json()["username"] == "mhs_user"

    # RBAC: mahasiswa tidak boleh approve pendaftaran PMB (403)
    forbidden_res = client.put(
        "/api/pmb/approve/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert forbidden_res.status_code == 403

    # RBAC via X-User-Role header
    role_header_res = client.put(
        "/api/pmb/approve/1",
        headers={"X-User-Role": "mahasiswa"},
    )
    assert role_header_res.status_code == 403

    # Inactive user check
    user = db_session.query(AppUser).filter_by(username="mhs_user").first()
    user.is_active = False
    db_session.commit()

    inactive_login = client.post(
        "/api/auth/login",
        json={"username": "mhs_user", "password": "password123"},
    )
    assert inactive_login.status_code == 403

    inactive_token_call = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert inactive_token_call.status_code == 401


# =====================================================
# 2. MINGGU 3-4: PMB & TRUE MULTI-THREAD CONCURRENCY NIM (P4)
# =====================================================

def test_pmb_3_arg_generate_nim_and_dosen_pa_assignment(client, db_session):
    nim = generate_nim(2025, "TIF", db_session)
    assert nim == "2025TIF-0001"

    dosen = Dosen(nidn="DSN_PMB_1", nama="Dosen PA PMB")
    db_session.add(dosen)
    db_session.commit()

    reg = client.post(
        "/api/pmb/register",
        json={
            "nama_lengkap": "Calon Mhs PA",
            "email": "pa_pmb@test.com",
            "phone": "081234567890",
            "tanggal_lahir": "2001-05-10",
            "alamat": "Jl. Pendidikan No. 1",
            "program_studi_id": 1,
            "jalur_masuk_id": 1,
        },
    )
    mhs_id = reg.json()["id"]

    res_404 = client.put(f"/api/pmb/approve/{mhs_id}?dosen_pa_id=9999")
    assert res_404.status_code == 404

    res_ok = client.put(f"/api/pmb/approve/{mhs_id}?dosen_pa_id={dosen.id}")
    assert res_ok.status_code == 200

    dosen2 = Dosen(nidn="DSN_PMB_2", nama="Dosen PA Baru")
    db_session.add(dosen2)
    db_session.commit()
    res_idem_404 = client.put(f"/api/pmb/approve/{mhs_id}?dosen_pa_id=8888")
    assert res_idem_404.status_code == 404
    res_idem = client.put(f"/api/pmb/approve/{mhs_id}?dosen_pa_id={dosen2.id}")
    assert res_idem.status_code == 200

    incomplete = CalonMahasiswa(
        nama_lengkap="",
        email="inc@test.com",
        phone="081234567890",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Alamat",
        program_studi_id=1,
        jalur_masuk_id=1,
        status=StatusPendaftaran.pending,
    )
    db_session.add(incomplete)
    db_session.commit()
    with pytest.raises(HTTPException) as exc:
        approve_calon_mahasiswa(db_session, incomplete.id)
    assert exc.value.status_code == 400


def test_concurrent_nim_generation_multithread_file_db(tmp_path):
    """
    P4: Pengujian konkurensi nyata menggunakan ThreadPoolExecutor (8 worker paralel)
    dan Barrier terhadap database SQLite berbasis file.
    Memastikan:
    1. 8 mahasiswa berbeda yang di-approve secara bersamaan oleh 8 thread paralel
       mendapatkan 8 NIM unik berurutan (-0001 s.d. -0008) tanpa duplikasi.
    2. 4 thread paralel yang meng-approve mahasiswa yang sama secara bersamaan
       bersifat idempotent dan mengembalikan 1 NIM yang sama.
    """
    db_file = tmp_path / "concurrent_pmb.db"
    eng = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(eng, "connect")
    def _set_pragma(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA busy_timeout = 30000")
        cur.close()

    Base.metadata.create_all(bind=eng)
    SessionMaker = sessionmaker(bind=eng, autocommit=False, autoflush=False)

    num_workers = 8
    with SessionMaker() as s:
        prodi = ProgramStudi(kode="001", nama="Teknik Informatika", fakultas="Fakultas Teknik")
        jalur = JalurMasuk(kode="SNBT", nama="SNBT")
        s.add_all([prodi, jalur])
        s.commit()
        for i in range(num_workers):
            s.add(
                CalonMahasiswa(
                    nama_lengkap=f"Concurrent {i}",
                    email=f"conc{i}@test.com",
                    phone="081234567890",
                    tanggal_lahir=date(2000, 1, 1),
                    alamat="Jl. Concurrent",
                    program_studi_id=prodi.id,
                    jalur_masuk_id=jalur.id,
                    status=StatusPendaftaran.pending,
                )
            )
        s.commit()

    barrier = threading.Barrier(num_workers)

    def approve_worker(student_id: int) -> str:
        barrier.wait(timeout=10)
        with SessionMaker() as session:
            mhs = approve_calon_mahasiswa(session, student_id)
            return mhs.nim

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        generated_nims = list(executor.map(approve_worker, range(1, num_workers + 1)))

    assert len(generated_nims) == num_workers
    assert len(set(generated_nims)) == num_workers
    sorted_suffixes = sorted(int(n[-4:]) for n in generated_nims)
    assert sorted_suffixes == list(range(1, num_workers + 1))

    # Uji konkurensi idempotent: 4 thread paralel meng-approve mahasiswa ID 1 bersamaan
    idem_barrier = threading.Barrier(4)

    def idempotent_worker(_idx: int) -> str:
        idem_barrier.wait(timeout=10)
        with SessionMaker() as session:
            mhs = approve_calon_mahasiswa(session, 1)
            return mhs.nim

    with ThreadPoolExecutor(max_workers=4) as executor:
        idem_nims = list(executor.map(idempotent_worker, range(4)))

    assert len(set(idem_nims)) == 1
    eng.dispose()


# =====================================================
# 3. MINGGU 5-6 & P2: KRS, PREREQ C VS KELULUSAN D
# =====================================================

def test_p2_grade_d_passed_in_gpa_but_rejected_in_prerequisite(client, db_session):
    """
    P2: Memastikan nilai A, B, C, D dianggap LULUS pada GPACalculator (sedangkan E TIDAK LULUS),
    namun nilai D tetap DITOLAK oleh PrerequisiteValidator (syarat prasyarat minimal C / 2.0).
    """
    scales = {}
    for huruf, bobot in [("A", 4.0), ("B", 3.0), ("C", 2.0), ("D", 1.0), ("E", 0.0)]:
        sk = SkalaNilai(nilai_huruf=huruf, bobot=bobot)
        db_session.add(sk)
        scales[huruf] = sk
    db_session.commit()

    mhs = CalonMahasiswa(
        nama_lengkap="Mhs P2",
        email="mhs_p2@test.com",
        phone="081234567890",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Jl. P2",
        program_studi_id=1,
        jalur_masuk_id=1,
        status=StatusPendaftaran.approved,
        nim="2025001-0200",
    )
    mk_dasar = Matakuliah(
        kode_mk="IF101",
        nama_mk="Algoritma Dasar",
        sks=3,
        semester=1,
        jenis_mk="Wajib",
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
    )
    mk_lanjut = Matakuliah(
        kode_mk="IF201",
        nama_mk="Struktur Data",
        sks=3,
        semester=2,
        jenis_mk="Wajib",
        hari="Selasa",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
    )
    mk_e = Matakuliah(
        kode_mk="IF102",
        nama_mk="Fisika",
        sks=2,
        semester=1,
        jenis_mk="Wajib",
        hari="Rabu",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
    )
    db_session.add_all([mhs, mk_dasar, mk_lanjut, mk_e])
    db_session.commit()

    db_session.add(Prerequisite(matakuliah_id=mk_lanjut.id, prerequisite_id=mk_dasar.id))
    # Berikan nilai D (1.0) untuk IF101 dan E (0.0) untuk IF102 pada semester 1
    db_session.add(
        RiwayatNilai(
            nim=mhs.nim,
            matakuliah_id=mk_dasar.id,
            skala_nilai_id=scales["D"].id,
            semester=1,
            presensi_persen=85.0,
            created_by="Dosen",
            version=1,
        )
    )
    db_session.add(
        RiwayatNilai(
            nim=mhs.nim,
            matakuliah_id=mk_e.id,
            skala_nilai_id=scales["E"].id,
            semester=1,
            presensi_persen=80.0,
            created_by="Dosen",
            version=1,
        )
    )
    db_session.commit()

    # 1. GPACalculator harus menghitung D sebagai LULUS (3 SKS, bobot 1.0) dan E sebagai TIDAK LULUS
    calc = GPACalculator(db_session)
    ipk_info = calc.calculate_ipk(mhs.nim)
    assert ipk_info["total_sks"] == 5
    assert ipk_info["total_sks_lulus"] == 3
    assert ipk_info["ipk"] == 1.0

    trans = calc.get_transcript(mhs.nim)
    status_by_kode = {r["kode_mk"]: r["status"] for r in trans["records"]}
    assert status_by_kode["IF101"] == "LULUS"
    assert status_by_kode["IF102"] == "TIDAK LULUS"

    # 2. PrerequisiteValidator harus MENOLAK pengambilan IF201 karena nilai IF101 baru D (< C)
    krs_sem2 = KRS(
        nim=mhs.nim,
        semester_akademik=2,
        tahun_akademik="2025/2026",
        total_sks=0,
        status="DRAFT",
    )
    db_session.add(krs_sem2)
    db_session.commit()

    prereq_val = PrerequisiteValidator()
    res_d = prereq_val.validate(
        {"db": db_session, "nim": mhs.nim, "krs": krs_sem2, "new_mk": mk_lanjut}
    )
    assert res_d.is_valid is False
    assert "Algoritma Dasar" in res_d.message

    # 3. Jika mahasiswa mengulang IF101 dan mendapat C (2.0), prasyarat terpenuhi & IPK naik ke 2.0
    rn_d = db_session.query(RiwayatNilai).filter_by(nim=mhs.nim, matakuliah_id=mk_dasar.id).first()
    rn_d.skala_nilai_id = scales["C"].id
    db_session.commit()

    res_c = prereq_val.validate(
        {"db": db_session, "nim": mhs.nim, "krs": krs_sem2, "new_mk": mk_lanjut}
    )
    assert res_c.is_valid is True
    assert calc.calculate_ipk(mhs.nim)["ipk"] == 2.0


def test_krs_chain_collect_all_strategy_and_prereq_previous_semester(client, db_session):
    mhs = CalonMahasiswa(
        nama_lengkap="Mhs KRS",
        email="mhs_krs_strat@test.com",
        phone="081234567890",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Jl. KRS",
        program_studi_id=1,
        jalur_masuk_id=1,
        status=StatusPendaftaran.approved,
        nim="2025001-0100",
    )
    dosen = Dosen(nidn="DSN_KRS_1", nama="Dosen PA KRS")
    mk_prereq = Matakuliah(
        kode_mk="IF100",
        nama_mk="Kalkulus I",
        sks=4,
        semester=1,
        jenis_mk="Wajib",
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
    )
    mk_target = Matakuliah(
        kode_mk="IF200",
        nama_mk="Kalkulus II",
        sks=22,
        semester=2,
        jenis_mk="Wajib",
        hari="Senin",
        jam_mulai=time(9, 0),
        jam_selesai=time(11, 0),
    )
    skala_c = SkalaNilai(nilai_huruf="C", bobot=2.0)
    db_session.add_all([mhs, dosen, mk_prereq, mk_target, skala_c])
    db_session.commit()

    mhs.dosen_pa_id = dosen.id
    prereq = Prerequisite(matakuliah_id=mk_target.id, prerequisite_id=mk_prereq.id)
    krs = KRS(
        nim=mhs.nim,
        semester_akademik=1,
        tahun_akademik="2025/2026",
        total_sks=4,
        status="DRAFT",
    )
    db_session.add_all([prereq, krs])
    db_session.commit()
    db_session.add(KRSDetail(krs_id=krs.id, matakuliah_id=mk_prereq.id))
    db_session.commit()

    chain_collect = build_chain(stop_on_first_error=False)
    res_collect = chain_collect.validate(
        {
            "db": db_session,
            "nim": mhs.nim,
            "krs": krs,
            "new_mk": mk_target,
        }
    )
    assert res_collect.is_valid is False
    assert len(res_collect.detail["errors"]) == 3

    exp_res = client.get(f"/api/krs/explain-prerequisite/{mhs.nim}/{mk_target.id}?semester=2")
    assert exp_res.status_code == 200
    assert len(exp_res.json()["query_plan"]) > 0

    get_res = client.get(f"/api/krs/{mhs.nim}")
    assert get_res.status_code == 200
    assert get_res.json()["total_sks"] == 4

    other_token = create_access_token({"role": "mahasiswa", "nim": "OTHER_NIM"})
    for ep, body in [
        ("/api/krs/add", {"nim": mhs.nim, "kode_mk": "IF100"}),
        ("/api/krs/remove", {"nim": mhs.nim, "kode_mk": "IF100"}),
    ]:
        r = client.post(ep, json=body, headers={"Authorization": f"Bearer {other_token}"})
        assert r.status_code == 403
    r_sub = client.post(
        f"/api/krs/submit/{mhs.nim}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert r_sub.status_code == 403

    client.post(f"/api/krs/submit/{mhs.nim}")
    rev_missing = client.post(f"/api/krs/revise/{mhs.nim}", json={})
    assert rev_missing.status_code == 400
    app_missing = client.post(f"/api/krs/approve/{mhs.nim}", json={})
    assert app_missing.status_code == 400

    rev_res = client.post(
        f"/api/krs/revise/{mhs.nim}",
        json={"dosen_pa_id": dosen.id},
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["status"] == "REVISION"

    client.post(f"/api/krs/submit/{mhs.nim}")
    app_res = client.post(
        f"/api/krs/approve/{mhs.nim}",
        json={"dosen_pa_id": dosen.id},
    )
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "APPROVED"


def test_submit_empty_krs_rejected(client, db_session):
    mhs = CalonMahasiswa(
        nama_lengkap="Empty KRS",
        email="empty_krs@test.com",
        phone="081234567890",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Jl. Kosong",
        program_studi_id=1,
        jalur_masuk_id=1,
        status=StatusPendaftaran.approved,
        nim="2025001-0101",
    )
    db_session.add(mhs)
    db_session.commit()

    res = client.post(f"/api/krs/submit/{mhs.nim}")
    assert res.status_code == 400
    assert "KRS tidak boleh kosong" in res.json()["detail"]


# =====================================================
# 4. MINGGU 7-8 & P3: JADWAL KULIAH SEBAGAI SUMBER AKTUAL KRS
# =====================================================

def test_p3_schedule_change_revalidates_krs_using_jadwal_kuliah(client, db_session):
    """
    P3: Memastikan JadwalKuliah menjadi sumber data aktual validasi konflik KRS
    tanpa menimpa kolom jadwal pada Matakuliah:
    - Ketika JadwalKuliah diubah sehingga bentrok dengan MK lain di KRS mahasiswa:
      1. Matakuliah asli tidak ditimpa.
      2. KRS mahasiswa terdampak ditandai needs_review = True.
      3. KrsTransition mencatat perubahan akibat jadwal bentrok.
      4. Notifikasi Observer terkirim setelah transaksi commit.
      5. Validasi ulang KRS membaca JadwalKuliah terbaru dan mendeteksi konflik.
    """
    mhs = CalonMahasiswa(
        nama_lengkap="Mhs Jadwal KRS",
        email="mhs_p3@test.com",
        phone="081234567890",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Jl. P3",
        program_studi_id=1,
        jalur_masuk_id=1,
        status=StatusPendaftaran.approved,
        nim="2025001-0300",
    )
    mk1 = Matakuliah(
        kode_mk="IF301",
        nama_mk="Jaringan Komputer",
        sks=3,
        semester=3,
        jenis_mk="Wajib",
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
    )
    mk2 = Matakuliah(
        kode_mk="IF302",
        nama_mk="Keamanan Informasi",
        sks=3,
        semester=3,
        jenis_mk="Wajib",
        hari="Selasa",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
    )
    d1 = Dosen(nidn="D_SCH_1", nama="Dosen Satu")
    d2 = Dosen(nidn="D_SCH_2", nama="Dosen Dua")
    r1 = Ruangan(kode_ruangan="R301", nama_ruangan="Lab Jarkom 1", kapasitas=40, is_active=True)
    r2 = Ruangan(kode_ruangan="R302", nama_ruangan="Lab Jarkom 2", kapasitas=40, is_active=True)
    db_session.add_all([mhs, mk1, mk2, d1, d2, r1, r2])
    db_session.commit()

    # Buat jadwal awal di JadwalKuliah: MK1 Senin 08-10 (R301), MK2 Selasa 08-10 (R302)
    c1 = client.post(
        "/api/schedules",
        json={
            "matakuliah_id": mk1.id,
            "dosen_id": d1.id,
            "ruangan_id": r1.id,
            "hari": "Senin",
            "jam_mulai": "08:00",
            "jam_selesai": "10:00",
            "tahun_akademik": "2025/2026",
            "semester_akademik": 1,
        },
    )
    assert c1.status_code == 200
    sched1_id = c1.json()["id"]

    c2 = client.post(
        "/api/schedules",
        json={
            "matakuliah_id": mk2.id,
            "dosen_id": d2.id,
            "ruangan_id": r2.id,
            "hari": "Selasa",
            "jam_mulai": "08:00",
            "jam_selesai": "10:00",
            "tahun_akademik": "2025/2026",
            "semester_akademik": 1,
        },
    )
    assert c2.status_code == 200
    sched2_id = c2.json()["id"]

    # Mahasiswa mengambil MK1 dan MK2 di KRS (tidak bentrok)
    assert client.post("/api/krs/add", json={"nim": mhs.nim, "kode_mk": "IF301"}).status_code == 200
    assert client.post("/api/krs/add", json={"nim": mhs.nim, "kode_mk": "IF302"}).status_code == 200
    val_before = client.get(f"/api/krs/validate/{mhs.nim}").json()
    assert val_before["is_valid"] is True

    # Ubah jadwal MK2 di JadwalKuliah menjadi Senin 09:00-11:00 (di Ruangan R302 & Dosen D2,
    # sehingga tidak bentrok ruangan/dosen di JadwalKuliah, tetapi BENTROK waktu di KRS mahasiswa!)
    upd_res = client.put(
        f"/api/schedules/{sched2_id}",
        json={"hari": "Senin", "jam_mulai": "09:00", "jam_selesai": "11:00"},
    )
    assert upd_res.status_code == 200

    # 1. Kolom hari pada Matakuliah tidak ditimpa secara langsung (tetap 'Selasa')
    db_session.refresh(mk2)
    assert mk2.hari == "Selasa"

    # 2. KRS mahasiswa terdampak ditandai needs_review = True
    krs_row = db_session.query(KRS).filter_by(nim=mhs.nim).first()
    assert krs_row.needs_review is True

    # 3. KrsTransition mencatat deteksi konflik akibat perubahan jadwal
    transitions = db_session.query(KrsTransition).filter_by(krs_id=krs_row.id).all()
    assert any("CONFLICT_DETECTED" in t.changed_by for t in transitions)

    # 4. Validasi ulang KRS membaca JadwalKuliah terbaru dan mendeteksi bentrok!
    val_after = client.get(f"/api/krs/validate/{mhs.nim}").json()
    assert val_after["is_valid"] is False
    assert any("Jadwal bentrok" in err for err in val_after["errors"])

    # Uji juga deteksi 3rd dimension (time_overlap untuk MK yang sama) & dashboard
    j_extra = JadwalKuliah(
        matakuliah_id=mk1.id,
        dosen_id=d2.id,
        ruangan_id=r2.id,
        hari="Senin",
        jam_mulai=time(8, 30),
        jam_selesai=time(10, 30),
        tahun_akademik="2025/2026",
        semester_akademik=1,
        status="AKTIF",
    )
    db_session.add(j_extra)
    db_session.commit()

    conf_res = client.get("/api/schedules/conflicts")
    assert conf_res.status_code == 200
    assert any(c["type"] == "time_overlap" for c in conf_res.json()["conflicts"])

    dash_res = client.get("/api/admin/scheduling/dashboard")
    assert dash_res.status_code == 200
    assert dash_res.json()["total_jadwal"] >= 2

    del_res = client.delete(f"/api/schedules/{sched1_id}")
    assert del_res.status_code == 200


# =====================================================
# 5. MINGGU 9-10 & 11 (P1 & P5): APSCHEDULER, UI, FINANCE & KRS
# =====================================================

def test_p1_apscheduler_and_p5_grades_ui_and_finance_integration(client, db_session):
    # P1: Verifikasi APScheduler BackgroundScheduler & CronTrigger
    assert isinstance(billing_scheduler.scheduler, BackgroundScheduler)
    sched_status = client.get("/api/billing/scheduler/status")
    assert sched_status.status_code == 200
    status_json = sched_status.json()
    assert status_json["scheduler_class"] == "BackgroundScheduler"
    job_ids = {j["id"] for j in status_json["jobs"]}
    assert {"semester_billing_generator", "overdue_billing_reminder"} <= job_ids

    # P5: Verifikasi form edit nilai pada /grades-ui
    grades_ui = client.get("/grades-ui")
    assert grades_ui.status_code == 200
    assert "updateGrade" in grades_ui.text
    assert "u_reason" in grades_ui.text
    assert client.get("/finance-dashboard").status_code == 200

    # Empty AI report before any billings
    empty_ai = client.get("/api/billing/ai-report")
    assert empty_ai.status_code == 200
    assert empty_ai.json()["total_mahasiswa_tertagih"] == 0

    prodi_si = ProgramStudi(
        kode="SIF",
        nama="Sistem Informasi",
        fakultas="Fakultas Ilmu Komputer",
        tarif_spp=Decimal("4500000.00"),
    )
    dosen = Dosen(nidn="DSN_FIN_1", nama="Dosen PA Finance")
    mk = Matakuliah(
        kode_mk="SIF101",
        nama_mk="Rekayasa Perangkat Lunak",
        sks=3,
        semester=1,
        jenis_mk="Wajib",
        hari="Rabu",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
    )
    db_session.add_all([prodi_si, dosen, mk])
    db_session.commit()

    mhs = CalonMahasiswa(
        nama_lengkap="Mahasiswa Finance",
        email="fin_mhs@test.com",
        phone="081234567890",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Jl. Keuangan",
        program_studi_id=prodi_si.id,
        jalur_masuk_id=1,
        dosen_pa_id=dosen.id,
        status=StatusPendaftaran.approved,
        nim="2025SIF-0001",
    )
    db_session.add(mhs)
    db_session.commit()

    # 1. Generate semester billing (idempotent)
    past_start = date.today() - timedelta(days=90)
    gen1 = client.post(
        "/api/billing/generate-semester",
        json={
            "semester": 1,
            "tahun": "2025/2026",
            "semester_start_date": str(past_start),
        },
    )
    assert gen1.status_code == 200
    assert gen1.json()["created_count"] == 1
    billing_id = gen1.json()["created_billings"][0]["billing_id"]

    gen2 = client.post(
        "/api/billing/generate-semester",
        json={
            "semester": 1,
            "tahun": "2025/2026",
            "semester_start_date": str(past_start),
        },
    )
    assert gen2.status_code == 200
    assert gen2.json()["created_count"] == 0
    assert gen2.json()["skipped_count"] == 1

    with pytest.raises(HTTPException) as exc_sem:
        BillingService(db_session).generate_semester_billing(0, "2025/2026")
    assert exc_sem.value.status_code == 400

    # 2. Run overdue reminders via scheduler endpoint & direct job helper
    rem_res = client.post("/api/billing/reminders/run")
    assert rem_res.status_code == 200
    assert rem_res.json()["reminders_sent"] == 1

    assert billing_scheduler.start()["status"] == "running"
    assert (
        billing_scheduler.run_semester_billing_job(
            db_session, semester=1, tahun="2025/2026"
        )["skipped_count"]
        >= 1
    )
    billing_scheduler._scheduled_semester_billing_task()
    billing_scheduler._scheduled_overdue_reminder_task()
    assert billing_scheduler.shutdown()["status"] == "stopped"

    # 3. KRS BLOCKED when student has overdue billing
    block_add = client.post(
        "/api/krs/add",
        json={"nim": mhs.nim, "kode_mk": "SIF101"},
    )
    assert block_add.status_code == 403
    assert "tunggakan" in block_add.json()["detail"].lower()

    block_sub = client.post(f"/api/krs/submit/{mhs.nim}")
    assert block_sub.status_code == 403

    # 4. Partial payment via /api/payments/process
    part_res = client.post(
        "/api/payments/process",
        json={
            "billing_id": billing_id,
            "amount": "2000000.00",
            "method": "BANK_TRANSFER",
            "reference_number": "TX-PART-001",
        },
    )
    assert part_res.status_code == 200
    assert part_res.json()["payment_status"] == "success"

    part_idem = client.post(
        "/api/payments/process",
        json={
            "billing_id": billing_id,
            "amount": "2000000.00",
            "method": "BANK_TRANSFER",
            "reference_number": "TX-PART-001",
        },
    )
    assert part_idem.status_code == 200
    assert part_idem.json()["idempotent"] is True

    part_conflict = client.post(
        "/api/payments/process",
        json={
            "billing_id": billing_id,
            "amount": "500000.00",
            "method": "BANK_TRANSFER",
            "reference_number": "TX-PART-001",
        },
    )
    assert part_conflict.status_code == 409

    dash_data = client.get("/api/billing/dashboard").json()
    assert len(dash_data["per_mahasiswa"]) == 1
    assert len(dash_data["daftar_mahasiswa_menunggak"]) == 1

    ai_data = client.get("/api/billing/ai-report").json()
    assert Decimal(ai_data["total_revenue_this_month"]) == Decimal("2000000.00")
    assert len(ai_data["top_10_mahasiswa_tunggakan_terbesar"]) == 1
    assert "Kirim reminder ke 1 mahasiswa" in ai_data["rekomendasi"]

    # 5. Webhook simulation for remaining 2,500,000.00
    webhook_payload = {
        "transaction_id": "WH-FULL-002",
        "billing_id": billing_id,
        "amount": "2500000.00",
        "status": "paid",
        "method": "VIRTUAL_ACCOUNT",
    }

    wh_bad = client.post(
        "/api/payments/webhook",
        json=webhook_payload,
        headers={"X-Webhook-Signature": "invalid_sig"},
    )
    assert wh_bad.status_code == 401

    sig_res = client.post(
        "/api/payments/webhook/simulate-signature",
        json=webhook_payload,
    )
    assert sig_res.status_code == 200
    valid_sig = sig_res.json()["signature"]

    wh_ok = client.post(
        "/api/payments/webhook",
        json=webhook_payload,
        headers={"X-Webhook-Signature": valid_sig},
    )
    assert wh_ok.status_code == 200
    assert wh_ok.json()["billing_status"] == "paid"

    wh_dup = client.post(
        "/api/payments/webhook",
        json=webhook_payload,
        headers={"X-Webhook-Signature": valid_sig},
    )
    assert wh_dup.status_code == 200
    assert wh_dup.json()["idempotent"] is True

    over_pay = client.post(
        "/api/payments/process",
        json={
            "billing_id": billing_id,
            "amount": "100000.00",
            "method": "CASH",
        },
    )
    assert over_pay.status_code == 409

    # 6. KRS UNBLOCKED once arrears are paid in full
    unblock_add = client.post(
        "/api/krs/add",
        json={"nim": mhs.nim, "kode_mk": "SIF101"},
    )
    assert unblock_add.status_code == 200
    assert unblock_add.json()["total_sks"] == 3

    unblock_sub = client.post(f"/api/krs/submit/{mhs.nim}")
    assert unblock_sub.status_code == 200
    assert unblock_sub.json()["status"] == "SUBMITTED"
