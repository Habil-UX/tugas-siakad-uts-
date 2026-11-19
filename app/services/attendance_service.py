import base64
from datetime import date, datetime, time, timedelta, timezone
import io
import os
from typing import Optional, Tuple
import uuid
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
import jwt
import qrcode
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    AttendanceQRToken,
    AttendanceRecord,
    AttendanceScanAttempt,
    AttendanceSession,
    CalonMahasiswa,
    Dosen,
    JadwalKuliah,
    KRS,
    KRSDetail,
    Matakuliah,
    StatusPendaftaran,
)
from app.utils.security import SECRET_KEY

JAKARTA_TZ = ZoneInfo("Asia/Jakarta")

DAY_NAME_ID = {
    0: "Senin",
    1: "Selasa",
    2: "Rabu",
    3: "Kamis",
    4: "Jumat",
    5: "Sabtu",
    6: "Minggu",
}

RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 60


def get_jwt_secret() -> str:
    return os.getenv("SECRET_KEY", SECRET_KEY)


def to_jakarta_naive(dt: Optional[datetime] = None) -> datetime:
    if dt is None:
        return datetime.now(JAKARTA_TZ).replace(tzinfo=None)
    if dt.tzinfo is not None:
        return dt.astimezone(JAKARTA_TZ).replace(tzinfo=None)
    return dt


def generate_attendance_qr(
    schedule_id: int,
    valid_minutes: int = 15,
    db: Optional[Session] = None,
    session_date: Optional[date] = None,
    current_time: Optional[datetime] = None,
    current_user: Optional[dict] = None,
    phase: Optional[str] = None,
    revoke_previous: bool = True,
) -> Tuple[object, str]:
    """
    Membuat QR Code (PIL/PyPNG Image) dan token JWT (HS256) untuk presensi kuliah.
    Mengembalikan tuple (qr_image, token) sesuai spesifikasi PDF Minggu 12.
    Apabila session `db` diberikan, otomatis memvalidasi jadwal & kewenangan dosen
    serta menyimpan AttendanceSession dan AttendanceQRToken ke database.
    """
    if valid_minutes <= 0 or valid_minutes > 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Masa berlaku QR Code presensi maksimal 15 menit (1-15 menit)",
        )

    if db is not None:
        svc = AttendanceService(db)
        result = svc.generate_qr(
            schedule_id=schedule_id,
            valid_minutes=valid_minutes,
            session_date=session_date,
            current_time=current_time,
            current_user=current_user,
            phase=phase,
            revoke_previous=revoke_previous,
        )
        return result["qr_image"], result["token"]

    gen_dt = to_jakarta_naive(current_time)
    exp_dt = gen_dt + timedelta(minutes=valid_minutes)
    jti = uuid.uuid4().hex
    now_utc = datetime.now(timezone.utc)
    payload = {
        "schedule_id": int(schedule_id),
        "session_id": 0,
        "generated_at": gen_dt.isoformat(),
        "expires_at": exp_dt.isoformat(),
        "iat": int(now_utc.timestamp()),
        "exp": int((now_utc + timedelta(minutes=valid_minutes)).timestamp()),
        "jti": jti,
        "phase": phase or "NORMAL",
    }
    token = jwt.encode(payload, get_jwt_secret(), algorithm="HS256")
    qr_img = _build_qr_image(token)
    return qr_img, token


def _build_qr_image(token: str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )
    qr.add_data(token)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white")


def qr_image_to_png_bytes(qr_img) -> bytes:
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    return buf.getvalue()


class AttendanceService:

    def __init__(self, db: Session):
        self.db = db

    def _verify_lecturer_ownership(
        self,
        schedule: JadwalKuliah,
        current_user: Optional[dict] = None,
        dosen_id: Optional[int] = None,
    ) -> None:
        if current_user is not None:
            role = str(current_user.get("role", "")).lower()
            if role not in ("dosen", "admin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Hanya dosen pengampu atau admin yang dapat membuat QR presensi",
                )
            if role == "dosen":
                user_dosen_id = current_user.get("dosen_id")
                user_nidn = current_user.get("nidn")
                if user_dosen_id is not None and int(user_dosen_id) != schedule.dosen_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Dosen tidak berwenang membuat QR untuk jadwal dosen lain",
                    )
                if user_nidn:
                    dosen = (
                        self.db.query(Dosen)
                        .filter(Dosen.nidn == str(user_nidn))
                        .first()
                    )
                    if dosen and dosen.id != schedule.dosen_id:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Dosen tidak berwenang membuat QR untuk jadwal dosen lain",
                        )

        if dosen_id is not None and int(dosen_id) != schedule.dosen_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dosen tidak berwenang membuat QR untuk jadwal dosen lain",
            )

    def generate_qr(
        self,
        schedule_id: int,
        valid_minutes: int = 15,
        session_date: Optional[date] = None,
        current_time: Optional[datetime] = None,
        current_user: Optional[dict] = None,
        dosen_id: Optional[int] = None,
        phase: Optional[str] = None,
        revoke_previous: bool = True,
    ) -> dict:
        if valid_minutes <= 0 or valid_minutes > 15:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Masa berlaku QR Code presensi maksimal 15 menit (1-15 menit)",
            )

        schedule = (
            self.db.query(JadwalKuliah)
            .filter(JadwalKuliah.id == schedule_id)
            .first()
        )
        if not schedule or schedule.status != "AKTIF":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jadwal kuliah aktif tidak ditemukan",
            )

        self._verify_lecturer_ownership(
            schedule=schedule,
            current_user=current_user,
            dosen_id=dosen_id,
        )

        gen_dt = to_jakarta_naive(current_time)
        target_date = session_date or gen_dt.date()

        session = (
            self.db.query(AttendanceSession)
            .filter(
                AttendanceSession.schedule_id == schedule.id,
                AttendanceSession.session_date == target_date,
            )
            .first()
        )
        if not session:
            session = AttendanceSession(
                schedule_id=schedule.id,
                session_date=target_date,
                session_status="OPEN",
                created_at=gen_dt,
            )
            self.db.add(session)
            self.db.flush()
        elif session.session_status != "OPEN":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sesi presensi sudah berstatus {session.session_status}",
            )

        class_start_dt = datetime.combine(target_date, schedule.jam_mulai)
        session_max_end_dt = class_start_dt + timedelta(minutes=30)

        elapsed_from_start = (gen_dt - class_start_dt).total_seconds() / 60.0
        if phase is None:
            if 15.0 <= elapsed_from_start <= 30.0:
                resolved_phase = "LATE"
            else:
                resolved_phase = "NORMAL"
        else:
            resolved_phase = phase.upper()

        raw_exp_dt = gen_dt + timedelta(minutes=valid_minutes)
        if class_start_dt <= gen_dt <= session_max_end_dt:
            if raw_exp_dt > session_max_end_dt:
                exp_dt = session_max_end_dt
            else:
                exp_dt = raw_exp_dt
        else:
            exp_dt = raw_exp_dt

        effective_seconds = max(1, int((exp_dt - gen_dt).total_seconds()))

        if revoke_previous:
            active_tokens = (
                self.db.query(AttendanceQRToken)
                .filter(
                    AttendanceQRToken.session_id == session.id,
                    AttendanceQRToken.revoked_at.is_(None),
                )
                .all()
            )
            for old_tok in active_tokens:
                old_tok.revoked_at = gen_dt

        jti = uuid.uuid4().hex
        now_utc = datetime.now(timezone.utc)
        jwt_exp_utc = now_utc + timedelta(seconds=effective_seconds)

        payload = {
            "schedule_id": schedule.id,
            "session_id": session.id,
            "generated_at": gen_dt.isoformat(),
            "expires_at": exp_dt.isoformat(),
            "iat": int(now_utc.timestamp()),
            "exp": int(jwt_exp_utc.timestamp()),
            "jti": jti,
            "phase": resolved_phase,
        }
        token = jwt.encode(payload, get_jwt_secret(), algorithm="HS256")

        qr_token_row = AttendanceQRToken(
            session_id=session.id,
            jti=jti,
            phase=resolved_phase,
            generated_at=gen_dt,
            expires_at=exp_dt,
            revoked_at=None,
        )
        self.db.add(qr_token_row)
        self.db.commit()
        self.db.refresh(qr_token_row)

        qr_img = _build_qr_image(token)
        png_bytes = qr_image_to_png_bytes(qr_img)

        return {
            "schedule_id": schedule.id,
            "session_id": session.id,
            "session_date": str(target_date),
            "jti": jti,
            "phase": resolved_phase,
            "generated_at": gen_dt.isoformat(),
            "expires_at": exp_dt.isoformat(),
            "expires_in_seconds": effective_seconds,
            "token": token,
            "qr_image": qr_img,
            "png_bytes": png_bytes,
            "qr_base64": "data:image/png;base64,"
            + base64.b64encode(png_bytes).decode("ascii"),
        }

    def _check_and_record_rate_limit(
        self,
        actor_key: str,
        schedule_id: Optional[int],
        attempt_time: datetime,
    ) -> None:
        window_start = attempt_time - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
        recent_count = (
            self.db.query(AttendanceScanAttempt)
            .filter(
                AttendanceScanAttempt.actor_key == actor_key,
                AttendanceScanAttempt.attempted_at >= window_start,
                AttendanceScanAttempt.attempted_at <= attempt_time + timedelta(seconds=5),
            )
            .count()
        )
        if recent_count >= RATE_LIMIT_MAX_ATTEMPTS:
            self._log_attempt(
                actor_key=actor_key,
                schedule_id=schedule_id,
                attempted_at=attempt_time,
                outcome="RATE_LIMITED",
                detail="Melebihi batas maksimum percobaan scan per menit",
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit terlampaui: maksimal {RATE_LIMIT_MAX_ATTEMPTS} "
                    f"percobaan scan dalam {RATE_LIMIT_WINDOW_SECONDS} detik"
                ),
            )

    def _log_attempt(
        self,
        actor_key: str,
        schedule_id: Optional[int],
        attempted_at: datetime,
        outcome: str,
        detail: Optional[str] = None,
    ) -> None:
        attempt = AttendanceScanAttempt(
            actor_key=actor_key,
            schedule_id=schedule_id,
            attempted_at=attempted_at,
            outcome=outcome,
            detail=detail,
        )
        self.db.add(attempt)
        self.db.commit()

    def scan_attendance(
        self,
        token: str,
        nim: str,
        current_user: Optional[dict] = None,
        scan_time: Optional[datetime] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> dict:
        clean_nim = (nim or "").strip()
        if not clean_nim:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NIM mahasiswa wajib diisi",
            )

        scan_dt = to_jakarta_naive(scan_time)

        # 1. Verifikasi identitas pengguna (cegah pemalsuan NIM oleh mahasiswa lain)
        if current_user is not None:
            role = str(current_user.get("role", "")).lower()
            if role not in ("mahasiswa", "admin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Hanya mahasiswa yang dapat melakukan scan presensi",
                )
            token_nim = current_user.get("nim")
            if role == "mahasiswa" and token_nim and str(token_nim).strip() != clean_nim:
                self._log_attempt(
                    actor_key=str(token_nim),
                    schedule_id=None,
                    attempted_at=scan_dt,
                    outcome="REJECTED_NIM_SPOOF",
                    detail=f"Mencoba scan menggunakan NIM {clean_nim}",
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Mahasiswa tidak diizinkan memalsukan atau menggunakan NIM mahasiswa lain",
                )

        # 2. Persistent Database-Backed Rate Limiting
        self._check_and_record_rate_limit(
            actor_key=clean_nim,
            schedule_id=None,
            attempt_time=scan_dt,
        )

        # 3. Decode & verifikasi JWT (HS256 signature & exp)
        try:
            # Jika scan_time disimulasikan, verifikasi signature secara ketat lalu periksa exp terhadap scan_dt
            verify_jwt_exp = scan_time is None
            payload = jwt.decode(
                token,
                get_jwt_secret(),
                algorithms=["HS256"],
                options={"verify_exp": verify_jwt_exp},
            )
        except jwt.ExpiredSignatureError:
            self._log_attempt(
                actor_key=clean_nim,
                schedule_id=None,
                attempted_at=scan_dt,
                outcome="REJECTED_EXPIRED_JWT",
                detail="JWT ExpiredSignatureError",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="QR Code presensi telah kedaluwarsa (expired)",
            )
        except jwt.InvalidTokenError:
            self._log_attempt(
                actor_key=clean_nim,
                schedule_id=None,
                attempted_at=scan_dt,
                outcome="REJECTED_INVALID_JWT",
                detail="Signature atau format JWT tidak valid",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token QR presensi tidak valid atau signature telah dimodifikasi",
            )

        schedule_id = payload.get("schedule_id")
        session_id = payload.get("session_id")
        jti = payload.get("jti")
        expires_at_str = payload.get("expires_at")

        if not schedule_id or not jti:
            self._log_attempt(
                actor_key=clean_nim,
                schedule_id=schedule_id,
                attempted_at=scan_dt,
                outcome="REJECTED_MALFORMED_PAYLOAD",
                detail="Payload tidak memiliki schedule_id atau jti",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload token QR presensi tidak lengkap",
            )

        if expires_at_str:
            try:
                payload_exp_dt = to_jakarta_naive(datetime.fromisoformat(expires_at_str))
                if scan_dt > payload_exp_dt:
                    self._log_attempt(
                        actor_key=clean_nim,
                        schedule_id=schedule_id,
                        attempted_at=scan_dt,
                        outcome="REJECTED_EXPIRED_PAYLOAD",
                        detail="Waktu scan melewati expires_at pada payload",
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="QR Code presensi telah kedaluwarsa (expired)",
                    )
            except ValueError:
                pass

        # 4. Periksa keberadaan jti, session_id, dan status pencabutan token di database
        qr_token_row = (
            self.db.query(AttendanceQRToken)
            .filter(AttendanceQRToken.jti == str(jti))
            .first()
        )
        if not qr_token_row:
            self._log_attempt(
                actor_key=clean_nim,
                schedule_id=schedule_id,
                attempted_at=scan_dt,
                outcome="REJECTED_UNKNOWN_JTI",
                detail="JTI tidak terdaftar di database",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token QR tidak dikenali atau bukan berasal dari sesi resmi",
            )

        if session_id and qr_token_row.session_id != int(session_id):
            self._log_attempt(
                actor_key=clean_nim,
                schedule_id=schedule_id,
                attempted_at=scan_dt,
                outcome="REJECTED_SESSION_MISMATCH",
                detail="Session ID pada token tidak cocok",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token QR tidak sesuai dengan sesi presensi",
            )

        if qr_token_row.revoked_at is not None and scan_dt >= qr_token_row.revoked_at:
            self._log_attempt(
                actor_key=clean_nim,
                schedule_id=schedule_id,
                attempted_at=scan_dt,
                outcome="REJECTED_REVOKED",
                detail="Token QR telah dicabut/digantikan",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token QR sudah tidak berlaku karena telah diterbitkan QR baru",
            )

        if scan_dt > qr_token_row.expires_at or scan_dt < qr_token_row.generated_at - timedelta(seconds=5):
            self._log_attempt(
                actor_key=clean_nim,
                schedule_id=schedule_id,
                attempted_at=scan_dt,
                outcome="REJECTED_EXPIRED_DB",
                detail="Melewati expires_at token di database",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="QR Code presensi telah kedaluwarsa (expired)",
            )

        session = (
            self.db.query(AttendanceSession)
            .filter(AttendanceSession.id == qr_token_row.session_id)
            .first()
        )
        if not session or session.schedule_id != int(schedule_id):
            self._log_attempt(
                actor_key=clean_nim,
                schedule_id=schedule_id,
                attempted_at=scan_dt,
                outcome="REJECTED_SCHEDULE_MISMATCH",
                detail="Token tidak cocok dengan jadwal kuliah",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token QR tidak berlaku untuk jadwal kelas ini",
            )

        if session.session_status != "OPEN":
            self._log_attempt(
                actor_key=clean_nim,
                schedule_id=schedule_id,
                attempted_at=scan_dt,
                outcome="REJECTED_SESSION_CLOSED",
                detail="Sesi presensi sudah ditutup",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sesi presensi untuk perkuliahan ini sudah ditutup",
            )

        schedule = (
            self.db.query(JadwalKuliah)
            .filter(JadwalKuliah.id == session.schedule_id)
            .first()
        )
        if not schedule or schedule.status != "AKTIF":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jadwal kuliah tidak ditemukan atau tidak aktif",
            )

        # 5. Periksa apakah jadwal benar-benar berlangsung pada hari tersebut
        expected_day_name = DAY_NAME_ID.get(session.session_date.weekday(), "")
        if (
            scan_dt.date() != session.session_date
            or expected_day_name.lower() != (schedule.hari or "").strip().lower()
        ):
            self._log_attempt(
                actor_key=clean_nim,
                schedule_id=schedule.id,
                attempted_at=scan_dt,
                outcome="REJECTED_WRONG_DAY",
                detail=f"Hari sesi ({expected_day_name}) != hari jadwal ({schedule.hari})",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Jadwal kuliah ini hanya berlangsung pada hari {schedule.hari}",
            )

        # 6. Periksa pendaftaran mahasiswa pada mata kuliah melalui KRS yang disetujui (APPROVED)
        student = (
            self.db.query(CalonMahasiswa)
            .filter(
                CalonMahasiswa.nim == clean_nim,
                CalonMahasiswa.status == StatusPendaftaran.approved,
            )
            .first()
        )
        if not student:
            self._log_attempt(
                actor_key=clean_nim,
                schedule_id=schedule.id,
                attempted_at=scan_dt,
                outcome="REJECTED_STUDENT_NOT_FOUND",
                detail="Mahasiswa tidak ditemukan atau belum approved",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mahasiswa aktif dengan NIM tersebut tidak ditemukan",
            )

        enrolled = (
            self.db.query(KRSDetail)
            .join(KRS, KRS.id == KRSDetail.krs_id)
            .filter(
                KRS.nim == clean_nim,
                KRS.status == "APPROVED",
                KRSDetail.matakuliah_id == schedule.matakuliah_id,
            )
            .first()
        )
        if not enrolled:
            self._log_attempt(
                actor_key=clean_nim,
                schedule_id=schedule.id,
                attempted_at=scan_dt,
                outcome="REJECTED_NOT_ENROLLED",
                detail="Mahasiswa tidak terdaftar di MK pada KRS APPROVED",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="DITOLAK: Mahasiswa tidak terdaftar pada mata kuliah/kelas ini dalam KRS yang disetujui",
            )

        # 7. Periksa apakah mahasiswa sudah melakukan presensi pada sesi ini (cegah duplikat)
        existing_record = (
            self.db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.session_id == session.id,
                AttendanceRecord.student_id == student.id,
            )
            .first()
        )
        if existing_record:
            self._log_attempt(
                actor_key=clean_nim,
                schedule_id=schedule.id,
                attempted_at=scan_dt,
                outcome="REJECTED_DUPLICATE",
                detail="Scan presensi duplikat pada sesi yang sama",
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Presensi duplikat ditolak: Anda sudah tercatat hadir pada sesi kuliah ini",
            )

        # 8. Hitung status HADIR (<= 15 menit) vs TERLAMBAT (> 15 s/d 30 menit) vs DITOLAK (> 30 menit)
        class_start_dt = datetime.combine(session.session_date, schedule.jam_mulai)
        elapsed_minutes = (scan_dt - class_start_dt).total_seconds() / 60.0

        if elapsed_minutes < 0:
            self._log_attempt(
                actor_key=clean_nim,
                schedule_id=schedule.id,
                attempted_at=scan_dt,
                outcome="REJECTED_TOO_EARLY",
                detail="Scan sebelum waktu mulai kuliah",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="DITOLAK: Sesi waktu perkuliahan belum dimulai",
            )

        if elapsed_minutes <= 15.0:
            attendance_status = "HADIR"
        elif elapsed_minutes <= 30.0:
            attendance_status = "TERLAMBAT"
        else:
            self._log_attempt(
                actor_key=clean_nim,
                schedule_id=schedule.id,
                attempted_at=scan_dt,
                outcome="REJECTED_LATE_OVER_30M",
                detail=f"Scan pada menit ke-{elapsed_minutes:.1f} (>30 menit)",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="DITOLAK: Batas waktu presensi (maksimal 30 menit sejak kuliah dimulai) telah berakhir",
            )

        record = AttendanceRecord(
            session_id=session.id,
            student_id=student.id,
            nim=student.nim,
            scanned_at=scan_dt,
            attendance_status=attendance_status,
            qr_token_id=qr_token_row.id,
            latitude=latitude,
            longitude=longitude,
        )
        try:
            self.db.add(record)
            self.db.add(
                AttendanceScanAttempt(
                    actor_key=clean_nim,
                    schedule_id=schedule.id,
                    attempted_at=scan_dt,
                    outcome="SUCCESS",
                    detail=f"Status: {attendance_status}",
                )
            )
            self.db.commit()
            self.db.refresh(record)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Presensi duplikat ditolak: Anda sudah tercatat hadir pada sesi kuliah ini",
            )

        mk = (
            self.db.query(Matakuliah)
            .filter(Matakuliah.id == schedule.matakuliah_id)
            .first()
        )

        return {
            "success": True,
            "status": attendance_status.lower(),
            "attendance_status": attendance_status,
            "message": (
                f"Presensi berhasil dicatat dengan status {attendance_status} "
                f"({elapsed_minutes:.1f} menit sejak kuliah dimulai)"
            ),
            "record_id": record.id,
            "session_id": session.id,
            "schedule_id": schedule.id,
            "nim": student.nim,
            "nama_mahasiswa": student.nama_lengkap,
            "kode_mk": mk.kode_mk if mk else "-",
            "nama_mk": mk.nama_mk if mk else "-",
            "scanned_at": scan_dt.isoformat(),
            "elapsed_minutes": round(elapsed_minutes, 2),
        }
