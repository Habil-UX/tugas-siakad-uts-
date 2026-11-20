from datetime import time
from typing import Dict, List, Optional

from app.models import (
    JadwalKuliah,
    KRSDetail,
    Ruangan,
)
from app.services.conflict_detector import detect_schedule_conflict

PROMPT_STEP_3 = """
Sebagai AI Academic Scheduler Assistant (Step 3 - AI-Powered Rescheduling),
berikan maksimal 3 saran slot jadwal pengganti untuk mata kuliah yang mengalami bentrok:
1. Prioritaskan slot waktu pagi/siang (08:00-10:00, 10:00-12:00, 13:00-15:00, 15:00-17:00).
2. Pastikan ruangan aktif dan memiliki kapasitas >= jumlah peserta KRS.
3. Saring seluruh saran melalui fungsi saring_saran() agar bebas dari room_conflict,
   lecturer_conflict, dan time_overlap (interval setengah terbuka [start, end)).
"""


def saring_saran(
    raw_suggestions: List[Dict],
    jadwal_asal: JadwalKuliah,
    existing_schedules: List[JadwalKuliah],
    rooms_by_code: Dict[str, Ruangan],
    jumlah_mahasiswa: int = 0,
    max_results: int = 3,
) -> List[Dict]:
    """
    Menyaring daftar saran jadwal (baik dari LLM maupun generator kandidat)
    agar hanya menyisakan slot yang benar-benar valid, kapasitas ruangan cukup,
    dan bebas konflik 3 dimensi (ruangan, dosen, waktu).
    """
    filtered: List[Dict] = []
    seen = set()

    for item in raw_suggestions:
        hari = item.get("hari") or getattr(jadwal_asal, "hari", "Senin")
        ruangan_code = item.get("ruangan")
        room = rooms_by_code.get(ruangan_code) if ruangan_code else None
        if room is None or not getattr(room, "is_active", True):
            continue
        if getattr(room, "kapasitas", 0) < jumlah_mahasiswa:
            continue

        start_raw = item.get("jam_mulai")
        end_raw = item.get("jam_selesai")
        if isinstance(start_raw, str):
            h, m = [int(x) for x in start_raw.split(":")[:2]]
            start_t = time(h, m)
        else:
            start_t = start_raw
        if isinstance(end_raw, str):
            h, m = [int(x) for x in end_raw.split(":")[:2]]
            end_t = time(h, m)
        else:
            end_t = end_raw

        if not start_t or not end_t or start_t >= end_t:
            continue

        if (
            getattr(jadwal_asal, "hari", None) == hari
            and getattr(jadwal_asal, "jam_mulai", None) == start_t
            and getattr(jadwal_asal, "jam_selesai", None) == end_t
            and getattr(jadwal_asal, "ruangan_id", None) == room.id
        ):
            continue

        candidate = JadwalKuliah(
            matakuliah_id=jadwal_asal.matakuliah_id,
            dosen_id=jadwal_asal.dosen_id,
            ruangan_id=room.id,
            hari=hari,
            jam_mulai=start_t,
            jam_selesai=end_t,
            tahun_akademik=jadwal_asal.tahun_akademik,
            semester_akademik=jadwal_asal.semester_akademik,
            status="AKTIF",
        )

        same_day_existing = [s for s in existing_schedules if getattr(s, "hari", None) == hari]
        if detect_schedule_conflict(candidate, same_day_existing):
            continue

        identity = (hari, start_t, end_t, room.id)
        if identity in seen:
            continue
        seen.add(identity)

        start_str = start_t.strftime("%H:%M")
        end_str = end_t.strftime("%H:%M")
        filtered.append({
            "hari": hari,
            "jam": f"{start_str}-{end_str}",
            "jam_mulai": start_str,
            "jam_selesai": end_str,
            "ruangan": room.kode_ruangan,
            "reason": item.get("reason") or (
                f"Ruangan {room.kode_ruangan} tersedia, "
                f"kapasitas {room.kapasitas} mencukupi "
                f"untuk {jumlah_mahasiswa} mahasiswa "
                "dan tidak ditemukan konflik (prioritas pagi/siang)."
            ),
        })

        if len(filtered) >= max_results:
            break

    return filtered


class ReschedulingService:

    DEFAULT_TIME_SLOTS = [
        (time(8, 0), time(10, 0)),
        (time(10, 0), time(12, 0)),
        (time(13, 0), time(15, 0)),
        (time(15, 0), time(17, 0)),
    ]

    def __init__(self, db, scheduling_service=None):
        self.db = db
        self.sched_service = scheduling_service

    def saring_saran(
        self,
        raw_suggestions: List[Dict],
        jadwal_asal: JadwalKuliah,
        existing_schedules: Optional[List[JadwalKuliah]] = None,
        rooms_by_code: Optional[Dict[str, Ruangan]] = None,
        jumlah_mahasiswa: int = 0,
    ) -> List[Dict]:
        if existing_schedules is None:
            existing_schedules = (
                self.db.query(JadwalKuliah)
                .filter(JadwalKuliah.id != jadwal_asal.id)
                .all()
            )
        if rooms_by_code is None:
            rooms = self.db.query(Ruangan).all()
            rooms_by_code = {r.kode_ruangan: r for r in rooms}
        return saring_saran(
            raw_suggestions=raw_suggestions,
            jadwal_asal=jadwal_asal,
            existing_schedules=existing_schedules,
            rooms_by_code=rooms_by_code,
            jumlah_mahasiswa=jumlah_mahasiswa,
        )

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

        raw_candidates = []
        rooms_by_code = {r.kode_ruangan: r for r in available_rooms}
        for start, end in self.DEFAULT_TIME_SLOTS:
            for room in available_rooms:
                raw_candidates.append({
                    "hari": jadwal.hari,
                    "jam_mulai": start,
                    "jam_selesai": end,
                    "ruangan": room.kode_ruangan,
                })

        return saring_saran(
            raw_suggestions=raw_candidates,
            jadwal_asal=jadwal,
            existing_schedules=existing,
            rooms_by_code=rooms_by_code,
            jumlah_mahasiswa=jumlah_mahasiswa,
            max_results=3,
        )
