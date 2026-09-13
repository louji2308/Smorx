"""Unit tests for the agent state machine."""

from __future__ import annotations

import pytest
from smorx_runtime.state import (
    TRANSITIONS,
    AgentState,
    AgentStateMachine,
    InvalidTransitionError,
    TransitionRecord,
)

CONTRACT_TRANSITIONS: dict[AgentState, tuple[AgentState, ...]] = {
    AgentState.CREATED: (AgentState.INSPECTED,),
    AgentState.INSPECTED: (AgentState.PLANNED,),
    AgentState.PLANNED: (AgentState.EXECUTING,),
    AgentState.EXECUTING: (AgentState.OBSERVED, AgentState.FAILED),
    AgentState.OBSERVED: (AgentState.ITERATING, AgentState.VERIFIED),
    AgentState.FAILED: (AgentState.ITERATING, AgentState.BLOCKED),
    AgentState.ITERATING: (AgentState.EXECUTING,),
    AgentState.VERIFIED: (AgentState.BLOCKED,),
    AgentState.BLOCKED: (),
}


def test_agent_state_members_values() -> None:
    assert [state.value for state in AgentState] == [
        "CREATED",
        "INSPECTED",
        "PLANNED",
        "EXECUTING",
        "OBSERVED",
        "FAILED",
        "ITERATING",
        "VERIFIED",
        "BLOCKED",
    ]


def test_transitions_match_phase_contract() -> None:
    assert set(TRANSITIONS) == set(AgentState)
    assert TRANSITIONS == CONTRACT_TRANSITIONS


@pytest.mark.parametrize("start", list(AgentState))
def test_can_transition_matches_transition_matrix(
    start: AgentState,
) -> None:
    machine = AgentStateMachine(start=start)
    for target in AgentState:
        assert machine.can_transition(target) is (target in CONTRACT_TRANSITIONS[start])


@pytest.mark.parametrize("start", list(TRANSITIONS))
def test_every_legal_transition_records_evidence(start: AgentState) -> None:
    for target in CONTRACT_TRANSITIONS[start]:
        machine = AgentStateMachine(start=start)
        record = machine.transition(
            target,
            reason="contract-driven",
            metadata={"step": start.value},
        )
        assert isinstance(record, TransitionRecord)
        assert record.from_state is start
        assert record.to_state is target
        assert record.reason == "contract-driven"
        assert record.metadata == {"step": start.value}
        assert record.at.tzinfo is not None
        assert machine.state is target
        assert len(machine.history) == 1


def test_happy_path_journey() -> None:
    machine = AgentStateMachine()
    expected_from = [
        AgentState.CREATED,
        AgentState.INSPECTED,
        AgentState.PLANNED,
        AgentState.EXECUTING,
        AgentState.OBSERVED,
        AgentState.ITERATING,
        AgentState.EXECUTING,
        AgentState.OBSERVED,
    ]
    expected_to = [
        AgentState.INSPECTED,
        AgentState.PLANNED,
        AgentState.EXECUTING,
        AgentState.OBSERVED,
        AgentState.ITERATING,
        AgentState.EXECUTING,
        AgentState.OBSERVED,
        AgentState.VERIFIED,
    ]
    journey = [
        AgentState.INSPECTED,
        AgentState.PLANNED,
        AgentState.EXECUTING,
        AgentState.OBSERVED,
        AgentState.ITERATING,
        AgentState.EXECUTING,
        AgentState.OBSERVED,
        AgentState.VERIFIED,
    ]
    for state in journey:
        machine.transition(state, reason=f"toward {state.value}")
    assert machine.state is AgentState.VERIFIED
    assert machine.is_terminal()
    assert [record.from_state for record in machine.history] == expected_from
    assert [record.to_state for record in machine.history] == expected_to


def test_failure_journey_ends_blocked() -> None:
    machine = AgentStateMachine()
    journey = [
        AgentState.INSPECTED,
        AgentState.PLANNED,
        AgentState.EXECUTING,
        AgentState.FAILED,
        AgentState.ITERATING,
        AgentState.EXECUTING,
        AgentState.FAILED,
        AgentState.BLOCKED,
    ]
    for state in journey:
        machine.transition(state, reason="failure evidence")
    assert machine.state is AgentState.BLOCKED
    assert machine.is_terminal()
    assert len(machine.history) == len(journey)


@pytest.mark.parametrize(
    "current, attempted",
    [
        (AgentState.CREATED, AgentState.EXECUTING),
        (AgentState.PLANNED, AgentState.OBSERVED),
        (AgentState.EXECUTING, AgentState.VERIFIED),
        (AgentState.FAILED, AgentState.VERIFIED),
        (AgentState.ITERATING, AgentState.VERIFIED),
        (AgentState.CREATED, AgentState.BLOCKED),
    ],
)
def test_illegal_transitions_raise_with_context(
    current: AgentState,
    attempted: AgentState,
) -> None:
    machine = AgentStateMachine(start=current)
    with pytest.raises(InvalidTransitionError) as excinfo:
        machine.transition(attempted)
    assert excinfo.value.current is current
    assert excinfo.value.attempted is attempted


def test_verified_only_allows_blocked() -> None:
    machine = AgentStateMachine()
    for state in (
        AgentState.INSPECTED,
        AgentState.PLANNED,
        AgentState.EXECUTING,
        AgentState.OBSERVED,
        AgentState.VERIFIED,
    ):
        machine.transition(state)
    assert machine.state is AgentState.VERIFIED
    for target in AgentState:
        if target is not AgentState.BLOCKED:
            with pytest.raises(InvalidTransitionError) as excinfo:
                machine.transition(target, reason="must be rejected")
            assert excinfo.value.current is AgentState.VERIFIED
            assert excinfo.value.attempted is target
    assert len(machine.history) == 5
    record = machine.transition(AgentState.BLOCKED, reason="policy block")
    assert record.to_state is AgentState.BLOCKED
    assert machine.state is AgentState.BLOCKED


def test_blocked_accepts_no_transitions() -> None:
    machine = AgentStateMachine()
    for state in (
        AgentState.INSPECTED,
        AgentState.PLANNED,
        AgentState.EXECUTING,
        AgentState.FAILED,
        AgentState.BLOCKED,
    ):
        machine.transition(state)
    assert machine.state is AgentState.BLOCKED
    for target in AgentState:
        with pytest.raises(InvalidTransitionError):
            machine.transition(target)
    assert len(machine.history) == 5


def test_failed_transition_leaves_machine_unchanged() -> None:
    machine = AgentStateMachine()
    machine.transition(AgentState.INSPECTED)
    before_history = machine.history
    with pytest.raises(InvalidTransitionError):
        machine.transition(AgentState.VERIFIED)
    assert machine.state is AgentState.INSPECTED
    assert machine.history == before_history
    assert len(machine.history) == 1


def test_history_timestamps_are_monotonic() -> None:
    machine = AgentStateMachine()
    journey = [
        AgentState.INSPECTED,
        AgentState.PLANNED,
        AgentState.EXECUTING,
        AgentState.OBSERVED,
        AgentState.ITERATING,
        AgentState.EXECUTING,
        AgentState.OBSERVED,
        AgentState.ITERATING,
        AgentState.EXECUTING,
        AgentState.OBSERVED,
        AgentState.VERIFIED,
    ]
    for state in journey:
        machine.transition(state)
    timestamps = [record.at for record in machine.history]
    assert timestamps == sorted(timestamps)
    assert len(set(timestamps)) == len(timestamps)


def test_execution_cycles_counts_iterations() -> None:
    machine = AgentStateMachine()
    journey = [
        AgentState.INSPECTED,
        AgentState.PLANNED,
        AgentState.EXECUTING,
        AgentState.OBSERVED,
        AgentState.ITERATING,
        AgentState.EXECUTING,
        AgentState.OBSERVED,
        AgentState.ITERATING,
        AgentState.EXECUTING,
        AgentState.OBSERVED,
        AgentState.VERIFIED,
    ]
    for state in journey:
        machine.transition(state)
    assert machine.execution_cycles() == 2
    assert machine.state is AgentState.VERIFIED


def test_reset_restores_created_and_clears_history() -> None:
    machine = AgentStateMachine()
    for state in (
        AgentState.INSPECTED,
        AgentState.PLANNED,
        AgentState.EXECUTING,
        AgentState.OBSERVED,
    ):
        machine.transition(state)
    assert machine.state is AgentState.OBSERVED
    assert len(machine.history) == 4
    machine.reset()
    assert machine.state is AgentState.CREATED
    assert machine.history == ()
    assert machine.execution_cycles() == 0


def test_is_terminal_flags() -> None:
    assert AgentStateMachine().is_terminal() is False
    assert AgentStateMachine(start=AgentState.VERIFIED).is_terminal() is True
    assert AgentStateMachine(start=AgentState.BLOCKED).is_terminal() is True
