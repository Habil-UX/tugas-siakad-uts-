from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.grade import GradeCreate, GradeUpdate
from app.services.grade_service import GradeService
from app.services.transcript_service import TranscriptService
from app.utils.pdf_generator import generate_transcript_pdf
from app.utils.security import require_roles

router = APIRouter(
    prefix="/api/grades",
    tags=["Grade Management"],
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
