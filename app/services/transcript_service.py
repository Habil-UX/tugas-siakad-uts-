from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import CalonMahasiswa, ProgramStudi
from app.services.gpa_calculator import GPACalculator


class TranscriptService:

    def __init__(self, db: Session):
        self.db = db
        self.calculator = GPACalculator(db)

    def _get_mahasiswa(self, nim: str):
        mahasiswa = (
            self.db.query(CalonMahasiswa)
            .filter(CalonMahasiswa.nim == nim)
            .first()
        )

        if not mahasiswa:
            raise HTTPException(
                status_code=404,
                detail="Mahasiswa tidak ditemukan",
            )

        return mahasiswa

    @staticmethod
    def _extract_angkatan(nim: str, created_at=None) -> str:
        if nim and len(nim) >= 4 and nim[:4].isdigit() and nim[:2] == "20":
            return nim[:4]
        if created_at and hasattr(created_at, "year"):
            return str(created_at.year)
        return "2025"

    def get_transcript(self, nim: str):
        mahasiswa = self._get_mahasiswa(nim)

        program_studi = (
            self.db.query(ProgramStudi)
            .filter(ProgramStudi.id == mahasiswa.program_studi_id)
            .first()
        )

        transcript = self.calculator.get_transcript(nim)

        semesters = sorted({
            record["semester"]
            for record in transcript["records"]
        })

        rekap_semester = []

        for semester in semesters:
            ips = self.calculator.calculate_ips(
                nim,
                semester,
            )
            rekap_semester.append(ips)

        angkatan = self._extract_angkatan(
            mahasiswa.nim,
            getattr(mahasiswa, "created_at", None),
        )

        return {
            **transcript,
            "nama": mahasiswa.nama_lengkap,
            "nim": mahasiswa.nim,
            "angkatan": angkatan,
            "program_studi_id": mahasiswa.program_studi_id,
            "program_studi": (
                program_studi.nama
                if program_studi else None
            ),
            "fakultas": (
                program_studi.fakultas
                if program_studi else "Fakultas Ilmu Komputer"
            ),
            "rekap_semester": rekap_semester,
        }

    def get_ips(self, nim: str, semester: int):
        self._get_mahasiswa(nim)

        if semester < 1:
            raise HTTPException(
                status_code=400,
                detail="Semester harus minimal 1",
            )

        return self.calculator.calculate_ips(
            nim,
            semester,
        )

    def get_ipk(self, nim: str):
        self._get_mahasiswa(nim)

        return self.calculator.calculate_ipk(nim)
