from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import (
    AttendanceRecord,
    JadwalKuliah,
    Matakuliah,
)
from app.services.attendance_report_service import AttendanceReportService
from app.services.attendance_service import DAY_NAME_ID, to_jakarta_naive

ID_TO_EN_DAY = {
    "senin": "Monday",
    "selasa": "Tuesday",
    "rabu": "Wednesday",
    "kamis": "Thursday",
    "jumat": "Friday",
    "sabtu": "Saturday",
    "minggu": "Sunday",
}
EN_TO_ID_DAY = {v.lower(): k.capitalize() for k, v in ID_TO_EN_DAY.items()}


class AIAttendanceAnalyzer:
    """
    Deterministic Statistical & Rule-Based Attendance Pattern Analyzer.
    Menganalisis data presensi aktual dari database maupun JSON array `attendance_records`
    tanpa ketergantungan API LLM eksternal berbayar.
    """

    WARNING_THRESHOLD = 75.0
    PATTERN_ABSENCE_THRESHOLD = 35.0
    HIGH_CLASS_ABSENCE_THRESHOLD = 30.0

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def analyze(
        self,
        attendance_records: Optional[List[dict]] = None,
        schedule_id: Optional[int] = None,
        matakuliah_id: Optional[int] = None,
        min_sessions: int = 2,
        reference_time: Optional[datetime] = None,
    ) -> dict:
        if attendance_records is not None:
            return self.analyze_records(
                attendance_records=attendance_records,
                min_sessions=min_sessions,
            )
        if self.db is None:
            return {
                "methodology": "Deterministic Statistical & Rule-Based Attendance Analyzer",
                "summary": {
                    "total_students_analyzed": 0,
                    "total_sessions_analyzed": 0,
                    "at_risk_students_count": 0,
                    "early_warning": "Tidak ada sampel data presensi yang tersedia.",
                },
                "student_metrics": [],
                "insights": [],
                "actions": [],
            }
        return self.analyze_from_db(
            schedule_id=schedule_id,
            matakuliah_id=matakuliah_id,
            min_sessions=min_sessions,
            reference_time=reference_time,
        )

    def analyze_from_db(
        self,
        schedule_id: Optional[int] = None,
        matakuliah_id: Optional[int] = None,
        min_sessions: int = 2,
        reference_time: Optional[datetime] = None,
    ) -> dict:
        ref_dt = to_jakarta_naive(reference_time)
        report_svc = AttendanceReportService(self.db)

        sched_query = self.db.query(JadwalKuliah).filter(
            JadwalKuliah.status == "AKTIF"
        )
        if schedule_id is not None:
            sched_query = sched_query.filter(JadwalKuliah.id == schedule_id)
        if matakuliah_id is not None:
            sched_query = sched_query.filter(
                JadwalKuliah.matakuliah_id == matakuliah_id
            )
        schedules = sched_query.order_by(JadwalKuliah.id.asc()).all()

        synthesized_records: List[dict] = []
        for sched in schedules:
            mk = (
                self.db.query(Matakuliah)
                .filter(Matakuliah.id == sched.matakuliah_id)
                .first()
            )
            course_name = (
                f"{mk.kode_mk} - {mk.nama_mk}"
                if mk
                else f"Jadwal #{sched.id}"
            )
            concluded_sessions = report_svc.get_concluded_sessions(
                schedule_id=sched.id,
                reference_time=ref_dt,
            )
            enrolled_students = report_svc.get_enrolled_students(
                sched.matakuliah_id
            )
            jam_str = (
                sched.jam_mulai.strftime("%H:%M")
                if hasattr(sched.jam_mulai, "strftime")
                else str(sched.jam_mulai)[:5]
            )

            for sess in concluded_sessions:
                actual_day_id = DAY_NAME_ID.get(
                    sess.session_date.weekday(), sched.hari or "Senin"
                )
                recs = (
                    self.db.query(AttendanceRecord)
                    .filter(AttendanceRecord.session_id == sess.id)
                    .all()
                )
                rec_by_student_id = {r.student_id: r for r in recs}

                for st in enrolled_students:
                    r = rec_by_student_id.get(st.id)
                    status_val = (
                        r.attendance_status.upper() if r else "TIDAK_HADIR"
                    )
                    synthesized_records.append(
                        {
                            "session_id": sess.id,
                            "session_date": str(sess.session_date),
                            "schedule_id": sched.id,
                            "course": course_name,
                            "kode_mk": mk.kode_mk if mk else "-",
                            "nama_mk": mk.nama_mk if mk else "-",
                            "nim": st.nim,
                            "student": st.nama_lengkap,
                            "day": actual_day_id,
                            "time": jam_str,
                            "status": status_val,
                        }
                    )

        return self.analyze_records(
            attendance_records=synthesized_records,
            min_sessions=min_sessions,
        )

    def analyze_records(
        self,
        attendance_records: List[dict],
        min_sessions: int = 2,
    ) -> dict:
        insights: List[dict] = []
        actions: List[dict] = []

        if not attendance_records:
            return {
                "methodology": (
                    "Deterministic Statistical & Rule-Based Attendance Pattern "
                    "Analyzer (Local Engine, Tanpa API LLM Eksternal)"
                ),
                "calculation_basis": (
                    "Persentase Kehadiran = (Hadir + Terlambat) / Total Sesi Berlangsung * 100%"
                ),
                "min_sample_sessions": min_sessions,
                "summary": {
                    "total_records_analyzed": 0,
                    "total_students_analyzed": 0,
                    "at_risk_students_count": 0,
                    "early_warning": "Belum ada sesi presensi yang selesai untuk dianalisis.",
                },
                "student_metrics": [],
                "insights": [],
                "actions": [],
            }

        # Group by student (nim or student name)
        student_entries: Dict[str, List[dict]] = defaultdict(list)
        student_names: Dict[str, str] = {}
        # Group by (student, day)
        student_day_entries: Dict[tuple, List[dict]] = defaultdict(list)
        # Group by (course, time)
        course_time_entries: Dict[tuple, List[dict]] = defaultdict(list)
        # Group by course
        course_entries: Dict[str, List[dict]] = defaultdict(list)

        for item in attendance_records:
            nim = str(item.get("nim") or item.get("student") or "UNKNOWN")
            name = str(item.get("student") or item.get("nama_mahasiswa") or nim)
            course = str(
                item.get("course")
                or item.get("nama_mk")
                or item.get("kode_mk")
                or "Mata Kuliah"
            )
            raw_day = str(item.get("day") or item.get("hari") or "Senin").strip()
            day_lower = raw_day.lower()
            if day_lower in ID_TO_EN_DAY:
                day_id = raw_day.capitalize()
                day_en = ID_TO_EN_DAY[day_lower]
            elif day_lower in EN_TO_ID_DAY:
                day_id = EN_TO_ID_DAY[day_lower]
                day_en = raw_day.capitalize()
            else:
                day_id = raw_day
                day_en = raw_day

            time_slot = str(
                item.get("time") or item.get("jam_mulai") or "08:00"
            )[:5]
            raw_status = str(
                item.get("status") or item.get("attendance_status") or "TIDAK_HADIR"
            ).upper()
            is_present = raw_status in ("HADIR", "TERLAMBAT", "PRESENT", "LATE")

            norm_row = {
                "nim": nim,
                "student": name,
                "course": course,
                "day_id": day_id,
                "day_en": day_en,
                "time_slot": time_slot,
                "status": raw_status,
                "is_present": is_present,
            }
            student_names[nim] = name
            student_entries[nim].append(norm_row)
            student_day_entries[(nim, day_id, day_en)].append(norm_row)
            course_time_entries[(course, time_slot)].append(norm_row)
            course_entries[course].append(norm_row)

        student_metrics: List[dict] = []
        at_risk_students: List[dict] = []

        # 1 & 2. Hitung persentase kehadiran setiap mahasiswa & identifikasi < 75%
        for nim, rows in sorted(student_entries.items()):
            total_sesi = len(rows)
            hadir_cnt = sum(1 for r in rows if r["status"] in ("HADIR", "PRESENT"))
            terlambat_cnt = sum(1 for r in rows if r["status"] in ("TERLAMBAT", "LATE"))
            absen_cnt = total_sesi - (hadir_cnt + terlambat_cnt)
            attendance_rate = round(((hadir_cnt + terlambat_cnt) / total_sesi) * 100.0, 2)
            absence_rate = round((absen_cnt / total_sesi) * 100.0, 2)
            is_at_risk = total_sesi >= min_sessions and attendance_rate < self.WARNING_THRESHOLD

            metric = {
                "nim": nim,
                "student": student_names[nim],
                "sample_sessions": total_sesi,
                "hadir": hadir_cnt,
                "terlambat": terlambat_cnt,
                "tidak_hadir": absen_cnt,
                "attendance_rate": attendance_rate,
                "absence_rate": absence_rate,
                "is_below_75_warning": is_at_risk,
            }
            student_metrics.append(metric)
            if is_at_risk:
                at_risk_students.append(metric)

        # 3. Deteksi pola absensi berdasarkan hari per mahasiswa
        for (nim, day_id, day_en), rows in sorted(student_day_entries.items()):
            sample_cnt = len(rows)
            if sample_cnt < min_sessions:
                continue
            absent_cnt = sum(1 for r in rows if not r["is_present"])
            day_abs_rate = round((absent_cnt / sample_cnt) * 100.0, 2)
            if absent_cnt > 0 and day_abs_rate >= self.PATTERN_ABSENCE_THRESHOLD:
                st_name = student_names[nim]
                insights.append(
                    {
                        "type": "attendance_pattern",
                        "student": st_name,
                        "nim": nim,
                        "pattern": f"Sering tidak hadir pada hari {day_id}",
                        "evidence": {
                            "day": day_en,
                            "day_id": day_id,
                            "absent_count": absent_cnt,
                            "sample_sessions": sample_cnt,
                            "absence_rate": day_abs_rate,
                        },
                    }
                )
                actions.append(
                    {
                        "priority": "high" if day_abs_rate >= 50.0 else "medium",
                        "target": st_name,
                        "recommendation": (
                            f"Mahasiswa {st_name} ({nim}) sering tidak hadir pada hari {day_id} "
                            f"({day_abs_rate}% dari {sample_cnt} sesi) -> hubungi mahasiswa untuk konseling akademik"
                        ),
                    }
                )

        # 4. Deteksi pola absensi berdasarkan jam kuliah (time slot)
        for (course, time_slot), rows in sorted(course_time_entries.items()):
            sample_cnt = len(rows)
            if sample_cnt < min_sessions:
                continue
            absent_cnt = sum(1 for r in rows if not r["is_present"])
            slot_abs_rate = round((absent_cnt / sample_cnt) * 100.0, 2)
            if absent_cnt > 0 and slot_abs_rate >= self.HIGH_CLASS_ABSENCE_THRESHOLD:
                insights.append(
                    {
                        "type": "time_slot_pattern",
                        "course": course,
                        "pattern": (
                            f"Kelas {course} di jam {time_slot} memiliki tingkat "
                            f"ketidakhadiran tinggi ({slot_abs_rate}%)"
                        ),
                        "evidence": {
                            "course": course,
                            "time_slot": time_slot,
                            "absent_count": absent_cnt,
                            "sample_records": sample_cnt,
                            "absence_rate": slot_abs_rate,
                        },
                    }
                )
                actions.append(
                    {
                        "priority": "medium" if slot_abs_rate < 50.0 else "high",
                        "target": course,
                        "recommendation": (
                            f"Kelas {course} di jam {time_slot} memiliki absen rate {slot_abs_rate}% "
                            f"({absent_cnt}/{sample_cnt} presensi) -> pertimbangkan evaluasi atau reschedule jadwal"
                        ),
                    }
                )

        # 5. Identifikasi kelas dengan tingkat ketidakhadiran tinggi secara keseluruhan
        for course, rows in sorted(course_entries.items()):
            sample_cnt = len(rows)
            if sample_cnt < min_sessions:
                continue
            absent_cnt = sum(1 for r in rows if not r["is_present"])
            c_abs_rate = round((absent_cnt / sample_cnt) * 100.0, 2)
            if absent_cnt > 0 and c_abs_rate >= self.HIGH_CLASS_ABSENCE_THRESHOLD:
                insights.append(
                    {
                        "type": "high_absence_class",
                        "course": course,
                        "pattern": f"Tingkat ketidakhadiran kelas {course} mencapai {c_abs_rate}%",
                        "evidence": {
                            "course": course,
                            "absent_count": absent_cnt,
                            "sample_records": sample_cnt,
                            "absence_rate": c_abs_rate,
                        },
                    }
                )

        # 6. Early warning mahasiswa berisiko (<75%)
        if at_risk_students:
            count_risk = len(at_risk_students)
            early_msg = (
                f"{count_risk} mahasiswa berisiko tidak memenuhi syarat presensi (<75%)"
            )
            insights.append(
                {
                    "type": "early_warning",
                    "pattern": early_msg,
                    "evidence": {
                        "at_risk_count": count_risk,
                        "threshold_percent": self.WARNING_THRESHOLD,
                        "students": [
                            {
                                "nim": s["nim"],
                                "student": s["student"],
                                "attendance_rate": s["attendance_rate"],
                                "sample_sessions": s["sample_sessions"],
                            }
                            for s in at_risk_students
                        ],
                    },
                }
            )
            for s in at_risk_students:
                rec_text = (
                    f"Hubungi mahasiswa {s['student']} ({s['nim']}) untuk konseling akademik "
                    f"(kehadiran saat ini {s['attendance_rate']}% dari {s['sample_sessions']} sesi, di bawah batas 75%)"
                )
                if not any(a.get("target") == s["student"] for a in actions):
                    actions.append(
                        {
                            "priority": "high",
                            "target": s["student"],
                            "recommendation": rec_text,
                        }
                    )
        else:
            early_msg = "Seluruh mahasiswa yang dianalisis memenuhi batas minimal kehadiran (>=75%)."

        return {
            "methodology": (
                "Deterministic Statistical & Rule-Based Attendance Pattern "
                "Analyzer (Local Engine, Tanpa API LLM Eksternal)"
            ),
            "calculation_basis": (
                "Persentase Kehadiran = (Hadir + Terlambat) / Total Sesi Berlangsung * 100%"
            ),
            "min_sample_sessions": min_sessions,
            "summary": {
                "total_records_analyzed": len(attendance_records),
                "total_students_analyzed": len(student_metrics),
                "at_risk_students_count": len(at_risk_students),
                "early_warning": early_msg,
            },
            "student_metrics": student_metrics,
            "insights": insights,
            "actions": actions,
        }
