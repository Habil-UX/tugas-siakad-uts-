from enum import Enum
from typing import Optional
from fastapi import HTTPException


class KRSStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REVISION = "REVISION"


class Actor(str, Enum):
    MAHASISWA = "MAHASISWA"
    DOSEN_PA = "DOSEN_PA"
    SISTEM = "SISTEM"


class KRSStateMachine:

    ALLOWED_TRANSITIONS = {
        KRSStatus.DRAFT: [
            KRSStatus.SUBMITTED,
        ],
        KRSStatus.SUBMITTED: [
            KRSStatus.APPROVED,
            KRSStatus.REVISION,
        ],
        KRSStatus.APPROVED: [],
        KRSStatus.REVISION: [
            KRSStatus.SUBMITTED,
        ],
    }

    # 6 transisi legal berbasis Actor (dari total 4 x 4 x 3 = 48 kombinasi -> 42 kombinasi ilegal)
    ALLOWED_ACTOR_TRANSITIONS = {
        (KRSStatus.DRAFT, KRSStatus.SUBMITTED, Actor.MAHASISWA),
        (KRSStatus.REVISION, KRSStatus.SUBMITTED, Actor.MAHASISWA),
        (KRSStatus.SUBMITTED, KRSStatus.APPROVED, Actor.DOSEN_PA),
        (KRSStatus.SUBMITTED, KRSStatus.REVISION, Actor.DOSEN_PA),
        (KRSStatus.SUBMITTED, KRSStatus.REVISION, Actor.SISTEM),
        (KRSStatus.APPROVED, KRSStatus.REVISION, Actor.SISTEM),
    }

    @staticmethod
    def can_transition(
        current_status: str | KRSStatus,
        target_status: str | KRSStatus,
        actor: Optional[str | Actor] = None,
    ) -> bool:
        try:
            current = KRSStatus(current_status)
            target = KRSStatus(target_status)
        except ValueError:
            return False

        if actor is not None:
            try:
                act = Actor(actor)
            except ValueError:
                return False
            return (current, target, act) in KRSStateMachine.ALLOWED_ACTOR_TRANSITIONS

        return target in KRSStateMachine.ALLOWED_TRANSITIONS.get(current, [])

    @staticmethod
    def transition(
        current_status: str | KRSStatus,
        target_status: KRSStatus | str,
        actor: Optional[Actor | str] = None,
    ) -> str:
        try:
            current = KRSStatus(current_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Status KRS tidak dikenal: {current_status}",
            )

        try:
            target = KRSStatus(target_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Target status KRS tidak dikenal: {target_status}",
            )

        if actor is not None:
            try:
                act = Actor(actor)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Actor tidak dikenal: {actor}",
                )
            if (current, target, act) not in KRSStateMachine.ALLOWED_ACTOR_TRANSITIONS:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Transisi ilegal dari {current.value} "
                        f"ke {target.value} oleh {act.value}"
                    ),
                )
            return target.value

        if target not in KRSStateMachine.ALLOWED_TRANSITIONS[current]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Transisi ilegal dari {current.value} "
                    f"ke {target.value}"
                ),
            )

        return target.value
