"""ContractRegistry — validation, schema resolution, and demo samples.

The registry enforces exactly the 17 master contracts declared in
``smorx_contracts.models``. Every contract name must resolve to a JSON Schema
file under ``packages/contracts/schemas/`` and to a pydantic v2 model. It also
enforces the mandatory cross-references (ADR-0002 §Verification):

- ``evidence`` must reference a claim (and may carry related task/run/artifact);
- ``certificate`` must reference verification evidence, a change identity, a
  commit, and a behavioral delta;
- ``tool_invocation`` must reference an action and may carry an embedded
  ``execution_result`` (validated against the ``execution_result`` model).

Unknown names are rejected with a clear error. Validation raises
``ContractValidationError`` for invalid instances and ``UnknownContractError``
for unknown names; both derive from ``ValueError``.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models import CONTRACT_MODELS, CONTRACT_NAMES, ExecutionResult, VersionedModel

_DEFAULT_SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent / "schemas"


class ContractError(ValueError):
    """Base error for the contract registry."""


class UnknownContractError(ContractError):
    """Raised when a contract name is not one of the 17 master contracts."""


class ContractValidationError(ContractError):
    """Raised when a contract instance fails model or cross-reference validation."""


SAMPLES: dict[str, dict[str, Any]] = {
    "task": {
        "id": "task-0184",
        "version": "1.0.0",
        "title": "Restore tenant isolation on payments API",
        "change_id": "Change #184",
        "repository": "payments-api",
        "objective": "Prevent cross-tenant data access after session reuse.",
        "status": "EXECUTING",
        "acceptance_criteria": [
            "ghost-221 replay PASS",
            "adversarial tenant switch PASS",
        ],
        "constraints": ["no shared mutable tenant context"],
        "created_at": "2026-09-13T09:00:00Z",
    },
    "action": {
        "id": "action-0001",
        "version": "1.0.0",
        "agent_run_id": "run-0001",
        "action_type": "INSPECT",
        "rationale": "Inspect repository before modifying",
        "target": "apps/api/app/deps.py",
        "expected_result": "Recorded reason for auth dependency",
        "performed_at": "2026-09-13T09:05:00Z",
    },
    "tool_invocation": {
        "id": "tool-inv-0007",
        "version": "1.0.0",
        "action_id": "action-0001",
        "invocation_id": "inv-0007",
        "tool_name": "repository.inspect",
        "tool_type": "REPOSITORY",
        "arguments": {"path": "apps/api/app/deps.py"},
        "executed_at": "2026-09-13T09:05:12Z",
    },
    "execution_result": {
        "id": "exec-0007",
        "version": "1.0.0",
        "tool_invocation_id": "inv-0007",
        "command": "python -m pytest tests/unit/test_tenant_isolation.py -q",
        "working_directory": "/workspace/payments-api",
        "exit_code": 1,
        "stdout": "1 failed, 4 passed",
        "stderr": "assert session.token != victim.token",
        "duration_seconds": 42.5,
        "started_at": "2026-09-13T09:06:00Z",
        "finished_at": "2026-09-13T09:06:42Z",
        "environment": {"backend": "sqlite", "python": "3.11"},
    },
    "failure": {
        "id": "failure-f-183",
        "version": "1.0.0",
        "failure_id": "F-183",
        "classification": "unit-test failure",
        "summary": "test_auth_tenant_isolation fails when session is reused",
        "observed_at": "2026-09-13T09:06:43Z",
        "evidence": "exec-0007 (exit_code=1)",
        "probable_cause": "tenant context not reset between requests",
        "next_action": "Isolate tenant context per request",
        "related_execution": "inv-0007",
        "related_change_id": "Change #184",
    },
    "evidence": {
        "id": "evidence-0001",
        "version": "1.0.0",
        "claim_id": "AUTH-017",
        "evidence_type": "TEST_RESULT",
        "source": "pytest tests/unit/test_tenant_isolation.py",
        "timestamp": "2026-09-13T09:06:43Z",
        "provenance": "exec-0007 -> inv-0007 -> action-0001",
        "related_task_id": "task-0184",
        "related_run_id": "run-0001",
        "related_artifact": "tests/unit/test_tenant_isolation.py",
        "machine_result": {"exit_code": 1, "passed": 4, "failed": 1},
        "hash": "sha256:abc123",
    },
    "claim": {
        "id": "claim-auth-017",
        "version": "1.0.0",
        "claim_id": "AUTH-017",
        "statement": "Tenant isolation must prevent cross-tenant data access.",
        "authority": "payments-api architecture",
        "confidence": 0.9,
        "status": "PROTECTED",
        "locked": True,
        "created_at": "2026-09-13T08:00:00Z",
        "evidence_ids": ["evidence-0001"],
    },
    "behavioral_object": {
        "id": "ghost-0221",
        "version": "1.0.0",
        "object_type": "GHOST",
        "name": "Ghost #221",
        "status": "ACTIVE",
        "description": "Cross-tenant data leak reappears when session is reused",
        "claim_ids": ["AUTH-017"],
        "repository": "payments-api",
        "created_at": "2026-09-13T07:30:00Z",
    },
    "intent": {
        "id": "intent-0001",
        "version": "1.0.0",
        "intent_type": "REPLACE",
        "description": "Replace per-request tenant context with scoped middleware",
        "change_id": "Change #184",
        "status": "LOCKED",
        "locked": True,
        "created_at": "2026-09-13T08:10:00Z",
    },
    "verification_plan": {
        "id": "vp-0001",
        "version": "1.0.0",
        "title": "Tenant isolation verification plan",
        "claim_ids": ["AUTH-017"],
        "modalities": [
            "STATIC_ANALYSIS",
            "HISTORICAL_GHOST_REPLAY",
            "ADVERSARIAL_SCENARIO",
        ],
        "status": "LOCKED",
        "locked": True,
        "created_at": "2026-09-13T08:20:00Z",
    },
    "candidate_patch": {
        "id": "patch-0001",
        "version": "1.0.0",
        "change_id": "Change #184",
        "candidate_number": 1,
        "sandbox_id": "sandbox-001",
        "commit": "abc1234",
        "status": "CANDIDATE",
        "description": "Introduce scoped tenant context middleware",
        "verification_plan_id": "vp-0001",
        "files": ["apps/api/app/deps.py", "apps/api/app/main.py"],
        "applied_at": "2026-09-13T09:10:00Z",
    },
    "behavioral_delta": {
        "id": "delta-0001",
        "version": "1.0.0",
        "change_id": "Change #184",
        "candidate_patch_id": "patch-0001",
        "classification": "ALTERED",
        "claim_id": "AUTH-017",
        "authorized": None,
        "intent_alignment": "PENDING",
        "observed_at": "2026-09-13T09:30:00Z",
        "evidence_ids": ["evidence-0001"],
    },
    "repair_package": {
        "id": "repair-0001",
        "version": "1.0.0",
        "failure_id": "F-183",
        "expected_behavior": "Tenant context resets per request",
        "observed_behavior": "Tenant context leaks across requests",
        "affected_claim_id": "AUTH-017",
        "evidence_ids": ["evidence-0001"],
        "suspected_path": "apps/api/app/deps.py",
        "required_outcome": "AUTH-017 verification evidence PASS",
        "acceptance_criteria": [
            "ghost replay PASS",
            "adversarial tenant switch PASS",
        ],
        "constraints": ["no persistence of tenant context in session"],
        "created_at": "2026-09-13T09:35:00Z",
    },
    "certificate": {
        "id": "cert-0001",
        "version": "1.0.0",
        "certificate_id": "CERT-0184",
        "change_id": "Change #184",
        "commit": "def5678",
        "behavioral_delta_id": "delta-0001",
        "verification_evidence_ids": ["evidence-0002", "evidence-0003"],
        "intent_ledger_id": "intent-0001",
        "protected_behaviors": ["AUTH-017"],
        "candidate_patch_id": "patch-0002",
        "environment": {"sandbox": "sandbox-002", "backend": "sqlite"},
        "dependency_state": {"pip-audit": "clean"},
        "status": "DRAFT",
        "certificate_hash": "sha256:cert-0184",
        "evidence_traversal": [
            "cert-0001 -> delta-0001 -> exec-0007 -> AUTH-017",
        ],
        "issued_at": "2026-09-13T10:00:00Z",
    },
    "agent_run": {
        "id": "run-0001",
        "version": "1.0.0",
        "role": "CODING",
        "assignment_id": "assign-0001",
        "status": "COMPLETED",
        "phase": "8",
        "summary": "Produced patch-0001 for Change #184",
        "started_at": "2026-09-13T09:03:00Z",
        "finished_at": "2026-09-13T09:12:00Z",
    },
    "subagent_run": {
        "id": "sub-run-0001",
        "version": "1.0.0",
        "agent_run_id": "run-0001",
        "capability": "CODING",
        "assignment_id": "assign-0002",
        "status": "COMPLETED",
        "started_at": "2026-09-13T09:04:00Z",
        "finished_at": "2026-09-13T09:11:00Z",
        "result_summary": "Returned candidate patch candidate_number=1",
        "evidence_ids": ["evidence-0001"],
    },
    "phase_gate": {
        "id": "gate-0001",
        "version": "1.0.0",
        "phase": "0",
        "status": "PASS",
        "checks": [
            {"name": "contracts", "passed": True, "detail": "all 17 contracts validated"},
        ],
        "started_at": "2026-09-13T09:00:00Z",
        "finished_at": "2026-09-13T09:01:00Z",
        "evidence": {"contracts": "all 17 contracts validated"},
    },
}


def _is_missing(value: Any) -> bool:
    return value is None or value == "" or value == []


def _describe_reference(name: str, field: str) -> str:
    labels = {
        "change_id": "a change identity",
        "commit": "a commit",
        "behavioral_delta_id": "a behavioral delta",
        "verification_evidence_ids": "verification evidence",
        "claim_id": "a claim",
    }
    return f"{name} must reference {labels.get(field, field)} ({field})"


class ContractRegistry:
    """Deterministic registry over exactly the 17 master contracts."""

    def __init__(self, schema_dir: Path | str | None = None) -> None:
        self._schema_dir = Path(schema_dir) if schema_dir is not None else _DEFAULT_SCHEMA_DIR
        missing_files = {
            name
            for name in CONTRACT_NAMES
            if not (self._schema_dir / f"{name}.schema.json").is_file()
        }
        if missing_files:
            listed = ", ".join(sorted(missing_files))
            raise ContractError(f"missing schema files in {self._schema_dir}: {listed}")
        self._schemas: dict[str, dict[str, Any]] = {
            name: self._load_schema(name) for name in CONTRACT_NAMES
        }
        self._models: dict[str, type[VersionedModel]] = dict(CONTRACT_MODELS)
        if set(self._models) != set(CONTRACT_NAMES):
            raise ContractError("CONTRACT_MODELS and CONTRACT_NAMES are out of sync")

    def _load_schema(self, name: str) -> dict[str, Any]:
        path = self._schema_dir / f"{name}.schema.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:  # pragma: no cover - guarded at construction
            raise ContractError(f"cannot read schema for {name!r}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ContractError(f"invalid JSON in schema for {name!r}: {exc}") from exc

    def _model_for(self, name: str) -> type[VersionedModel]:
        try:
            return self._models[name]
        except KeyError as exc:
            known = ", ".join(CONTRACT_NAMES)
            raise UnknownContractError(
                f"unknown contract {name!r}; expected one of: {known}"
            ) from exc

    def names(self) -> list[str]:
        """Return exactly the 17 master contract names, in registry order."""
        return list(CONTRACT_NAMES)

    def schema_for(self, name: str) -> dict[str, Any]:
        """Return the JSON Schema dict for a contract (cached, JSON-serializable)."""
        self._model_for(name)
        return copy.deepcopy(self._schemas[name])

    def validate(self, name: str, instance: Mapping[str, Any]) -> bool:
        """Validate ``instance`` against the pydantic model and cross-references.

        Raises ``UnknownContractError`` for unknown names and
        ``ContractValidationError`` for invalid instances.
        """
        model = self._model_for(name)
        try:
            validated = model.model_validate(dict(instance))
        except ValidationError as exc:
            raise ContractValidationError(
                f"contract {name!r} instance is invalid: {exc}"
            ) from exc
        self._check_cross_references(name, validated)
        return True

    def _check_cross_references(self, name: str, validated: VersionedModel) -> None:
        if name == "evidence":
            claim_id = getattr(validated, "claim_id", None)
            if _is_missing(claim_id):
                raise ContractValidationError(_describe_reference("evidence", "claim_id"))
            return
        if name == "certificate":
            missing = [
                field
                for field in (
                    "change_id",
                    "commit",
                    "behavioral_delta_id",
                    "verification_evidence_ids",
                )
                if _is_missing(getattr(validated, field, None))
            ]
            if missing:
                details = "; ".join(_describe_reference("certificate", field) for field in missing)
                raise ContractValidationError(details)
            return
        if name == "tool_invocation":
            execution_result = getattr(validated, "execution_result", None)
            if execution_result is not None:
                try:
                    ExecutionResult.model_validate(execution_result.model_dump())
                except ValidationError as exc:
                    raise ContractValidationError(
                        "tool_invocation.execution_result is not a valid "
                        f"execution_result: {exc}"
                    ) from exc


_registry: ContractRegistry | None = None


def get_registry() -> ContractRegistry:
    """Return the process-wide singleton ``ContractRegistry``."""
    global _registry
    if _registry is None:
        _registry = ContractRegistry()
    return _registry


def sample_instance(name: str) -> dict[str, Any]:
    """Return a realistic minimal valid instance for a contract (deep copy)."""
    if name not in CONTRACT_NAMES:
        known = ", ".join(CONTRACT_NAMES)
        raise UnknownContractError(
            f"unknown contract {name!r}; expected one of: {known}"
        )
    return copy.deepcopy(SAMPLES[name])
