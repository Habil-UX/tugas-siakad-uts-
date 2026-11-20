from typing import List
from sqlalchemy.orm import Session

from app.models import KRS, KRSDetail, KrsTransition
from app.services.krs_state_machine import Actor, KRSStateMachine, KRSStatus


class KRSInvalidator:
    """
    Layanan invalidasi KRS otomatis ketika jadwal kuliah berubah.
    Mendukung transisi Actor.SISTEM menuju REVISION untuk KRS terdampak
    maupun penandaan needs_review = True beserta pencatatan KrsTransition.
    """

    def __init__(self, db: Session):
        self.db = db

    def invalidate_by_matakuliah(
        self,
        matakuliah_id: int,
        force_transition_to_revision: bool = False,
    ) -> List[KRS]:
        affected = (
            self.db.query(KRS)
            .join(KRSDetail)
            .filter(KRSDetail.matakuliah_id == matakuliah_id)
            .all()
        )

        for krs in affected:
            old_status = krs.status
            if force_transition_to_revision and KRSStateMachine.can_transition(
                old_status, KRSStatus.REVISION, actor=Actor.SISTEM
            ):
                new_status = KRSStateMachine.transition(
                    old_status, KRSStatus.REVISION, actor=Actor.SISTEM
                )
                krs.status = new_status
                krs.needs_review = True
                if isinstance(self.db, Session) and getattr(krs, "id", None) is not None:
                    self.db.add(
                        KrsTransition(
                            krs_id=krs.id,
                            from_status=old_status,
                            to_status=new_status,
                            changed_by=Actor.SISTEM.value,
                        )
                    )
            elif krs.status != "APPROVED":
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
