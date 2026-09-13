"""Unit tests for the bounded execution-loop controls."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import smorx_runtime.loop_controls as loop_controls_module
from pydantic import ValidationError
from smorx_runtime import LOOP_ENV_PREFIX
from smorx_runtime.loop_controls import (
    IterationBudget,
    LoopControlError,
    LoopControls,
    NoProgressDetector,
)


def test_defaults_are_development_safe() -> None:
    controls = LoopControls()
    assert controls.max_iterations == 25
    assert controls.max_runtime_seconds == 7200.0
    assert controls.max_command_count == 200
    assert controls.max_repair_attempts == 5
    assert controls.no_progress_threshold == 3
    assert controls.tool_timeouts_seconds == {"*": 120.0}
    assert controls.per_agent_timeout_seconds == 1800.0
    assert controls.total_phase_timeout_seconds == 14400.0


def test_for_env_development_matches_defaults() -> None:
    assert LoopControls.for_env("development") == LoopControls()


def test_for_env_production_is_stricter() -> None:
    production = LoopControls.for_env("production")
    assert production.max_iterations == 8
    assert production.max_runtime_seconds == 1800.0
    assert production.max_command_count == 60
    assert production.max_repair_attempts == 2
    assert production.no_progress_threshold == 2
    assert production.tool_timeouts_seconds == {"*": 60.0}
    assert production.per_agent_timeout_seconds == 600.0
    assert production.total_phase_timeout_seconds == 3600.0
    assert LoopControls.for_env("anything-else") == production


def test_from_env_applies_overrides_and_keeps_missing() -> None:
    controls = LoopControls.from_env(
        {
            f"{LOOP_ENV_PREFIX}MAX_ITERATIONS": "12",
            f"{LOOP_ENV_PREFIX}MAX_RUNTIME_SECONDS": "300.5",
            f"{LOOP_ENV_PREFIX}MAX_COMMAND_COUNT": "45",
            f"{LOOP_ENV_PREFIX}MAX_REPAIR_ATTEMPTS": "3",
            f"{LOOP_ENV_PREFIX}NO_PROGRESS_THRESHOLD": "2",
            f"{LOOP_ENV_PREFIX}TOOL_TIMEOUTS_SECONDS": '{"run": 5.0}',
            f"{LOOP_ENV_PREFIX}PER_AGENT_TIMEOUT_SECONDS": "900",
            f"{LOOP_ENV_PREFIX}TOTAL_PHASE_TIMEOUT_SECONDS": "3600",
        }
    )
    assert controls.max_iterations == 12
    assert controls.max_runtime_seconds == 300.5
    assert controls.max_command_count == 45
    assert controls.max_repair_attempts == 3
    assert controls.no_progress_threshold == 2
    assert controls.tool_timeouts_seconds == {"*": 120.0, "run": 5.0}
    assert controls.per_agent_timeout_seconds == 900.0
    assert controls.total_phase_timeout_seconds == 3600.0


def test_from_env_missing_keys_keep_base_values() -> None:
    controls = LoopControls.from_env({f"{LOOP_ENV_PREFIX}MAX_ITERATIONS": "30"})
    defaults = LoopControls()
    assert controls.max_iterations == 30
    assert controls.max_runtime_seconds == defaults.max_runtime_seconds
    assert controls.max_command_count == defaults.max_command_count
    assert controls.max_repair_attempts == defaults.max_repair_attempts
    assert controls.no_progress_threshold == defaults.no_progress_threshold
    assert controls.tool_timeouts_seconds == defaults.tool_timeouts_seconds
    assert controls.per_agent_timeout_seconds == defaults.per_agent_timeout_seconds
    assert controls.total_phase_timeout_seconds == defaults.total_phase_timeout_seconds
    assert LoopControls.from_env({}) == defaults


def test_from_env_reads_os_environ_when_not_passed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(f"{LOOP_ENV_PREFIX}MAX_ITERATIONS", "17")
    controls = LoopControls.from_env()
    assert controls.max_iterations == 17


def test_from_env_custom_prefix() -> None:
    controls = LoopControls.from_env(
        {f"{LOOP_ENV_PREFIX}MAX_ITERATIONS": "5"},
        prefix="ZZ_",
    )
    assert controls.max_iterations == 25
    controls = LoopControls.from_env(
        {"ZZ_MAX_ITERATIONS": "5", "ZZ_MAX_REPAIR_ATTEMPTS": "2"},
        prefix="ZZ_",
    )
    assert controls.max_iterations == 5
    assert controls.max_repair_attempts == 2


def test_from_env_tool_timeouts_overlay_on_base() -> None:
    base = LoopControls(tool_timeouts_seconds={"*": 60.0, "run": 5.0})
    controls = LoopControls.from_env(
        {f"{LOOP_ENV_PREFIX}TOOL_TIMEOUTS_SECONDS": '{"fmt": 30.0}'},
        base=base,
    )
    assert controls.tool_timeouts_seconds == {"*": 60.0, "run": 5.0, "fmt": 30.0}


def test_from_env_invalid_integer_raises_loop_control_error() -> None:
    with pytest.raises(LoopControlError):
        LoopControls.from_env({f"{LOOP_ENV_PREFIX}MAX_ITERATIONS": "abc"})


def test_from_env_invalid_float_raises_loop_control_error() -> None:
    with pytest.raises(LoopControlError):
        LoopControls.from_env({f"{LOOP_ENV_PREFIX}MAX_RUNTIME_SECONDS": "slow"})


def test_from_env_bad_json_raises_loop_control_error() -> None:
    with pytest.raises(LoopControlError):
        LoopControls.from_env({f"{LOOP_ENV_PREFIX}TOOL_TIMEOUTS_SECONDS": "{not json"})


def test_from_env_non_object_json_raises_loop_control_error() -> None:
    with pytest.raises(LoopControlError):
        LoopControls.from_env({f"{LOOP_ENV_PREFIX}TOOL_TIMEOUTS_SECONDS": "[1, 2, 3]"})


def test_from_env_negative_tool_timeout_raises() -> None:
    with pytest.raises((LoopControlError, ValidationError)):
        LoopControls.from_env(
            {f"{LOOP_ENV_PREFIX}TOOL_TIMEOUTS_SECONDS": '{"run": -1.0}'}
        )


def test_from_env_field_violation_raises_loop_control_error() -> None:
    with pytest.raises(LoopControlError):
        LoopControls.from_env({f"{LOOP_ENV_PREFIX}MAX_REPAIR_ATTEMPTS": "-1"})


def test_from_env_ordering_violation_across_base_and_override_raises() -> None:
    base = LoopControls(max_iterations=8)
    with pytest.raises((LoopControlError, ValidationError)):
        LoopControls.from_env(
            {f"{LOOP_ENV_PREFIX}MAX_REPAIR_ATTEMPTS": "9"},
            base=base,
        )


def test_ordering_violation_repair_exceeds_iterations_raises() -> None:
    with pytest.raises(ValidationError):
        LoopControls(max_iterations=3)


def test_ordering_violation_no_progress_exceeds_iterations_raises() -> None:
    with pytest.raises(ValidationError):
        LoopControls(max_iterations=5, no_progress_threshold=6)


def test_ordering_violation_per_agent_exceeds_phase_raises() -> None:
    with pytest.raises(ValidationError):
        LoopControls(
            per_agent_timeout_seconds=20000.0,
            total_phase_timeout_seconds=14400.0,
        )


def test_tool_timeout_seconds_resolution() -> None:
    controls = LoopControls(tool_timeouts_seconds={"*": 60.0, "run": 5.5})
    assert controls.tool_timeout_seconds("run") == 5.5
    assert controls.tool_timeout_seconds("fmt") == 60.0
    assert LoopControls().tool_timeout_seconds("anything") == 120.0


def test_no_progress_detector_flips_at_threshold() -> None:
    detector = NoProgressDetector(3)
    assert detector.observe("F1-syntax") is False
    assert detector.observe("F1-syntax") is False
    assert detector.observe("F1-syntax") is True
    assert detector.consecutive == 3


def test_no_progress_detector_resets_on_different_signature() -> None:
    detector = NoProgressDetector(3)
    detector.observe("sig-a")
    detector.observe("sig-a")
    detector.observe("sig-b")
    assert detector.consecutive == 1
    assert detector.observe("sig-b") is False
    assert detector.observe("sig-b") is True
    assert detector.consecutive == 3


def test_no_progress_detector_reset() -> None:
    detector = NoProgressDetector(2)
    detector.observe("same")
    detector.observe("same")
    assert detector.consecutive == 2
    detector.reset()
    assert detector.consecutive == 0
    assert detector.observe("same") is False


def test_no_progress_detector_rejects_low_threshold() -> None:
    with pytest.raises(ValueError):
        NoProgressDetector(1)


def test_no_progress_detector_from_controls() -> None:
    controls = LoopControls(no_progress_threshold=2)
    detector = NoProgressDetector.from_controls(controls)
    assert detector.observe("x") is False
    assert detector.observe("x") is True


def test_iteration_budget_counts_and_flips_at_bounds() -> None:
    controls = LoopControls(
        max_iterations=2,
        max_command_count=3,
        max_repair_attempts=1,
        max_runtime_seconds=3600.0,
        no_progress_threshold=2,
    )
    budget = IterationBudget(controls)
    assert budget.iterations == 0
    assert budget.commands == 0
    assert budget.repairs == 0
    assert budget.started_at.tzinfo is not None
    assert budget.within_bounds() is True
    assert budget.blocked_reasons() == []

    budget.record_iteration()
    assert budget.iterations == 1
    assert budget.exceeded_iterations() is False

    budget.record_iteration()
    assert budget.iterations == 2
    assert budget.exceeded_iterations() is True

    budget.record_command()
    budget.record_command()
    budget.record_command()
    assert budget.commands == 3
    assert budget.exceeded_commands() is True

    budget.record_repair()
    assert budget.repairs == 1
    assert budget.exceeded_repairs() is True

    assert budget.exceeded_runtime() is False
    assert budget.exceeded_phase_timeout() is False
    assert budget.within_bounds() is False

    reasons = budget.blocked_reasons()
    assert len(reasons) == 3
    assert any("iteration" in reason for reason in reasons)
    assert any("command" in reason for reason in reasons)
    assert any("repair" in reason for reason in reasons)


class _FakeClock:
    """Deterministic stand-in for ``datetime`` inside loop_controls."""

    value: datetime

    def now(self, tz=UTC) -> datetime:
        assert tz is UTC
        return self.value


def test_iteration_budget_runtime_and_phase_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = _FakeClock()
    start = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    clock.value = start
    monkeypatch.setattr(loop_controls_module, "datetime", clock)

    runtime_budget = IterationBudget(
        LoopControls(
            max_runtime_seconds=60.0,
            total_phase_timeout_seconds=14400.0,
        )
    )
    assert runtime_budget.exceeded_runtime() is False
    clock.value = datetime(2026, 1, 1, 12, 1, 1, tzinfo=UTC)
    assert runtime_budget.elapsed_seconds() == 61.0
    assert runtime_budget.exceeded_runtime() is True
    assert runtime_budget.exceeded_phase_timeout() is False

    phase_budget = IterationBudget(
        LoopControls(
            max_runtime_seconds=120.0,
            total_phase_timeout_seconds=60.0,
            per_agent_timeout_seconds=30.0,
        )
    )
    assert phase_budget.exceeded_phase_timeout() is False
    clock.value = datetime(2026, 1, 1, 12, 2, 2, tzinfo=UTC)
    assert phase_budget.exceeded_phase_timeout() is True
    assert phase_budget.exceeded_runtime() is False
    assert any(
        "total_phase_timeout" in reason for reason in phase_budget.blocked_reasons()
    )
