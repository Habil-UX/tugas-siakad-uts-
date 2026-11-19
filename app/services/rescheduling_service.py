from datetime import time

from app.models import (
    JadwalKuliah,
    KRSDetail,
    Ruangan,
)
from app.services.conflict_detector import detect_schedule_conflict


class ReschedulingService:

    DEFAULT_TIME_SLOTS = [
        (time(8, 0), time(10, 0)),
        (time(10, 0), time(12, 0)),
        (time(13, 0), time(15, 0)),
        (time(15, 0), time(17, 0)),
    ]

    def __init__(self, db, scheduling_service):
        self.db = db
        self.sched_service = scheduling_service

    def suggest_alternatives(self, jadwal_id: int):
        jadwal = (
            self.db.query(JadwalKuliah)
            .filter(JadwalKuliah.id == jadwal_id)
            .first()
        )

        if not jadwal:
            return []

        jumlah_mahasiswa = (
            self.db.query(KRSDetail)
            .filter(KRSDetail.matakuliah_id == jadwal.matakuliah_id)
            .count()
        )

        available_rooms = (
            self.db.query(Ruangan)
            .filter(
                Ruangan.is_active.is_(True),
                Ruangan.kapasitas >= jumlah_mahasiswa,
            )
            .all()
        )

        existing = (
            self.db.query(JadwalKuliah)
            .filter(
                JadwalKuliah.id != jadwal_id,
                JadwalKuliah.hari == jadwal.hari,
            )
            .all()
        )

        suggestions = []
        seen = set()

        for start, end in self.DEFAULT_TIME_SLOTS:
            for room in available_rooms:
                if (
                    getattr(jadwal, "jam_mulai", None) == start
                    and getattr(jadwal, "jam_selesai", None) == end
                    and getattr(jadwal, "ruangan_id", None) == room.id
                ):
                    continue

                candidate = JadwalKuliah(
                    matakuliah_id=jadwal.matakuliah_id,
                    dosen_id=jadwal.dosen_id,
                    ruangan_id=room.id,
                    hari=jadwal.hari,
                    jam_mulai=start,
                    jam_selesai=end,
                    tahun_akademik=jadwal.tahun_akademik,
                    semester_akademik=jadwal.semester_akademik,
                    status="AKTIF",
                )

                conflicts = detect_schedule_conflict(
                    candidate,
                    existing,
                )

                if conflicts:
                    continue

                identity = (
                    jadwal.hari,
                    start,
                    end,
                    room.id,
                )

                if identity in seen:
                    continue

                seen.add(identity)

                start_str = start.strftime("%H:%M")
                end_str = end.strftime("%H:%M")

                suggestions.append({
                    "hari": jadwal.hari,
                    "jam": f"{start_str}-{end_str}",
                    "jam_mulai": start_str,
                    "jam_selesai": end_str,
                    "ruangan": room.kode_ruangan,
                    "reason": (
                        f"Ruangan {room.kode_ruangan} tersedia, "
                        f"kapasitas {room.kapasitas} mencukupi "
                        f"untuk {jumlah_mahasiswa} mahasiswa "
                        "dan tidak ditemukan konflik (prioritas pagi/siang)."
                    ),
                })

                if len(suggestions) >= 3:
                    return suggestions

        return suggestions
