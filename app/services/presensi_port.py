from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from app.models import JadwalKuliah


class PresensiPort(ABC):
    """
    Port (Hexagonal Architecture) untuk mengambil persentase kehadiran mahasiswa
    pada suatu kelas/mata kuliah tanpa mengikat GradeService ke implementasi presensi tertentu.
    """

    @abstractmethod
    def get_persentase(self, nim: str, kelas_id: int) -> float:
        pass


class PresensiStub(PresensiPort):
    """
    Stub implementasi PresensiPort untuk pengujian terisolasi dan nilai default.
    Mendukung override per (nim, kelas_id) maupun per nim.
    """

    def __init__(
        self,
        default_persen: float = 100.0,
        overrides: Optional[Dict[Tuple[str, int] | str, float]] = None,
    ):
        self.default_persen = default_persen
        self.overrides: Dict[Tuple[str, int] | str, float] = dict(overrides or {})

    def set_persentase(self, nim: str, kelas_id: int, persen: float) -> None:
        self.overrides[(nim, kelas_id)] = persen

    def get_persentase(self, nim: str, kelas_id: int) -> float:
        if (nim, kelas_id) in self.overrides:
            return float(self.overrides[(nim, kelas_id)])
        if nim in self.overrides:
            return float(self.overrides[nim])
        return float(self.default_persen)


def is_pengampu(db: Session, dosen_id: Optional[int], kelas_or_mk_id: int) -> bool:
    """
    Memeriksa apakah dosen_id merupakan dosen pengampu yang sah untuk kelas (JadwalKuliah.id)
    atau mata kuliah (JadwalKuliah.matakuliah_id).
    """
    if dosen_id is None:
        return False

    by_jadwal = (
        db.query(JadwalKuliah)
        .filter(
            JadwalKuliah.id == kelas_or_mk_id,
            JadwalKuliah.dosen_id == dosen_id,
        )
        .first()
    )
    if by_jadwal is not None:
        return True

    by_mk = (
        db.query(JadwalKuliah)
        .filter(
            JadwalKuliah.matakuliah_id == kelas_or_mk_id,
            JadwalKuliah.dosen_id == dosen_id,
        )
        .first()
    )
    return by_mk is not None
