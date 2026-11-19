from typing import Optional

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import JadwalKuliah
from app.services.conflict_detector import detect_all_schedule_conflicts
from app.services.rescheduling_service import ReschedulingService
from app.services.scheduling_service import SchedulingService
from app.utils.security import require_roles

router = APIRouter(prefix="/api/schedules", tags=["Scheduling"])


@router.post("")
def create_jadwal(
    data: dict,
    db: Session = Depends(get_db),
    _user: Optional[dict] = Depends(require_roles(["admin"])),
):
    service = SchedulingService(db)
    return service.create_schedule(data)


@router.get("")
def get_all_jadwal(db: Session = Depends(get_db)):
    return db.query(JadwalKuliah).all()


@router.get("/conflicts")
def get_schedule_conflicts(db: Session = Depends(get_db)):
    schedules = db.query(JadwalKuliah).all()
    conflicts = detect_all_schedule_conflicts(schedules)
    return {
        "total_jadwal": len(schedules),
        "total_konflik": len(conflicts),
        "conflicts": conflicts,
    }


@router.put("/{id}")
def update_jadwal(
    id: int = Path(ge=1),
    data: dict = ...,
    db: Session = Depends(get_db),
    _user: Optional[dict] = Depends(require_roles(["admin"])),
):
    service = SchedulingService(db)
    return service.update_schedule(id, data)


@router.delete("/{id}")
def delete_jadwal(
    id: int = Path(ge=1),
    db: Session = Depends(get_db),
    _user: Optional[dict] = Depends(require_roles(["admin"])),
):
    service = SchedulingService(db)
    return service.delete_schedule(id)


@router.post("/{id}/suggestions")
def get_suggestions(id: int, db: Session = Depends(get_db)):
    service = ReschedulingService(db, SchedulingService(db))
    return service.suggest_alternatives(id)
