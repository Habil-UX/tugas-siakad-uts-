
from datetime import date, time

import pytest
from fastapi import HTTPException

from app.models import (
    ProgramStudi,
    JalurMasuk,
    CalonMahasiswa,
    StatusPendaftaran,
    Matakuliah,
    SkalaNilai,
    RiwayatNilai,
)

from app.services.gpa_calculator import GPACalculator
from app.services.transcript_service import TranscriptService


# ==========================================
# HELPER DATA TEST
# ==========================================

def setup_student(db):

    prodi = db.query(ProgramStudi).first()
    jalur = db.query(JalurMasuk).first()

    mahasiswa = CalonMahasiswa(
        nama_lengkap="Mahasiswa Transcript",
        email="transcript@test.com",
        phone="081234567890",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Jalan Test",
        program_studi_id=prodi.id,
        jalur_masuk_id=jalur.id,
        status=StatusPendaftaran.approved,
        nim="12345678"
    )

    db.add(mahasiswa)
    db.commit()

    return mahasiswa


def setup_scales(db):

    scales = [
        SkalaNilai(nilai_huruf="A", bobot=4.0),
        SkalaNilai(nilai_huruf="B", bobot=3.0),
        SkalaNilai(nilai_huruf="C", bobot=2.0),
        SkalaNilai(nilai_huruf="D", bobot=1.0),
        SkalaNilai(nilai_huruf="E", bobot=0.0),
    ]

    db.add_all(scales)
    db.commit()

    return {
        scale.nilai_huruf: scale
        for scale in scales
    }


def create_course(
    db,
    kode="IF101",
    nama="Pemrograman",
    sks=3
):

    course = Matakuliah(
        kode_mk=kode,
        nama_mk=nama,
        sks=sks,
        semester=1,
        jenis_mk="Wajib",
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0)
    )

    db.add(course)
    db.commit()

    return course


def add_grade(
    db,
    nim,
    course,
    scale,
    semester=1
):

    grade = RiwayatNilai(
        nim=nim,
        matakuliah_id=course.id,
        skala_nilai_id=scale.id,
        semester=semester,
        presensi_persen=90,
        created_by="Dosen Test",
        version=1
    )

    db.add(grade)
    db.commit()

    return grade


# ==========================================
# TEST GPACALCULATOR
# ==========================================

def test_calculate_empty_grades(db_session):

    calculator = GPACalculator(db_session)

    result = calculator._calculate([])

    assert result["total_sks"] == 0
    assert result["total_sks_lulus"] == 0
    assert result["total_mutu"] == 0
    assert result["ip"] == 0.0


def test_calculate_gpa_totals(db_session):

    calculator = GPACalculator(db_session)

    courses = [
        {
            "sks": 3,
            "bobot": 4.0
        },
        {
            "sks": 2,
            "bobot": 1.0
        }
    ]

    result = calculator._calculate(courses)

    assert result["total_sks"] == 5
    assert result["total_sks_lulus"] == 5
    assert result["total_mutu"] == 14.0
    assert result["ip"] == 2.8


def test_get_best_courses_empty(db_session):

    calculator = GPACalculator(db_session)

    result = calculator._get_best_courses([])

    assert result == []


def test_get_best_courses_selects_best_grade(db_session):

    mahasiswa = setup_student(db_session)
    scales = setup_scales(db_session)

    course = create_course(db_session)

    add_grade(
        db_session,
        mahasiswa.nim,
        course,
        scales["B"],
        semester=1
    )

    add_grade(
        db_session,
        mahasiswa.nim,
        course,
        scales["A"],
        semester=2
    )

    calculator = GPACalculator(db_session)

    records = calculator._get_grades(mahasiswa.nim)

    result = calculator._get_best_courses(records)

    assert len(result) == 1
    assert result[0]["nilai_huruf"] == "A"
    assert result[0]["bobot"] == 4.0
    assert result[0]["semester"] == 2


def test_get_best_courses_keeps_higher_previous_grade(
    db_session
):

    mahasiswa = setup_student(db_session)
    scales = setup_scales(db_session)

    course = create_course(db_session)

    add_grade(
        db_session,
        mahasiswa.nim,
        course,
        scales["A"],
        semester=1
    )

    add_grade(
        db_session,
        mahasiswa.nim,
        course,
        scales["B"],
        semester=2
    )

    calculator = GPACalculator(db_session)

    records = calculator._get_grades(mahasiswa.nim)

    result = calculator._get_best_courses(records)

    assert len(result) == 1
    assert result[0]["nilai_huruf"] == "A"
    assert result[0]["semester"] == 1


def test_get_best_courses_same_grade_prefers_later_semester(
    db_session
):

    mahasiswa = setup_student(db_session)
    scales = setup_scales(db_session)

    course = create_course(db_session)

    add_grade(
        db_session,
        mahasiswa.nim,
        course,
        scales["B"],
        semester=1
    )

    add_grade(
        db_session,
        mahasiswa.nim,
        course,
        scales["B"],
        semester=2
    )

    calculator = GPACalculator(db_session)

    records = calculator._get_grades(mahasiswa.nim)

    result = calculator._get_best_courses(records)

    assert result[0]["semester"] == 2


def test_calculate_ips_success(db_session):

    mahasiswa = setup_student(db_session)
    scales = setup_scales(db_session)

    course = create_course(db_session)

    add_grade(
        db_session,
        mahasiswa.nim,
        course,
        scales["A"],
        semester=1
    )

    calculator = GPACalculator(db_session)

    result = calculator.calculate_ips(
        mahasiswa.nim,
        1
    )

    assert result["ips"] == 4.0
    assert result["total_sks"] == 3
    assert result["total_sks_lulus"] == 3
    assert result["total_mutu"] == 12.0


def test_calculate_ips_empty_semester(db_session):

    mahasiswa = setup_student(db_session)

    calculator = GPACalculator(db_session)

    result = calculator.calculate_ips(
        mahasiswa.nim,
        2
    )

    assert result["ips"] == 0.0
    assert result["total_sks"] == 0


def test_calculate_ipk_success(db_session):

    mahasiswa = setup_student(db_session)
    scales = setup_scales(db_session)

    mk1 = create_course(
        db_session,
        "IF101",
        "Pemrograman",
        3
    )

    mk2 = create_course(
        db_session,
        "IF102",
        "Basis Data",
        2
    )

    add_grade(
        db_session,
        mahasiswa.nim,
        mk1,
        scales["A"],
        semester=1
    )

    add_grade(
        db_session,
        mahasiswa.nim,
        mk2,
        scales["B"],
        semester=1
    )

    calculator = GPACalculator(db_session)

    result = calculator.calculate_ipk(mahasiswa.nim)

    assert result["ipk"] == 3.6
    assert result["total_sks"] == 5
    assert result["total_sks_lulus"] == 5
    assert result["total_mutu"] == 18.0
    assert result["jumlah_mata_kuliah"] == 2


def test_calculate_ipk_empty(db_session):

    mahasiswa = setup_student(db_session)

    calculator = GPACalculator(db_session)

    result = calculator.calculate_ipk(mahasiswa.nim)

    assert result["ipk"] == 0.0
    assert result["jumlah_mata_kuliah"] == 0


# ==========================================
# TEST TRANSCRIPT
# ==========================================

def test_get_transcript_success(db_session):

    mahasiswa = setup_student(db_session)
    scales = setup_scales(db_session)

    mk1 = create_course(
        db_session,
        "IF101",
        "Pemrograman",
        3
    )

    mk2 = create_course(
        db_session,
        "IF102",
        "Basis Data",
        2
    )

    add_grade(
        db_session,
        mahasiswa.nim,
        mk1,
        scales["A"],
        semester=1
    )

    add_grade(
        db_session,
        mahasiswa.nim,
        mk2,
        scales["E"],
        semester=1
    )

    calculator = GPACalculator(db_session)

    result = calculator.get_transcript(mahasiswa.nim)

    
    assert result["nim"] == mahasiswa.nim
    assert result["total_sks"] == 5
    assert result["total_sks_lulus"] == 3
    assert result["ipk"] == 4.0
    assert result["predikat"] == "Cum Laude"

    assert len(result["records"]) == 2

    assert result["records"][0]["status"] == "LULUS"
    assert result["records"][1]["status"] == "TIDAK LULUS"



def test_get_transcript_without_grades(db_session):

    mahasiswa = setup_student(db_session)

    calculator = GPACalculator(db_session)

    result = calculator.get_transcript(mahasiswa.nim)

    assert result["nim"] == mahasiswa.nim
    assert result["records"] == []
    assert result["ipk"] == 0.0
    assert result["predikat"] == "Belum Ada Nilai"


# ==========================================
# TEST PREDIKAT AKADEMIK
# ==========================================

@pytest.mark.parametrize(
    "ipk, expected",
    [
        (4.0, "Cum Laude"),
        (3.5, "Cum Laude"),
        (3.49, "Sangat Memuaskan"),
        (3.0, "Sangat Memuaskan"),
        (2.99, "Memuaskan"),
        (2.0, "Memuaskan"),
        (1.99, "Kurang Memuaskan"),
        (0.1, "Kurang Memuaskan"),
        (0.0, "Belum Ada Nilai"),
    ]
)
def test_get_predikat(db_session, ipk, expected):

    result = GPACalculator.get_predikat(ipk)

    assert result == expected


# ==========================================
# TEST TRANSCRIPT SERVICE
# ==========================================

def test_get_mahasiswa_not_found(db_session):

    service = TranscriptService(db_session)

    with pytest.raises(HTTPException) as exc:

        service._get_mahasiswa("99999999")

    assert exc.value.status_code == 404


def test_get_mahasiswa_success(db_session):

    mahasiswa = setup_student(db_session)

    service = TranscriptService(db_session)

    result = service._get_mahasiswa(mahasiswa.nim)

    assert result.nim == mahasiswa.nim


def test_get_ips_invalid_semester(db_session):

    mahasiswa = setup_student(db_session)

    service = TranscriptService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.get_ips(
            mahasiswa.nim,
            0
        )

    assert exc.value.status_code == 400


def test_get_ips_success(db_session):

    mahasiswa = setup_student(db_session)
    scales = setup_scales(db_session)

    course = create_course(db_session)

    add_grade(
        db_session,
        mahasiswa.nim,
        course,
        scales["A"],
        semester=1
    )

    service = TranscriptService(db_session)

    result = service.get_ips(
        mahasiswa.nim,
        1
    )

    assert result["ips"] == 4.0


def test_get_ipk_success(db_session):

    mahasiswa = setup_student(db_session)
    scales = setup_scales(db_session)

    course = create_course(db_session)

    add_grade(
        db_session,
        mahasiswa.nim,
        course,
        scales["A"]
    )

    service = TranscriptService(db_session)

    result = service.get_ipk(mahasiswa.nim)

    assert result["ipk"] == 4.0


def test_get_transcript_service_success(db_session):

    mahasiswa = setup_student(db_session)
    scales = setup_scales(db_session)

    mk1 = create_course(
        db_session,
        "IF101",
        "Pemrograman",
        3
    )

    mk2 = create_course(
        db_session,
        "IF102",
        "Basis Data",
        2
    )

    add_grade(
        db_session,
        mahasiswa.nim,
        mk1,
        scales["A"],
        semester=1
    )

    add_grade(
        db_session,
        mahasiswa.nim,
        mk2,
        scales["B"],
        semester=2
    )

    service = TranscriptService(db_session)

    result = service.get_transcript(mahasiswa.nim)

    assert result["nama"] == mahasiswa.nama_lengkap
    assert result["nim"] == mahasiswa.nim
    assert result["program_studi"] == "Teknik Informatika"

    assert len(result["records"]) == 2
    assert len(result["rekap_semester"]) == 2

    assert result["rekap_semester"][0]["semester"] == 1
    assert result["rekap_semester"][1]["semester"] == 2


def test_get_transcript_service_not_found(db_session):

    service = TranscriptService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.get_transcript("99999999")

    assert exc.value.status_code == 404


# ==========================================
# TEST PERHITUNGAN IPK DENGAN 12 KASUS (MINGGU 9-10)
# ==========================================

@pytest.mark.parametrize(
    "case_name,entries,expected_ipk,expected_sks_lulus",
    [
        ("1_belum_ada_nilai", [], 0.0, 0),
        ("2_semua_A_sempurna", [("IF101", 3, "A", 1), ("IF102", 3, "A", 1)], 4.0, 6),
        ("3_semua_B", [("IF101", 3, "B", 1), ("IF102", 2, "B", 1)], 3.0, 5),
        ("4_semua_C", [("IF101", 3, "C", 1), ("IF102", 3, "C", 1)], 2.0, 6),
        ("5_ulang_naik_C_ke_A", [("IF101", 3, "C", 1), ("IF101", 3, "A", 2)], 4.0, 3),
        ("6_ulang_turun_A_ke_B_ambil_tertinggi", [("IF101", 3, "A", 1), ("IF101", 3, "B", 2)], 4.0, 3),
        ("7_ada_E_tidak_dihitung", [("IF101", 3, "A", 1), ("IF102", 2, "E", 1)], 4.0, 3),
        ("8_nilai_D_lulus_dan_E_tidak_lulus", [("IF101", 3, "E", 1), ("IF102", 3, "D", 1)], 1.0, 3),
        ("8b_semua_E_tidak_lulus", [("IF101", 3, "E", 1), ("IF102", 3, "E", 2)], 0.0, 0),
        ("9_gagal_E_lalu_ulang_lulus_B", [("IF101", 3, "E", 1), ("IF101", 3, "B", 2)], 3.0, 3),
        ("9b_ulang_D_ke_B_ambil_tertinggi", [("IF101", 3, "D", 1), ("IF101", 3, "B", 2)], 3.0, 3),
        ("10_bobot_sks_berbeda", [("IF101", 4, "A", 1), ("IF102", 3, "B", 1), ("IF103", 3, "C", 1)], 3.1, 10),
        ("11_lintas_semester_kompleks", [("IF101", 3, "B", 1), ("IF102", 3, "C", 1), ("IF102", 3, "A", 2), ("IF103", 2, "E", 2)], 3.5, 6),
        ("12_pembulatan_dua_desimal", [("IF101", 3, "A", 1), ("IF102", 3, "B", 1), ("IF103", 3, "B", 2)], 3.33, 9),
    ],
)
def test_calculate_ipk_12_cases(
    db_session,
    case_name,
    entries,
    expected_ipk,
    expected_sks_lulus,
):
    mahasiswa = setup_student(db_session)
    scales = setup_scales(db_session)

    courses_map = {}
    for kode, sks, huruf, sem in entries:
        if kode not in courses_map:
            courses_map[kode] = create_course(db_session, kode=kode, nama=f"MK {kode}", sks=sks)
        add_grade(db_session, mahasiswa.nim, courses_map[kode], scales[huruf], semester=sem)

    calculator = GPACalculator(db_session)
    res = calculator.calculate_ipk(mahasiswa.nim)

    assert res["ipk"] == expected_ipk, f"Failed on {case_name}"
    assert res["total_sks_lulus"] == expected_sks_lulus, f"Failed SKS on {case_name}"

