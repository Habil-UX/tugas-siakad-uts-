from datetime import datetime, timedelta
import io
from typing import List, Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy.orm import Session

from app.models import (
    AttendanceRecord,
    AttendanceSession,
    CalonMahasiswa,
    JadwalKuliah,
    KRS,
    KRSDetail,
    Matakuliah,
    StatusPendaftaran,
)
from app.services.attendance_service import to_jakarta_naive


class AttendanceReportService:

    WARNING_THRESHOLD = 75.0

    def __init__(self, db: Session):
        self.db = db

    def is_session_concluded(
        self,
        session: AttendanceSession,
        schedule: JadwalKuliah,
        ref_dt: datetime,
    ) -> bool:
        if session.session_status == "CANCELLED":
            return False
        if session.session_status == "CLOSED":
            return True
        window_end = datetime.combine(
            session.session_date,
            schedule.jam_mulai,
        ) + timedelta(minutes=30)
        return ref_dt >= window_end

    def get_concluded_sessions(
        self,
        schedule_id: int,
        reference_time: Optional[datetime] = None,
    ) -> List[AttendanceSession]:
        ref_dt = to_jakarta_naive(reference_time)
        schedule = (
            self.db.query(JadwalKuliah)
            .filter(JadwalKuliah.id == schedule_id)
            .first()
        )
        if not schedule:
            return []
        sessions = (
            self.db.query(AttendanceSession)
            .filter(AttendanceSession.schedule_id == schedule_id)
            .order_by(AttendanceSession.session_date.asc(), AttendanceSession.id.asc())
            .all()
        )
        return [
            s
            for s in sessions
            if self.is_session_concluded(s, schedule, ref_dt)
        ]

    def get_enrolled_students(self, matakuliah_id: int) -> List[CalonMahasiswa]:
        rows = (
            self.db.query(CalonMahasiswa)
            .join(KRS, KRS.nim == CalonMahasiswa.nim)
            .join(KRSDetail, KRSDetail.krs_id == KRS.id)
            .filter(
                CalonMahasiswa.status == StatusPendaftaran.approved,
                KRS.status == "APPROVED",
                KRSDetail.matakuliah_id == matakuliah_id,
            )
            .order_by(CalonMahasiswa.nim.asc())
            .all()
        )
        seen = set()
        unique_students = []
        for s in rows:
            if s.nim not in seen:
                seen.add(s.nim)
                unique_students.append(s)
        return unique_students

    def get_attendance_report(
        self,
        schedule_id: Optional[int] = None,
        matakuliah_id: Optional[int] = None,
        nim: Optional[str] = None,
        reference_time: Optional[datetime] = None,
    ) -> dict:
        ref_dt = to_jakarta_naive(reference_time)

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

        report_rows = []
        warnings = []

        for sched in schedules:
            mk = (
                self.db.query(Matakuliah)
                .filter(Matakuliah.id == sched.matakuliah_id)
                .first()
            )
            concluded_sessions = self.get_concluded_sessions(
                schedule_id=sched.id,
                reference_time=ref_dt,
            )
            concluded_ids = {s.id for s in concluded_sessions}
            total_sesi = len(concluded_sessions)

            enrolled_students = self.get_enrolled_students(sched.matakuliah_id)
            if nim:
                enrolled_students = [
                    st for st in enrolled_students if st.nim == nim.strip()
                ]

            for st in enrolled_students:
                records = []
                if concluded_ids:
                    records = (
                        self.db.query(AttendanceRecord)
                        .filter(
                            AttendanceRecord.session_id.in_(concluded_ids),
                            AttendanceRecord.student_id == st.id,
                        )
                        .all()
                    )

                jumlah_hadir = sum(
                    1
                    for r in records
                    if (r.attendance_status or "").upper() == "HADIR"
                )
                jumlah_terlambat = sum(
                    1
                    for r in records
                    if (r.attendance_status or "").upper() == "TERLAMBAT"
                )
                total_masuk = jumlah_hadir + jumlah_terlambat
                jumlah_tidak_hadir = max(0, total_sesi - total_masuk)

                if total_sesi > 0:
                    persentase = round((total_masuk / total_sesi) * 100.0, 2)
                    is_warning = persentase < self.WARNING_THRESHOLD
                else:
                    persentase = 0.0
                    is_warning = False

                status_warning = (
                    "WARNING (<75%)"
                    if is_warning
                    else ("BELUM ADA SESI" if total_sesi == 0 else "AMAN (>=75%)")
                )

                row_item = {
                    "nim": st.nim,
                    "student_id": st.id,
                    "nama_mahasiswa": st.nama_lengkap,
                    "schedule_id": sched.id,
                    "matakuliah_id": sched.matakuliah_id,
                    "kode_mk": mk.kode_mk if mk else "-",
                    "nama_mk": mk.nama_mk if mk else "-",
                    "hari": sched.hari,
                    "jam_mulai": str(sched.jam_mulai),
                    "total_sesi_berlangsung": total_sesi,
                    "jumlah_hadir": jumlah_hadir,
                    "jumlah_terlambat": jumlah_terlambat,
                    "jumlah_tidak_hadir": jumlah_tidak_hadir,
                    "persentase_kehadiran": persentase,
                    "is_warning": is_warning,
                    "status_warning": status_warning,
                }
                report_rows.append(row_item)
                if is_warning:
                    warnings.append(row_item)

        return {
            "generated_at": ref_dt.isoformat(),
            "threshold_warning_percent": self.WARNING_THRESHOLD,
            "total_rows": len(report_rows),
            "total_warning_count": len(warnings),
            "records": report_rows,
            "warnings": warnings,
        }

    def export_excel_bytes(
        self,
        schedule_id: Optional[int] = None,
        matakuliah_id: Optional[int] = None,
        nim: Optional[str] = None,
        reference_time: Optional[datetime] = None,
    ) -> bytes:
        report = self.get_attendance_report(
            schedule_id=schedule_id,
            matakuliah_id=matakuliah_id,
            nim=nim,
            reference_time=reference_time,
        )

        wb = Workbook()
        ws = wb.active
        ws.title = "Laporan Presensi"

        headers = [
            "NIM",
            "Nama Mahasiswa",
            "Kode MK",
            "Mata Kuliah",
            "Total Sesi",
            "Jumlah Hadir",
            "Jumlah Terlambat",
            "Jumlah Tidak Hadir",
            "Persentase Kehadiran (%)",
            "Status Warning",
        ]
        ws.append(headers)

        header_fill = PatternFill(
            start_color="263B5E",
            end_color="263B5E",
            fill_type="solid",
        )
        header_font = Font(color="FFFFFF", bold=True)
        warn_fill = PatternFill(
            start_color="FEE2E2",
            end_color="FEE2E2",
            fill_type="solid",
        )
        warn_font = Font(color="991B1B", bold=True)

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for row_idx, item in enumerate(report["records"], start=2):
            ws.append(
                [
                    item["nim"],
                    item["nama_mahasiswa"],
                    item["kode_mk"],
                    item["nama_mk"],
                    item["total_sesi_berlangsung"],
                    item["jumlah_hadir"],
                    item["jumlah_terlambat"],
                    item["jumlah_tidak_hadir"],
                    item["persentase_kehadiran"],
                    item["status_warning"],
                ]
            )
            if item["is_warning"]:
                for c_idx in range(1, len(headers) + 1):
                    c = ws.cell(row=row_idx, column=c_idx)
                    c.fill = warn_fill
                    if c_idx == len(headers):
                        c.font = warn_font

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(14, min(40, max_len + 4))

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
