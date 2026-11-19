
from datetime import date, time

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.models import (
    ProgramStudi,
    JalurMasuk,
    CalonMahasiswa,
    StatusPendaftaran,
    Matakuliah,
    SkalaNilai,
    RiwayatNilai,
)

from app.schemas.grade import GradeCreate
from app.services.grade_service import GradeService


# ==========================================
# HELPER: DATA PENGUJIAN
# ==========================================

def seed_grade_data(db_session):

    prodi = db_session.query(ProgramStudi).first()
    jalur = db_session.query(JalurMasuk).first()

    mahasiswa = CalonMahasiswa(
        nama_lengkap="Mahasiswa Test",
        email="grade@test.com",
        phone="081234567890",
        tanggal_lahir=date(2000, 1, 1),
        alamat="Jalan Test",
        program_studi_id=prodi.id,
        jalur_masuk_id=jalur.id,
        status=StatusPendaftaran.approved,
        nim="12345678"
    )

    mk = Matakuliah(
        kode_mk="IF999",
        nama_mk="Pemrograman Test",
        sks=3,
        semester=1,
        jenis_mk="Wajib",
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0)
    )

    skala_a = SkalaNilai(
        nilai_huruf="A",
        bobot=4.0
    )

    skala_b = SkalaNilai(
        nilai_huruf="B",
        bobot=3.0
    )

    db_session.add_all([
        mahasiswa,
        mk,
        skala_a,
        skala_b
    ])

    db_session.commit()

    return mahasiswa, mk, skala_a, skala_b


def make_grade_data(mk, nilai="A", presensi=90):

    return GradeCreate(
        nim="12345678",
        matakuliah_id=mk.id,
        semester=1,
        nilai_huruf=nilai,
        presensi_persen=presensi,
        changed_by="Dosen Test"
    )


def install_audit_objects(db_session):

    db_session.execute(text("""
        CREATE TABLE IF NOT EXISTS grade_audit_context (
            grade_id INTEGER PRIMARY KEY,
            changed_by VARCHAR(100) NOT NULL,
            reason TEXT NOT NULL
        )
    """))

    db_session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS trg_grade_history_update
        AFTER UPDATE OF skala_nilai_id ON riwayat_nilai
        FOR EACH ROW
        WHEN OLD.skala_nilai_id != NEW.skala_nilai_id
        BEGIN

            INSERT INTO grade_history (
                grade_id,
                old_value,
                new_value,
                changed_by,
                changed_at,
                reason
            )
            SELECT
                NEW.id,
                old_scale.nilai_huruf,
                new_scale.nilai_huruf,
                COALESCE(ctx.changed_by, 'SYSTEM'),
                CURRENT_TIMESTAMP,
                COALESCE(ctx.reason, 'Perubahan nilai')
            FROM skala_nilai AS old_scale
            JOIN skala_nilai AS new_scale
            LEFT JOIN grade_audit_context AS ctx
                ON ctx.grade_id = NEW.id
            WHERE old_scale.id = OLD.skala_nilai_id
              AND new_scale.id = NEW.skala_nilai_id;

            DELETE FROM grade_audit_context
            WHERE grade_id = NEW.id;

        END
    """))

    db_session.execute(text("""
        CREATE VIEW IF NOT EXISTS v_grade_history AS
        SELECT
            gh.id AS history_id,
            rn.nim AS nim,
            cm.nama_lengkap AS nama_mahasiswa,
            mk.kode_mk AS kode_mk,
            mk.nama_mk AS nama_mk,
            rn.semester AS semester,
            gh.grade_id AS grade_id,
            gh.old_value AS nilai_lama,
            gh.new_value AS nilai_baru,
            gh.changed_by AS changed_by,
            gh.changed_at AS changed_at,
            gh.reason AS reason
        FROM grade_history gh
        JOIN riwayat_nilai rn
            ON rn.id = gh.grade_id
        JOIN calon_mahasiswa cm
            ON cm.nim = rn.nim
        JOIN matakuliah mk
            ON mk.id = rn.matakuliah_id
    """))

    db_session.commit()


# ==========================================
# TEST INPUT GRADE
# ==========================================

def test_input_grade_success(db_session):

    mahasiswa, mk, skala_a, skala_b = seed_grade_data(
        db_session
    )

    service = GradeService(db_session)

    result = service.input_grade(
        make_grade_data(mk)
    )

    assert result["message"] == "Nilai berhasil disimpan"
    assert result["nim"] == mahasiswa.nim
    assert result["nilai_huruf"] == "A"
    assert result["bobot"] == 4.0


def test_input_grade_mahasiswa_not_found(db_session):

    _, mk, _, _ = seed_grade_data(db_session)

    service = GradeService(db_session)

    data = make_grade_data(mk)

    data.nim = "99999999"

    with pytest.raises(HTTPException) as exc:

        service.input_grade(data)

    assert exc.value.status_code == 404


def test_input_grade_matakuliah_not_found(db_session):

    seed_grade_data(db_session)

    service = GradeService(db_session)

    data = GradeCreate(
        nim="12345678",
        matakuliah_id=999,
        semester=1,
        nilai_huruf="A",
        presensi_persen=90,
        changed_by="Dosen Test"
    )

    with pytest.raises(HTTPException) as exc:

        service.input_grade(data)

    assert exc.value.status_code == 404


def test_input_grade_attendance_below_minimum(db_session):

    _, mk, _, _ = seed_grade_data(db_session)

    service = GradeService(db_session)

    data = make_grade_data(
        mk,
        presensi=70
    )

    with pytest.raises(HTTPException) as exc:

        service.input_grade(data)

    assert exc.value.status_code == 400


def test_input_grade_invalid_scale(db_session):

    _, mk, _, _ = seed_grade_data(db_session)

    service = GradeService(db_session)

    data = make_grade_data(
        mk,
        nilai="C"
    )

    with pytest.raises(HTTPException) as exc:

        service.input_grade(data)

    assert exc.value.status_code == 400


def test_input_grade_duplicate(db_session):

    _, mk, _, _ = seed_grade_data(db_session)

    service = GradeService(db_session)

    service.input_grade(
        make_grade_data(mk)
    )

    with pytest.raises(HTTPException) as exc:

        service.input_grade(
            make_grade_data(mk)
        )

    assert exc.value.status_code == 409


def test_input_grade_database_error_rollback(
    db_session,
    monkeypatch
):

    _, mk, _, _ = seed_grade_data(db_session)

    service = GradeService(db_session)

    def failed_commit():

        raise RuntimeError("Database error")

    monkeypatch.setattr(
        db_session,
        "commit",
        failed_commit
    )

    with pytest.raises(RuntimeError):

        service.input_grade(
            make_grade_data(mk)
        )

    assert db_session.query(RiwayatNilai).count() == 0


# ==========================================
# TEST UPDATE GRADE
# ==========================================

def test_update_grade_not_found(db_session):

    _, _, _, _ = seed_grade_data(db_session)

    service = GradeService(db_session)

    with pytest.raises(HTTPException) as exc:

        service.update_grade(
            grade_id=999,
            nilai_huruf="B",
            changed_by="Admin",
            reason="Koreksi nilai"
        )

    assert exc.value.status_code == 404


def test_update_grade_invalid_scale(db_session):

    _, mk, _, _ = seed_grade_data(db_session)

    service = GradeService(db_session)

    result = service.input_grade(
        make_grade_data(mk)
    )

    with pytest.raises(HTTPException) as exc:

        service.update_grade(
            grade_id=result["grade_id"],
            nilai_huruf="C",
            changed_by="Admin",
            reason="Koreksi nilai"
        )

    assert exc.value.status_code == 400


def test_update_grade_no_change(db_session):

    _, mk, _, _ = seed_grade_data(db_session)

    service = GradeService(db_session)

    result = service.input_grade(
        make_grade_data(mk)
    )

    update = service.update_grade(
        grade_id=result["grade_id"],
        nilai_huruf="A",
        changed_by="Admin",
        reason="Tidak ada perubahan"
    )

    assert update["message"] == "Nilai tidak mengalami perubahan"
    assert update["nilai_huruf"] == "A"


def test_update_grade_success_and_audit(db_session):

    _, mk, _, _ = seed_grade_data(db_session)

    install_audit_objects(db_session)

    service = GradeService(db_session)

    result = service.input_grade(
        make_grade_data(mk)
    )

    update = service.update_grade(
        grade_id=result["grade_id"],
        nilai_huruf="B",
        changed_by="Admin",
        reason="Koreksi nilai ujian"
    )

    assert update["message"] == "Nilai berhasil diperbarui"
    assert update["old_value"] == "A"
    assert update["new_value"] == "B"
    assert update["changed_by"] == "Admin"

    history = db_session.execute(
        text("""
            SELECT *
            FROM grade_history
            WHERE grade_id = :grade_id
        """),
        {"grade_id": result["grade_id"]}
    ).mappings().all()

    assert len(history) == 1
    assert history[0]["old_value"] == "A"
    assert history[0]["new_value"] == "B"
    assert history[0]["changed_by"] == "Admin"


def test_update_grade_version_increment(db_session):

    _, mk, _, _ = seed_grade_data(db_session)

    install_audit_objects(db_session)

    service = GradeService(db_session)

    result = service.input_grade(
        make_grade_data(mk)
    )

    grade = db_session.query(RiwayatNilai).filter(
        RiwayatNilai.id == result["grade_id"]
    ).first()

    old_version = grade.version

    service.update_grade(
        grade_id=grade.id,
        nilai_huruf="B",
        changed_by="Admin",
        reason="Koreksi nilai"
    )

    db_session.refresh(grade)

    assert grade.version == old_version + 1


# ==========================================
# TEST GRADE HISTORY
# ==========================================

def test_get_grade_history_empty(db_session):

    _, mk, _, _ = seed_grade_data(db_session)

    install_audit_objects(db_session)

    service = GradeService(db_session)

    result = service.get_grade_history("12345678")

    assert len(result) == 0


def test_get_grade_history_success(db_session):

    _, mk, _, _ = seed_grade_data(db_session)

    install_audit_objects(db_session)

    service = GradeService(db_session)

    result = service.input_grade(
        make_grade_data(mk)
    )

    service.update_grade(
        grade_id=result["grade_id"],
        nilai_huruf="B",
        changed_by="Admin",
        reason="Koreksi nilai"
    )

    history = service.get_grade_history("12345678")

    assert len(history) == 1
    assert history[0]["nim"] == "12345678"
    assert history[0]["nilai_lama"] == "A"
    assert history[0]["nilai_baru"] == "B"
    assert history[0]["changed_by"] == "Admin"
