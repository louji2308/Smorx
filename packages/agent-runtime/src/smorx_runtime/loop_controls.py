"""Bounded execution-loop controls for the agent runtime.

The autonomous agent is never allowed to retry forever
(``Requirements & Contract.md`` section 10, LOOP-CONTRACT-01).  This module
provides:

* :class:`LoopControls` -- validated, environment-overridable execution
  bounds and per-tool timeouts.
* :class:`NoProgressDetector` -- detects materially equivalent repeated
  failures so the agent BLOCKS instead of spinning.
* :class:`IterationBudget` -- an instrumented runtime counter that reports
  the first bounds that were exceeded.

Environment overrides use the ``SMORX_LOOP_`` prefix (see
:func:`LoopControls.from_env`).  ``LoopControls.for_env("development")`` keeps
the permissive development-safe defaults; every other app environment
receives the strict production profile because an uncontrolled autonomous
loop is never acceptable in production.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError

LOOP_ENV_PREFIX: str = "SMORX_LOOP_"


class LoopControlError(Exception):
    """Raised when an environment-derived loop-control value is invalid."""


class LoopControls(BaseModel):
    """Validated bounds for the agent execution loop (development-safe defaults).

    Semantics of the bounds:

    * ``max_iterations`` -- maximum recorded iterations before the loop is
      blocked.
    * ``max_runtime_seconds`` -- maximum wall-clock runtime for one run.
    * ``max_command_count`` -- maximum recorded tool/command invocations.
    * ``max_repair_attempts`` -- maximum recorded repair attempts.
    * ``no_progress_threshold`` -- consecutive materially identical failures
      after which BLOCK is recommended.
    * ``tool_timeouts_seconds`` -- per-tool timeout overrides keyed by tool
      name; ``"*"`` is the global default.
    * ``per_agent_timeout_seconds`` -- max runtime for one sub-agent.
    * ``total_phase_timeout_seconds`` -- max runtime for the whole phase.

    Validation invariants: ``max_repair_attempts <= max_iterations``,
    ``no_progress_threshold <= max_iterations`` and
    ``per_agent_timeout_seconds <= total_phase_timeout_seconds``.
    """

    max_iterations: int = Field(default=25, ge=1)
    max_runtime_seconds: float = Field(default=7200.0, gt=0)
    max_command_count: int = Field(default=200, ge=1)
    max_repair_attempts: int = Field(default=5, ge=0)
    no_progress_threshold: int = Field(default=3, ge=2)
    tool_timeouts_seconds: dict[str, float] = Field(default_factory=lambda: {"*": 120.0})
    per_agent_timeout_seconds: float = Field(default=1800.0, gt=0)
    total_phase_timeout_seconds: float = Field(default=14400.0, gt=0)

    @field_validator("tool_timeouts_seconds")
    @classmethod
    def _check_tool_timeouts(cls, timeouts: dict[str, float]) -> dict[str, float]:
        for tool, seconds in timeouts.items():
            if seconds <= 0:
                raise ValueError(f"tool timeout for {tool!r} must be > 0, got {seconds}")
        return timeouts

    @model_validator(mode="after")
    def _check_bound_ordering(self) -> Self:
        if self.max_repair_attempts > self.max_iterations:
            raise ValueError(
                f"max_repair_attempts={self.max_repair_attempts} must be "
                f"<= max_iterations={self.max_iterations}"
            )
        if self.no_progress_threshold > self.max_iterations:
            raise ValueError(
                f"no_progress_threshold={self.no_progress_threshold} must be "
                f"<= max_iterations={self.max_iterations}"
            )
        if self.per_agent_timeout_seconds > self.total_phase_timeout_seconds:
            raise ValueError(
                f"per_agent_timeout_seconds={self.per_agent_timeout_seconds} must be "
                f"<= total_phase_timeout_seconds={self.total_phase_timeout_seconds}"
            )
        return self

    def tool_timeout_seconds(self, tool_name: str) -> float:
        timeout = self.tool_timeouts_seconds.get(tool_name)
        if timeout is None:
            timeout = self.tool_timeouts_seconds.get("*", 120.0)
        return timeout

    @classmethod
    def for_env(cls, app_env: str) -> LoopControls:
        """Return loop controls for an app environment.

        ``development`` keeps the permissive defaults.  Anything else returns
        the intentionally conservative production profile: an uncontrolled
        loop is never acceptable in production.
        """
        if app_env == "development":
            return cls()
        return cls(
            max_iterations=8,
            max_runtime_seconds=1800.0,
            max_command_count=60,
            max_repair_attempts=2,
            no_progress_threshold=2,
            tool_timeouts_seconds={"*": 60.0},
            per_agent_timeout_seconds=600.0,
            total_phase_timeout_seconds=3600.0,
        )

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        prefix: str = LOOP_ENV_PREFIX,
        base: LoopControls | None = None,
    ) -> LoopControls:
        """Build loop controls from environment overrides.

        Recognized keys (``<prefix>`` defaults to ``SMORX_LOOP_``):

        * ``<prefix>MAX_ITERATIONS``
        * ``<prefix>MAX_RUNTIME_SECONDS``
        * ``<prefix>MAX_COMMAND_COUNT``
        * ``<prefix>MAX_REPAIR_ATTEMPTS``
        * ``<prefix>NO_PROGRESS_THRESHOLD``
        * ``<prefix>TOOL_TIMEOUTS_SECONDS`` (JSON object, per-tool overrides)
        * ``<prefix>PER_AGENT_TIMEOUT_SECONDS``
        * ``<prefix>TOTAL_PHASE_TIMEOUT_SECONDS``

        Unset keys keep the ``base`` values.  Invalid values raise
        :class:`LoopControlError`.
        """
        source: Mapping[str, str] = os.environ if environ is None else environ
        start: LoopControls = base or cls()
        values: dict[str, Any] = start.model_dump()

        int_keys = {
            "MAX_ITERATIONS": "max_iterations",
            "MAX_COMMAND_COUNT": "max_command_count",
            "MAX_REPAIR_ATTEMPTS": "max_repair_attempts",
            "NO_PROGRESS_THRESHOLD": "no_progress_threshold",
        }
        float_keys = {
            "MAX_RUNTIME_SECONDS": "max_runtime_seconds",
            "PER_AGENT_TIMEOUT_SECONDS": "per_agent_timeout_seconds",
            "TOTAL_PHASE_TIMEOUT_SECONDS": "total_phase_timeout_seconds",
        }
        for suffix, field in int_keys.items():
            raw = source.get(prefix + suffix)
            if raw is None:
                continue
            try:
                values[field] = int(raw)
            except ValueError as exc:
                raise LoopControlError(f"{prefix}{suffix}={raw!r} is not an integer") from exc
        for suffix, field in float_keys.items():
            raw = source.get(prefix + suffix)
            if raw is None:
                continue
            try:
                values[field] = float(raw)
            except ValueError as exc:
                raise LoopControlError(f"{prefix}{suffix}={raw!r} is not a number") from exc

        raw_timeouts = source.get(prefix + "TOOL_TIMEOUTS_SECONDS")
        if raw_timeouts is not None:
            try:
                parsed = json.loads(raw_timeouts)
            except json.JSONDecodeError as exc:
                raise LoopControlError(
                    f"{prefix}TOOL_TIMEOUTS_SECONDS={raw_timeouts!r} is not valid JSON"
                ) from exc
            if not isinstance(parsed, dict):
                raise LoopControlError(
                    f"{prefix}TOOL_TIMEOUTS_SECONDS must be a JSON object, "
                    f"got {type(parsed).__name__}"
                )
            converted: dict[str, float] = {}
            for tool, seconds in parsed.items():
                if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
                    raise LoopControlError(
                        f"tool timeout for {tool!r} must be a number, got {seconds!r}"
                    )
                converted[str(tool)] = float(seconds)
            values["tool_timeouts_seconds"] = {
                **start.tool_timeouts_seconds,
                **converted,
            }

        try:
            return cls(**values)
        except PydanticValidationError as exc:
            raise LoopControlError(
                f"invalid loop-control configuration from environment: {exc}"
            ) from exc


class NoProgressDetector:
    """Detects consecutive materially equivalent failure signatures.

    Feeding the same failure signature ``threshold`` times in a row reports
    "no progress" (returns ``True``).  A different signature resets the
    consecutive counter.
    """

    def __init__(self, threshold: int) -> None:
        if threshold < 2:
            raise ValueError(f"threshold must be >= 2, got {threshold}")
        self._threshold = threshold
        self._signature: str | None = None
        self._consecutive = 0

    @property
    def consecutive(self) -> int:
        return self._consecutive

    def observe(self, signature: str) -> bool:
        if signature == self._signature:
            self._consecutive += 1
        else:
            self._signature = signature
            self._consecutive = 1
        return self._consecutive >= self._threshold

    def reset(self) -> None:
        self._signature = None
        self._consecutive = 0

    @classmethod
    def from_controls(cls, controls: LoopControls) -> NoProgressDetector:
        return cls(controls.no_progress_threshold)


class IterationBudget:
    """Runtime accounting for the bounded execution loop.

    The budget records real counters and reports why the loop should be
    blocked.  Every ``exceeded_*`` helper flips to ``True`` once the recorded
    value reaches the corresponding bound (the bound is an inclusive cap).
    """

    def __init__(self, controls: LoopControls) -> None:
        self._controls = controls
        self._iterations = 0
        self._commands = 0
        self._repairs = 0
        self._started_at = datetime.now(UTC)

    @property
    def iterations(self) -> int:
        return self._iterations

    @property
    def commands(self) -> int:
        return self._commands

    @property
    def repairs(self) -> int:
        return self._repairs

    @property
    def started_at(self) -> datetime:
        return self._started_at

    def record_iteration(self) -> None:
        self._iterations += 1

    def record_command(self) -> None:
        self._commands += 1

    def record_repair(self) -> None:
        self._repairs += 1

    def elapsed_seconds(self) -> float:
        return (datetime.now(UTC) - self._started_at).total_seconds()

    def exceeded_iterations(self) -> bool:
        return self._iterations >= self._controls.max_iterations

    def exceeded_commands(self) -> bool:
        return self._commands >= self._controls.max_command_count

    def exceeded_repairs(self) -> bool:
        return self._repairs >= self._controls.max_repair_attempts

    def exceeded_runtime(self) -> bool:
        return self.elapsed_seconds() >= self._controls.max_runtime_seconds

    def exceeded_phase_timeout(self) -> bool:
        return self.elapsed_seconds() >= self._controls.total_phase_timeout_seconds

    def within_bounds(self) -> bool:
        return not self.blocked_reasons()

    def blocked_reasons(self) -> list[str]:
        reasons: list[str] = []
        elapsed = self.elapsed_seconds()
        if self.exceeded_iterations():
            reasons.append(
                f"max_iterations exceeded: {self._iterations} recorded, "
                f"limit {self._controls.max_iterations}"
            )
        if self.exceeded_commands():
            reasons.append(
                f"max_command_count exceeded: {self._commands} recorded, "
                f"limit {self._controls.max_command_count}"
            )
        if self.exceeded_repairs():
            reasons.append(
                f"max_repair_attempts exceeded: {self._repairs} recorded, "
                f"limit {self._controls.max_repair_attempts}"
            )
        if self.exceeded_runtime():
            reasons.append(
                f"max_runtime_seconds exceeded: {elapsed:.1f}s elapsed, "
                f"limit {self._controls.max_runtime_seconds}s"
            )
        if self.exceeded_phase_timeout():
            reasons.append(
                f"total_phase_timeout_seconds exceeded: {elapsed:.1f}s elapsed, "
                f"limit {self._controls.total_phase_timeout_seconds}s"
            )
        return reasons
