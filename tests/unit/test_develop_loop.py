"""Phase 8 unit tests — bounds (§8.10), loop (§8.9), candidates (§8.11), trace (§8.12).

Loop tests drive a REAL sandbox against a real throwaway project whose
"tests" are real subprocesses, so exit codes are machine facts, not
staged results. Covers: iteration/repair/command exhaustion, no-progress
detection; evidence-based success; diagnosis required for repair;
unauthorized repair DENIED_BY_POLICY; decider STOP; candidate comparison
(evidence beats model preference; all-fail selects nothing); trace hash
chain integrity and tamper detection.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import uuid

import pytest
from smorx_develop.agent import (
    CodingAgentError,
    CodingAgentLoop,
    DecisionDirective,
    Diagnosis,
    MutationDirective,
)
from smorx_develop.bounds import BoundsExhaustedError, LoopBounds, LoopBoundsController
from smorx_develop.candidates import build_candidate, compare_candidates
from smorx_develop.plan import build_development_plan
from smorx_develop.sandbox import DevelopmentSandbox
from smorx_develop.trace import build_trace, verify_trace_integrity

pytest.importorskip("smorx_develop.agent")


class TestLoopBounds:
    def test_iteration_exhaustion(self) -> None:
        controller = LoopBoundsController(LoopBounds(max_iterations=2))
        controller.record_iteration()
        controller.record_iteration()
        with pytest.raises(BoundsExhaustedError) as excinfo:
            controller.check()
        assert excinfo.value.bound == "max_iterations"

    def test_command_exhaustion(self) -> None:
        controller = LoopBoundsController(LoopBounds(max_commands=1))
        controller.check()
        controller.record_command()
        with pytest.raises(BoundsExhaustedError) as excinfo:
            controller.check()
        assert excinfo.value.bound == "max_commands"

    def test_repair_exhaustion(self) -> None:
        controller = LoopBoundsController(LoopBounds(max_repair_attempts=1))
        controller.record_repair()
        with pytest.raises(BoundsExhaustedError) as excinfo:
            controller.check()
        assert excinfo.value.bound == "max_repair_attempts"

    def test_no_progress_identical_signatures(self) -> None:
        controller = LoopBoundsController(LoopBounds(no_progress_threshold=2))
        assert controller.record_execution_signature("F2|1") is False
        assert (
            controller.record_execution_signature("F2|1") is True
        )  # repeated -> block

    def test_no_progress_resets_on_change(self) -> None:
        controller = LoopBoundsController(LoopBounds(no_progress_threshold=2))
        assert controller.record_execution_signature("F2|1") is False
        assert (
            controller.record_execution_signature("F1|2") is False
        )  # changed -> progress
        assert controller.record_execution_signature("F1|2") is True  # repeats -> block
        # The hit clears the window: a new sequence must rebuild the count.
        assert controller.record_execution_signature("F1|2") is False
        assert controller.record_execution_signature("F1|2") is True

    def test_from_budget_mapping(self) -> None:
        bounds = LoopBounds.from_budget({"max_iterations": 9, "max_commands": 7})
        assert bounds.max_iterations == 9
        assert bounds.max_commands == 7
        assert bounds.max_repair_attempts == 3  # default retained


def _py(code: str) -> str:
    return f'"{sys.executable.replace(chr(92), "/")}" -c "{code}"'


def _plan(test_command: str) -> object:
    return build_development_plan(
        interpretation="make the marker pass",
        affected_components=["module demo"],
        affected_files=["demo.py"],
        implementation_strategy="write the file, then run the check",
        tests_to_run=[test_command],
        completion_criteria=["marker check exits 0"],
    )


def _diagnosis(records_tail: str = "marker check failed") -> Diagnosis:
    return Diagnosis(
        failure_codes=("F2_UNIT_TEST",),
        observed=records_tail,
        probable_cause="demo.py missing the expected marker",
        next_action="write demo.py containing MARKER-OK",
    )


def _run_loop(coro):
    return asyncio.run(coro)


class TestCodingAgentLoop:
    def test_success_first_pass_is_evidence_based(self) -> None:
        async def _run() -> None:
            with tempfile.TemporaryDirectory() as source:
                sandbox = await DevelopmentSandbox.create(source_root=source)
                try:
                    loop = CodingAgentLoop(
                        sandbox=sandbox, bounds=LoopBounds(max_iterations=3)
                    )
                    plan = _plan(_py("print('MARKER-OK')"))
                    calls: list[int] = []

                    async def decider(view):  # pragma: no cover - must not be called
                        calls.append(1)
                        raise AssertionError(
                            "decider must not run when first pass passes"
                        )

                    result = await loop.run(
                        plan=plan,  # type: ignore[arg-type]
                        context=None,  # type: ignore[arg-type]
                        barrier=_AllowBarrier(),
                        authorized=True,
                        decider=decider,
                    )
                    assert result.final_state == "CANDIDATE_PASSED"
                    assert result.termination.kind == "SUCCESS_EVIDENCED"
                    assert result.executions[0].exit_code == 0
                    assert calls == []
                finally:
                    await sandbox.destroy()

        _run_loop(_run())

    def test_repair_requires_diagnosis(self) -> None:
        async def _run() -> None:
            with tempfile.TemporaryDirectory() as source:
                sandbox = await DevelopmentSandbox.create(source_root=source)
                try:
                    loop = CodingAgentLoop(sandbox=sandbox, bounds=LoopBounds())
                    with pytest.raises(CodingAgentError) as excinfo:
                        loop.decide(
                            directive=DecisionDirective(
                                action="REPAIR",
                                rationale="fix it",
                                diagnosis=None,
                            ),
                            authorized=True,
                        )
                    assert "requires a diagnosis" in str(excinfo.value)
                finally:
                    await sandbox.destroy()

        _run_loop(_run())

    def test_unauthorized_repair_is_denied_and_stops_loop(self) -> None:
        async def _run() -> None:
            with tempfile.TemporaryDirectory() as source:
                sandbox = await DevelopmentSandbox.create(source_root=source)
                try:
                    loop = CodingAgentLoop(sandbox=sandbox, bounds=LoopBounds())
                    directive = DecisionDirective(
                        action="REPAIR",
                        rationale="fix the marker",
                        diagnosis=_diagnosis(),
                        mutation=MutationDirective(
                            path="demo.py",
                            content="MARKER-OK = True\n",
                            reason="repair",
                        ),
                    )
                    decision = loop.decide(directive=directive, authorized=False)
                    assert decision.policy_state == "DENIED_BY_POLICY"
                    assert decision.authorized is False
                    assert "explicit authorization" in decision.policy_reason
                finally:
                    await sandbox.destroy()

        _run_loop(_run())

    def test_failed_then_repaired_loop_with_real_commands(self) -> None:
        async def _run() -> None:
            with tempfile.TemporaryDirectory() as source:
                sandbox = await DevelopmentSandbox.create(source_root=source)
                try:
                    loop = CodingAgentLoop(
                        sandbox=sandbox,
                        bounds=LoopBounds(max_iterations=4, max_repair_attempts=3),
                    )
                    plan = _plan(
                        _py(
                            "import pathlib; raise SystemExit(0 if pathlib.Path('demo.py').read_text().count('MARKER-OK') else 1)"
                        )
                    )
                    first = {"done": False}

                    async def decider(view):
                        if first["done"]:
                            return DecisionDirective(
                                action="STOP",
                                rationale="second failure; stop the loop",
                            )
                        first["done"] = True
                        return DecisionDirective(
                            action="REPAIR",
                            rationale="demo.py missing; write it",
                            diagnosis=_diagnosis(),
                            mutation=MutationDirective(
                                path="demo.py",
                                content="MARKER-OK\n",
                                reason="add the marker",
                            ),
                        )

                    result = await loop.run(
                        plan=plan,  # type: ignore[arg-type]
                        context=None,  # type: ignore[arg-type]
                        barrier=_AllowBarrier(),
                        authorized=True,
                        decider=decider,
                    )
                    assert result.final_state == "CANDIDATE_PASSED"
                    assert result.termination.kind == "SUCCESS_EVIDENCED"
                    assert len(result.executions) == 2
                    assert result.executions[0].exit_code != 0
                    assert result.executions[1].exit_code == 0
                    assert len(result.mutations) == 1
                    assert any(d.action == "REPAIR" for d in result.decisions)
                finally:
                    await sandbox.destroy()

        _run_loop(_run())

    def test_decider_stop_yields_failed_candidate_not_success(self) -> None:
        """A STOP can end the loop but can never mark it passed (I2/I6)."""

        async def _run() -> None:
            with tempfile.TemporaryDirectory() as source:
                sandbox = await DevelopmentSandbox.create(source_root=source)
                try:
                    loop = CodingAgentLoop(
                        sandbox=sandbox, bounds=LoopBounds(max_iterations=3)
                    )
                    plan = _plan(_py("raise SystemExit(1)"))

                    async def decider(view):
                        return DecisionDirective(
                            action="STOP",
                            rationale="model believes it is fine",  # claim without evidence
                        )

                    result = await loop.run(
                        plan=plan,  # type: ignore[arg-type]
                        context=None,  # type: ignore[arg-type]
                        barrier=_AllowBarrier(),
                        authorized=True,
                        decider=decider,
                    )
                    assert result.final_state == "CANDIDATE_FAILED"
                    assert result.termination.kind == "STOP_REQUESTED"
                    # Machine record remains authoritative: the execution failed.
                    assert result.executions[0].exit_code == 1
                finally:
                    await sandbox.destroy()

        _run_loop(_run())

    def test_no_progress_blocks_the_loop(self) -> None:
        async def _run() -> None:
            with tempfile.TemporaryDirectory() as source:
                sandbox = await DevelopmentSandbox.create(source_root=source)
                try:
                    loop = CodingAgentLoop(
                        sandbox=sandbox,
                        bounds=LoopBounds(
                            max_iterations=10,
                            max_repair_attempts=10,
                            no_progress_threshold=2,
                        ),
                    )
                    plan = _plan(_py("raise SystemExit(1)"))

                    async def decider(view):
                        return DecisionDirective(
                            action="REPAIR",
                            rationale="try again",
                            diagnosis=_diagnosis(),
                            mutation=MutationDirective(
                                path="demo.py",
                                content="still wrong\n",
                                reason="attempt",
                            ),
                        )

                    result = await loop.run(
                        plan=plan,  # type: ignore[arg-type]
                        context=None,  # type: ignore[arg-type]
                        barrier=_AllowBarrier(),
                        authorized=True,
                        decider=decider,
                    )
                    assert result.final_state == "BLOCKED"
                    assert result.termination.kind == "NO_PROGRESS"
                finally:
                    await sandbox.destroy()

        _run_loop(_run())

    def test_iteration_bound_blocks_the_loop(self) -> None:
        async def _run() -> None:
            with tempfile.TemporaryDirectory() as source:
                sandbox = await DevelopmentSandbox.create(source_root=source)
                try:
                    loop = CodingAgentLoop(
                        sandbox=sandbox,
                        bounds=LoopBounds(max_iterations=2, max_repair_attempts=5),
                    )
                    plan = _plan(_py("raise SystemExit(1)"))

                    async def decider(view):
                        return DecisionDirective(
                            action="REPAIR",
                            rationale="keep trying",
                            diagnosis=_diagnosis(),
                            mutation=MutationDirective(
                                path="demo.py",
                                content=f"attempt {view.iteration}\n",  # varied content
                                reason="attempt",
                            ),
                        )

                    result = await loop.run(
                        plan=plan,  # type: ignore[arg-type]
                        context=None,  # type: ignore[arg-type]
                        barrier=_AllowBarrier(),
                        authorized=True,
                        decider=decider,
                    )
                    assert result.final_state == "BLOCKED"
                    assert result.termination.kind == "BOUNDS_EXHAUSTED"
                    assert "max_iterations" in result.termination.detail
                finally:
                    await sandbox.destroy()

        _run_loop(_run())


class _AllowBarrier:
    """Barrier stand-in for loop-level tests (barrier itself is tested
    against the real Phase 7 lock in test_develop_barrier_handoff.py)."""

    def evaluate(self, *, context, authorized: bool):
        class _V:
            state = "PASS"
            failed_conditions: tuple[str, ...] = ()
            handoff = None
            allowed = True

        return _V()


class TestCandidates:
    def _result(self, final_state: str, exits: tuple[int, ...], duration: float = 0.5):
        from smorx_develop.execution import ExecutionCapture
        from smorx_tools.execution import CommandResult

        capture = ExecutionCapture(sandbox_id="s", sandbox_backend="LOCAL_WORKSPACE")
        for exit_code in exits:
            capture.record(
                kind="UNIT_TEST",
                command=("pytest",),
                result=CommandResult(
                    exit_code=exit_code,
                    stdout="1 failed" if exit_code else "",
                    stderr="",
                    duration_seconds=duration,
                    timed_out=False,
                    command_name="pytest",
                ),
            )
        from smorx_develop.agent import LoopResult, LoopTermination

        return LoopResult(
            loop_id=f"loop-{uuid.uuid4().hex[:8]}",
            final_state=final_state,
            termination=LoopTermination(kind="SUCCESS_EVIDENCED", detail="d"),
            iterations=1,
            decisions=(),
            executions=capture.records,
            mutations=(),
            checkpoints=(),
        )

    def test_passing_beats_failing_by_evidence(self) -> None:
        a = build_candidate(
            candidate_index=1,
            label="A",
            result=self._result("CANDIDATE_FAILED", (1, 1)),
            sandbox_id="s",
            sandbox_backend="LOCAL_WORKSPACE",
        )
        b = build_candidate(
            candidate_index=2,
            label="B",
            result=self._result("CANDIDATE_PASSED", (0, 0)),
            sandbox_id="s",
            sandbox_backend="LOCAL_WORKSPACE",
        )
        comparison = compare_candidates([a, b])
        assert comparison.outcome == "SELECTED"
        assert comparison.selected_candidate_id == b.candidate_id

    def test_b_beats_a_by_duration_evidence(self) -> None:
        """§12 case 18: both complete; execution evidence breaks the tie."""
        a = build_candidate(
            candidate_index=1,
            label="A (slow)",
            result=self._result("CANDIDATE_PASSED", (0, 0), duration=0.9),
            sandbox_id="s",
            sandbox_backend="LOCAL_WORKSPACE",
        )
        b = build_candidate(
            candidate_index=2,
            label="B (fast)",
            result=self._result("CANDIDATE_PASSED", (0, 0), duration=0.1),
            sandbox_id="s",
            sandbox_backend="LOCAL_WORKSPACE",
        )
        comparison = compare_candidates([a, b])
        assert comparison.outcome == "SELECTED"
        assert comparison.selected_candidate_id == b.candidate_id

    def test_partial_executions_do_not_select_a_failed_candidate(self) -> None:
        """Only CANDIDATE_PASSED final state is selectable: the loop's
        completion rule is all plan executions passing, so per-execution
        ratios cannot promote an incomplete candidate."""
        a = build_candidate(
            candidate_index=1,
            label="A",
            result=self._result("CANDIDATE_FAILED", (1, 1, 1)),
            sandbox_id="s",
            sandbox_backend="LOCAL_WORKSPACE",
        )
        b = build_candidate(
            candidate_index=2,
            label="B",
            result=self._result("CANDIDATE_FAILED", (1, 0, 0)),
            sandbox_id="s",
            sandbox_backend="LOCAL_WORKSPACE",
        )
        comparison = compare_candidates([a, b])
        assert comparison.outcome == "ALL_FAILED"
        assert comparison.selected_candidate_id is None
        # Evidence still ranks B above A for reporting.
        assert comparison.ranked[0]["candidate_id"] == b.candidate_id

    def test_all_failed_selects_nothing(self) -> None:
        a = build_candidate(
            candidate_index=1,
            label="A",
            result=self._result("CANDIDATE_FAILED", (1,)),
            sandbox_id="s",
            sandbox_backend="LOCAL_WORKSPACE",
        )
        b = build_candidate(
            candidate_index=2,
            label="B",
            result=self._result("CANDIDATE_FAILED", (1,)),
            sandbox_id="s",
            sandbox_backend="LOCAL_WORKSPACE",
        )
        comparison = compare_candidates([a, b])
        assert comparison.outcome == "ALL_FAILED"
        assert comparison.selected_candidate_id is None

    def test_no_candidates(self) -> None:
        comparison = compare_candidates([])
        assert comparison.outcome == "NO_CANDIDATES"


class TestTrace:
    def _loop_result(self) -> object:
        from smorx_develop.agent import Decision, Diagnosis, LoopResult, LoopTermination
        from smorx_develop.execution import ExecutionCapture
        from smorx_tools.execution import CommandResult

        capture = ExecutionCapture(sandbox_id="s", sandbox_backend="LOCAL_WORKSPACE")
        record = capture.record(
            kind="UNIT_TEST",
            command=("pytest", "-q"),
            result=CommandResult(
                exit_code=0,
                stdout="",
                stderr="",
                duration_seconds=0.1,
                timed_out=False,
                command_name="pytest",
            ),
        )
        decision = Decision(
            decision_id="dec-1",
            iteration=1,
            action="REPAIR",
            rationale="r",
            diagnosis=Diagnosis(("F2",), "obs", "cause", "next"),
            mutation_path="demo.py",
            authorized=True,
            policy_state="ALLOWED",
        )
        return LoopResult(
            loop_id="loop-x",
            final_state="CANDIDATE_PASSED",
            termination=LoopTermination(kind="SUCCESS_EVIDENCED", detail="d"),
            iterations=1,
            decisions=(decision,),
            executions=(record,),
            mutations=(
                {"mutation_id": "mut-1", "operation": "WRITE", "path": "demo.py"},
            ),
            checkpoints=("pre-candidate",),
        )

    def test_trace_builds_and_verifies(self) -> None:
        result = self._loop_result()
        trace = build_trace(
            task_id=uuid.uuid4(),
            handoff_id=uuid.uuid4(),
            result=result,  # type: ignore[arg-type]
        )
        ok, detail = verify_trace_integrity(trace)
        assert ok, detail
        kinds = [entry.kind for entry in trace.entries]
        assert kinds[0] == "TASK"
        assert "DECISION" in kinds
        assert "MUTATION" in kinds
        assert "EXECUTION_RESULT" in kinds
        as_dict = trace.as_dict()
        assert as_dict["loop_id"] == "loop-x"

    def test_trace_tamper_detection(self) -> None:
        from dataclasses import replace

        result = self._loop_result()
        trace = build_trace(
            task_id=uuid.uuid4(),
            handoff_id=uuid.uuid4(),
            result=result,  # type: ignore[arg-type]
        )
        # Tamper with an interior payload.
        entry = trace.entries[2]
        tampered_payload = dict(entry.payload)
        tampered_payload["exit_code"] = 0  # falsify a failure
        tampered = replace(entry, payload=tampered_payload)
        entries = list(trace.entries)
        entries[2] = tampered
        from dataclasses import replace as _replace

        modified_trace = _replace(trace, entries=tuple(entries))
        ok, detail = verify_trace_integrity(modified_trace)
        assert not ok
        assert "chain broken" in detail or "mismatch" in detail
