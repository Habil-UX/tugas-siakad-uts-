from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    CalonMahasiswa,
    JalurMasuk,
    ProgramStudi,
    StatusPendaftaran,
)
from app.schemas.pmb import (
    CalonMahasiswaCreate,
    CalonMahasiswaResponse,
    StatsResponse,
    StatusResponse,
)
from app.services.pmb_service import (
    approve_calon_mahasiswa,
    reject_calon_mahasiswa,
)
from app.utils.security import require_roles

router = APIRouter(prefix="/api/pmb", tags=["PMB"])


@router.post(
    "/register",
    response_model=CalonMahasiswaResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_calon_mahasiswa(
    payload: CalonMahasiswaCreate,
    db: Session = Depends(get_db),
):
    existing_email = (
        db.query(CalonMahasiswa)
        .filter(CalonMahasiswa.email == payload.email)
        .first()
    )
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email sudah terdaftar.",
        )

    prodi = (
        db.query(ProgramStudi)
        .filter(ProgramStudi.id == payload.program_studi_id)
        .first()
    )
    if not prodi:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Program studi tidak ditemukan.",
        )

    jalur = (
        db.query(JalurMasuk)
        .filter(JalurMasuk.id == payload.jalur_masuk_id)
        .first()
    )
    if not jalur:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jalur masuk tidak ditemukan.",
        )

    new_mahasiswa = CalonMahasiswa(
        **payload.model_dump(),
        status=StatusPendaftaran.pending,
        nim=None,
    )

    try:
        db.add(new_mahasiswa)
        db.commit()
        db.refresh(new_mahasiswa)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email sudah terdaftar (konflik database).",
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan internal server.",
        )

    return new_mahasiswa


@router.put(
    "/approve/{id}",
    response_model=CalonMahasiswaResponse,
)
def approve_pendaftaran(
    id: int,
    dosen_pa_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    _user: Optional[dict] = Depends(require_roles(["admin"])),
):
    return approve_calon_mahasiswa(db, id, dosen_pa_id=dosen_pa_id)


@router.put(
    "/reject/{id}",
    response_model=CalonMahasiswaResponse,
)
def reject_pendaftaran(
    id: int,
    db: Session = Depends(get_db),
    _user: Optional[dict] = Depends(require_roles(["admin"])),
):
    return reject_calon_mahasiswa(db, id)


@router.get(
    "/status/{id}",
    response_model=StatusResponse,
)
def get_status_pendaftaran(
    id: int,
    db: Session = Depends(get_db),
):
    mahasiswa = (
        db.query(CalonMahasiswa)
        .filter(CalonMahasiswa.id == id)
        .first()
    )
    if not mahasiswa:
        raise HTTPException(
            status_code=404,
            detail="Data tidak ditemukan",
        )

    return StatusResponse(
        id=mahasiswa.id,
        nama_lengkap=mahasiswa.nama_lengkap,
        email=mahasiswa.email,
        program_studi=mahasiswa.program_studi.nama,
        jalur_masuk=mahasiswa.jalur_masuk.nama,
        status=mahasiswa.status,
        nim=mahasiswa.nim,
        created_at=mahasiswa.created_at,
        approved_at=mahasiswa.approved_at,
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
)
def get_statistik(
    db: Session = Depends(get_db),
):
    total = db.query(func.count(CalonMahasiswa.id)).scalar()

    status_counts = (
        db.query(
            CalonMahasiswa.status,
            func.count(CalonMahasiswa.id),
        )
        .group_by(CalonMahasiswa.status)
        .all()
    )
    status_dict = {str(s.value): count for s, count in status_counts}

    prodi_counts = (
        db.query(
            ProgramStudi.nama,
            func.count(CalonMahasiswa.id),
        )
        .join(
            CalonMahasiswa,
            CalonMahasiswa.program_studi_id == ProgramStudi.id,
        )
        .group_by(ProgramStudi.nama)
        .all()
    )

    jalur_counts = (
        db.query(
            JalurMasuk.nama,
            func.count(CalonMahasiswa.id),
        )
        .join(
            CalonMahasiswa,
            CalonMahasiswa.jalur_masuk_id == JalurMasuk.id,
        )
        .group_by(JalurMasuk.nama)
        .all()
    )

    return StatsResponse(
        total_pendaftar=total,
        status_pending=status_dict.get("pending", 0),
        status_approved=status_dict.get("approved", 0),
        status_rejected=status_dict.get("rejected", 0),
        pendaftar_per_prodi={nama: count for nama, count in prodi_counts},
        pendaftar_per_jalur={nama: count for nama, count in jalur_counts},
    )
