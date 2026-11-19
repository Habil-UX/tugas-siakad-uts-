
from enum import Enum
from fastapi import HTTPException


class KRSStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REVISION = "REVISION"


class KRSStateMachine:

    ALLOWED_TRANSITIONS = {
        KRSStatus.DRAFT: [
            KRSStatus.SUBMITTED
        ],
        KRSStatus.SUBMITTED: [
            KRSStatus.APPROVED,
            KRSStatus.REVISION
        ],
        KRSStatus.APPROVED: [],
        KRSStatus.REVISION: [
            KRSStatus.SUBMITTED
        ]
    }

    @staticmethod
    def transition(current_status: str, target_status: KRSStatus):

        try:
            current = KRSStatus(current_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Status KRS tidak dikenal: {current_status}"
            )

        if target_status not in KRSStateMachine.ALLOWED_TRANSITIONS[current]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Transisi ilegal dari {current.value} "
                    f"ke {target_status.value}"
                )
            )

        return target_status.value
