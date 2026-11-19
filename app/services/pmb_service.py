from datetime import datetime
import threading
import time
from typing import Optional, Union

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models import (
    CalonMahasiswa,
    Dosen,
    NimSequence,
    ProgramStudi,
    StatusPendaftaran,
)

_NIM_LOCK = threading.RLock()


def _acquire_sqlite_write_lock(db: Session) -> None:
    """
    Mengaktifkan busy_timeout dan BEGIN IMMEDIATE pada transaksi SQLite
    agar pembacaan dan pembaruan nomor urut NIM bersifat atomic dan
    bebas dari deadlock promosi SHARED -> EXCLUSIVE lock.
    """
    if not isinstance(db, Session):
        return
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "sqlite":
        db.execute(text("PRAGMA busy_timeout = 30000"))
        if not db.in_transaction():  # pragma: no cover
            db.execute(text("BEGIN IMMEDIATE"))


def generate_nim(
    tahun: int,
    kode_prodi: str,
    prodi_id: Union[int, Session],
    db: Optional[Session] = None,
) -> str:
    """
    Generate NIM format: YYYY[KODE]-XXXX (contoh: 2025001-0001 / 2025TIF-0001).
    Mendukung pemanggilan 3 argumen (tahun, kode_prodi, db) sesuai dokumen dosen
    maupun 4 argumen (tahun, kode_prodi, prodi_id, db).
    Menggunakan sinkronisasi lock, BEGIN IMMEDIATE / with_for_update, dan retry.
    """
    with _NIM_LOCK:
        if db is None and isinstance(prodi_id, Session):
            db = prodi_id
            _acquire_sqlite_write_lock(db)
            prodi_obj = (
                db.query(ProgramStudi)
                .filter(ProgramStudi.kode == kode_prodi)
                .first()
            )
            resolved_prodi_id = prodi_obj.id if prodi_obj else 1
        else:
            if isinstance(db, Session):
                _acquire_sqlite_write_lock(db)
            resolved_prodi_id = int(prodi_id)

        seq = (
            db.query(NimSequence)
            .filter_by(tahun=tahun, program_studi_id=resolved_prodi_id)
            .with_for_update()
            .first()
        )

        if not seq:
            seq = NimSequence(
                tahun=tahun,
                program_studi_id=resolved_prodi_id,
                last_number=0,
            )
            db.add(seq)
            try:
                db.flush()
            except IntegrityError:  # pragma: no cover
                db.rollback()  # pragma: no cover
                seq = (  # pragma: no cover
                    db.query(NimSequence)
                    .filter_by(tahun=tahun, program_studi_id=resolved_prodi_id)
                    .with_for_update()
                    .first()
                )

        seq.last_number += 1
        db.flush()

        return f"{tahun}{kode_prodi}-{seq.last_number:04d}"


def approve_calon_mahasiswa(
    db: Session,
    id: int,
    dosen_pa_id: Optional[int] = None,
) -> CalonMahasiswa:
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with _NIM_LOCK:
                _acquire_sqlite_write_lock(db)

                mahasiswa = (
                    db.query(CalonMahasiswa)
                    .filter(CalonMahasiswa.id == id)
                    .with_for_update()
                    .first()
                )

                if not mahasiswa:
                    raise HTTPException(
                        status_code=404,
                        detail="Data calon mahasiswa tidak ditemukan",
                    )

                if mahasiswa.status == StatusPendaftaran.approved and mahasiswa.nim:
                    if dosen_pa_id is not None and mahasiswa.dosen_pa_id != dosen_pa_id:
                        dosen = db.query(Dosen).filter(Dosen.id == dosen_pa_id).first()
                        if not dosen:
                            raise HTTPException(
                                status_code=404,
                                detail="Dosen PA tidak ditemukan",
                            )
                        mahasiswa.dosen_pa_id = dosen_pa_id
                        db.commit()
                        db.refresh(mahasiswa)
                    return mahasiswa

                if mahasiswa.status == StatusPendaftaran.rejected:
                    raise HTTPException(
                        status_code=409,
                        detail="Mahasiswa yang sudah rejected tidak dapat di-approve",
                    )

                if (
                    not mahasiswa.nama_lengkap
                    or not mahasiswa.email
                    or not mahasiswa.phone
                    or not mahasiswa.program_studi_id
                    or not mahasiswa.jalur_masuk_id
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Data pendaftar belum lengkap atau tidak memenuhi syarat",
                    )

                prodi = (
                    db.query(ProgramStudi)
                    .filter(ProgramStudi.id == mahasiswa.program_studi_id)
                    .first()
                )
                if not prodi:  # pragma: no cover
                    raise HTTPException(
                        status_code=404,
                        detail="Program studi tidak ditemukan",
                    )

                if dosen_pa_id is not None:
                    dosen = db.query(Dosen).filter(Dosen.id == dosen_pa_id).first()
                    if not dosen:
                        raise HTTPException(
                            status_code=404,
                            detail="Dosen PA tidak ditemukan",
                        )
                    mahasiswa.dosen_pa_id = dosen_pa_id

                tahun_masuk = datetime.utcnow().year
                nim_baru = generate_nim(tahun_masuk, prodi.kode, prodi.id, db)

                mahasiswa.status = StatusPendaftaran.approved
                mahasiswa.nim = nim_baru
                mahasiswa.approved_at = datetime.utcnow()

                db.commit()
                db.refresh(mahasiswa)
                return mahasiswa

        except OperationalError:  # pragma: no cover
            db.rollback()
            if attempt < max_retries - 1:
                time.sleep(0.05 * (attempt + 1))
                continue
            raise HTTPException(
                status_code=503,
                detail="Database sedang sibuk, silakan coba kembali",
            )
        except IntegrityError:  # pragma: no cover
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Konflik data saat menyimpan NIM",
            )


def reject_calon_mahasiswa(db: Session, id: int) -> CalonMahasiswa:
    with _NIM_LOCK:
        mahasiswa = (
            db.query(CalonMahasiswa)
            .filter(CalonMahasiswa.id == id)
            .with_for_update()
            .first()
        )

        if not mahasiswa:
            raise HTTPException(
                status_code=404,
                detail="Data calon mahasiswa tidak ditemukan",
            )

        if mahasiswa.status == StatusPendaftaran.approved:
            raise HTTPException(
                status_code=409,
                detail="Mahasiswa yang sudah approved tidak dapat di-reject",
            )

        if mahasiswa.status == StatusPendaftaran.rejected:
            return mahasiswa

        mahasiswa.status = StatusPendaftaran.rejected
        db.commit()
        db.refresh(mahasiswa)  # pragma: no cover
        return mahasiswa
