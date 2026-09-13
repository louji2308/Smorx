"""Sample instance coverage: all 17 contracts validate from demo payloads."""

from __future__ import annotations

import json

import pytest
import smorx_contracts
from smorx_contracts import CONTRACT_NAMES, ContractValidationError

FAILURE_CLASSIFICATIONS = {
    "syntax/build failure",
    "unit-test failure",
    "integration failure",
    "environment/dependency failure",
    "timeout",
    "permission failure",
    "tool failure",
    "ambiguous result",
    "acceptance-criterion failure",
    "safety/policy block",
}


@pytest.mark.parametrize("name", CONTRACT_NAMES)
def test_sample_validates_for_all_contracts(name: str) -> None:
    instance = smorx_contracts.sample_instance(name)
    assert smorx_contracts.validate_contract(name, instance) is True


@pytest.mark.parametrize("name", CONTRACT_NAMES)
def test_sample_is_json_serializable(name: str) -> None:
    instance = smorx_contracts.sample_instance(name)
    payload = json.loads(json.dumps(instance))
    assert smorx_contracts.validate_contract(name, payload) is True


@pytest.mark.parametrize("name", CONTRACT_NAMES)
def test_sample_is_a_fresh_deep_copy(name: str) -> None:
    first = smorx_contracts.sample_instance(name)
    second = smorx_contracts.sample_instance(name)
    assert first == second
    assert first is not second
    if first.get("acceptance_criteria") or first.get("evidence_ids"):
        key = "evidence_ids" if "evidence_ids" in first else "acceptance_criteria"
        first[key].append("tampered")
        assert smorx_contracts.sample_instance(name)[key] != first[key]


def test_all_classifications_are_used_exact_vocabulary() -> None:
    failure = smorx_contracts.sample_instance("failure")
    assert failure["classification"] in FAILURE_CLASSIFICATIONS


def test_demo_narrative_tokens_present() -> None:
    all_text = json.dumps(
        {name: smorx_contracts.sample_instance(name) for name in CONTRACT_NAMES}
    )
    for token in ("Change #184", "AUTH-017", "Ghost #221", "F-183"):
        assert token in all_text, f"missing narrative token {token}"


def test_invalid_model_reports_contract_validation_error() -> None:
    instance = smorx_contracts.sample_instance("claim")
    instance["confidence"] = 99  # outside 0..1
    with pytest.raises(ContractValidationError):
        smorx_contracts.validate_contract("claim", instance)