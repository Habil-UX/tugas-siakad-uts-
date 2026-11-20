from datetime import date, time
from decimal import Decimal, ROUND_HALF_UP
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

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
from app.services.gpa_calculator import GPACalculator
from app.services.grade_service import GradeService
from app.services.nilai_repo import NilaiRepo
from app.services.presensi_port import PresensiStub, is_pengampu
from app.utils.security import create_access_token


def _seed_scales(db):
    scales = [
        ("A", 4.0, True),
        ("B", 3.0, True),
        ("C", 2.0, True),
        ("D", 1.0, True),
        ("E", 0.0, False),
    ]
    out = {}
    for huruf, bobot, lulus in scales:
        s = db.query(SkalaNilai).filter(SkalaNilai.nilai_huruf == huruf).first()
        if not s:
            s = SkalaNilai(nilai_huruf=huruf, bobot=bobot, lulus=lulus)
            db.add(s)
            db.flush()
        out[huruf] = s
    return out


# =====================================================================
# 1. TEST MIGRATION FIELDS (krs_detail.nilai FK, skala_nilai.lulus, grade_history)
#    + PresensiPort/PresensiStub + is_pengampu + PUT /api/kelas/{id}/nilai/{nim}
# =====================================================================

def test_week9_presensi_port_is_pengampu_and_put_kelas_nilai(db_session):
    _seed_scales(db_session)

    prodi = ProgramStudi(kode="IF9", nama="Informatika W9", fakultas="FIK")
    jalur = JalurMasuk(kode="SNBP9", nama="SNBP W9")
    dosen_pengampu = Dosen(nidn="990011", nama="Dr. Pengampu Sah")
    dosen_lain = Dosen(nidn="990022", nama="Dr. Bukan Pengampu")
    ruangan = Ruangan(kode_ruangan="R901", nama_ruangan="Lab 901", kapasitas=40, is_active=True)
    db_session.add_all([prodi, jalur, dosen_pengampu, dosen_lain, ruangan])
    db_session.flush()

    mhs = CalonMahasiswa(
        nama_lengkap="Mahasiswa Minggu 9",
        email="mhs.w9@example.com",
        phone="081234567809",
        tanggal_lahir=date(2005, 9, 9),
        alamat="Jl. Kampus 9",
        program_studi_id=prodi.id,
        jalur_masuk_id=jalur.id,
        status=StatusPendaftaran.approved,
        nim="2026IF9-0001",
    )
    mk = Matakuliah(
        kode_mk="IF901",
        nama_mk="Pemrograman Berorientasi Objek Lanjut",
        sks=3,
        semester=3,
        jenis_mk="Wajib",
        hari="Rabu",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
    )
    db_session.add_all([mhs, mk])
    db_session.flush()

    kelas = JadwalKuliah(
        matakuliah_id=mk.id,
        dosen_id=dosen_pengampu.id,
        ruangan_id=ruangan.id,
        hari="Rabu",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
        tahun_akademik="2026/2027",
        semester_akademik=3,
        status="AKTIF",
    )
    krs = KRS(
        nim=mhs.nim,
        semester_akademik=3,
        tahun_akademik="2026/2027",
        total_sks=3,
        status="APPROVED",
    )
    db_session.add_all([kelas, krs])
    db_session.flush()
    kd = KRSDetail(krs_id=krs.id, matakuliah_id=mk.id)
    db_session.add(kd)
    db_session.commit()

    # Verifikasi is_pengampu
    assert is_pengampu(db_session, dosen_pengampu.id, kelas.id) is True
    assert is_pengampu(db_session, dosen_lain.id, kelas.id) is False

    # Verifikasi PresensiStub menolak jika kehadiran < 75%
    stub = PresensiStub(default_persen=85.0)
    stub.set_persentase(mhs.nim, kelas.id, 60.0)
    svc = GradeService(db_session, presensi_port=stub)

    with pytest.raises(HTTPException) as exc_low:
        svc.set_nilai_kelas(kelas.id, mhs.nim, "A", dosen_id=dosen_pengampu.id)
    assert exc_low.value.status_code == 400

    # Verifikasi penolakan jika bukan dosen pengampu (403 Forbidden)
    stub.set_persentase(mhs.nim, kelas.id, 90.0)
    with pytest.raises(HTTPException) as exc_forbidden:
        svc.set_nilai_kelas(kelas.id, mhs.nim, "A", dosen_id=dosen_lain.id)
    assert exc_forbidden.value.status_code == 403

    # Input nilai sah oleh dosen pengampu
    res1 = svc.set_nilai_kelas(
        kelas.id,
        mhs.nim,
        "B",
        dosen_id=dosen_pengampu.id,
        changed_by="dosen_pengampu",
    )
    assert res1["nilai_huruf"] == "B"
    db_session.refresh(kd)
    assert kd.nilai == "B"

    # Revisi nilai melalui endpoint PUT /api/kelas/{id}/nilai/{nim} -> mencatat grade_history di transaksi yang sama
    token = create_access_token({"sub": "dosen_pengampu", "role": "dosen"})
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        resp = TestClient(app).put(
            f"/api/kelas/{kelas.id}/nilai/{mhs.nim}",
            json={
                "nilai_huruf": "A",
                "dosen_id": dosen_pengampu.id,
                "changed_by": "dosen_pengampu",
                "reason": "Koreksi nilai proyek akhir",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["new_value"] == "A"
    db_session.refresh(kd)
    assert kd.nilai == "A"

    # Verifikasi NilaiRepo & GPACalculator hitung_ips / hitung_ipk
    repo = NilaiRepo(db_session)
    calc = GPACalculator(db_session, repo=repo)
    assert calc.hitung_ips(mhs.nim, 3)["ips"] == 4.0
    assert calc.hitung_ipk(mhs.nim)["ipk"] == 4.0


# =====================================================================
# 2. 10+ KASUS PARAMETRIZE PERHITUNGAN IPK (DECIMAL & ROUND_HALF_UP SEKALI)
# =====================================================================

@pytest.mark.parametrize(
    "courses,expected_ipk,expected_sks_lulus",
    [
        # 1. Semua A
        ([("MK1", 3, "A", 4.0, True, 1), ("MK2", 3, "A", 4.0, True, 1)], 4.00, 6),
        # 2. Campuran A dan B
        ([("MK1", 3, "A", 4.0, True, 1), ("MK2", 3, "B", 3.0, True, 1)], 3.50, 6),
        # 3. Pembulatan ROUND_HALF_UP sekali (20 mutu / 6 sks = 3.333... -> 3.33)
        ([("MK1", 4, "A", 4.0, True, 1), ("MK2", 2, "C", 2.0, True, 1)], 3.33, 6),
        # 4. Pembulatan ROUND_HALF_UP sekali (22 mutu / 6 sks = 3.666... -> 3.67)
        ([("MK1", 4, "A", 4.0, True, 1), ("MK2", 2, "B", 3.0, True, 1)], 3.67, 6),
        # 5. Pembulatan exact .005 -> ROUND_HALF_UP ke .01 (misal 2.005)
        ([("MK1", 199, "C", 2.0, True, 1), ("MK2", 1, "B", 3.0, True, 1)], 2.01, 200),
        # 6. Nilai D dihitung lulus (skala_nilai.lulus = True)
        ([("MK1", 3, "D", 1.0, True, 1), ("MK2", 3, "B", 3.0, True, 1)], 2.00, 6),
        # 7. Nilai E tidak lulus (skala_nilai.lulus = False) -> tidak dihitung di SKS lulus
        ([("MK1", 3, "A", 4.0, True, 1), ("MK2", 3, "E", 0.0, False, 1)], 4.00, 3),
        # 8. Hanya nilai E -> IPK 0.00
        ([("MK1", 3, "E", 0.0, False, 1)], 0.00, 0),
        # 9. Belum ada mata kuliah -> IPK 0.00
        ([], 0.00, 0),
        # 10. Mengulang MK yang sama (D di Sem 1 -> A di Sem 3) -> terbaik per kode_mk (A)
        ([("MK1", 3, "D", 1.0, True, 1), ("MK1", 3, "A", 4.0, True, 3)], 4.00, 3),
        # 11. Mengulang MK tetapi nilai kedua lebih rendah (B di Sem 1 -> C di Sem 2) -> tetap terbaik (B)
        ([("MK1", 3, "B", 3.0, True, 1), ("MK1", 3, "C", 2.0, True, 2)], 3.00, 3),
        # 12. Mengulang MK dari E (Sem 1) ke C (Sem 2) -> lulus dengan C (2.00)
        ([("MK1", 3, "E", 0.0, False, 1), ("MK1", 3, "C", 2.0, True, 2)], 2.00, 3),
    ],
)
def test_12_parametrized_gpa_cases(db_session, courses, expected_ipk, expected_sks_lulus):
    calc = GPACalculator(db_session)
    formatted = [
        {
            "grade_id": idx + 1,
            "kode_mk": kode,
            "nama_mk": f"Course {kode}",
            "sks": sks,
            "nilai_huruf": huruf,
            "bobot": bobot,
            "lulus": lulus,
            "semester": sem,
        }
        for idx, (kode, sks, huruf, bobot, lulus, sem) in enumerate(courses)
    ]
    # Deduplikasi terbaik per kode_mk
    best = {}
    for c in formatted:
        cur = best.get(c["kode_mk"])
        if cur is None or (c["bobot"], c["semester"], c["grade_id"]) > (
            cur["bobot"],
            cur["semester"],
            cur["grade_id"],
        ):
            best[c["kode_mk"]] = c

    res = calc._calculate(list(best.values()), only_passed=True)
    assert res["ip"] == expected_ipk
    assert res["total_sks_lulus"] == expected_sks_lulus


# =====================================================================
# 3. TIGA (3) PROPERTI HYPOTHESIS UNTUK GPACalculator
# =====================================================================

course_strategy = st.fixed_dictionaries({
    "kode_mk": st.sampled_from(["IF101", "IF102", "IF103", "IF104", "IF105"]),
    "sks": st.integers(min_value=1, max_value=6),
    "bobot": st.sampled_from([0.0, 1.0, 2.0, 3.0, 4.0]),
    "semester": st.integers(min_value=1, max_value=8),
})


@settings(max_examples=100, deadline=None)
@given(st.lists(course_strategy, min_size=1, max_size=15))
def test_hypothesis_property_1_ipk_bounded_and_round_half_up(raw_list):
    """Properti 1: IPK selalu berada pada rentang [0.00, 4.00] dan sesuai Decimal ROUND_HALF_UP sekali."""
    courses = [
        {
            **c,
            "grade_id": i + 1,
            "nama_mk": c["kode_mk"],
            "nilai_huruf": "A" if c["bobot"] == 4 else "B",
            "lulus": c["bobot"] >= 1.0,
        }
        for i, c in enumerate(raw_list)
    ]
    calc = GPACalculator(db=None)
    res = calc._calculate(courses, only_passed=True)
    assert 0.0 <= res["ip"] <= 4.0

    passed = [c for c in courses if c["lulus"]]
    if passed:
        expected_dec = (
            sum((Decimal(str(c["sks"])) * Decimal(str(c["bobot"])) for c in passed), Decimal("0"))
            / Decimal(str(sum(c["sks"] for c in passed)))
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        assert res["ip"] == float(expected_dec)
    else:
        assert res["ip"] == 0.0


@settings(max_examples=100, deadline=None)
@given(
    st.integers(min_value=1, max_value=4),
    st.sampled_from([1.0, 2.0, 3.0, 4.0]),
    st.sampled_from([1.0, 2.0, 3.0, 4.0]),
)
def test_hypothesis_property_2_retake_best_per_kode_mk_never_lowers_grade(sks, bobot_awal, bobot_ulang):
    """Properti 2: Mengulang mata kuliah dengan kode_mk yang sama selalu mengambil nilai tertinggi (tidak pernah menurunkan IPK)."""
    class DummyObj:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    mk = DummyObj(id=1, kode_mk="IF101", nama_mk="PBO", sks=sks)
    g1 = DummyObj(id=1, semester=1)
    s1 = DummyObj(nilai_huruf="X", bobot=bobot_awal, lulus=True)
    g2 = DummyObj(id=2, semester=2)
    s2 = DummyObj(nilai_huruf="Y", bobot=bobot_ulang, lulus=True)

    calc = GPACalculator(db=None)
    best_single = calc._get_best_courses([(g1, s1, mk)])
    best_retake = calc._get_best_courses([(g1, s1, mk), (g2, s2, mk)])

    assert len(best_retake) == 1
    assert best_retake[0]["bobot"] == max(bobot_awal, bobot_ulang)
    assert best_retake[0]["bobot"] >= best_single[0]["bobot"]


@settings(max_examples=100, deadline=None)
@given(st.lists(course_strategy, min_size=1, max_size=10))
def test_hypothesis_property_3_unpassed_courses_excluded_from_sks_lulus(raw_list):
    """Properti 3: Mata kuliah dengan skala_nilai.lulus == False (E) tidak pernah menambah total_sks_lulus."""
    courses = [
        {
            **c,
            "grade_id": i + 1,
            "nama_mk": c["kode_mk"],
            "nilai_huruf": "E" if c["bobot"] == 0.0 else "B",
            "lulus": c["bobot"] >= 1.0,
        }
        for i, c in enumerate(raw_list)
    ]
    calc = GPACalculator(db=None)
    res_with_e = calc._calculate(courses, only_passed=True)
    only_lulus = [c for c in courses if c["lulus"]]
    res_without_e = calc._calculate(only_lulus, only_passed=True)

    assert res_with_e["total_sks_lulus"] == res_without_e["total_sks_lulus"]
    assert res_with_e["ip"] == res_without_e["ip"]
