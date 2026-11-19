from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import (
    Dosen,
    JadwalKuliah,
    KRS,
    KRSDetail,
    KrsTransition,
    Matakuliah,
    Ruangan,
    ScheduleChangeLog,
)
from app.observers.concrete_observers import (
    AdminObserver,
    LecturerObserver,
    StudentObserver,
)
from app.observers.schedule_subject import ScheduleSubject
from app.services.conflict_detector import detect_schedule_conflict


class SchedulingService:

    def __init__(self, db: Session):
        self.db = db

    def _parse_time(self, value):
        if hasattr(value, "hour"):
            return value

        if not isinstance(value, str):
            raise ValueError("Format waktu tidak valid")

        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue

        raise ValueError(f"Format waktu tidak valid: {value}")

    def _invalidate_krs(self, matakuliah_id):
        affected = (
            self.db.query(KRS)
            .join(KRSDetail)
            .filter(KRSDetail.matakuliah_id == matakuliah_id)
            .all()
        )

        for krs in affected:
            if krs.status != "APPROVED":
                krs.needs_review = True
                if isinstance(self.db, Session) and getattr(krs, "id", None) is not None:
                    from app.services.krs_manager import KRSManager

                    validation = KRSManager(self.db).validate_krs(krs.nim)
                    reason_tag = (
                        "SYSTEM_SCHEDULE_CHANGED_CONFLICT_DETECTED"
                        if not validation["is_valid"]
                        else "SYSTEM_SCHEDULE_CHANGED_NEEDS_REVIEW"
                    )
                    self.db.add(
                        KrsTransition(
                            krs_id=krs.id,
                            from_status=krs.status,
                            to_status=krs.status,
                            changed_by=reason_tag,
                        )
                    )

        return affected

    def _trigger_observers(
        self,
        event_type,
        jadwal,
        mk,
        dosen_id,
    ):
        subject = ScheduleSubject()

        subject.attach(AdminObserver(self.db))
        subject.attach(LecturerObserver(self.db, dosen_id))

        krs_list = (
            self.db.query(KRS)
            .join(KRSDetail)
            .filter(KRSDetail.matakuliah_id == mk.id)
            .all()
        )

        nims = list(dict.fromkeys(k.nim for k in krs_list))

        if nims:
            subject.attach(StudentObserver(self.db, nims))

        subject.notify(
            event_type,
            {
                "nama_mk": mk.nama_mk,
                "id": jadwal.id,
            },
        )

    def _validate_schedule(self, data, exclude_id=None):
        mk = None
        ruangan = None
        dosen = None

        if data.get("matakuliah_id") is not None:
            mk = (
                self.db.query(Matakuliah)
                .filter(Matakuliah.id == data["matakuliah_id"])
                .first()
            )
            if not mk:
                raise HTTPException(
                    status_code=404,
                    detail="Mata kuliah tidak ditemukan",
                )

        if data.get("ruangan_id") is not None:
            ruangan = (
                self.db.query(Ruangan)
                .filter(Ruangan.id == data["ruangan_id"])
                .first()
            )
            if not ruangan:
                raise HTTPException(
                    status_code=404,
                    detail="Ruangan tidak ditemukan",
                )

        if data.get("dosen_id") is not None:
            dosen = (
                self.db.query(Dosen)
                .filter(Dosen.id == data["dosen_id"])
                .first()
            )
            if not dosen:
                raise HTTPException(
                    status_code=404,
                    detail="Dosen tidak ditemukan",
                )

        required = [
            "matakuliah_id",
            "dosen_id",
            "ruangan_id",
            "hari",
            "jam_mulai",
            "jam_selesai",
            "tahun_akademik",
            "semester_akademik",
        ]

        for field in required:
            if field not in data or data[field] is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"Field {field} wajib diisi",
                )

        try:
            data["jam_mulai"] = self._parse_time(data["jam_mulai"])
            data["jam_selesai"] = self._parse_time(data["jam_selesai"])
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            )

        if data["jam_mulai"] >= data["jam_selesai"]:
            raise HTTPException(
                status_code=422,
                detail="Jam selesai harus setelah jam mulai",
            )

        if not ruangan.is_active:
            raise HTTPException(
                status_code=400,
                detail="Ruangan tidak aktif",
            )

        jumlah_mahasiswa = (
            self.db.query(KRSDetail)
            .filter(KRSDetail.matakuliah_id == mk.id)
            .count()
        )

        if jumlah_mahasiswa > ruangan.kapasitas:
            raise HTTPException(
                status_code=400,
                detail="Kapasitas ruangan tidak mencukupi",
            )

        candidate = JadwalKuliah(**data)

        query = self.db.query(JadwalKuliah).filter(
            JadwalKuliah.hari == candidate.hari
        )

        if exclude_id is not None:
            query = query.filter(JadwalKuliah.id != exclude_id)

        existing = query.all()

        conflicts = detect_schedule_conflict(candidate, existing)

        if conflicts:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Konflik terdeteksi",
                    "conflicts": conflicts,
                },
            )

        return candidate, mk

    def create_schedule(self, data: dict):
        data = dict(data)
        candidate, mk = self._validate_schedule(data)

        try:
            self.db.add(candidate)
            self.db.flush()

            self.db.add(
                ScheduleChangeLog(
                    jadwal_id=candidate.id,
                    action_type="CREATE",
                    old_data=None,
                    new_data=str(data),
                    changed_by="system",
                )
            )

            self.db.commit()
            self.db.refresh(candidate)
        except Exception:
            self.db.rollback()
            raise

        self._trigger_observers(
            "SCHEDULE_CREATED",
            candidate,
            mk,
            candidate.dosen_id,
        )

        if isinstance(self.db, Session):
            self.db.refresh(candidate)

        return candidate

    def update_schedule(self, id: int, data: dict):
        jadwal = (
            self.db.query(JadwalKuliah)
            .filter(JadwalKuliah.id == id)
            .with_for_update()
            .first()
        )

        if not jadwal:
            raise HTTPException(
                status_code=404,
                detail="Jadwal tidak ditemukan",
            )

        old_data = {
            "matakuliah_id": jadwal.matakuliah_id,
            "dosen_id": jadwal.dosen_id,
            "ruangan_id": jadwal.ruangan_id,
            "hari": jadwal.hari,
            "jam_mulai": jadwal.jam_mulai,
            "jam_selesai": jadwal.jam_selesai,
            "tahun_akademik": jadwal.tahun_akademik,
            "semester_akademik": jadwal.semester_akademik,
            "status": jadwal.status,
        }

        merged_data = {
            **old_data,
            **data,
        }

        candidate, mk = self._validate_schedule(
            merged_data,
            exclude_id=id,
        )

        try:
            for key, value in merged_data.items():
                setattr(jadwal, key, value)

            if isinstance(self.db, Session):
                self.db.flush()

            self.db.add(
                ScheduleChangeLog(
                    jadwal_id=jadwal.id,
                    action_type="UPDATE",
                    old_data=str(old_data),
                    new_data=str(merged_data),
                    changed_by="system",
                )
            )

            self._invalidate_krs(old_data["matakuliah_id"])

            if merged_data["matakuliah_id"] != old_data["matakuliah_id"]:
                self._invalidate_krs(merged_data["matakuliah_id"])

            self.db.commit()
            self.db.refresh(jadwal)
        except Exception:
            self.db.rollback()
            raise

        self._trigger_observers(
            "SCHEDULE_UPDATED",
            jadwal,
            mk,
            jadwal.dosen_id,
        )

        if isinstance(self.db, Session):
            self.db.refresh(jadwal)

        return jadwal

    def delete_schedule(self, id: int):
        jadwal = (
            self.db.query(JadwalKuliah)
            .filter(JadwalKuliah.id == id)
            .with_for_update()
            .first()
        )

        if not jadwal:
            raise HTTPException(
                status_code=404,
                detail="Jadwal tidak ditemukan",
            )

        mk = (
            self.db.query(Matakuliah)
            .filter(Matakuliah.id == jadwal.matakuliah_id)
            .first()
        )

        old_data = {
            "matakuliah_id": jadwal.matakuliah_id,
            "dosen_id": jadwal.dosen_id,
            "ruangan_id": jadwal.ruangan_id,
            "hari": jadwal.hari,
            "jam_mulai": str(jadwal.jam_mulai),
            "jam_selesai": str(jadwal.jam_selesai),
        }

        try:
            self.db.add(
                ScheduleChangeLog(
                    jadwal_id=jadwal.id,
                    action_type="DELETE",
                    old_data=str(old_data),
                    new_data=None,
                    changed_by="system",
                )
            )

            self._invalidate_krs(jadwal.matakuliah_id)

            jadwal_id = jadwal.id
            dosen_id = jadwal.dosen_id

            self.db.delete(jadwal)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        if mk:
            self._trigger_observers(
                "SCHEDULE_DELETED",
                jadwal,
                mk,
                dosen_id,
            )

        return {
            "message": "Jadwal berhasil dihapus",
            "id": jadwal_id,
        }
