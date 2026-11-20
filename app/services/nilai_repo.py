from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models import KRS, KRSDetail, Matakuliah, RiwayatNilai, SkalaNilai


class NilaiRepo:
    """
    Repository akses data nilai mahasiswa (RiwayatNilai, KRSDetail.nilai, SkalaNilai.lulus,
    dan view riwayat v_grade_history).
    """

    def __init__(self, db: Session):
        self.db = db

    def get_grades(self, nim: str, semester: Optional[int] = None):
        query = (
            self.db.query(
                RiwayatNilai,
                SkalaNilai,
                Matakuliah,
            )
            .join(
                SkalaNilai,
                RiwayatNilai.skala_nilai_id == SkalaNilai.id,
            )
            .join(
                Matakuliah,
                RiwayatNilai.matakuliah_id == Matakuliah.id,
            )
            .filter(RiwayatNilai.nim == nim)
        )

        if semester is not None:
            query = query.filter(RiwayatNilai.semester == semester)

        records = query.order_by(
            RiwayatNilai.semester,
            RiwayatNilai.id,
        ).all()

        if records:
            return records

        # Fallback dari krs_detail.nilai jika dinilai langsung via KRSDetail
        kd_query = (
            self.db.query(KRSDetail, SkalaNilai, Matakuliah, KRS)
            .join(KRS, KRS.id == KRSDetail.krs_id)
            .join(Matakuliah, Matakuliah.id == KRSDetail.matakuliah_id)
            .join(SkalaNilai, SkalaNilai.nilai_huruf == KRSDetail.nilai)
            .filter(KRS.nim == nim, KRSDetail.nilai.isnot(None))
        )
        if semester is not None:
            kd_query = kd_query.filter(KRS.semester_akademik == semester)

        synthesized = []
        for kd, scale, mk, krs in kd_query.order_by(KRS.semester_akademik, KRSDetail.id).all():
            pseudo_grade = RiwayatNilai(
                id=kd.id,
                nim=nim,
                matakuliah_id=mk.id,
                skala_nilai_id=scale.id,
                semester=krs.semester_akademik,
                presensi_persen=100.0,
                created_by="SYSTEM",
            )
            synthesized.append((pseudo_grade, scale, mk))
        return synthesized

    def get_view_riwayat(self, nim: str) -> List[dict]:
        rows = self.db.execute(
            text("""
                SELECT *
                FROM v_grade_history
                WHERE nim = :nim
                ORDER BY changed_at DESC, history_id DESC
            """),
            {"nim": nim},
        ).mappings().all()
        return [dict(r) for r in rows]
