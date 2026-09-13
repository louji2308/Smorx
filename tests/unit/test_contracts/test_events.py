"""Structured consequential event (§2.4) tests."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from smorx_contracts import ConsequentialEvent

CONFORMING_EVENT: dict = {
    "event_type": "RESULT_OBSERVED",
    "occurred_at": "2026-09-13T09:06:42Z",
    "trace_id": "trace-0184",
    "payload": {"tool_invocation_id": "inv-0007", "exit_code": 1},
    "related_task_id": "task-0184",
    "related_run_id": "run-0001",
    "related_claim_id": "AUTH-017",
    "related_certificate_id": "cert-0001",
}


def test_conforming_event_accepted() -> None:
    event = ConsequentialEvent.model_validate(CONFORMING_EVENT)
    assert event.event_type == "RESULT_OBSERVED"
    assert event.trace_id == "trace-0184"
    assert event.payload["exit_code"] == 1


def test_event_round_trips_through_json() -> None:
    event = ConsequentialEvent.model_validate(CONFORMING_EVENT)
    restored = ConsequentialEvent.model_validate_json(event.model_dump_json())
    assert restored.model_dump() == event.model_dump()


def test_bad_event_type_rejected() -> None:
    bad = {**CONFORMING_EVENT, "event_type": "NOT_A_REAL_EVENT"}
    with pytest.raises(ValidationError):
        ConsequentialEvent.model_validate(bad)


def test_missing_occurred_at_rejected() -> None:
    bad = {k: v for k, v in CONFORMING_EVENT.items() if k != "occurred_at"}
    with pytest.raises(ValidationError):
        ConsequentialEvent.model_validate(bad)


def test_missing_trace_id_rejected() -> None:
    bad = {k: v for k, v in CONFORMING_EVENT.items() if k != "trace_id"}
    with pytest.raises(ValidationError):
        ConsequentialEvent.model_validate(bad)


def test_missing_payload_rejected() -> None:
    bad = {k: v for k, v in CONFORMING_EVENT.items() if k != "payload"}
    with pytest.raises(ValidationError):
        ConsequentialEvent.model_validate(bad)


def test_unknown_top_level_field_rejected() -> None:
    with pytest.raises(ValidationError):
        ConsequentialEvent.model_validate({**CONFORMING_EVENT, "extra": True})


@pytest.mark.parametrize(
    "event_type",
    [
        "TASK_RECEIVED",
        "REPOSITORY_INSPECTED",
        "PLAN_GENERATED",
        "SANDBOX_CREATED",
        "ACTION_EXECUTED",
        "RESULT_OBSERVED",
        "FAILURE_CLASSIFIED",
        "PATCH_GENERATED",
        "EVIDENCE_RECORDED",
        "VERIFICATION_RUN",
        "BEHAVIORAL_DELTA",
        "INTENT_ALIGNMENT",
        "REPAIR",
        "REVERIFICATION",
        "CERTIFICATION",
        "MEMORY_UPDATE",
        "MERGE",
        "BLOCKED",
    ],
)
def test_all_event_kinds_accepted(event_type: str) -> None:
    event = ConsequentialEvent.model_validate(
        {**CONFORMING_EVENT, "event_type": event_type}
    )
    assert event.event_type == event_type


def test_occurred_at_parses_as_utc_datetime() -> None:
    event = ConsequentialEvent.model_validate(CONFORMING_EVENT)
    parsed = event.occurred_at_dt()
    assert parsed.tzinfo is not None
    assert parsed.isoformat() == "2026-09-13T09:06:42+00:00"


def test_event_name_is_not_a_master_contract() -> None:
    import smorx_contracts

    assert "consequential_event" not in smorx_contracts.CONTRACT_NAMES


def test_event_payload_is_jsonable() -> None:
    event = ConsequentialEvent.model_validate(CONFORMING_EVENT)
    json.loads(json.dumps(event.model_dump(mode="json")))
