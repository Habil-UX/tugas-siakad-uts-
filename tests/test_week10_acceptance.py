from datetime import date, time
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import (
    CalonMahasiswa,
    Dosen,
    JadwalKuliah,
    JalurMasuk,
    KRS,
    KRSDetail,
    Matakuliah,
    ProgramStudi,
    Ruangan,
    SkalaNilai,
    StatusPendaftaran,
)
from app.services.grade_service import GradeService
from app.services.transcript_service import TranscriptService
from app.utils.pdf_generator import generate_transcript_pdf, render_transcript_html


def _seed_scales(db):
    for huruf, bobot, lulus in [
        ("A", 4.0, True),
        ("B", 3.0, True),
        ("C", 2.0, True),
        ("D", 1.0, True),
        ("E", 0.0, False),
    ]:
        if not db.query(SkalaNilai).filter(SkalaNilai.nilai_huruf == huruf).first():
            db.add(SkalaNilai(nilai_huruf=huruf, bobot=bobot, lulus=lulus))
    db.flush()


def test_week10_multi_semester_acceptance_transcript_html_and_pdf(db_session):
    """
    Acceptance test multi-semester (Semester 1 s/d Semester 4):
    - Pengambilan mata kuliah lintas 4 semester
    - Pengulangan mata kuliah (IF1001 dapat nilai D di Semester 1, diulang di Semester 3 dapat nilai A)
    - Revisi nilai di Semester 2 beserta audit trail grade_history
    - Verifikasi get_transcript(nim): tampilan historis per semester, IPS tiap semester,
      IPK kumulatif terbaik per kode_mk (Decimal ROUND_HALF_UP), dan Predikat Kelulusan di footer
    - Verifikasi render HTML template (app/templates/transcript.html) dan PDF binary (%PDF)
    """
    _seed_scales(db_session)

    prodi = ProgramStudi(kode="T10", nama="Teknik Informatika W10", fakultas="Fakultas Ilmu Komputer")
    jalur = JalurMasuk(kode="SNBT10", nama="SNBT W10")
    dosen = Dosen(nidn="10101010", nama="Prof. Hendra Pengampu")
    ruangan = Ruangan(kode_ruangan="R1010", nama_ruangan="Ruang 1010", kapasitas=45, is_active=True)
    db_session.add_all([prodi, jalur, dosen, ruangan])
    db_session.flush()

    mhs = CalonMahasiswa(
        nama_lengkap="Citra Lestari Multi-Semester",
        email="citra.w10@example.com",
        phone="081234561010",
        tanggal_lahir=date(2005, 10, 10),
        alamat="Jl. Akademik No. 10",
        program_studi_id=prodi.id,
        jalur_masuk_id=jalur.id,
        status=StatusPendaftaran.approved,
        nim="2025T10-0001",
    )
    mk1 = Matakuliah(
        kode_mk="IF1001",
        nama_mk="Algoritma & Struktur Data",
        sks=4,
        semester=1,
        jenis_mk="Wajib",
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
    )
    mk2 = Matakuliah(
        kode_mk="IF1002",
        nama_mk="Pemrograman Berorientasi Objek",
        sks=3,
        semester=2,
        jenis_mk="Wajib",
        hari="Selasa",
        jam_mulai=time(10, 0),
        jam_selesai=time(12, 0),
    )
    mk3 = Matakuliah(
        kode_mk="IF1003",
        nama_mk="Basis Data Lanjut",
        sks=3,
        semester=3,
        jenis_mk="Wajib",
        hari="Rabu",
        jam_mulai=time(13, 0),
        jam_selesai=time(15, 0),
    )
    mk4 = Matakuliah(
        kode_mk="IF1004",
        nama_mk="Rekayasa Perangkat Lunak",
        sks=4,
        semester=4,
        jenis_mk="Wajib",
        hari="Kamis",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
    )
    db_session.add_all([mhs, mk1, mk2, mk3, mk4])
    db_session.flush()

    grade_svc = GradeService(db_session)

    # Semester 1: IF1001 (4 SKS) -> awalnya mendapat D (1.0)
    k1 = JadwalKuliah(
        matakuliah_id=mk1.id,
        dosen_id=dosen.id,
        ruangan_id=ruangan.id,
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
        tahun_akademik="2025/2026",
        semester_akademik=1,
        status="AKTIF",
    )
    db_session.add(k1)
    db_session.flush()
    grade_svc.set_nilai_kelas(k1.id, mhs.nim, "D", dosen_id=dosen.id, semester=1)

    # Semester 2: IF1002 (3 SKS) -> awalnya B (3.0), lalu direvisi menjadi A (4.0)
    k2 = JadwalKuliah(
        matakuliah_id=mk2.id,
        dosen_id=dosen.id,
        ruangan_id=ruangan.id,
        hari="Selasa",
        jam_mulai=time(10, 0),
        jam_selesai=time(12, 0),
        tahun_akademik="2025/2026",
        semester_akademik=2,
        status="AKTIF",
    )
    db_session.add(k2)
    db_session.flush()
    grade_svc.set_nilai_kelas(k2.id, mhs.nim, "B", dosen_id=dosen.id, semester=2)
    grade_svc.set_nilai_kelas(
        k2.id,
        mhs.nim,
        "A",
        dosen_id=dosen.id,
        semester=2,
        reason="Koreksi nilai ujian praktikum",
    )

    # Semester 3: Mengulang IF1001 (4 SKS) -> mendapat A (4.0), dan mengambil IF1003 (3 SKS) -> B (3.0)
    grade_svc.set_nilai_kelas(k1.id, mhs.nim, "A", dosen_id=dosen.id, semester=3)
    k3 = JadwalKuliah(
        matakuliah_id=mk3.id,
        dosen_id=dosen.id,
        ruangan_id=ruangan.id,
        hari="Rabu",
        jam_mulai=time(13, 0),
        jam_selesai=time(15, 0),
        tahun_akademik="2026/2027",
        semester_akademik=3,
        status="AKTIF",
    )
    db_session.add(k3)
    db_session.flush()
    grade_svc.set_nilai_kelas(k3.id, mhs.nim, "B", dosen_id=dosen.id, semester=3)

    # Semester 4: IF1004 (4 SKS) -> A (4.0)
    k4 = JadwalKuliah(
        matakuliah_id=mk4.id,
        dosen_id=dosen.id,
        ruangan_id=ruangan.id,
        hari="Kamis",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
        tahun_akademik="2026/2027",
        semester_akademik=4,
        status="AKTIF",
    )
    db_session.add(k4)
    db_session.flush()
    grade_svc.set_nilai_kelas(k4.id, mhs.nim, "A", dosen_id=dosen.id, semester=4)

    # Verifikasi get_transcript(nim) — catatan akademik lengkap & tampilan historis
    ts = TranscriptService(db_session)
    transcript = ts.get_transcript(mhs.nim)

    assert transcript["nim"] == "2025T10-0001"
    assert transcript["nama"] == "Citra Lestari Multi-Semester"
    assert len(transcript["records"]) == 5  # Tampilan historis mencatat semua 5 pengambilan
    assert len(transcript["rekap_semester"]) == 4  # Semester 1, 2, 3, 4

    # Terbaik per kode_mk:
    # IF1001 (4 SKS, A=4.0 -> 16), IF1002 (3 SKS, A=4.0 -> 12), IF1003 (3 SKS, B=3.0 -> 9), IF1004 (4 SKS, A=4.0 -> 16)
    # Total SKS Lulus = 14, Total Mutu = 53 -> IPK = 53 / 14 = 3.7857... -> ROUND_HALF_UP = 3.79 (Cum Laude)
    assert transcript["total_sks_lulus"] == 14
    assert transcript["ipk"] == 3.79
    assert transcript["predikat"] == "Cum Laude"

    # Verifikasi render HTML template dengan Predikat Kelulusan di footer
    html_str = render_transcript_html(transcript)
    assert "<footer>" in html_str
    assert "Predikat Kelulusan: Cum Laude" in html_str
    assert "Algoritma &amp; Struktur Data" in html_str

    # Verifikasi endpoint HTML & PDF
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        c = TestClient(app)
        resp_html = c.get(f"/api/grades/transcript/{mhs.nim}/html")
        assert resp_html.status_code == 200
        assert "Predikat Kelulusan: Cum Laude" in resp_html.text

        resp_pdf = c.get(f"/api/grades/transcript/{mhs.nim}/pdf")
        assert resp_pdf.status_code == 200
        assert resp_pdf.headers["content-type"] == "application/pdf"
        assert resp_pdf.content.startswith(b"%PDF")
    finally:
        app.dependency_overrides.clear()
