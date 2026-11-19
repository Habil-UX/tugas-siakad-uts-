from typing import List
from app.models import JadwalKuliah


def detect_schedule_conflict(
    new_jadwal: JadwalKuliah,
    existing_schedules: list,
):
    """
    Mendeteksi konflik jadwal berdasarkan 3 dimensi:
    1. Bentrok ruangan (ROOM_CONFLICT / room_conflict).
    2. Bentrok dosen (LECTURER_CONFLICT / lecturer_conflict).
    3. Bentrok waktu (TIME_OVERLAP / time_overlap).

    Menggunakan interval setengah terbuka [start, end).
    """
    conflicts = []

    if new_jadwal is None:
        return conflicts

    if new_jadwal.jam_mulai is None or new_jadwal.jam_selesai is None:
        return conflicts

    if new_jadwal.jam_mulai >= new_jadwal.jam_selesai:
        return conflicts

    for existing in existing_schedules or []:
        if existing is None:
            continue

        if getattr(existing, "status", "AKTIF") not in (None, "AKTIF"):
            continue

        if (
            getattr(existing, "tahun_akademik", None)
            != getattr(new_jadwal, "tahun_akademik", None)
        ):
            continue

        if (
            getattr(existing, "semester_akademik", None)
            != getattr(new_jadwal, "semester_akademik", None)
        ):
            continue

        if (
            getattr(existing, "id", None) is not None
            and existing.id == getattr(new_jadwal, "id", None)
        ):
            continue

        if existing.hari != new_jadwal.hari:
            continue

        if existing.jam_mulai is None or existing.jam_selesai is None:
            continue

        time_overlap = (
            existing.jam_mulai < new_jadwal.jam_selesai
            and new_jadwal.jam_mulai < existing.jam_selesai
        )

        if not time_overlap:
            continue

        room_matched = existing.ruangan_id == new_jadwal.ruangan_id
        lecturer_matched = existing.dosen_id == new_jadwal.dosen_id

        if room_matched:
            conflicts.append({
                "type": "ROOM_CONFLICT",
                "conflict_type": "room_conflict",
                "description": (
                    f"Ruangan bentrok dengan jadwal ID {existing.id}"
                ),
                "schedule_id": existing.id,
                "affected_schedules": [
                    existing.id,
                    getattr(new_jadwal, "id", None),
                ],
            })

        if lecturer_matched:
            conflicts.append({
                "type": "LECTURER_CONFLICT",
                "conflict_type": "lecturer_conflict",
                "description": (
                    f"Dosen bentrok dengan jadwal ID {existing.id}"
                ),
                "schedule_id": existing.id,
                "affected_schedules": [
                    existing.id,
                    getattr(new_jadwal, "id", None),
                ],
            })

        new_mk_id = getattr(new_jadwal, "matakuliah_id", None)
        ex_mk_id = getattr(existing, "matakuliah_id", None)
        if (
            not room_matched
            and not lecturer_matched
            and new_mk_id is not None
            and ex_mk_id is not None
            and new_mk_id == ex_mk_id
        ):
            conflicts.append({
                "type": "TIME_OVERLAP",
                "conflict_type": "time_overlap",
                "description": (
                    f"Waktu kuliah bentrok untuk mata kuliah yang sama dengan jadwal ID {existing.id}"
                ),
                "schedule_id": existing.id,
                "affected_schedules": [
                    existing.id,
                    getattr(new_jadwal, "id", None),
                ],
            })

    return conflicts


def detect_all_schedule_conflicts(schedules: List[JadwalKuliah]) -> List[dict]:
    """
    Memeriksa seluruh pasangan jadwal dalam list dan mengembalikan detail konflik
    ('room_conflict', 'lecturer_conflict', 'time_overlap') beserta affected_schedules.
    """
    results: List[dict] = []
    items = [s for s in (schedules or []) if s is not None]
    n = len(items)
    for i in range(n):
        s1 = items[i]
        for j in range(i + 1, n):
            s2 = items[j]
            found = detect_schedule_conflict(s2, [s1])
            for c in found:
                results.append({
                    "type": c["conflict_type"],
                    "code": c["type"],
                    "description": c["description"],
                    "affected_schedules": [
                        getattr(s1, "id", None),
                        getattr(s2, "id", None),
                    ],
                })
    return results
