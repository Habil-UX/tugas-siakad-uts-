from datetime import date, datetime, time, timedelta
import io

import jwt
from openpyxl import load_workbook
import pytest

from app.models import (
    AttendanceQRToken,
    AttendanceRecord,
    AttendanceScanAttempt,
    AttendanceSession,
    CalonMahasiswa,
    Dosen,
    JadwalKuliah,
    KRS,
    KRSDetail,
    Matakuliah,
    Ruangan,
    StatusPendaftaran,
)
from app.services.ai_attendance_analyzer import AIAttendanceAnalyzer
from app.services.attendance_report_service import AttendanceReportService
from app.services.attendance_service import (
    AttendanceService,
    generate_attendance_qr,
    get_jwt_secret,
    qr_image_to_png_bytes,
)
from app.utils.security import create_access_token


def _seed_week12_environment(db_session):
    """
    Membuat data uji lengkap:
    - 2 Dosen (dosen_1 pengampu IF401, dosen_2 pengampu IF402)
    - 2 Ruangan
    - 2 Mata Kuliah (IF401 pada Senin 08:00-10:00, IF402 pada Selasa 07:00-09:00)
    - 2 JadwalKuliah
    - 3 Mahasiswa:
      - mhs_1 (terdaftar di IF401 pada KRS APPROVED)
      - mhs_2 (terdaftar di IF401 pada KRS APPROVED)
      - mhs_other (hanya terdaftar di IF402, BUKAN peserta IF401)
      - mhs_unapproved (KRS masih DRAFT, belum APPROVED)
    """
    dosen_1 = Dosen(nidn="198801012015011001", nama="Dr. Budi Santoso")
    dosen_2 = Dosen(nidn="198902022016011002", nama="Dr. Siti Aminah")
    ruangan_1 = Ruangan(
        kode_ruangan="LAB-A1",
        nama_ruangan="Lab AI 1",
        kapasitas=40,
        is_active=True,
    )
    ruangan_2 = Ruangan(
        kode_ruangan="LAB-B2",
        nama_ruangan="Lab Jarkom 2",
        kapasitas=40,
        is_active=True,
    )
    mk_1 = Matakuliah(
        kode_mk="IF401",
        nama_mk="Kecerdasan Buatan",
        sks=3,
        semester=5,
        jenis_mk="Wajib",
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
    )
    mk_2 = Matakuliah(
        kode_mk="IF402",
        nama_mk="Pemrograman Jaringan",
        sks=3,
        semester=5,
        jenis_mk="Wajib",
        hari="Selasa",
        jam_mulai=time(7, 0),
        jam_selesai=time(9, 0),
    )
    db_session.add_all([dosen_1, dosen_2, ruangan_1, ruangan_2, mk_1, mk_2])
    db_session.commit()

    sched_1 = JadwalKuliah(
        matakuliah_id=mk_1.id,
        dosen_id=dosen_1.id,
        ruangan_id=ruangan_1.id,
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
        tahun_akademik="2026/2027",
        semester_akademik=1,
        status="AKTIF",
    )
    sched_2 = JadwalKuliah(
        matakuliah_id=mk_2.id,
        dosen_id=dosen_2.id,
        ruangan_id=ruangan_2.id,
        hari="Selasa",
        jam_mulai=time(7, 0),
        jam_selesai=time(9, 0),
        tahun_akademik="2026/2027",
        semester_akademik=1,
        status="AKTIF",
    )
    db_session.add_all([sched_1, sched_2])
    db_session.commit()

    mhs_1 = CalonMahasiswa(
        nama_lengkap="Andi Pratama",
        email="andi.w12@example.com",
        phone="081234567001",
        tanggal_lahir=date(2004, 3, 10),
        alamat="Jl. Merdeka No. 1",
        program_studi_id=1,
        jalur_masuk_id=1,
        dosen_pa_id=dosen_1.id,
        status=StatusPendaftaran.approved,
        nim="2026TIF-0101",
    )
    mhs_2 = CalonMahasiswa(
        nama_lengkap="Bela Kusuma",
        email="bela.w12@example.com",
        phone="081234567002",
        tanggal_lahir=date(2004, 6, 15),
        alamat="Jl. Merdeka No. 2",
        program_studi_id=1,
        jalur_masuk_id=1,
        dosen_pa_id=dosen_1.id,
        status=StatusPendaftaran.approved,
        nim="2026TIF-0102",
    )
    mhs_other = CalonMahasiswa(
        nama_lengkap="Citra Lestari",
        email="citra.w12@example.com",
        phone="081234567003",
        tanggal_lahir=date(2004, 8, 20),
        alamat="Jl. Merdeka No. 3",
        program_studi_id=1,
        jalur_masuk_id=1,
        dosen_pa_id=dosen_2.id,
        status=StatusPendaftaran.approved,
        nim="2026TIF-0103",
    )
    mhs_unapproved = CalonMahasiswa(
        nama_lengkap="Doni Draft",
        email="doni.w12@example.com",
        phone="081234567004",
        tanggal_lahir=date(2004, 9, 25),
        alamat="Jl. Merdeka No. 4",
        program_studi_id=1,
        jalur_masuk_id=1,
        dosen_pa_id=dosen_1.id,
        status=StatusPendaftaran.approved,
        nim="2026TIF-0104",
    )
    db_session.add_all([mhs_1, mhs_2, mhs_other, mhs_unapproved])
    db_session.commit()

    krs_1 = KRS(
        nim=mhs_1.nim,
        semester_akademik=5,
        tahun_akademik="2026/2027",
        total_sks=6,
        status="APPROVED",
    )
    krs_2 = KRS(
        nim=mhs_2.nim,
        semester_akademik=5,
        tahun_akademik="2026/2027",
        total_sks=6,
        status="APPROVED",
    )
    krs_other = KRS(
        nim=mhs_other.nim,
        semester_akademik=5,
        tahun_akademik="2026/2027",
        total_sks=3,
        status="APPROVED",
    )
    krs_draft = KRS(
        nim=mhs_unapproved.nim,
        semester_akademik=5,
        tahun_akademik="2026/2027",
        total_sks=3,
        status="DRAFT",
    )
    db_session.add_all([krs_1, krs_2, krs_other, krs_draft])
    db_session.commit()

    db_session.add_all(
        [
            KRSDetail(krs_id=krs_1.id, matakuliah_id=mk_1.id),
            KRSDetail(krs_id=krs_1.id, matakuliah_id=mk_2.id),
            KRSDetail(krs_id=krs_2.id, matakuliah_id=mk_1.id),
            KRSDetail(krs_id=krs_2.id, matakuliah_id=mk_2.id),
            KRSDetail(krs_id=krs_other.id, matakuliah_id=mk_2.id),
            KRSDetail(krs_id=krs_draft.id, matakuliah_id=mk_1.id),
        ]
    )
    db_session.commit()

    return {
        "dosen_1": dosen_1,
        "dosen_2": dosen_2,
        "mk_1": mk_1,
        "mk_2": mk_2,
        "sched_1": sched_1,
        "sched_2": sched_2,
        "mhs_1": mhs_1,
        "mhs_2": mhs_2,
        "mhs_other": mhs_other,
        "mhs_unapproved": mhs_unapproved,
    }


# =====================================================
# 1. PENGUJIAN QR GENERATION SERVICE (30%)
# =====================================================

def test_qr_generation_png_jwt_expiry_and_unique_jti(client, db_session):
    env = _seed_week12_environment(db_session)
    sched_1 = env["sched_1"]

    # Uji fungsi langsung generate_attendance_qr(schedule_id, valid_minutes=15)
    qr_img_1, token_1 = generate_attendance_qr(
        sched_1.id,
        valid_minutes=15,
        db=db_session,
        session_date=date(2026, 11, 16),  # Senin
        current_time=datetime(2026, 11, 16, 8, 0, 0),
    )
    png_bytes = qr_image_to_png_bytes(qr_img_1)
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    decoded_1 = jwt.decode(
        token_1,
        get_jwt_secret(),
        algorithms=["HS256"],
        options={"verify_exp": False},
    )
    assert decoded_1["schedule_id"] == sched_1.id
    assert decoded_1["session_id"] >= 1
    assert "jti" in decoded_1
    assert decoded_1["exp"] - decoded_1["iat"] == 15 * 60

    # Uji keunikan jti pada penerbitan kedua
    _, token_2 = generate_attendance_qr(
        sched_1.id,
        valid_minutes=15,
        db=db_session,
        session_date=date(2026, 11, 16),
        current_time=datetime(2026, 11, 16, 8, 5, 0),
    )
    decoded_2 = jwt.decode(
        token_2,
        get_jwt_secret(),
        algorithms=["HS256"],
        options={"verify_exp": False},
    )
    assert decoded_1["jti"] != decoded_2["jti"]

    # Uji endpoint GET /attendance/qr/{schedule_id} mengembalikan image/png + header countdown
    res_png = client.get(
        f"/attendance/qr/{sched_1.id}?session_date=2026-11-16",
        headers={"X-User-Role": "dosen", "X-User-Nidn": env["dosen_1"].nidn},
    )
    assert res_png.status_code == 200
    assert res_png.headers["content-type"] == "image/png"
    assert res_png.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert int(res_png.headers["X-Attendance-Expires-In"]) <= 900
    assert res_png.headers["X-Attendance-JTI"] != ""

    # Uji jadwal tidak ditemukan -> 404
    res_404 = client.get(
        "/attendance/qr/99999",
        headers={"X-User-Role": "dosen"},
    )
    assert res_404.status_code == 404


def test_lecturer_authorization_on_qr_generation(client, db_session):
    env = _seed_week12_environment(db_session)
    sched_1 = env["sched_1"]

    # Dosen 2 mencoba membuat QR untuk jadwal Dosen 1 -> Ditolak 403
    res_other_lecturer = client.get(
        f"/attendance/qr/{sched_1.id}",
        headers={"X-User-Role": "dosen", "X-User-Nidn": env["dosen_2"].nidn},
    )
    assert res_other_lecturer.status_code == 403
    assert "tidak berwenang" in res_other_lecturer.json()["detail"].lower()

    # Mahasiswa mencoba membuat QR -> Ditolak 403
    res_mhs = client.get(
        f"/attendance/qr/{sched_1.id}",
        headers={"X-User-Role": "mahasiswa"},
    )
    assert res_mhs.status_code == 403


# =====================================================
# 2. PENGUJIAN SCAN VALIDATION, HADIR vs TERLAMBAT & RE-ISSUE QR (30%)
# =====================================================

def test_scan_hadir_terlambat_late_reissue_and_over_30m_rejected(client, db_session):
    env = _seed_week12_environment(db_session)
    sched_1 = env["sched_1"]
    mhs_1 = env["mhs_1"]
    mhs_2 = env["mhs_2"]
    svc = AttendanceService(db_session)

    # Senin, 16 Nov 2026 pukul 08:00:00 (Jadwal kuliah mulai pukul 08:00)
    monday_date = date(2026, 11, 16)
    qr_normal = svc.generate_qr(
        schedule_id=sched_1.id,
        valid_minutes=15,
        session_date=monday_date,
        current_time=datetime(2026, 11, 16, 8, 0, 0),
        phase="NORMAL",
    )
    assert qr_normal["phase"] == "NORMAL"

    # 1. Mahasiswa 1 scan pada pukul 08:10 (10 menit sejak mulai) -> HADIR
    res_hadir = client.post(
        "/attendance/scan",
        json={
            "token": qr_normal["token"],
            "nim": mhs_1.nim,
            "scan_time": "2026-11-16T08:10:00",
        },
    )
    assert res_hadir.status_code == 200
    body_hadir = res_hadir.json()
    assert body_hadir["success"] is True
    assert body_hadir["status"] == "hadir"
    assert body_hadir["attendance_status"] == "HADIR"

    # 2. Mahasiswa 1 mencoba scan duplikat pada sesi yang sama -> Ditolak 409
    res_dup = client.post(
        "/attendance/scan",
        json={
            "token": qr_normal["token"],
            "nim": mhs_1.nim,
            "scan_time": "2026-11-16T08:11:00",
        },
    )
    assert res_dup.status_code == 409
    assert "duplikat" in res_dup.json()["detail"].lower()

    # 3. Mahasiswa 2 mencoba scan menggunakan QR pertama pada pukul 08:20 (QR pertama sudah >15m expired) -> Ditolak 400
    res_exp_qr1 = client.post(
        "/attendance/scan",
        json={
            "token": qr_normal["token"],
            "nim": mhs_2.nim,
            "scan_time": "2026-11-16T08:20:00",
        },
    )
    assert res_exp_qr1.status_code == 400
    assert "expired" in res_exp_qr1.json()["detail"].lower()

    # 4. Dosen menerbitkan QR baru pada pukul 08:16 untuk periode keterlambatan (15-30m)
    qr_late = svc.generate_qr(
        schedule_id=sched_1.id,
        valid_minutes=15,
        session_date=monday_date,
        current_time=datetime(2026, 11, 16, 8, 16, 0),
    )
    assert qr_late["phase"] == "LATE"
    assert qr_late["jti"] != qr_normal["jti"]
    # Masa berlaku QR kedua otomatis dibatasi tidak melewati 08:30:00 (14 menit = 840 detik)
    assert qr_late["expires_in_seconds"] == 14 * 60

    # 5. Mahasiswa 2 scan QR kedua pada pukul 08:22 (22 menit sejak mulai kuliah) -> TERLAMBAT
    res_late = client.post(
        "/attendance/scan",
        json={
            "token": qr_late["token"],
            "nim": mhs_2.nim,
            "scan_time": "2026-11-16T08:22:00",
        },
    )
    assert res_late.status_code == 200
    body_late = res_late.json()
    assert body_late["success"] is True
    assert body_late["status"] == "terlambat"
    assert body_late["attendance_status"] == "TERLAMBAT"

    # 6. Uji scan setelah 30 menit (> 08:30) -> Ditolak 400
    qr_late_2 = svc.generate_qr(
        schedule_id=sched_1.id,
        valid_minutes=15,
        session_date=monday_date,
        current_time=datetime(2026, 11, 16, 8, 25, 0),
        revoke_previous=False,
    )
    # Paksa perpanjang expires_at di DB & payload untuk menguji guard > 30 menit secara terisolasi
    tok_row = db_session.query(AttendanceQRToken).filter_by(jti=qr_late_2["jti"]).first()
    tok_row.expires_at = datetime(2026, 11, 16, 8, 40, 0)
    db_session.commit()
    custom_tok = jwt.encode(
        {
            "schedule_id": sched_1.id,
            "session_id": qr_late_2["session_id"],
            "generated_at": "2026-11-16T08:25:00",
            "expires_at": "2026-11-16T08:40:00",
            "iat": int(datetime.now().timestamp()),
            "exp": int((datetime.now() + timedelta(minutes=15)).timestamp()),
            "jti": qr_late_2["jti"],
        },
        get_jwt_secret(),
        algorithm="HS256",
    )
    # Tambahkan mahasiswa ke-3 yang terdaftar di IF401 untuk uji scan menit ke-35
    mhs_3 = CalonMahasiswa(
        nama_lengkap="Eko Terlambat",
        email="eko.w12@example.com",
        phone="081234567005",
        tanggal_lahir=date(2004, 1, 1),
        alamat="Jl. Eko",
        program_studi_id=1,
        jalur_masuk_id=1,
        status=StatusPendaftaran.approved,
        nim="2026TIF-0105",
    )
    db_session.add(mhs_3)
    db_session.commit()
    krs_3 = KRS(nim=mhs_3.nim, semester_akademik=5, tahun_akademik="2026/2027", total_sks=3, status="APPROVED")
    db_session.add(krs_3)
    db_session.commit()
    db_session.add(KRSDetail(krs_id=krs_3.id, matakuliah_id=env["mk_1"].id))
    db_session.commit()

    res_over_30 = client.post(
        "/attendance/scan",
        json={
            "token": custom_tok,
            "nim": mhs_3.nim,
            "scan_time": "2026-11-16T08:35:00",
        },
    )
    assert res_over_30.status_code == 400
    assert "30 menit" in res_over_30.json()["detail"].lower()


def test_scan_rejects_unregistered_wrong_class_invalid_sig_and_revoked_token(client, db_session):
    env = _seed_week12_environment(db_session)
    sched_1 = env["sched_1"]
    sched_2 = env["sched_2"]
    mhs_1 = env["mhs_1"]
    mhs_other = env["mhs_other"]
    mhs_unapproved = env["mhs_unapproved"]
    svc = AttendanceService(db_session)

    monday_date = date(2026, 11, 16)
    qr_1 = svc.generate_qr(
        schedule_id=sched_1.id,
        valid_minutes=15,
        session_date=monday_date,
        current_time=datetime(2026, 11, 16, 8, 0, 0),
    )

    # 1. Mahasiswa kelas lain (mhs_other hanya ambil IF402, bukan IF401) -> Ditolak 403
    res_wrong_class = client.post(
        "/attendance/scan",
        json={
            "token": qr_1["token"],
            "nim": mhs_other.nim,
            "scan_time": "2026-11-16T08:05:00",
        },
    )
    assert res_wrong_class.status_code == 403
    assert "tidak terdaftar" in res_wrong_class.json()["detail"].lower()

    # 2. Mahasiswa dengan KRS belum APPROVED (masih DRAFT) -> Ditolak 403
    res_unapproved = client.post(
        "/attendance/scan",
        json={
            "token": qr_1["token"],
            "nim": mhs_unapproved.nim,
            "scan_time": "2026-11-16T08:05:00",
        },
    )
    assert res_unapproved.status_code == 403

    # 3. Token dengan signature dimodifikasi / palsu -> Ditolak 400
    forged_token = jwt.encode(
        {
            "schedule_id": sched_1.id,
            "session_id": qr_1["session_id"],
            "jti": qr_1["jti"],
            "exp": int((datetime.now() + timedelta(minutes=15)).timestamp()),
        },
        "wrong-secret-key-attacker",
        algorithm="HS256",
    )
    res_bad_sig = client.post(
        "/attendance/scan",
        json={
            "token": forged_token,
            "nim": mhs_1.nim,
            "scan_time": "2026-11-16T08:05:00",
        },
    )
    assert res_bad_sig.status_code == 400
    assert "tidak valid" in res_bad_sig.json()["detail"].lower()

    # 4. Token dicabut karena dosen menerbitkan QR baru -> Token lama ditolak 400
    qr_new = svc.generate_qr(
        schedule_id=sched_1.id,
        valid_minutes=15,
        session_date=monday_date,
        current_time=datetime(2026, 11, 16, 8, 6, 0),
        revoke_previous=True,
    )
    res_revoked = client.post(
        "/attendance/scan",
        json={
            "token": qr_1["token"],
            "nim": mhs_1.nim,
            "scan_time": "2026-11-16T08:07:00",
        },
    )
    assert res_revoked.status_code == 400
    assert "tidak berlaku" in res_revoked.json()["detail"].lower()

    # Sedangkan menggunakan QR baru berhasil!
    res_ok_new = client.post(
        "/attendance/scan",
        json={
            "token": qr_new["token"],
            "nim": mhs_1.nim,
            "scan_time": "2026-11-16T08:07:00",
        },
    )
    assert res_ok_new.status_code == 200

    # 5. Token dengan schedule_id dari kelas lain yang dimanipulasi -> Ditolak 400
    mismatched_schedule_token = jwt.encode(
        {
            "schedule_id": sched_2.id,
            "session_id": qr_new["session_id"],
            "jti": qr_new["jti"],
            "exp": int((datetime.now() + timedelta(minutes=15)).timestamp()),
        },
        get_jwt_secret(),
        algorithm="HS256",
    )
    res_sched_mismatch = client.post(
        "/attendance/scan",
        json={
            "token": mismatched_schedule_token,
            "nim": env["mhs_2"].nim,
            "scan_time": "2026-11-16T08:08:00",
        },
    )
    assert res_sched_mismatch.status_code == 400


# =====================================================
# 3. PENGUJIAN SECURITY: NIM SPOOFING, RATE LIMITING & REPORT PROTECTION
# =====================================================

def test_security_nim_spoofing_rate_limiting_and_report_protection(client, db_session):
    env = _seed_week12_environment(db_session)
    sched_1 = env["sched_1"]
    mhs_1 = env["mhs_1"]
    mhs_2 = env["mhs_2"]
    svc = AttendanceService(db_session)

    monday_date = date(2026, 11, 16)
    qr = svc.generate_qr(
        schedule_id=sched_1.id,
        valid_minutes=15,
        session_date=monday_date,
        current_time=datetime(2026, 11, 16, 8, 0, 0),
    )

    # 1. Mahasiswa 1 login dengan Bearer token miliknya, tetapi mencoba mengirim NIM Mahasiswa 2 -> 403
    token_mhs_1 = create_access_token({"role": "mahasiswa", "nim": mhs_1.nim})
    res_spoof = client.post(
        "/attendance/scan",
        headers={"Authorization": f"Bearer {token_mhs_1}"},
        json={
            "token": qr["token"],
            "nim": mhs_2.nim,
            "scan_time": "2026-11-16T08:05:00",
        },
    )
    assert res_spoof.status_code == 403
    assert "memalsukan" in res_spoof.json()["detail"].lower()

    # 2. Proteksi Akses Laporan: Tanpa kredensial -> 401, Role mahasiswa -> 403, Role dosen -> 200
    assert client.get("/attendance/report").status_code == 401
    assert client.get("/attendance/report/export").status_code == 401
    assert client.get("/attendance/ai-insights").status_code == 401

    assert (
        client.get(
            "/attendance/report",
            headers={"Authorization": f"Bearer {token_mhs_1}"},
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/attendance/report",
            headers={"X-User-Role": "dosen"},
        ).status_code
        == 200
    )

    # 3. Persistent Database-Backed Rate Limiting: > 5 percobaan scan dalam 60 detik oleh NIM yang sama -> 429
    spam_nim = "2026TIF-SPAM"
    for i in range(5):
        r = client.post(
            "/attendance/scan",
            json={
                "token": "invalid.jwt.token",
                "nim": spam_nim,
                "scan_time": f"2026-11-16T08:05:0{i}",
            },
        )
        assert r.status_code == 400

    r_limited = client.post(
        "/attendance/scan",
        json={
            "token": "invalid.jwt.token",
            "nim": spam_nim,
            "scan_time": "2026-11-16T08:05:10",
        },
    )
    assert r_limited.status_code == 429
    assert "rate limit" in r_limited.json()["detail"].lower()

    attempts_in_db = (
        db_session.query(AttendanceScanAttempt)
        .filter_by(actor_key=spam_nim)
        .count()
    )
    assert attempts_in_db == 6


# =====================================================
# 4. PENGUJIAN ATTENDANCE REPORT, WARNING <75%, FUTURE SESSIONS & EXCEL
# =====================================================

def test_attendance_report_warning_future_session_exclusion_and_excel_export(
    client, db_session
):
    env = _seed_week12_environment(db_session)
    sched_1 = env["sched_1"]
    mhs_1 = env["mhs_1"]
    mhs_2 = env["mhs_2"]
    svc = AttendanceService(db_session)

    # Buat 4 sesi kuliah yang SUDAH BERLANGSUNG di masa lalu (Senin: 2, 9, 16, 23 Nov 2026)
    past_mondays = [
        date(2026, 11, 2),
        date(2026, 11, 9),
        date(2026, 11, 16),
        date(2026, 11, 23),
    ]
    for idx, d in enumerate(past_mondays):
        qr = svc.generate_qr(
            schedule_id=sched_1.id,
            valid_minutes=15,
            session_date=d,
            current_time=datetime.combine(d, time(8, 0)),
        )
        # mhs_1 hadir di ke-4 sesi (3 HADIR, 1 TERLAMBAT -> 100%)
        scan_min = 5 if idx < 3 else 20
        qr_to_use = qr
        if scan_min > 15:
            qr_to_use = svc.generate_qr(
                schedule_id=sched_1.id,
                valid_minutes=15,
                session_date=d,
                current_time=datetime.combine(d, time(8, 16)),
            )
        svc.scan_attendance(
            token=qr_to_use["token"],
            nim=mhs_1.nim,
            scan_time=datetime.combine(d, time(8, scan_min)),
        )
        # mhs_2 hanya hadir di 2 dari 4 sesi (2/4 = 50.0% -> WARNING <75%!)
        if idx < 2:
            svc.scan_attendance(
                token=qr["token"],
                nim=mhs_2.nim,
                scan_time=datetime.combine(d, time(8, 8)),
            )

    # Tambahkan 2 sesi MASA DEPAN yang BELUM berlangsung (30 Nov & 7 Des 2026)
    for future_d in [date(2026, 11, 30), date(2026, 12, 7)]:
        db_session.add(
            AttendanceSession(
                schedule_id=sched_1.id,
                session_date=future_d,
                session_status="OPEN",
            )
        )
    db_session.commit()

    # Evaluasi laporan pada waktu referensi 24 Nov 2026 pukul 12:00
    # Sesi yang telah berlangsung harus = 4 (2 sesi masa depan TIDAK dihitung sebagai absen!)
    rep_res = client.get(
        f"/attendance/report?schedule_id={sched_1.id}&reference_time=2026-11-24T12:00:00",
        headers={"X-User-Role": "dosen"},
    )
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert rep_data["total_rows"] == 2
    assert rep_data["total_warning_count"] == 1

    by_nim = {r["nim"]: r for r in rep_data["records"]}
    r1 = by_nim[mhs_1.nim]
    assert r1["total_sesi_berlangsung"] == 4
    assert r1["jumlah_hadir"] == 3
    assert r1["jumlah_terlambat"] == 1
    assert r1["jumlah_tidak_hadir"] == 0
    assert r1["persentase_kehadiran"] == 100.0
    assert r1["is_warning"] is False

    r2 = by_nim[mhs_2.nim]
    assert r2["total_sesi_berlangsung"] == 4
    assert r2["jumlah_hadir"] == 2
    assert r2["jumlah_terlambat"] == 0
    assert r2["jumlah_tidak_hadir"] == 2
    assert r2["persentase_kehadiran"] == 50.0
    assert r2["is_warning"] is True
    assert "WARNING" in r2["status_warning"]

    # Uji Export Excel (.xlsx) dan pastikan dapat dibuka dengan openpyxl serta datanya cocok
    xlsx_res = client.get(
        f"/attendance/report/export?schedule_id={sched_1.id}&reference_time=2026-11-24T12:00:00",
        headers={"X-User-Role": "dosen"},
    )
    assert xlsx_res.status_code == 200
    assert (
        xlsx_res.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    wb = load_workbook(io.BytesIO(xlsx_res.content))
    ws = wb.active
    assert ws.title == "Laporan Presensi"
    rows = list(ws.iter_rows(values_only=True))
    assert len(rows) == 3  # 1 header + 2 mahasiswa
    assert rows[1][0] == mhs_1.nim
    assert rows[1][8] == 100.0
    assert rows[2][0] == mhs_2.nim
    assert rows[2][8] == 50.0
    assert "WARNING" in rows[2][9]

    # Uji juga AI Attendance Insights langsung dari database (GET /attendance/ai-insights)
    db_ai_res = client.get(
        f"/attendance/ai-insights?schedule_id={sched_1.id}&reference_time=2026-11-24T12:00:00",
        headers={"X-User-Role": "dosen"},
    )
    assert db_ai_res.status_code == 200
    db_ai_json = db_ai_res.json()
    assert db_ai_json["summary"]["at_risk_students_count"] == 1
    assert any(i["type"] == "attendance_pattern" for i in db_ai_json["insights"])


def test_session_records_close_and_validation_edge_cases(client, db_session):
    env = _seed_week12_environment(db_session)
    sched_1 = env["sched_1"]
    mhs_1 = env["mhs_1"]

    # 1. valid_minutes > 15 harus ditolak (400)
    with pytest.raises(Exception):
        generate_attendance_qr(sched_1.id, valid_minutes=20)

    # 2. Generate QR tanpa DB (standalone mode)
    qr_standalone, tok_standalone = generate_attendance_qr(sched_1.id, valid_minutes=10)
    assert qr_image_to_png_bytes(qr_standalone).startswith(b"\x89PNG")
    assert isinstance(tok_standalone, str)

    # 3. Generate QR 10 menit sebelum kuliah dimulai (07:50 < 08:00) dan uji scan terlalu awal
    svc = AttendanceService(db_session)
    qr_early = svc.generate_qr(
        schedule_id=sched_1.id,
        valid_minutes=15,
        session_date=date(2026, 11, 16),
        current_time=datetime(2026, 11, 16, 7, 50, 0),
    )
    res_early = client.post(
        "/attendance/scan",
        json={"token": qr_early["token"], "nim": mhs_1.nim, "scan_time": "2026-11-16T07:52:00"},
    )
    assert res_early.status_code == 400
    assert "belum dimulai" in res_early.json()["detail"].lower()

    # 4. Generate QR via POST /attendance/qr/{schedule_id}/generate dan perbarui waktu untuk simulasi pukul 08:00
    gen_res = client.post(
        f"/attendance/qr/{sched_1.id}/generate",
        headers={"X-User-Role": "dosen"},
        json={"valid_minutes": 15, "session_date": "2026-11-16", "phase": "NORMAL"},
    )
    assert gen_res.status_code == 200
    qr_on_time = svc.generate_qr(
        schedule_id=sched_1.id,
        valid_minutes=15,
        session_date=date(2026, 11, 16),
        current_time=datetime(2026, 11, 16, 8, 0, 0),
    )
    session_id = qr_on_time["session_id"]
    token = qr_on_time["token"]

    # 5. Scan berhasil pada pukul 08:05
    res_ok = client.post(
        "/attendance/scan",
        json={"token": token, "nim": mhs_1.nim, "scan_time": "2026-11-16T08:05:00"},
    )
    assert res_ok.status_code == 200

    # 6. Cek daftar mahasiswa hadir pada sesi (GET /attendance/session/{session_id}/records)
    rec_res = client.get(f"/attendance/session/{session_id}/records")
    assert rec_res.status_code == 200
    assert rec_res.json()["total_present"] == 1
    assert rec_res.json()["records"][0]["nim"] == mhs_1.nim
    assert client.get("/attendance/session/99999/records").status_code == 404

    # 7. Tutup sesi (POST /attendance/session/{session_id}/close)
    close_res = client.post(
        f"/attendance/session/{session_id}/close",
        headers={"X-User-Role": "dosen"},
    )
    assert close_res.status_code == 200
    assert close_res.json()["session_status"] == "CLOSED"
    assert client.post("/attendance/session/99999/close", headers={"X-User-Role": "dosen"}).status_code == 404

    # 8. Scan pada sesi yang sudah ditutup -> Ditolak 400
    res_closed = client.post(
        "/attendance/scan",
        json={"token": token, "nim": env["mhs_2"].nim, "scan_time": "2026-11-16T08:06:00"},
    )
    assert res_closed.status_code == 400
    assert "ditutup" in res_closed.json()["detail"].lower()


# =====================================================
# 5. PENGUJIAN AI ATTENDANCE INSIGHTS & FRONTEND UI (15%)
# =====================================================

def test_ai_attendance_insights_day_hour_early_warning_and_ui(client, db_session):
    # 1. Uji AI Attendance Analyzer dengan dataset JSON terstruktur (pola hari Senin & jam 07:00)
    sample_records = [
        {"nim": "2026001", "student": "Mahasiswa X", "course": "IF401", "day": "Senin", "time": "07:00", "status": "TIDAK_HADIR"},
        {"nim": "2026001", "student": "Mahasiswa X", "course": "IF401", "day": "Senin", "time": "07:00", "status": "TIDAK_HADIR"},
        {"nim": "2026001", "student": "Mahasiswa X", "course": "IF401", "day": "Senin", "time": "07:00", "status": "HADIR"},
        {"nim": "2026001", "student": "Mahasiswa X", "course": "IF401", "day": "Senin", "time": "07:00", "status": "HADIR"},
        {"nim": "2026002", "student": "Mahasiswa Y", "course": "IF401", "day": "Senin", "time": "07:00", "status": "HADIR"},
        {"nim": "2026002", "student": "Mahasiswa Y", "course": "IF401", "day": "Senin", "time": "07:00", "status": "HADIR"},
        {"nim": "2026002", "student": "Mahasiswa Y", "course": "IF401", "day": "Senin", "time": "07:00", "status": "HADIR"},
        {"nim": "2026002", "student": "Mahasiswa Y", "course": "IF401", "day": "Senin", "time": "07:00", "status": "TIDAK_HADIR"},
    ]

    ai_res = client.post(
        "/attendance/ai-insights",
        headers={"X-User-Role": "dosen"},
        json={"attendance_records": sample_records, "min_sessions": 2},
    )
    assert ai_res.status_code == 200
    ai_json = ai_res.json()

    assert "insights" in ai_json
    assert "actions" in ai_json
    assert ai_json["summary"]["at_risk_students_count"] == 1

    insight_types = {i["type"] for i in ai_json["insights"]}
    assert "attendance_pattern" in insight_types
    assert "time_slot_pattern" in insight_types
    assert "early_warning" in insight_types

    day_insight = next(i for i in ai_json["insights"] if i["type"] == "attendance_pattern")
    assert day_insight["student"] == "Mahasiswa X"
    assert "Senin" in day_insight["pattern"]
    assert day_insight["evidence"]["day"] == "Monday"
    assert day_insight["evidence"]["absence_rate"] == 50.0

    assert any("konseling" in a["recommendation"].lower() for a in ai_json["actions"])
    assert any("reschedule" in a["recommendation"].lower() for a in ai_json["actions"])

    # 2. Uji UI Halaman /attendance-ui
    ui_res = client.get("/attendance-ui")
    assert ui_res.status_code == 200
    assert "Generate QR" in ui_res.text
    assert "Scan QR Code Presensi" in ui_res.text
    assert "AI Attendance Insights" in ui_res.text
