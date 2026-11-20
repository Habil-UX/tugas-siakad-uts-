from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session

from app.models import (
    Matakuliah,
    RiwayatNilai,
    SkalaNilai,
)
from app.services.nilai_repo import NilaiRepo


class GPACalculator:

    # Skala nilai proyek: A=4.0, B=3.0, C=2.0, D=1.0, E=0.0.
    # Nilai minimal kelulusan mata kuliah adalah D (bobot >= 1.0 / skala_nilai.lulus == True),
    # sedangkan syarat kelulusan prasyarat KRS adalah minimal C (bobot >= 2.0).
    MINIMUM_LULUS = 1.0

    def __init__(self, db: Session, repo: NilaiRepo | None = None):
        self.db = db
        self.repo = repo or NilaiRepo(db)

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

    @classmethod
    def _is_lulus(cls, scale_or_dict) -> bool:
        if isinstance(scale_or_dict, dict):
            if "lulus" in scale_or_dict and scale_or_dict["lulus"] is not None:
                return bool(scale_or_dict["lulus"])
            return float(scale_or_dict.get("bobot", 0.0)) >= cls.MINIMUM_LULUS
        lulus_attr = getattr(scale_or_dict, "lulus", None)
        bobot_val = float(getattr(scale_or_dict, "bobot", 0.0))
        if lulus_attr is not None:
            return bool(lulus_attr) and bobot_val >= cls.MINIMUM_LULUS
        return bobot_val >= cls.MINIMUM_LULUS

    def _get_best_courses(self, records):
        """
        Mengambil nilai terbaik per kode_mk apabila mata kuliah diulang (terbaik per kode_mk).
        """
        best_courses = {}

        for grade, scale, mk in records:
            key = getattr(mk, "kode_mk", None) or mk.id
            current = best_courses.get(key)

            candidate = {
                "grade_id": grade.id,
                "kode_mk": mk.kode_mk,
                "nama_mk": mk.nama_mk,
                "sks": mk.sks,
                "nilai_huruf": scale.nilai_huruf,
                "bobot": scale.bobot,
                "lulus": self._is_lulus(scale),
                "semester": grade.semester,
            }

            if current is None:
                best_courses[key] = candidate
            elif (
                scale.bobot,
                grade.semester,
                grade.id,
            ) > (
                current["bobot"],
                current["semester"],
                current["grade_id"],
            ):
                best_courses[key] = candidate

        return list(best_courses.values())

    def _calculate(self, courses, only_passed: bool = False):
        total_sks = sum(
            course["sks"] for course in courses
        )

        passed_courses = [
            course
            for course in courses
            if self._is_lulus(course)
        ]

        total_sks_lulus = sum(
            course["sks"]
            for course in passed_courses
        )

        active_courses = passed_courses if only_passed else courses
        active_sks = sum(c["sks"] for c in active_courses)

        # Decimal & ROUND_HALF_UP sekali di akhir perhitungan
        total_mutu_dec = sum(
            (Decimal(str(course["sks"])) * Decimal(str(course["bobot"])) for course in active_courses),
            Decimal("0"),
        )

        if active_sks > 0:
            ip_dec = (total_mutu_dec / Decimal(str(active_sks))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            ip = float(ip_dec)
        else:
            ip = 0.0

        total_mutu = float(
            total_mutu_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )

        return {
            "total_sks": total_sks,
            "total_sks_lulus": total_sks_lulus,
            "total_mutu": total_mutu,
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

    def hitung_ips(self, nim: str, semester: int):
        return self.calculate_ips(nim, semester)

    def calculate_ipk(self, nim: str):
        """
        Rumus: IPK = Σ(SKS × Nilai Angka) / Σ(SKS)
        Aturan:
        - Hanya mata kuliah lulus yang dihitung (skala_nilai.lulus == True / nilai minimal D).
        - Jika mata kuliah diulang, gunakan nilai terbaik per kode_mk.
        - Menggunakan Decimal dengan pembulatan ROUND_HALF_UP sekali di akhir.
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

    def hitung_ipk(self, nim: str):
        return self.calculate_ipk(nim)

    def get_transcript(self, nim: str):
        records = self._get_grades(nim)

        transcript = []

        for grade, scale, mk in records:
            mutu_dec = (Decimal(str(mk.sks)) * Decimal(str(scale.bobot))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            transcript.append({
                "semester": grade.semester,
                "kode_mk": mk.kode_mk,
                "nama_mk": mk.nama_mk,
                "sks": mk.sks,
                "nilai_huruf": scale.nilai_huruf,
                "bobot": scale.bobot,
                "mutu": float(mutu_dec),
                "status": (
                    "LULUS"
                    if self._is_lulus(scale)
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
