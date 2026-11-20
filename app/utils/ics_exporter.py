from datetime import date, datetime, timedelta
from typing import Iterable
from sqlalchemy.orm import Session
from app.models import Dosen, JadwalKuliah, KRS, KRSDetail, Matakuliah, Ruangan

HARI_OFFSET = {
    "senin": 0,
    "selasa": 1,
    "rabu": 2,
    "kamis": 3,
    "jumat": 4,
    "sabtu": 5,
    "minggu": 6,
}


def generate_ics_from_schedules(db: Session, schedules: Iterable[JadwalKuliah]) -> str:
    """
    Mengekspor daftar JadwalKuliah ke format iCalendar (.ics) RFC 5545.
    """
    base_monday = date(2026, 11, 16)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SIAKAD Universitas//Jadwal Kuliah//ID",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for sched in schedules:
        mk = db.query(Matakuliah).filter(Matakuliah.id == sched.matakuliah_id).first()
        room = db.query(Ruangan).filter(Ruangan.id == sched.ruangan_id).first()
        dosen = db.query(Dosen).filter(Dosen.id == sched.dosen_id).first()

        offset = HARI_OFFSET.get(str(sched.hari).strip().lower(), 0)
        event_date = base_monday + timedelta(days=offset)
        dt_start = datetime.combine(event_date, sched.jam_mulai)
        dt_end = datetime.combine(event_date, sched.jam_selesai)

        summary = f"{mk.kode_mk} - {mk.nama_mk}" if mk else f"Jadwal #{sched.id}"
        location = room.kode_ruangan if room else f"Ruangan #{sched.ruangan_id}"
        description = f"Dosen: {dosen.nama}" if dosen else f"Dosen ID: {sched.dosen_id}"

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:jadwal-{sched.id}@siakad.ac.id",
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{dt_start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{dt_end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{summary}",
            f"LOCATION:{location}",
            f"DESCRIPTION:{description}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def export_student_ics(db: Session, nim: str) -> str:
    schedules = (
        db.query(JadwalKuliah)
        .join(KRSDetail, KRSDetail.matakuliah_id == JadwalKuliah.matakuliah_id)
        .join(KRS, KRS.id == KRSDetail.krs_id)
        .filter(KRS.nim == nim)
        .all()
    )
    return generate_ics_from_schedules(db, schedules)
