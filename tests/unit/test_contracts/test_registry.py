"""Registry tests: the 17 contracts resolve to schema + model and cross-refs hold."""

from __future__ import annotations

import json

import pytest
import smorx_contracts
from smorx_contracts import (
    CONTRACT_NAMES,
    ContractValidationError,
    UnknownContractError,
    versioning,
)
from smorx_contracts import models as contract_models

EXPECTED_17 = (
    "task",
    "action",
    "tool_invocation",
    "execution_result",
    "failure",
    "evidence",
    "claim",
    "behavioral_object",
    "intent",
    "verification_plan",
    "candidate_patch",
    "behavioral_delta",
    "repair_package",
    "certificate",
    "agent_run",
    "subagent_run",
    "phase_gate",
)


def test_names_are_exactly_the_17_in_order() -> None:
    assert tuple(CONTRACT_NAMES) == EXPECTED_17
    assert list(smorx_contracts.get_registry().names()) == list(EXPECTED_17)
    assert len(set(CONTRACT_NAMES)) == 17


def test_unknown_name_rejected() -> None:
    registry = smorx_contracts.get_registry()
    with pytest.raises(UnknownContractError):
        registry.schema_for("not_a_contract")
    with pytest.raises(UnknownContractError):
        registry.validate("not_a_contract", {})
    with pytest.raises(UnknownContractError):
        smorx_contracts.validate_contract("not_a_contract", {})
    with pytest.raises(UnknownContractError):
        smorx_contracts.sample_instance("not_a_contract")


def test_every_name_resolves_to_schema_and_model() -> None:
    registry = smorx_contracts.get_registry()
    for name in CONTRACT_NAMES:
        schema = registry.schema_for(name)
        assert schema["title"] == name
        assert schema["type"] == "object"
        assert versioning.validate_version(schema["version"])
        assert "id" in schema["required"]
        assert "version" in schema["required"]
        assert name in contract_models.CONTRACT_MODELS


def test_schema_for_is_json_serializable() -> None:
    registry = smorx_contracts.get_registry()
    for name in CONTRACT_NAMES:
        payload = json.loads(json.dumps(registry.schema_for(name)))
        assert payload["title"] == name


def test_schema_for_returns_copy_not_cached_mutable() -> None:
    registry = smorx_contracts.get_registry()
    first = registry.schema_for("task")
    first["properties"]["id"]["description"] = "tampered"
    second = registry.schema_for("task")
    assert second["properties"]["id"]["description"] != "tampered"


def test_schemas_and_models_are_in_sync() -> None:
    registry = smorx_contracts.get_registry()
    for name in CONTRACT_NAMES:
        schema_props = set(registry.schema_for(name)["properties"])
        model_fields = set(contract_models.CONTRACT_MODELS[name].model_fields)
        assert schema_props == model_fields, f"drift on {name}"


def test_get_registry_is_singleton() -> None:
    assert smorx_contracts.get_registry() is smorx_contracts.get_registry()


def test_evidence_without_claim_rejected() -> None:
    registry = smorx_contracts.get_registry()
    valid = smorx_contracts.sample_instance("evidence")
    with pytest.raises(ContractValidationError):
        registry.validate(
            "evidence", {k: v for k, v in valid.items() if k != "claim_id"}
        )


def test_evidence_with_claim_passes() -> None:
    registry = smorx_contracts.get_registry()
    assert (
        registry.validate("evidence", smorx_contracts.sample_instance("evidence"))
        is True
    )
    stripped = {
        k: v
        for k, v in smorx_contracts.sample_instance("evidence").items()
        if k != "claim_id"
    }
    assert (
        smorx_contracts.validate_contract(
            "evidence", {"claim_id": "AUTH-017", **stripped}
        )
        is True
    )


def test_certificate_without_verification_evidence_rejected() -> None:
    registry = smorx_contracts.get_registry()
    valid = smorx_contracts.sample_instance("certificate")
    stripped = {k: v for k, v in valid.items() if k != "verification_evidence_ids"}
    stripped["verification_evidence_ids"] = []
    with pytest.raises(ContractValidationError):
        registry.validate("certificate", stripped)
    without = {k: v for k, v in valid.items() if k != "verification_evidence_ids"}
    with pytest.raises(ContractValidationError):
        registry.validate("certificate", without)


def test_certificate_without_commit_or_delta_rejected() -> None:
    registry = smorx_contracts.get_registry()
    valid = smorx_contracts.sample_instance("certificate")
    for field in ("commit", "behavioral_delta_id", "change_id"):
        stripped = {k: v for k, v in valid.items() if k != field}
        with pytest.raises(ContractValidationError):
            registry.validate("certificate", stripped)


def test_certificate_complete_passes() -> None:
    registry = smorx_contracts.get_registry()
    assert (
        registry.validate("certificate", smorx_contracts.sample_instance("certificate"))
        is True
    )


def test_tool_invocation_may_carry_valid_execution_result() -> None:
    registry = smorx_contracts.get_registry()
    invocation = smorx_contracts.sample_instance("tool_invocation")
    invocation["execution_result"] = smorx_contracts.sample_instance("execution_result")
    assert registry.validate("tool_invocation", invocation) is True


def test_tool_invocation_rejects_malformed_execution_result() -> None:
    registry = smorx_contracts.get_registry()
    invocation = smorx_contracts.sample_instance("tool_invocation")
    bad_result = smorx_contracts.sample_instance("execution_result")
    del bad_result["exit_code"]
    invocation["execution_result"] = bad_result
    with pytest.raises(ContractValidationError):
        registry.validate("tool_invocation", invocation)


def test_consequential_event_is_not_a_master_contract() -> None:
    assert "consequential_event" not in CONTRACT_NAMES
