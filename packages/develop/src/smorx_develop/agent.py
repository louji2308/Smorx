"""Phase 8.6-8.9 — The Coding Agent loop.

The decision/action/observation loop that turns the locked pre-coding
context into a final candidate state:

    EXECUTE → OBSERVE → CLASSIFY → DIAGNOSE → DECIDE → MODIFY → RE-EXECUTE

Rules enforced structurally (master prompt §8.6-8.10, AGENTS.md §3):

- the loop runs ONLY with a PASS verdict from the Phase 8 execution
  barrier for the handoff — :meth:`CodingAgentLoop.run` refuses otherwise;
- every file mutation goes through the sandbox's controlled, attributed
  mutation methods — never direct writes;
- every command/test runs through the sandbox and is captured as a
  machine-authoritative execution record (I2: model assertions never
  replace machine results);
- a REPAIR decision REQUIRES a diagnosis record; an unauthorized repair
  is DENIED_BY_POLICY and stops the loop — it is never executed;
- success is decided ONLY from passing execution records; a decider that
  requests STOP can end the loop but can never mark it passed;
- the loop is bounded by :class:`LoopBoundsController`; exhaustion and
  no-progress BLOCK the loop and are reported, never hidden.
"""

from __future__ import annotations

import shlex
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from smorx_precode.lock_gate import PreCodingContext

from smorx_develop.barrier import ExecutionBarrier
from smorx_develop.bounds import BoundsExhaustedError, LoopBounds, LoopBoundsController
from smorx_develop.execution import ExecutionCapture, ExecutionRecord
from smorx_develop.plan import DevelopmentPlan
from smorx_develop.sandbox import DevelopmentSandbox

__all__ = [
    "CodingAgentError",
    "CodingAgentLoop",
    "Decision",
    "DecisionDirective",
    "Diagnosis",
    "LoopResult",
    "LoopTermination",
    "LoopView",
    "MutationDirective",
]


class CodingAgentError(Exception):
    """Raised for loop-contract violations (not for ordinary failures)."""


@dataclass(frozen=True)
class Diagnosis:
    """Observed failure + probable cause + next action (AGENTS.md §14)."""

    failure_codes: tuple[str, ...]
    observed: str
    probable_cause: str
    next_action: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "failure_codes": list(self.failure_codes),
            "observed": self.observed,
            "probable_cause": self.probable_cause,
            "next_action": self.next_action,
        }


@dataclass(frozen=True)
class MutationDirective:
    """One controlled file change proposed by a repair decision."""

    path: str
    content: str
    reason: str


@dataclass(frozen=True)
class DecisionDirective:
    """What the decider (model/orchestrator) asks the loop to do next."""

    action: str  # REPAIR | STOP
    rationale: str
    diagnosis: Diagnosis | None = None
    mutation: MutationDirective | None = None


@dataclass(frozen=True)
class Decision:
    """One bounded loop decision with its policy state."""

    decision_id: str
    iteration: int
    action: str
    rationale: str
    diagnosis: Diagnosis | None
    mutation_path: str
    authorized: bool
    policy_state: str  # ALLOWED | DENIED_BY_POLICY
    policy_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "iteration": self.iteration,
            "action": self.action,
            "rationale": self.rationale,
            "diagnosis": self.diagnosis.as_dict() if self.diagnosis else None,
            "mutation_path": self.mutation_path,
            "authorized": self.authorized,
            "policy_state": self.policy_state,
            "policy_reason": self.policy_reason,
        }


@dataclass(frozen=True)
class LoopView:
    """Read-only view handed to the decider between iterations."""

    iteration: int
    plan: DevelopmentPlan
    failing_records: tuple[dict[str, Any], ...]
    bounds_usage: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "plan": self.plan.as_dict(),
            "failing_records": list(self.failing_records),
            "bounds_usage": dict(self.bounds_usage),
        }


@dataclass(frozen=True)
class LoopTermination:
    """Why and how the loop stopped (objective, never 'looks good')."""

    kind: str  # SUCCESS_EVIDENCED | BOUNDS_EXHAUSTED | NO_PROGRESS | POLICY_STOP | STOP_REQUESTED
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "detail": self.detail}


@dataclass(frozen=True)
class LoopResult:
    """The final candidate state produced by one loop run."""

    loop_id: str
    final_state: str  # CANDIDATE_PASSED | CANDIDATE_FAILED | BLOCKED
    termination: LoopTermination
    iterations: int
    decisions: tuple[Decision, ...]
    executions: tuple[ExecutionRecord, ...]
    mutations: tuple[dict[str, Any], ...]
    checkpoints: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "loop_id": self.loop_id,
            "final_state": self.final_state,
            "termination": self.termination.as_dict(),
            "iterations": self.iterations,
            "decisions": [d.as_dict() for d in self.decisions],
            "executions": [e.as_dict() for e in self.executions],
            "mutations": list(self.mutations),
            "checkpoints": list(self.checkpoints),
        }


Decider = Callable[[LoopView], Awaitable[DecisionDirective]]


def _command_kind(command: str) -> str:
    lowered = command.lower()
    if "integration" in lowered:
        return "INTEGRATION_TEST"
    if "pytest" in lowered or " test" in f" {lowered}" or lowered.startswith("test"):
        return "UNIT_TEST"
    if "mypy" in lowered or "typecheck" in lowered or "tsc" in lowered:
        return "TYPECHECK"
    if "ruff" in lowered or "lint" in lowered or "eslint" in lowered:
        return "LINT"
    if "build" in lowered or "compile" in lowered:
        return "BUILD"
    return "COMMAND"


def _no_progress_signature(records: tuple[ExecutionRecord, ...]) -> str:
    """Materially equivalent = same failure codes and exit codes."""
    codes = tuple(record.failure_code for record in records)
    exits = tuple(record.exit_code for record in records)
    return f"{codes}|{exits}"


class CodingAgentLoop:
    """Bounded EXECUTE→OBSERVE→CLASSIFY→DIAGNOSE→DECIDE→MODIFY→RE-EXECUTE."""

    def __init__(
        self,
        *,
        sandbox: DevelopmentSandbox,
        bounds: LoopBounds,
    ) -> None:
        self._sandbox = sandbox
        self._bounds_controller = LoopBoundsController(bounds)
        self._capture = ExecutionCapture(
            sandbox_id=sandbox.identity.sandbox_id,
            sandbox_backend=sandbox.identity.backend,
        )
        self._decisions: list[Decision] = []
        self._mutations: list[dict[str, Any]] = []
        self._checkpoints: list[str] = []
        self._loop_id = f"loop-{uuid.uuid4().hex[:12]}"

    # -- primitives --------------------------------------------------------

    def _check_bounds(self) -> None:
        self._bounds_controller.check()

    async def execute_command(
        self,
        kind: str,
        command: str | tuple[str, ...],
        *,
        timeout_seconds: float | None = None,
        artifacts: tuple[str, ...] = (),
    ) -> ExecutionRecord:
        """Run one real command inside the sandbox and capture it."""
        self._check_bounds()
        self._bounds_controller.record_command()
        args = tuple(shlex.split(command)) if isinstance(command, str) else tuple(command)
        timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else float(self._bounds_controller.bounds.per_tool_timeout_seconds)
        )
        result = await self._sandbox.execute(args, timeout_seconds=timeout)
        return self._capture.record(kind=kind, command=args, result=result, artifacts=artifacts)

    def mutate_file(self, directive: MutationDirective) -> dict[str, Any]:
        """Apply one controlled, attributed mutation."""
        mutation = self._sandbox.write_file(
            directive.path, directive.content, reason=directive.reason
        )
        record = mutation.as_dict()
        self._mutations.append(record)
        return record

    async def checkpoint(self, label: str) -> str:
        ref = await self._sandbox.checkpoint(label)
        self._checkpoints.append(ref)
        return ref

    async def rollback(self, checkpoint_ref: str) -> None:
        await self._sandbox.rollback(checkpoint_ref)

    # -- decision policy -----------------------------------------------------

    def decide(self, *, directive: DecisionDirective, authorized: bool) -> Decision:
        """Validate one directive through the loop's policy gate.

        - STOP is always allowed (the agent can stop safely, I5);
        - REPAIR requires a diagnosis — repairing without one raises;
        - an unauthorized REPAIR is recorded DENIED_BY_POLICY and never
          executed (the caller must stop the loop on that state).
        """
        iteration = self._bounds_controller._state.iteration
        if directive.action not in {"REPAIR", "STOP"}:
            raise CodingAgentError(f"unknown directive action {directive.action!r}")
        if directive.action == "REPAIR":
            if directive.diagnosis is None:
                raise CodingAgentError(
                    "repair decision requires a diagnosis record "
                    "(observed failure → probable cause → next action)"
                )
            if (
                not directive.diagnosis.observed.strip()
                or not directive.diagnosis.next_action.strip()
            ):
                raise CodingAgentError("diagnosis must state the observed failure and next action")

        if directive.action == "REPAIR" and not authorized:
            decision = Decision(
                decision_id=f"dec-{uuid.uuid4().hex[:12]}",
                iteration=iteration,
                action=directive.action,
                rationale=directive.rationale,
                diagnosis=directive.diagnosis,
                mutation_path=directive.mutation.path if directive.mutation else "",
                authorized=False,
                policy_state="DENIED_BY_POLICY",
                policy_reason="unauthorized repair; an explicit authorization flag is required",
            )
            self._decisions.append(decision)
            return decision

        decision = Decision(
            decision_id=f"dec-{uuid.uuid4().hex[:12]}",
            iteration=iteration,
            action=directive.action,
            rationale=directive.rationale,
            diagnosis=directive.diagnosis,
            mutation_path=directive.mutation.path if directive.mutation else "",
            authorized=True,
            policy_state="ALLOWED",
        )
        self._decisions.append(decision)
        return decision

    # -- the loop ------------------------------------------------------------

    async def _execute_plan(self, plan: DevelopmentPlan) -> tuple[ExecutionRecord, ...]:
        records: list[ExecutionRecord] = []
        for command in plan.tests_to_run:
            records.append(await self.execute_command(_command_kind(command), command))
        return tuple(records)

    def _failing(self, records: tuple[ExecutionRecord, ...]) -> tuple[ExecutionRecord, ...]:
        return tuple(record for record in records if not record.passed)

    def _result(
        self,
        *,
        final_state: str,
        termination: LoopTermination,
    ) -> LoopResult:
        return LoopResult(
            loop_id=self._loop_id,
            final_state=final_state,
            termination=termination,
            iterations=self._bounds_controller._state.iteration,
            decisions=tuple(self._decisions),
            executions=self._capture.records,
            mutations=tuple(self._mutations),
            checkpoints=tuple(self._checkpoints),
        )

    async def run(
        self,
        *,
        plan: DevelopmentPlan,
        context: PreCodingContext,
        barrier: ExecutionBarrier,
        authorized: bool,
        decider: Decider,
    ) -> LoopResult:
        """Run the bounded loop; returns the objective final candidate state."""
        verdict = barrier.evaluate(context=context, authorized=authorized)
        if not verdict.allowed:
            return self._result(
                final_state="BLOCKED",
                termination=LoopTermination(
                    kind="POLICY_STOP",
                    detail="execution barrier BLOCKED: " + "; ".join(verdict.failed_conditions),
                ),
            )

        await self.checkpoint("pre-candidate")

        records = await self._execute_plan(plan)
        self._bounds_controller.record_iteration()
        if not self._failing(records):
            return self._result(
                final_state="CANDIDATE_PASSED",
                termination=LoopTermination(
                    kind="SUCCESS_EVIDENCED",
                    detail=f"all {len(records)} plan executions passed (exit code 0, machine-captured)",
                ),
            )

        while True:
            try:
                self._check_bounds()
            except BoundsExhaustedError as exc:
                return self._result(
                    final_state="BLOCKED",
                    termination=LoopTermination(
                        kind="BOUNDS_EXHAUSTED", detail=f"{exc.bound}: {exc}"
                    ),
                )

            failing = self._failing(records)
            view = LoopView(
                iteration=self._bounds_controller._state.iteration,
                plan=plan,
                failing_records=tuple(record.as_dict() for record in failing),
                bounds_usage=self._bounds_controller.as_dict(),
            )
            directive = await decider(view)
            decision = self.decide(directive=directive, authorized=authorized)

            if decision.policy_state == "DENIED_BY_POLICY":
                return self._result(
                    final_state="BLOCKED",
                    termination=LoopTermination(
                        kind="POLICY_STOP",
                        detail=f"decision {decision.decision_id} denied by policy: "
                        f"{decision.policy_reason}",
                    ),
                )
            if directive.action == "STOP":
                return self._result(
                    final_state="CANDIDATE_FAILED",
                    termination=LoopTermination(
                        kind="STOP_REQUESTED",
                        detail=f"decider requested stop: {directive.rationale}",
                    ),
                )

            # REPAIR path (authorized, diagnosed).
            self._bounds_controller.record_repair()
            assert directive.mutation is not None or directive.diagnosis is not None
            if directive.mutation is not None:
                self.mutate_file(directive.mutation)
            records = await self._execute_plan(plan)
            self._bounds_controller.record_iteration()
            failing = self._failing(records)
            if not failing:
                return self._result(
                    final_state="CANDIDATE_PASSED",
                    termination=LoopTermination(
                        kind="SUCCESS_EVIDENCED",
                        detail=f"all {len(records)} plan executions passed after repair "
                        f"(decision {decision.decision_id})",
                    ),
                )
            if self._bounds_controller.record_execution_signature(_no_progress_signature(failing)):
                return self._result(
                    final_state="BLOCKED",
                    termination=LoopTermination(
                        kind="NO_PROGRESS",
                        detail="no-progress threshold reached: materially equivalent "
                        "failures repeated without measurable progress",
                    ),
                )
