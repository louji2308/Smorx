"""Unit tests for the phase 3 agent runtime contracts and capability catalog.

Covers the frozen ``smorx_runtime.agents`` interface (assignment/context
construction, tool-permission matching, result discipline) and the
``smorx_runtime.capabilities`` specialist catalog (enum order, completeness,
phase resolution).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from smorx_runtime.agents import (
    AgentAssignment,
    AgentContext,
    AgentEvidence,
    AgentExecutor,
    AgentExecutorFactory,
    AgentFailure,
    AgentResult,
    AgentSpec,
    assignment_allows_tool,
    validate_result,
)
from smorx_runtime.capabilities import (
    CAPABILITY_CATALOG,
    AgentCapability,
    SpecialistCapability,
    capabilities_for_phase,
    capability_for,
)

FIXED_AT = datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC)

EXPECTED_ORDER = [
    "ARCHAEOLOGY",
    "KNOWLEDGE",
    "INTENT",
    "IMPACT",
    "CODING",
    "VERIFICATION",
    "EVIDENCE",
    "REPAIR",
    "CERTIFICATION",
]


def _context(**overrides: object) -> AgentContext:
    values: dict[str, object] = {
        "run_id": "run-7",
        "phase": "6",
        "task_id": "task-9",
        "correlation_id": "corr-2",
        "repository": "acme/repo",
        "change_id": "change-3",
        "environment": {"SMORX_ENV": "development"},
        "extra": {"seed": 42},
    }
    values.update(overrides)
    return AgentContext(**values)


def _assignment(
    *, allowed_tools: tuple[str, ...] = ("file.", "command.run")
) -> AgentAssignment:
    return AgentAssignment(
        id="assign-1",
        task_id="task-9",
        wave_id="wave-3",
        agent_id="coding-1",
        objective="Implement AUTH-017 fix",
        capability=SpecialistCapability.CODING,
        context=_context(),
        inputs={"expected": 42},
        constraints=("max_iterations=3",),
        allowed_tools=allowed_tools,
        expected_artifact="patch.diff",
        timeout_seconds=300.0,
        created_at=FIXED_AT,
    )


def _result(status: str, **overrides: object) -> AgentResult:
    values: dict[str, object] = {
        "assignment_id": "assign-1",
        "task_id": "task-9",
        "status": status,
        "started_at": FIXED_AT,
        "finished_at": FIXED_AT,
    }
    values.update(overrides)
    return AgentResult(**values)


def _failure() -> AgentFailure:
    return AgentFailure(
        failure_id="failure-1",
        classification="unit-test failure",
        summary="AUTH-017 refresh test fails",
        observed_at=FIXED_AT,
        evidence="trace://run/7",
        probable_cause="missing authorization check",
        next_action="repair token refresh guard",
    )


# -- SpecialistCapability enum -------------------------------------------------


def test_specialist_capability_members_and_values() -> None:
    members = list(SpecialistCapability)
    assert [member.name for member in members] == EXPECTED_ORDER
    assert [member.value for member in members] == EXPECTED_ORDER
    assert len(SpecialistCapability) == 9


def test_specialist_capability_is_str_enum() -> None:
    assert SpecialistCapability.CODING == "CODING"
    assert isinstance(SpecialistCapability.VERIFICATION, str)


# -- Capability catalog ---------------------------------------------------------


def test_capability_catalog_is_complete() -> None:
    assert set(CAPABILITY_CATALOG) == set(SpecialistCapability)
    for capability in SpecialistCapability:
        entry = CAPABILITY_CATALOG[capability]
        assert isinstance(entry, AgentCapability)
        assert entry.capability is capability
        assert entry.description.strip()
        assert entry.allowed_tool_prefixes
        assert all(prefix.strip() for prefix in entry.allowed_tool_prefixes)
        assert isinstance(entry.required_for_phase, tuple)


def test_capability_for_returns_catalog_entry() -> None:
    assert (
        capability_for(SpecialistCapability.CODING)
        is CAPABILITY_CATALOG[SpecialistCapability.CODING]
    )


def test_capability_for_unknown_raises_helpful_key_error() -> None:
    with pytest.raises(KeyError) as excinfo:
        capability_for("NOPE")  # type: ignore[arg-type]
    message = str(excinfo.value)
    assert "NOPE" in message
    assert "CODING" in message
    assert "AVAILABLE:" not in message


def test_capabilities_for_phase_returns_sensible_subset() -> None:
    capabilities = capabilities_for_phase("6")
    assert capabilities
    for capability in capabilities:
        entry = CAPABILITY_CATALOG[capability]
        assert not entry.required_for_phase or "6" in entry.required_for_phase
    assert SpecialistCapability.ARCHAEOLOGY in capabilities
    assert SpecialistCapability.CERTIFICATION not in capabilities
    by_order = tuple(c for c in SpecialistCapability if c in capabilities)
    assert capabilities == by_order


def test_capabilities_for_phase_pulls_phase_specific_roles() -> None:
    coding_phase = capabilities_for_phase("8")
    assert SpecialistCapability.CODING in coding_phase
    assert SpecialistCapability.REPAIR not in coding_phase
    certification_phase = capabilities_for_phase("11")
    assert SpecialistCapability.VERIFICATION in certification_phase
    assert SpecialistCapability.CERTIFICATION in certification_phase


# -- AgentContext / AgentAssignment construction -------------------------------


def test_agent_context_construction_all_fields() -> None:
    context = _context()
    assert context.run_id == "run-7"
    assert context.phase == "6"
    assert context.task_id == "task-9"
    assert context.correlation_id == "corr-2"
    assert context.repository == "acme/repo"
    assert context.change_id == "change-3"
    assert context.environment == {"SMORX_ENV": "development"}
    assert context.extra == {"seed": 42}


def test_agent_context_environment_is_immutable() -> None:
    context = _context()
    with pytest.raises(TypeError):
        context.environment["SMORX_ENV"] = "production"
    with pytest.raises(TypeError):
        context.extra["seed"] = 1


def test_agent_assignment_construction_all_fields() -> None:
    assignment = _assignment()
    assert assignment.id == "assign-1"
    assert assignment.task_id == "task-9"
    assert assignment.wave_id == "wave-3"
    assert assignment.agent_id == "coding-1"
    assert assignment.objective == "Implement AUTH-017 fix"
    assert assignment.capability is SpecialistCapability.CODING
    assert assignment.context.run_id == "run-7"
    assert assignment.inputs == {"expected": 42}
    assert assignment.constraints == ("max_iterations=3",)
    assert assignment.allowed_tools == ("file.", "command.run")
    assert assignment.expected_artifact == "patch.diff"
    assert assignment.timeout_seconds == 300.0
    assert assignment.created_at == FIXED_AT


def test_agent_spec_construction() -> None:
    spec = AgentSpec(
        agent_id="verify-1", name="verify", capability=SpecialistCapability.VERIFICATION
    )
    assert spec.agent_id == "verify-1"
    assert spec.name == "verify"
    assert spec.capability is SpecialistCapability.VERIFICATION
    assert spec.replacement_weight == 1


# -- assignment_allows_tool ----------------------------------------------------


def test_assignment_allows_tool_exact_match() -> None:
    assignment = _assignment(allowed_tools=("file.", "command.run"))
    assert assignment_allows_tool(assignment, "command.run") is True


def test_assignment_allows_tool_prefix_match() -> None:
    assignment = _assignment(allowed_tools=("file.", "command.run"))
    assert assignment_allows_tool(assignment, "file.read") is True
    assert assignment_allows_tool(assignment, "file.write") is True


def test_assignment_allows_tool_no_match() -> None:
    assignment = _assignment(allowed_tools=("file.", "command.run"))
    assert assignment_allows_tool(assignment, "repository.inspect") is False
    assert assignment_allows_tool(assignment, "command.shell") is False
    assert assignment_allows_tool(assignment, "test.run") is False
    assert assignment_allows_tool(assignment, "file") is False


def test_assignment_allows_tool_empty_allowed_tools() -> None:
    assignment = _assignment(allowed_tools=())
    assert assignment_allows_tool(assignment, "file.read") is False
    assert assignment_allows_tool(assignment, "command.run") is False


# -- validate_result -----------------------------------------------------------


def test_validate_result_succeeded_without_evidence() -> None:
    result = _result("SUCCEEDED")
    issues = validate_result(result)
    assert "SUCCEEDED without evidence" in issues


def test_validate_result_succeeded_with_failures() -> None:
    result = _result(
        "SUCCEEDED", failures=(_failure(),), execution_references=("exec://run/7",)
    )
    issues = validate_result(result)
    assert "SUCCEEDED with failures" in issues


def test_validate_result_valid_succeeded_with_execution_reference() -> None:
    result = _result("SUCCEEDED", execution_references=("exec://run/7",))
    assert validate_result(result) == ()


def test_validate_result_valid_succeeded_with_evidence() -> None:
    evidence = AgentEvidence(
        evidence_id="e-1", source="nebius-sandbox-1", timestamp=FIXED_AT
    )
    result = _result("SUCCEEDED", evidence=(evidence,))
    assert validate_result(result) == ()


def test_validate_result_failed_without_failure_record() -> None:
    result = _result("FAILED")
    issues = validate_result(result)
    assert "FAILED without failure record" in issues


def test_validate_result_valid_failed() -> None:
    result = _result("FAILED", failures=(_failure(),))
    assert validate_result(result) == ()


def test_validate_result_blocked_needs_no_evidence_or_failure() -> None:
    result = _result("BLOCKED")
    assert validate_result(result) == ()


def test_validate_result_finished_at_before_started_at() -> None:
    later_at = datetime(2026, 9, 13, 13, 0, 0, tzinfo=UTC)
    result = _result(
        "SUCCEEDED",
        execution_references=("exec://run/7",),
        started_at=later_at,
        finished_at=FIXED_AT,
    )
    issues = validate_result(result)
    assert "finished_at before started_at" in issues


def _raw_result(**values: object) -> AgentResult:
    """Build an AgentResult bypassing construction validation (defensive-branch test)."""
    result = object.__new__(AgentResult)
    for name, value in values.items():
        object.__setattr__(result, name, value)
    return result


def test_validate_result_confidence_out_of_range_is_issue() -> None:
    result = _raw_result(
        assignment_id="assign-1",
        task_id="task-9",
        status="SUCCEEDED",
        started_at=FIXED_AT,
        finished_at=FIXED_AT,
        execution_references=("exec://run/7",),
        confidence=1.5,
    )
    issues = validate_result(result)
    assert "confidence out of range" in issues


def test_confidence_out_of_range_rejected_at_construction() -> None:
    with pytest.raises(ValueError):
        _result("SUCCEEDED", execution_references=("exec://run/7",), confidence=1.5)
    with pytest.raises(ValueError):
        _result("FAILED", failures=(_failure(),), confidence=-0.1)
    with pytest.raises(ValueError):
        _result(
            "SUCCEEDED", execution_references=("exec://run/7",), confidence=1.0 + 1e-9
        )


def test_validate_result_returns_multiple_issues() -> None:
    later_at = datetime(2026, 9, 13, 13, 0, 0, tzinfo=UTC)
    result = _result("FAILED", started_at=later_at, finished_at=FIXED_AT)
    issues = validate_result(result)
    assert "FAILED without failure record" in issues
    assert "finished_at before started_at" in issues


# -- AgentExecutor protocol ----------------------------------------------------


def test_agent_executor_protocol_satisfied_by_class_instance() -> None:
    class FakeExecutor:
        async def execute(self, assignment: AgentAssignment) -> AgentResult:
            return _result("SUCCEEDED", execution_references=("exec://run/7",))

    assert isinstance(FakeExecutor(), AgentExecutor)


def test_agent_executor_protocol_satisfied_by_async_callable() -> None:
    async def fake_execute(assignment: AgentAssignment) -> AgentResult:
        return _result("SUCCEEDED", execution_references=("exec://run/7",))

    fake_execute.execute = (
        fake_execute  # attach the protocol member to the function object
    )
    assert isinstance(fake_execute, AgentExecutor)


def test_agent_executor_protocol_rejects_non_conforming_object() -> None:
    class NotAnExecutor:
        pass

    assert not isinstance(NotAnExecutor(), AgentExecutor)


def test_agent_executor_factory_protocol() -> None:
    class FakeExecutor:
        async def execute(self, assignment: AgentAssignment) -> AgentResult:
            return _result("SUCCEEDED", execution_references=("exec://run/7",))

    class FakeFactory:
        def create(
            self, spec: AgentSpec, *, allowed_tools: tuple[str, ...]
        ) -> AgentExecutor:
            return FakeExecutor()

    factory = FakeFactory()
    assert isinstance(factory, AgentExecutorFactory)
    executor = factory.create(
        AgentSpec(
            agent_id="coding-1", name="coding", capability=SpecialistCapability.CODING
        ),
        allowed_tools=("file.",),
    )
    assert isinstance(executor, AgentExecutor)


def test_agent_result_evidence_and_failures_round_trip() -> None:
    evidence = AgentEvidence(
        evidence_id="e-1",
        source="nebius-sandbox-1",
        timestamp=FIXED_AT,
        evidence_type="EXECUTION_TRACE",
        machine_result={"exit_code": 0, "stdout": "42 passed"},
        provenance="exec://run/7",
    )
    result = _result(
        "SUCCEEDED",
        evidence=(evidence,),
        claims=("AUTH-017 fixed",),
        artifacts={"patch": "diff"},
        next_recommendation="proceed to verification",
        summary="refresh guard hardened",
        confidence=0.95,
    )
    assert validate_result(result) == ()
    assert result.evidence[0].evidence_type == "EXECUTION_TRACE"
    assert result.evidence[0].machine_result == {"exit_code": 0, "stdout": "42 passed"}
    assert result.claims == ("AUTH-017 fixed",)
    assert result.artifacts == {"patch": "diff"}
    assert result.confidence == 0.95
