import pytest
from fastapi import HTTPException
from app.services.krs_state_machine import KRSStateMachine, KRSStatus


def test_legal_transition_draft_to_submitted():
    new_status = KRSStateMachine.transition("DRAFT", KRSStatus.SUBMITTED)
    assert new_status == "SUBMITTED"


def test_legal_transition_submitted_to_approved():
    new_status = KRSStateMachine.transition("SUBMITTED", KRSStatus.APPROVED)
    assert new_status == "APPROVED"


def test_illegal_transition_draft_to_approved():
    with pytest.raises(HTTPException) as excinfo:
        KRSStateMachine.transition("DRAFT", KRSStatus.APPROVED)
    assert excinfo.value.status_code == 400
    assert "Transisi ilegal" in excinfo.value.detail


def test_illegal_transition_approved_to_draft():
    with pytest.raises(HTTPException) as excinfo:
        KRSStateMachine.transition("APPROVED", KRSStatus.DRAFT)
    assert excinfo.value.status_code == 400


def test_unknown_krs_status():
    with pytest.raises(HTTPException) as excinfo:
        KRSStateMachine.transition(
            "UNKNOWN_STATUS",
            KRSStatus.SUBMITTED,
        )
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == (
        "Status KRS tidak dikenal: UNKNOWN_STATUS"
    )


@pytest.mark.parametrize(
    "current_status,target_status",
    [
        ("DRAFT", KRSStatus.SUBMITTED),
        ("SUBMITTED", KRSStatus.APPROVED),
        ("SUBMITTED", KRSStatus.REVISION),
        ("REVISION", KRSStatus.SUBMITTED),
    ],
)
def test_all_legal_transitions_parametrized(current_status, target_status):
    assert KRSStateMachine.transition(current_status, target_status) == target_status.value


@pytest.mark.parametrize(
    "current_status,target_status",
    [
        ("DRAFT", KRSStatus.DRAFT),
        ("DRAFT", KRSStatus.APPROVED),
        ("DRAFT", KRSStatus.REVISION),
        ("SUBMITTED", KRSStatus.DRAFT),
        ("SUBMITTED", KRSStatus.SUBMITTED),
        ("APPROVED", KRSStatus.DRAFT),
        ("APPROVED", KRSStatus.SUBMITTED),
        ("APPROVED", KRSStatus.APPROVED),
        ("APPROVED", KRSStatus.REVISION),
        ("REVISION", KRSStatus.DRAFT),
        ("REVISION", KRSStatus.APPROVED),
        ("REVISION", KRSStatus.REVISION),
    ],
)
def test_all_12_illegal_transitions_parametrized(current_status, target_status):
    with pytest.raises(HTTPException) as excinfo:
        KRSStateMachine.transition(current_status, target_status)
    assert excinfo.value.status_code == 400
    assert "Transisi ilegal" in excinfo.value.detail
