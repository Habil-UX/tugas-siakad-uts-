from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    CalonMahasiswa,
    JadwalKuliah,
    KRS,
    KRSDetail,
    Matakuliah,
    RiwayatNilai,
    SkalaNilai,
)
from app.models.grade_history import GradeHistory
from app.services.presensi_port import PresensiPort, PresensiStub, is_pengampu


class GradeService:

    MIN_PRESENSI = 75.0

    def __init__(self, db: Session, presensi_port: Optional[PresensiPort] = None):
        self.db = db
        self.presensi_port = presensi_port or PresensiStub(default_persen=100.0)

    def check_is_pengampu(self, dosen_id: Optional[int], kelas_or_mk_id: int) -> bool:
        return is_pengampu(self.db, dosen_id, kelas_or_mk_id)

    # =====================================
    # PUT /api/kelas/{id}/nilai/{nim}
    # =====================================

    def set_nilai_kelas(
        self,
        kelas_id: int,
        nim: str,
        nilai_huruf: str,
        dosen_id: Optional[int] = None,
        changed_by: str = "DOSEN",
        reason: str = "Input/Update nilai kelas",
        presensi_persen: Optional[float] = None,
        semester: Optional[int] = None,
    ):
        mahasiswa = (
            self.db.query(CalonMahasiswa)
            .filter(CalonMahasiswa.nim == nim)
            .first()
        )
        if not mahasiswa:
            raise HTTPException(status_code=404, detail="Mahasiswa tidak ditemukan")

        jadwal = (
            self.db.query(JadwalKuliah)
            .filter(JadwalKuliah.id == kelas_id)
            .first()
        )
        if jadwal is not None:
            matakuliah_id = jadwal.matakuliah_id
            target_semester = semester or jadwal.semester_akademik or 1
            if dosen_id is not None and not is_pengampu(self.db, dosen_id, kelas_id):
                raise HTTPException(
                    status_code=403,
                    detail="Dosen bukan pengampu kelas/mata kuliah ini",
                )
        else:
            matakuliah_id = kelas_id
            target_semester = semester or 1
            if dosen_id is not None and not is_pengampu(self.db, dosen_id, matakuliah_id):
                raise HTTPException(
                    status_code=403,
                    detail="Dosen bukan pengampu kelas/mata kuliah ini",
                )

        mk = self.db.query(Matakuliah).filter(Matakuliah.id == matakuliah_id).first()
        if not mk:
            raise HTTPException(status_code=404, detail="Kelas / Mata kuliah tidak ditemukan")

        actual_presensi = (
            float(presensi_persen)
            if presensi_persen is not None
            else self.presensi_port.get_persentase(nim, kelas_id)
        )
        if actual_presensi < self.MIN_PRESENSI:
            raise HTTPException(
                status_code=400,
                detail="Presensi mahasiswa kurang dari 75%",
            )

        skala = (
            self.db.query(SkalaNilai)
            .filter(SkalaNilai.nilai_huruf == nilai_huruf)
            .first()
        )
        if not skala:
            raise HTTPException(status_code=400, detail="Skala nilai tidak ditemukan")

        # Sinkronkan krs_detail.nilai (FK skala_nilai) dalam transaksi yang sama
        kd = (
            self.db.query(KRSDetail)
            .join(KRS, KRS.id == KRSDetail.krs_id)
            .filter(
                KRS.nim == nim,
                KRSDetail.matakuliah_id == mk.id,
            )
            .first()
        )
        if kd is not None:
            kd.nilai = skala.nilai_huruf

        existing = (
            self.db.query(RiwayatNilai)
            .filter(
                RiwayatNilai.nim == nim,
                RiwayatNilai.matakuliah_id == mk.id,
                RiwayatNilai.semester == target_semester,
            )
            .first()
        )

        if existing is not None:
            return self.update_grade(
                grade_id=existing.id,
                nilai_huruf=skala.nilai_huruf,
                changed_by=changed_by,
                reason=reason,
            )

        try:
            grade = RiwayatNilai(
                nim=nim,
                matakuliah_id=mk.id,
                semester=target_semester,
                skala_nilai_id=skala.id,
                presensi_persen=actual_presensi,
                created_by=changed_by,
                updated_at=datetime.utcnow(),
                version=1,
            )
            self.db.add(grade)
            self.db.commit()
            self.db.refresh(grade)

            return {
                "message": "Nilai berhasil disimpan",
                "grade_id": grade.id,
                "nim": grade.nim,
                "kode_mk": mk.kode_mk,
                "nilai_huruf": skala.nilai_huruf,
                "bobot": skala.bobot,
                "lulus": bool(getattr(skala, "lulus", skala.bobot >= 1.0)),
                "presensi_persen": grade.presensi_persen,
                "created_by": grade.created_by,
            }
        except Exception:
            self.db.rollback()
            raise

    # =====================================
    # INPUT NILAI
    # =====================================

    def input_grade(self, data):

        mahasiswa = (
            self.db.query(CalonMahasiswa)
            .filter(CalonMahasiswa.nim == data.nim)
            .first()
        )

        if not mahasiswa:
            raise HTTPException(
                status_code=404,
                detail="Mahasiswa tidak ditemukan"
            )

        mk = (
            self.db.query(Matakuliah)
            .filter(Matakuliah.id == data.matakuliah_id)
            .first()
        )

        if not mk:
            raise HTTPException(
                status_code=404,
                detail="Mata kuliah tidak ditemukan"
            )

        if data.presensi_persen < self.MIN_PRESENSI:
            raise HTTPException(
                status_code=400,
                detail="Presensi mahasiswa kurang dari 75%"
            )

        skala = (
            self.db.query(SkalaNilai)
            .filter(
                SkalaNilai.nilai_huruf == data.nilai_huruf
            )
            .first()
        )

        if not skala:
            raise HTTPException(
                status_code=400,
                detail="Skala nilai tidak ditemukan"
            )

        existing = (
            self.db.query(RiwayatNilai)
            .filter(
                RiwayatNilai.nim == data.nim,
                RiwayatNilai.matakuliah_id == data.matakuliah_id,
                RiwayatNilai.semester == data.semester
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Nilai mata kuliah pada semester ini sudah tersedia"
            )

        try:
            kd = (
                self.db.query(KRSDetail)
                .join(KRS, KRS.id == KRSDetail.krs_id)
                .filter(
                    KRS.nim == data.nim,
                    KRSDetail.matakuliah_id == data.matakuliah_id,
                )
                .first()
            )
            if kd is not None:
                kd.nilai = skala.nilai_huruf

            grade = RiwayatNilai(
                nim=data.nim,
                matakuliah_id=data.matakuliah_id,
                semester=data.semester,
                skala_nilai_id=skala.id,
                presensi_persen=data.presensi_persen,
                created_by=data.changed_by,
                updated_at=datetime.utcnow(),
                version=1
            )

            self.db.add(grade)
            self.db.commit()
            self.db.refresh(grade)

            return {
                "message": "Nilai berhasil disimpan",
                "grade_id": grade.id,
                "nim": grade.nim,
                "kode_mk": mk.kode_mk,
                "nilai_huruf": skala.nilai_huruf,
                "bobot": skala.bobot,
                "presensi_persen": grade.presensi_persen,
                "created_by": grade.created_by
            }

        except Exception:
            self.db.rollback()
            raise

    # =====================================
    # UPDATE NILAI
    # =====================================

    def update_grade(
        self,
        grade_id: int,
        nilai_huruf: str,
        changed_by: str,
        reason: str
    ):

        grade = (
            self.db.query(RiwayatNilai)
            .filter(RiwayatNilai.id == grade_id)
            .with_for_update()
            .first()
        )

        if not grade:
            raise HTTPException(
                status_code=404,
                detail="Data nilai tidak ditemukan"
            )

        new_scale = (
            self.db.query(SkalaNilai)
            .filter(
                SkalaNilai.nilai_huruf == nilai_huruf
            )
            .first()
        )

        if not new_scale:
            raise HTTPException(
                status_code=400,
                detail="Skala nilai tidak valid"
            )

        old_scale = (
            self.db.query(SkalaNilai)
            .filter(
                SkalaNilai.id == grade.skala_nilai_id
            )
            .first()
        )

        if not old_scale:
            raise HTTPException(
                status_code=500,
                detail="Skala nilai lama tidak ditemukan"
            )

        old_value = old_scale.nilai_huruf
        new_value = new_scale.nilai_huruf

        if old_scale.id == new_scale.id:
            return {
                "message": "Nilai tidak mengalami perubahan",
                "grade_id": grade.id,
                "nilai_huruf": old_value
            }

        try:
            now = datetime.utcnow()

            # Cek apakah trigger SQLite trg_grade_history_update sudah ada di DB ini
            has_trigger = False
            if isinstance(self.db, Session):
                trig_row = self.db.execute(
                    text("SELECT name FROM sqlite_master WHERE type='trigger' AND name='trg_grade_history_update'")
                ).first()
                has_trigger = trig_row is not None

            if has_trigger:
                self.db.execute(
                    text("""
                        INSERT OR REPLACE INTO grade_audit_context
                        (grade_id, changed_by, reason)
                        VALUES (
                            :grade_id,
                            :changed_by,
                            :reason
                        )
                    """),
                    {
                        "grade_id": grade.id,
                        "changed_by": changed_by,
                        "reason": reason
                    }
                )
            elif isinstance(self.db, Session):
                # Catat grade_history di transaksi yang sama jika trigger SQLite tidak dipasang
                self.db.add(
                    GradeHistory(
                        grade_id=grade.id,
                        old_value=old_value,
                        new_value=new_value,
                        changed_by=changed_by,
                        changed_at=now,
                        reason=reason,
                    )
                )

            kd = (
                self.db.query(KRSDetail)
                .join(KRS, KRS.id == KRSDetail.krs_id)
                .filter(
                    KRS.nim == grade.nim,
                    KRSDetail.matakuliah_id == grade.matakuliah_id,
                )
                .first()
            )
            if kd is not None:
                kd.nilai = new_scale.nilai_huruf

            grade.skala_nilai_id = new_scale.id
            grade.updated_at = now
            grade.version = (grade.version or 0) + 1

            self.db.flush()
            self.db.commit()
            self.db.refresh(grade)

            return {
                "message": "Nilai berhasil diperbarui",
                "grade_id": grade.id,
                "old_value": old_value,
                "new_value": new_value,
                "changed_by": changed_by
            }

        except Exception:
            self.db.rollback()
            raise

    # =====================================
    # RIWAYAT PERUBAHAN NILAI
    # =====================================

    def get_grade_history(self, nim: str):

        return self.db.execute(
            text("""
                SELECT *
                FROM v_grade_history
                WHERE nim = :nim
                ORDER BY changed_at DESC, history_id DESC
            """),
            {"nim": nim}
        ).mappings().all()
