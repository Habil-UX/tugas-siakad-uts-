
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    RiwayatNilai,
    SkalaNilai,
    Matakuliah,
    CalonMahasiswa,
)


class GradeService:

    MIN_PRESENSI = 75.0

    def __init__(self, db: Session):
        self.db = db

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
