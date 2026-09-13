"""Agent state machine for the Software Evolution Intelligence System.

The agent lifecycle is an explicit state machine so the workflow can be
audited, resumed, bounded, and safely stopped.  The states and the transition
table implement the phase contract in ``Requirements & Contract.md`` section 3
("Agent state contract") and the bounded-loop contract in section 10, and are
mirrored in ``IMPLEMENTATION_PLAN.md`` phase 0.3.

Rationale for each legal transition in :data:`TRANSITIONS` (the authoritative
transition table):

``CREATED -> INSPECTED``
    A task exists.  The agent must demonstrate repository understanding
    before it is allowed to plan.
``INSPECTED -> PLANNED``
    Planning may only start on inspected evidence: repository, files, tests,
    and environment are understood.
``PLANNED -> EXECUTING``
    A plan exists (interpretation, strategy, validation strategy); the agent
    is now allowed to act on the repository.
``EXECUTING -> OBSERVED``
    The action completed and produced machine-readable results (evidence).
``EXECUTING -> FAILED``
    The action completed but at least one expected condition was not met.
``OBSERVED -> ITERATING``
    Evidence was observed and the agent decides another action is required.
``OBSERVED -> VERIFIED``
    Observed evidence satisfies all acceptance criteria.
``FAILED -> ITERATING``
    Failure is information: the agent may diagnose and decide the next
    action (failure -> evidence -> next decision).
``FAILED -> BLOCKED``
    Safe stop after failure: unrecoverable condition, no-progress detection,
    or policy block.  BLOCKED is not success.
``ITERATING -> EXECUTING``
    The agent executes the next action decided from observed/derived evidence.
``VERIFIED -> BLOCKED``
    Post-verification policy block (for example intent misalignment discovered
    after verification).  A verified agent may never resume violating work.

Everything else is illegal.  ``AgentStateMachine`` enforces these rules
strictly for the terminal states as well: from ``VERIFIED`` the only legal
move is to ``BLOCKED``, and from ``BLOCKED`` no transition exists.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


class AgentState(enum.StrEnum):
    """Lifecycle states of a coding agent run."""

    CREATED = "CREATED"
    INSPECTED = "INSPECTED"
    PLANNED = "PLANNED"
    EXECUTING = "EXECUTING"
    OBSERVED = "OBSERVED"
    FAILED = "FAILED"
    ITERATING = "ITERATING"
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"


TRANSITIONS: dict[AgentState, tuple[AgentState, ...]] = {
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


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed by the contract."""

    current: AgentState
    attempted: AgentState

    def __init__(self, current: AgentState, attempted: AgentState) -> None:
        super().__init__(f"invalid transition from {current.value} to {attempted.value}")
        self.current = current
        self.attempted = attempted


@dataclass(frozen=True)
class TransitionRecord:
    """Append-only evidence entry describing one executed transition."""

    from_state: AgentState
    to_state: AgentState
    at: datetime
    reason: str
    metadata: dict[str, object]


class AgentStateMachine:
    """Explicit, auditable agent state machine.

    The machine only moves through :data:`TRANSITIONS`.  A failed attempt
    leaves the machine unchanged, so rejected moves are not observable in
    the history.
    """

    def __init__(self, start: AgentState = AgentState.CREATED) -> None:
        self._state = start
        self._history: list[TransitionRecord] = []

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def history(self) -> tuple[TransitionRecord, ...]:
        return tuple(self._history)

    def can_transition(self, target: AgentState) -> bool:
        return target in TRANSITIONS[self._state]

    def transition(
        self,
        target: AgentState,
        *,
        reason: str = "",
        metadata: dict[str, object] | None = None,
    ) -> TransitionRecord:
        current = self._state
        if current is AgentState.BLOCKED:
            raise InvalidTransitionError(current, target)
        if current is AgentState.VERIFIED and target is not AgentState.BLOCKED:
            raise InvalidTransitionError(current, target)
        if target not in TRANSITIONS[current]:
            raise InvalidTransitionError(current, target)
        record = TransitionRecord(
            from_state=current,
            to_state=target,
            at=self._next_timestamp(),
            reason=reason,
            metadata=dict(metadata) if metadata is not None else {},
        )
        self._history.append(record)
        self._state = target
        return record

    def reset(self) -> None:
        self._state = AgentState.CREATED
        self._history.clear()

    def is_terminal(self) -> bool:
        return self._state in (AgentState.VERIFIED, AgentState.BLOCKED)

    def execution_cycles(self) -> int:
        """Number of ITERATING -> EXECUTING transitions (iteration metric)."""
        return sum(
            1
            for record in self._history
            if record.from_state is AgentState.ITERATING and record.to_state is AgentState.EXECUTING
        )

    def _next_timestamp(self) -> datetime:
        now = datetime.now(UTC)
        if self._history:
            last = self._history[-1].at
            if now <= last:
                return last + timedelta(microseconds=1)
        return now
