from datetime import date
from decimal import Decimal
from typing import Union

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    Billing,
    CalonMahasiswa,
    Dosen,
    KRS,
    KRSDetail,
    KrsTransition,
    Matakuliah,
    Payment,
)
from app.services.krs.validators import (
    ConflictValidator,
    DuplicateValidator,
    PrerequisiteValidator,
    SKSValidator,
    build_chain,
)
from app.services.krs_state_machine import (
    KRSStateMachine,
    KRSStatus,
)


class KRSManager:

    def __init__(self, db: Session, stop_on_first_error: bool = True):
        self.db = db
        self.validator_chain = build_chain(
            stop_on_first_error=stop_on_first_error
        )

    # ==========================================
    # PEMERIKSAAN TUNGGAKAN PEMBAYARAN SPP
    # ==========================================

    def _check_payment_arrears(self, nim: str):
        if not isinstance(self.db, Session):
            return

        billings = (
            self.db.query(Billing)
            .filter(Billing.nim == nim)
            .all()
        )
        today = date.today()

        for billing in billings:
            is_overdue = billing.status == "overdue" or (
                billing.due_date is not None
                and billing.due_date < today
                and billing.status in ("unpaid", "partial")
            )
            if not is_overdue:
                continue

            paid = (
                self.db.query(func.coalesce(func.sum(Payment.amount), 0))
                .filter(
                    Payment.billing_id == billing.id,
                    Payment.status == "success",
                )
                .scalar()
            )
            paid_dec = Decimal(str(paid or 0))
            amount_dec = Decimal(str(billing.amount))

            if paid_dec < amount_dec:
                if billing.status != "overdue":
                    billing.status = "overdue"
                    self.db.commit()
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Mahasiswa memiliki tunggakan pembayaran SPP yang belum lunas. "
                        "Pengisian KRS diblokir hingga tunggakan dilunasi."
                    ),
                )

    # ==========================================
    # MENCARI MAHASISWA
    # ==========================================

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

    # ==========================================
    # VALIDASI DOSEN PA
    # ==========================================

    def _get_authorized_dosen(
        self,
        nim: str,
        nidn_dosen_pa: Union[str, int],
    ):
        mahasiswa = self._get_mahasiswa(nim)

        if not mahasiswa.dosen_pa_id:
            raise HTTPException(
                status_code=409,
                detail="Dosen PA mahasiswa belum ditetapkan",
            )

        dosen = (
            self.db.query(Dosen)
            .filter(Dosen.nidn == str(nidn_dosen_pa))
            .first()
        )

        if (
            not dosen
            and isinstance(self.db, Session)
            and str(nidn_dosen_pa).isdigit()
        ):
            dosen = (
                self.db.query(Dosen)
                .filter(Dosen.id == int(nidn_dosen_pa))
                .first()
            )

        if not dosen:
            raise HTTPException(
                status_code=404,
                detail="Dosen dengan NIDN tersebut tidak ditemukan",
            )

        if dosen.id != mahasiswa.dosen_pa_id:
            raise HTTPException(
                status_code=403,
                detail="Dosen tidak berwenang mengelola KRS mahasiswa ini",
            )

        return dosen

    # ==========================================
    # GET OR CREATE KRS
    # ==========================================

    def _get_or_create_krs(
        self,
        nim: str,
        semester: int = 1,
        tahun: str = "2024/2025",
    ):
        self._get_mahasiswa(nim)

        krs = (
            self.db.query(KRS)
            .filter(
                KRS.nim == nim,
                KRS.semester_akademik == semester,
            )
            .with_for_update()
            .first()
        )

        if krs is not None:
            return krs

        krs = KRS(
            nim=nim,
            semester_akademik=semester,
            tahun_akademik=tahun,
            status="DRAFT",
            total_sks=0,
            version=1,
        )

        try:
            self.db.add(krs)
            self.db.commit()
            self.db.refresh(krs)

            return krs

        except Exception:
            self.db.rollback()
            raise

    # ==========================================
    # GET KRS DETAIL
    # ==========================================

    def get_krs(self, nim: str, semester: int = 1):
        krs = self._get_or_create_krs(nim, semester=semester)
        courses = []
        for d in getattr(krs, "details", []) or []:
            mk = d.matakuliah
            courses.append(
                {
                    "kode_mk": mk.kode_mk,
                    "nama_mk": mk.nama_mk,
                    "sks": mk.sks,
                    "semester": mk.semester,
                    "jenis_mk": mk.jenis_mk,
                    "hari": mk.hari,
                    "jam_mulai": str(mk.jam_mulai),
                    "jam_selesai": str(mk.jam_selesai),
                }
            )
        return {
            "id": krs.id,
            "nim": krs.nim,
            "semester_akademik": krs.semester_akademik,
            "tahun_akademik": krs.tahun_akademik,
            "status": krs.status,
            "total_sks": krs.total_sks,
            "needs_review": bool(getattr(krs, "needs_review", False)),
            "version": getattr(krs, "version", 1),
            "courses": courses,
        }

    # ==========================================
    # LOG TRANSITION
    # ==========================================

    def _log_transition(
        self,
        krs_id: int,
        from_stat: str,
        to_stat: str,
        actor: str,
    ):
        log = KrsTransition(
            krs_id=krs_id,
            from_status=from_stat,
            to_status=to_stat,
            changed_by=actor,
        )

        self.db.add(log)

    # ==========================================
    # SUBMIT KRS
    # ==========================================

    def submit_krs(self, nim: str):
        self._check_payment_arrears(nim)

        krs = self._get_or_create_krs(nim)

        new_status = KRSStateMachine.transition(
            krs.status,
            KRSStatus.SUBMITTED,
        )

        details_attr = getattr(krs, "details", None)
        if isinstance(details_attr, list) and len(details_attr) == 0:
            raise HTTPException(
                status_code=400,
                detail="KRS tidak boleh kosong saat disubmit",
            )

        validation = self.validate_krs(nim)

        if not validation["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "KRS tidak valid",
                    "errors": validation["errors"],
                },
            )

        old_status = krs.status

        try:
            krs.status = new_status
            krs.version = (krs.version or 0) + 1
            if hasattr(krs, "needs_review"):
                krs.needs_review = False

            self._log_transition(
                krs.id,
                old_status,
                new_status,
                f"Mahasiswa_{nim}",
            )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return {
            "message": "KRS berhasil disubmit",
            "status": krs.status,
        }

    # ==========================================
    # APPROVE KRS
    # ==========================================

    def approve_krs(
        self,
        nim: str,
        nidn_dosen_pa: Union[str, int],
    ):
        krs = (
            self.db.query(KRS)
            .filter(KRS.nim == nim)
            .with_for_update()
            .first()
        )

        if not krs:
            raise HTTPException(
                status_code=404,
                detail="KRS tidak ditemukan",
            )

        dosen = self._get_authorized_dosen(
            nim,
            nidn_dosen_pa,
        )

        new_status = KRSStateMachine.transition(
            krs.status,
            KRSStatus.APPROVED,
        )

        old_status = krs.status

        try:
            krs.status = new_status
            krs.version = (krs.version or 0) + 1

            self._log_transition(
                krs.id,
                old_status,
                new_status,
                dosen.nidn,
            )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return {
            "message": "KRS berhasil disetujui",
            "status": krs.status,
        }

    # ==========================================
    # REVISE KRS
    # ==========================================

    def revise_krs(
        self,
        nim: str,
        nidn_dosen_pa: Union[str, int],
    ):
        krs = (
            self.db.query(KRS)
            .filter(KRS.nim == nim)
            .with_for_update()
            .first()
        )

        if not krs:
            raise HTTPException(
                status_code=404,
                detail="KRS tidak ditemukan",
            )

        dosen = self._get_authorized_dosen(
            nim,
            nidn_dosen_pa,
        )

        new_status = KRSStateMachine.transition(
            krs.status,
            KRSStatus.REVISION,
        )

        old_status = krs.status

        try:
            krs.status = new_status
            krs.version = (krs.version or 0) + 1

            self._log_transition(
                krs.id,
                old_status,
                new_status,
                dosen.nidn,
            )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return {
            "message": "KRS dikembalikan untuk revisi",
            "status": krs.status,
        }

    # ==========================================
    # VALIDATE KRS
    # ==========================================

    def validate_krs(self, nim: str):
        krs = self._get_or_create_krs(nim)

        errors = []

        if not krs.details:
            return {
                "is_valid": True,
                "errors": [],
            }

        validators = [
            SKSValidator(),
            PrerequisiteValidator(),
            ConflictValidator(),
            DuplicateValidator(),
        ]

        for detail in krs.details:
            context = {
                "db": self.db,
                "nim": nim,
                "krs": krs,
                "new_mk": detail.matakuliah,
                "existing_details": [
                    item
                    for item in krs.details
                    if item is not detail
                ],
            }

            for validator in validators:
                result = validator._validate(context)

                if not result.is_valid:
                    errors.append(result.message)

        return {
            "is_valid": len(errors) == 0,
            "errors": list(dict.fromkeys(errors)),
        }

    # ==========================================
    # ADD COURSE
    # ==========================================

    def add_course(self, nim: str, kode_mk: str):
        self._check_payment_arrears(nim)

        krs = self._get_or_create_krs(nim)

        if krs.status not in ["DRAFT", "REVISION"]:
            raise HTTPException(
                status_code=400,
                detail="KRS tidak dapat diedit",
            )

        mk = (
            self.db.query(Matakuliah)
            .filter(Matakuliah.kode_mk == kode_mk)
            .first()
        )

        if not mk:
            raise HTTPException(
                status_code=404,
                detail="Mata kuliah tidak ditemukan",
            )

        context = {
            "db": self.db,
            "nim": nim,
            "krs": krs,
            "new_mk": mk,
        }

        result = self.validator_chain.validate(context)

        if not result.is_valid:
            raise HTTPException(
                status_code=400,
                detail=result.message,
            )

        try:
            krs.details.append(
                KRSDetail(matakuliah_id=mk.id)
            )

            krs.total_sks += mk.sks
            krs.version = (
                getattr(krs, "version", 0) or 0
            ) + 1

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return {
            "message": "Mata kuliah berhasil ditambahkan",
            "total_sks": krs.total_sks,
        }

    # ==========================================
    # REMOVE COURSE
    # ==========================================

    def remove_course(self, nim: str, kode_mk: str):
        krs = self._get_or_create_krs(nim)

        if krs.status not in ["DRAFT", "REVISION"]:
            raise HTTPException(
                status_code=400,
                detail="KRS tidak dapat diedit (status bukan DRAFT/REVISION)",
            )

        mk = (
            self.db.query(Matakuliah)
            .filter(Matakuliah.kode_mk == kode_mk)
            .first()
        )

        if not mk:
            raise HTTPException(
                status_code=404,
                detail="Mata kuliah tidak ditemukan",
            )

        detail = (
            self.db.query(KRSDetail)
            .filter(
                KRSDetail.krs_id == krs.id,
                KRSDetail.matakuliah_id == mk.id,
            )
            .first()
        )

        if not detail:
            raise HTTPException(
                status_code=404,
                detail="Mata kuliah tidak terdaftar di KRS",
            )

        try:
            krs.total_sks -= mk.sks

            krs.version = (
                getattr(krs, "version", 0) or 0
            ) + 1

            self.db.delete(detail)
            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return {
            "message": f"Mata kuliah {mk.nama_mk} berhasil dihapus",
            "total_sks": krs.total_sks,
        }
