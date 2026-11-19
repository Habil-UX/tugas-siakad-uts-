from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import (
    JadwalKuliah,
    KRS,
    Matakuliah,
    Prerequisite,
    RiwayatNilai,
    SkalaNilai,
)


@dataclass
class ValidationResult:
    is_valid: bool
    message: str = ""
    validator_name: str = ""
    detail: Optional[dict] = None


class Validator(ABC):

    def __init__(self, stop_on_first_error: bool = True):
        self._next_validator: Optional["Validator"] = None
        self.stop_on_first_error: bool = stop_on_first_error

    def set_next(self, validator: "Validator") -> "Validator":
        validator.stop_on_first_error = self.stop_on_first_error
        self._next_validator = validator
        return validator

    def validate(self, context: dict) -> ValidationResult:
        if not self.stop_on_first_error:
            results = self.validate_all(context)
            failed = [r for r in results if not r.is_valid]
            if failed:
                messages = list(dict.fromkeys(r.message for r in failed))
                return ValidationResult(
                    is_valid=False,
                    message="; ".join(messages),
                    validator_name=failed[0].validator_name,
                    detail={"errors": messages},
                )
            return ValidationResult(is_valid=True)

        result = self._validate(context)

        if not result.is_valid:
            return result

        if self._next_validator:
            return self._next_validator.validate(context)

        return ValidationResult(is_valid=True)

    def validate_all(self, context: dict) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        current: Optional[Validator] = self
        while current is not None:
            res = current._validate(context)
            if not res.is_valid:
                results.append(res)
            current = current._next_validator
        return results

    @abstractmethod
    def _validate(self, context: dict) -> ValidationResult:
        pass


class SKSValidator(Validator):

    def _validate(self, context: dict) -> ValidationResult:
        krs: KRS = context["krs"]
        new_mk: Matakuliah = context["new_mk"]

        existing_details = context.get(
            "existing_details",
            krs.details,
        )

        current_sks = sum(
            detail.matakuliah.sks
            for detail in existing_details
        )

        total_sks = current_sks + new_mk.sks

        if total_sks > 24:
            return ValidationResult(
                is_valid=False,
                message=(
                    "Total SKS melebihi batas maksimal 24 SKS. "
                    f"(Saat ini: {current_sks}, "
                    f"Tambahan: {new_mk.sks})"
                ),
                validator_name="SKSValidator",
            )

        return ValidationResult(is_valid=True)


class PrerequisiteValidator(Validator):

    @staticmethod
    def build_prerequisite_query(
        nim: str,
        matakuliah_id: int,
        bobot_c: float = 2.0,
        krs_semester: Optional[int] = None,
    ):
        passed_subq = (
            select(RiwayatNilai.id)
            .join(
                SkalaNilai,
                RiwayatNilai.skala_nilai_id == SkalaNilai.id,
            )
            .where(RiwayatNilai.nim == nim)
            .where(RiwayatNilai.matakuliah_id == Matakuliah.id)
            .where(SkalaNilai.bobot >= bobot_c)
        )
        if isinstance(krs_semester, int) and krs_semester > 1:
            passed_subq = passed_subq.where(
                RiwayatNilai.semester < krs_semester
            )

        return (
            select(Matakuliah.nama_mk)
            .join(
                Prerequisite,
                Prerequisite.prerequisite_id == Matakuliah.id,
            )
            .where(Prerequisite.matakuliah_id == matakuliah_id)
            .where(~passed_subq.exists())
        )

    @staticmethod
    def explain_prerequisite_query(
        db: Session,
        nim: str,
        matakuliah_id: int,
        krs_semester: Optional[int] = None,
    ) -> List[dict]:
        sql = """
            EXPLAIN QUERY PLAN
            SELECT matakuliah.nama_mk
            FROM matakuliah
            JOIN prerequisite ON prerequisite.prerequisite_id = matakuliah.id
            WHERE prerequisite.matakuliah_id = :mk_id
              AND NOT EXISTS (
                  SELECT 1
                  FROM riwayat_nilai
                  JOIN skala_nilai ON riwayat_nilai.skala_nilai_id = skala_nilai.id
                  WHERE riwayat_nilai.nim = :nim
                    AND riwayat_nilai.matakuliah_id = matakuliah.id
                    AND skala_nilai.bobot >= :bobot_c
                    AND (:sem IS NULL OR riwayat_nilai.semester < :sem)
              )
        """
        rows = db.execute(
            text(sql),
            {
                "mk_id": matakuliah_id,
                "nim": nim,
                "bobot_c": 2.0,
                "sem": krs_semester if (isinstance(krs_semester, int) and krs_semester > 1) else None,
            },
        ).all()
        return [
            {"id": r[0], "parent": r[1], "notused": r[2], "detail": str(r[3])}
            for r in rows
        ]

    def _validate(self, context: dict) -> ValidationResult:
        db: Session = context["db"]
        nim: str = context["nim"]
        new_mk: Matakuliah = context["new_mk"]
        krs = context.get("krs")
        krs_semester = getattr(krs, "semester_akademik", None)

        bobot_c = (
            db.query(SkalaNilai.bobot)
            .filter(SkalaNilai.nilai_huruf == "C")
            .scalar()
            or 2.0
        )

        prereq_query = self.build_prerequisite_query(
            nim=nim,
            matakuliah_id=new_mk.id,
            bobot_c=bobot_c,
            krs_semester=krs_semester,
        )

        missing_prereqs = [
            row[0]
            for row in db.execute(prereq_query).all()
        ]

        if missing_prereqs:
            return ValidationResult(
                is_valid=False,
                message=(
                    "Prasyarat tidak terpenuhi: "
                    + ", ".join(missing_prereqs)
                ),
                validator_name="PrerequisiteValidator",
                detail={"missing": missing_prereqs},
            )

        return ValidationResult(is_valid=True)


class ConflictValidator(Validator):

    @staticmethod
    def _get_course_schedules(db, mk) -> list:
        """
        Mengambil daftar slot waktu (hari, jam_mulai, jam_selesai) mata kuliah.
        Menggunakan tabel JadwalKuliah (status AKTIF) sebagai sumber data aktual
        apabila tersedia di database, sehingga perubahan jadwal langsung terbaca
        dan mendukung mata kuliah dengan satu atau beberapa sesi jadwal.
        Apabila belum ada baris di JadwalKuliah (atau pada unit test berbasis mock),
        fallback ke atribut jadwal bawaan pada objek Matakuliah.
        """
        mk_id = getattr(mk, "id", None)
        if isinstance(db, Session) and mk_id is not None:
            active_schedules = (
                db.query(JadwalKuliah)
                .filter(
                    JadwalKuliah.matakuliah_id == mk_id,
                    JadwalKuliah.status == "AKTIF",
                )
                .all()
            )
            if active_schedules:
                slots = [
                    (
                        getattr(s, "hari", None),
                        getattr(s, "jam_mulai", None),
                        getattr(s, "jam_selesai", None),
                    )
                    for s in active_schedules
                ]
                valid_slots = [
                    slot for slot in slots if all(slot)
                ]
                if valid_slots:
                    return valid_slots

        day = getattr(mk, "hari", None)
        start = getattr(mk, "jam_mulai", None)
        end = getattr(mk, "jam_selesai", None)
        if all([day, start, end]):
            return [(day, start, end)]
        return []

    def _validate(self, context: dict) -> ValidationResult:
        db = context.get("db")
        krs = context["krs"]
        new_mk = context["new_mk"]

        existing_details = context.get(
            "existing_details",
            krs.details,
        )

        new_mk_id = getattr(new_mk, "id", None)
        new_slots = self._get_course_schedules(db, new_mk)
        if not new_slots:
            return ValidationResult(is_valid=True)

        for detail in existing_details:
            detail_mk_id = getattr(detail, "matakuliah_id", None)
            if (
                detail_mk_id is not None
                and new_mk_id is not None
                and detail_mk_id == new_mk_id
            ):
                continue

            existing_mk = detail.matakuliah
            existing_slots = self._get_course_schedules(db, existing_mk)
            if not existing_slots:
                continue

            for existing_day, existing_start, existing_end in existing_slots:
                for new_day, new_start, new_end in new_slots:
                    if (
                        existing_day == new_day
                        and existing_start < new_end
                        and new_start < existing_end
                    ):
                        nama_mk = getattr(
                            existing_mk,
                            "nama_mk",
                            "Mata kuliah lain",
                        )

                        return ValidationResult(
                            is_valid=False,
                            message=f"Jadwal bentrok dengan mata kuliah {nama_mk}",
                            validator_name="ConflictValidator",
                        )

        return ValidationResult(is_valid=True)


class DuplicateValidator(Validator):

    def _validate(self, context: dict) -> ValidationResult:
        krs: KRS = context["krs"]
        new_mk: Matakuliah = context["new_mk"]

        existing_details = context.get(
            "existing_details",
            krs.details,
        )

        for detail in existing_details:
            if detail.matakuliah_id == new_mk.id:
                return ValidationResult(
                    is_valid=False,
                    message=(
                        f"Mata kuliah {new_mk.nama_mk} "
                        "sudah terdaftar di KRS."
                    ),
                    validator_name="DuplicateValidator",
                )

        return ValidationResult(is_valid=True)


def build_chain(stop_on_first_error: bool = True) -> Validator:
    sks = SKSValidator(stop_on_first_error=stop_on_first_error)
    prereq = PrerequisiteValidator(stop_on_first_error=stop_on_first_error)
    conflict = ConflictValidator(stop_on_first_error=stop_on_first_error)
    duplicate = DuplicateValidator(stop_on_first_error=stop_on_first_error)

    sks.set_next(prereq).set_next(conflict).set_next(duplicate)

    return sks
