from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.grade import GradeCreate, GradeUpdate
from app.services.grade_service import GradeService
from app.services.transcript_service import TranscriptService
from app.utils.pdf_generator import generate_transcript_pdf, render_transcript_html
from app.utils.security import require_roles

router = APIRouter(
    prefix="/api/grades",
    tags=["Grade Management"],
)

kelas_router = APIRouter(
    prefix="/api/kelas",
    tags=["Grade Management - Kelas"],
)


@kelas_router.put("/{id}/nilai/{nim}")
def put_nilai_kelas(
    id: int = Path(ge=1),
    nim: str = ...,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user: Optional[dict] = Depends(require_roles(["dosen", "admin"])),
):
    service = GradeService(db)
    nilai_huruf = payload.get("nilai_huruf") or payload.get("nilai")
    changed_by = (
        payload.get("changed_by")
        or (user.get("username") if isinstance(user, dict) else None)
        or "DOSEN"
    )
    reason = payload.get("reason", "Input/Update nilai kelas")
    dosen_id = payload.get("dosen_id")
    presensi_persen = payload.get("presensi_persen")
    semester = payload.get("semester")
    return service.set_nilai_kelas(
        kelas_id=id,
        nim=nim,
        nilai_huruf=nilai_huruf,
        dosen_id=dosen_id,
        changed_by=changed_by,
        reason=reason,
        presensi_persen=presensi_persen,
        semester=semester,
    )


@router.post("/input")
def input_grade(
    data: GradeCreate,
    db: Session = Depends(get_db),
    _user: Optional[dict] = Depends(require_roles(["dosen", "admin"])),
):
    service = GradeService(db)
    return service.input_grade(data)


@router.put("/update/{grade_id}")
def update_grade(
    grade_id: int = Path(ge=1),
    data: GradeUpdate = ...,
    db: Session = Depends(get_db),
    _user: Optional[dict] = Depends(require_roles(["dosen", "admin"])),
):
    service = GradeService(db)

    return service.update_grade(
        grade_id=grade_id,
        nilai_huruf=data.nilai_huruf,
        changed_by=data.changed_by,
        reason=data.reason,
    )


@router.get("/history/{nim}")
def get_grade_history(
    nim: str,
    db: Session = Depends(get_db),
):
    service = GradeService(db)
    history = service.get_grade_history(nim)

    return [
        dict(item)
        for item in history
    ]


@router.get("/ips/{nim}/{semester}")
def get_ips(
    nim: str,
    semester: int = Path(ge=1),
    db: Session = Depends(get_db),
):
    service = TranscriptService(db)

    return service.get_ips(
        nim=nim,
        semester=semester,
    )


@router.get("/ipk/{nim}")
def get_ipk(
    nim: str,
    db: Session = Depends(get_db),
):
    service = TranscriptService(db)
    return service.get_ipk(nim)


@router.get("/transcript/{nim}")
def get_transcript(
    nim: str,
    db: Session = Depends(get_db),
):
    service = TranscriptService(db)
    return service.get_transcript(nim)


@router.get("/transcript/{nim}/html", response_class=HTMLResponse)
def view_transcript_html(
    nim: str,
    db: Session = Depends(get_db),
):
    service = TranscriptService(db)
    transcript = service.get_transcript(nim)
    return HTMLResponse(content=render_transcript_html(transcript))


@router.get("/transcript/{nim}/pdf")
def download_transcript_pdf(
    nim: str,
    db: Session = Depends(get_db),
):
    service = TranscriptService(db)
    transcript = service.get_transcript(nim)
    pdf_bytes = generate_transcript_pdf(transcript)
    filename = f"transkrip_{nim}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )
