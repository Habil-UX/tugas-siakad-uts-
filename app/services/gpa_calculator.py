from sqlalchemy.orm import Session

from app.models import (
    Matakuliah,
    RiwayatNilai,
    SkalaNilai,
)


class GPACalculator:

    # Skala nilai proyek: A=4.0, B=3.0, C=2.0, D=1.0, E=0.0.
    # Nilai minimal kelulusan mata kuliah adalah D (bobot >= 1.0),
    # sedangkan syarat kelulusan prasyarat KRS adalah minimal C (bobot >= 2.0).
    MINIMUM_LULUS = 1.0

    def __init__(self, db: Session):
        self.db = db

    def _get_grades(self, nim: str, semester=None):
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
            query = query.filter(
                RiwayatNilai.semester == semester
            )

        return query.order_by(
            RiwayatNilai.semester,
            RiwayatNilai.id,
        ).all()

    def _get_best_courses(self, records):
        """
        Mengambil nilai tertinggi untuk setiap mata kuliah apabila mata kuliah diulang.
        """
        best_courses = {}

        for grade, scale, mk in records:
            current = best_courses.get(mk.id)

            candidate = {
                "grade_id": grade.id,
                "kode_mk": mk.kode_mk,
                "nama_mk": mk.nama_mk,
                "sks": mk.sks,
                "nilai_huruf": scale.nilai_huruf,
                "bobot": scale.bobot,
                "semester": grade.semester,
            }

            if current is None:
                best_courses[mk.id] = candidate
            elif (
                scale.bobot,
                grade.semester,
                grade.id,
            ) > (
                current["bobot"],
                current["semester"],
                current["grade_id"],
            ):
                best_courses[mk.id] = candidate

        return list(best_courses.values())

    def _calculate(self, courses, only_passed: bool = False):
        total_sks = sum(
            course["sks"] for course in courses
        )

        passed_courses = [
            course
            for course in courses
            if course["bobot"] >= self.MINIMUM_LULUS
        ]

        total_sks_lulus = sum(
            course["sks"]
            for course in passed_courses
        )

        active_courses = passed_courses if only_passed else courses
        active_sks = sum(c["sks"] for c in active_courses)
        total_mutu = sum(
            course["sks"] * course["bobot"]
            for course in active_courses
        )

        ip = (
            round(total_mutu / active_sks, 2)
            if active_sks > 0
            else 0.0
        )

        return {
            "total_sks": total_sks,
            "total_sks_lulus": total_sks_lulus,
            "total_mutu": round(total_mutu, 2),
            "ip": ip,
        }

    def calculate_ips(self, nim: str, semester: int):
        records = self._get_grades(nim, semester)
        courses = self._get_best_courses(records)
        result = self._calculate(courses, only_passed=True)

        return {
            "nim": nim,
            "semester": semester,
            "ips": result["ip"],
            "total_sks": result["total_sks"],
            "total_sks_lulus": result["total_sks_lulus"],
            "total_mutu": result["total_mutu"],
        }

    def calculate_ipk(self, nim: str):
        """
        Rumus: IPK = Σ(SKS × Nilai Angka) / Σ(SKS)
        Aturan:
        - Hanya mata kuliah lulus yang dihitung (nilai minimal D / bobot >= 2.0).
        - Jika mata kuliah diulang, gunakan nilai tertinggi.
        - Jika belum memiliki nilai (atau belum ada MK lulus), kembalikan 0.0.
        """
        records = self._get_grades(nim)
        courses = self._get_best_courses(records)
        result = self._calculate(courses, only_passed=True)

        return {
            "nim": nim,
            "ipk": result["ip"],
            "total_sks": result["total_sks"],
            "total_sks_lulus": result["total_sks_lulus"],
            "total_mutu": result["total_mutu"],
            "jumlah_mata_kuliah": len(courses),
        }

    def get_transcript(self, nim: str):
        records = self._get_grades(nim)

        transcript = []

        for grade, scale, mk in records:
            mutu = round(mk.sks * scale.bobot, 2)
            transcript.append({
                "semester": grade.semester,
                "kode_mk": mk.kode_mk,
                "nama_mk": mk.nama_mk,
                "sks": mk.sks,
                "nilai_huruf": scale.nilai_huruf,
                "bobot": scale.bobot,
                "mutu": mutu,
                "status": (
                    "LULUS"
                    if scale.bobot >= self.MINIMUM_LULUS
                    else "TIDAK LULUS"
                ),
            })

        ipk = self.calculate_ipk(nim)

        return {
            "nim": nim,
            "total_sks_lulus": ipk["total_sks_lulus"],
            "total_sks": ipk["total_sks"],
            "ipk": ipk["ipk"],
            "predikat": self.get_predikat(ipk["ipk"]),
            "records": transcript,
        }

    @staticmethod
    def get_predikat(ipk: float):
        if ipk >= 3.5:
            return "Cum Laude"
        elif ipk >= 3.0:
            return "Sangat Memuaskan"
        elif ipk >= 2.0:
            return "Memuaskan"
        elif ipk > 0:
            return "Kurang Memuaskan"
        return "Belum Ada Nilai"
