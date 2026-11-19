from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.krs import (
    CourseAction,
    KRSActorRequest,
    KRSResponse,
    RecommendationResponse,
)
from app.services.krs.validators import PrerequisiteValidator
from app.services.krs_manager import KRSManager
from app.services.krs_recommender import KRSRecommender
from app.utils.security import require_roles

router = APIRouter(prefix="/api/krs", tags=["KRS"])


@router.get("/{nim}")
def get_krs(
    nim: str,
    semester: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
):
    manager = KRSManager(db)
    return manager.get_krs(nim, semester=semester)


@router.get("/explain-prerequisite/{nim}/{matakuliah_id}")
def explain_prerequisite(
    nim: str,
    matakuliah_id: int,
    semester: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    plan = PrerequisiteValidator.explain_prerequisite_query(
        db=db,
        nim=nim,
        matakuliah_id=matakuliah_id,
        krs_semester=semester,
    )
    return {"nim": nim, "matakuliah_id": matakuliah_id, "query_plan": plan}


@router.post("/add", response_model=KRSResponse)
def add_course(
    payload: CourseAction,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(
        require_roles(["mahasiswa", "admin"])
    ),
):
    if (
        current_user
        and current_user.get("role") == "mahasiswa"
        and current_user.get("nim")
        and current_user.get("nim") != payload.nim
    ):
        raise HTTPException(
            status_code=403,
            detail="Mahasiswa hanya dapat mengubah KRS miliknya sendiri",
        )
    manager = KRSManager(db)
    return manager.add_course(payload.nim, payload.kode_mk)


@router.post("/remove", response_model=KRSResponse)
def remove_course(
    payload: CourseAction,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(
        require_roles(["mahasiswa", "admin"])
    ),
):
    if (
        current_user
        and current_user.get("role") == "mahasiswa"
        and current_user.get("nim")
        and current_user.get("nim") != payload.nim
    ):
        raise HTTPException(
            status_code=403,
            detail="Mahasiswa hanya dapat mengubah KRS miliknya sendiri",
        )
    manager = KRSManager(db)
    return manager.remove_course(payload.nim, payload.kode_mk)


@router.get("/validate/{nim}")
def validate_krs(
    nim: str,
    db: Session = Depends(get_db),
):
    manager = KRSManager(db)
    return manager.validate_krs(nim)


@router.post("/submit/{nim}")
def submit_krs(
    nim: str,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(
        require_roles(["mahasiswa", "admin"])
    ),
):
    if (
        current_user
        and current_user.get("role") == "mahasiswa"
        and current_user.get("nim")
        and current_user.get("nim") != nim
    ):
        raise HTTPException(
            status_code=403,
            detail="Mahasiswa hanya dapat mensubmit KRS miliknya sendiri",
        )
    manager = KRSManager(db)
    return manager.submit_krs(nim)


@router.post("/approve/{nim}")
def approve_krs(
    nim: str,
    payload: KRSActorRequest,
    db: Session = Depends(get_db),
    _user: Optional[dict] = Depends(require_roles(["dosen", "admin"])),
):
    actor = payload.nidn_dosen_pa or (
        str(payload.dosen_pa_id) if payload.dosen_pa_id is not None else None
    )
    if not actor:
        raise HTTPException(
            status_code=400,
            detail="nidn_dosen_pa atau dosen_pa_id wajib diisi",
        )
    manager = KRSManager(db)
    return manager.approve_krs(nim=nim, nidn_dosen_pa=actor)


@router.post("/revise/{nim}")
def revise_krs(
    nim: str,
    payload: KRSActorRequest,
    db: Session = Depends(get_db),
    _user: Optional[dict] = Depends(require_roles(["dosen", "admin"])),
):
    actor = payload.nidn_dosen_pa or (
        str(payload.dosen_pa_id) if payload.dosen_pa_id is not None else None
    )
    if not actor:
        raise HTTPException(
            status_code=400,
            detail="nidn_dosen_pa atau dosen_pa_id wajib diisi",
        )
    manager = KRSManager(db)
    return manager.revise_krs(nim=nim, nidn_dosen_pa=actor)


@router.post(
    "/recommend/{nim}",
    response_model=RecommendationResponse,
)
def recommend_krs(
    nim: str,
    db: Session = Depends(get_db),
):
    recommender = KRSRecommender(db)
    try:
        return recommender.generate_recommendation(nim)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )
