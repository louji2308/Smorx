"""Phase 8.10 — Loop bounds.

Honors the configured budgets from the Phase 7 change definition:
maximum iterations, maximum runtime, maximum commands, maximum repair
attempts, no-progress threshold, per-tool timeout, per-agent timeout.
When a bound is reached the loop BLOCKS/STOPS — it never continues
indefinitely (master prompt §8.10, AGENTS.md §14).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

__all__ = ["BoundsExhaustedError", "LoopBounds", "LoopBoundsController"]


class BoundsExhaustedError(Exception):
    """Raised when a loop bound is exhausted; carries which bound and why."""

    def __init__(self, message: str, *, bound: str) -> None:
        super().__init__(message)
        self.bound = bound


@dataclass(frozen=True)
class LoopBounds:
    """Immutable budget configuration consumed by the repair loop."""

    max_iterations: int = 5
    max_runtime_seconds: int = 600
    max_commands: int = 40
    max_repair_attempts: int = 3
    no_progress_threshold: int = 2
    per_tool_timeout_seconds: int = 60
    per_agent_timeout_seconds: int = 300

    @classmethod
    def from_budget(cls, budget: dict[str, int]) -> LoopBounds:
        """Build bounds from a Phase 7 :class:`Budget` dict."""
        return cls(**budget)

    def as_dict(self) -> dict[str, int]:
        return {
            "max_iterations": self.max_iterations,
            "max_runtime_seconds": self.max_runtime_seconds,
            "max_commands": self.max_commands,
            "max_repair_attempts": self.max_repair_attempts,
            "no_progress_threshold": self.no_progress_threshold,
            "per_tool_timeout_seconds": self.per_tool_timeout_seconds,
            "per_agent_timeout_seconds": self.per_agent_timeout_seconds,
        }


@dataclass
class _MutableState:
    iteration: int = 0
    commands: int = 0
    repairs: int = 0
    started_at: float = field(default_factory=time.monotonic)
    recent_signatures: list[str] = field(default_factory=list)


class LoopBoundsController:
    """Bounded-loop controller: check() before every step, record() after."""

    def __init__(self, bounds: LoopBounds) -> None:
        self.bounds = bounds
        self._state = _MutableState()

    def check(self) -> None:
        """Raise :class:`BoundsExhaustedError` when any budget is exhausted."""
        state = self._state
        if state.iteration >= self.bounds.max_iterations:
            raise BoundsExhaustedError(
                f"maximum iterations reached ({self.bounds.max_iterations})", bound="max_iterations"
            )
        elapsed = time.monotonic() - state.started_at
        if elapsed >= self.bounds.max_runtime_seconds:
            raise BoundsExhaustedError(
                f"maximum runtime reached ({self.bounds.max_runtime_seconds}s)",
                bound="max_runtime_seconds",
            )
        if state.commands >= self.bounds.max_commands:
            raise BoundsExhaustedError(
                f"maximum commands reached ({self.bounds.max_commands})", bound="max_commands"
            )
        if state.repairs >= self.bounds.max_repair_attempts:
            raise BoundsExhaustedError(
                f"maximum repair attempts reached ({self.bounds.max_repair_attempts})",
                bound="max_repair_attempts",
            )

    def record_iteration(self) -> int:
        self._state.iteration += 1
        return self._state.iteration

    def record_command(self) -> int:
        self._state.commands += 1
        return self._state.commands

    def record_repair(self) -> int:
        self._state.repairs += 1
        return self._state.repairs

    def record_execution_signature(self, signature: str) -> bool:
        """Record a failure signature; return True when no-progress is hit.

        No-progress means: the threshold's worth of most recent failure
        signatures are materially equivalent (identical) — the loop is
        repeating without measurable progress and must stop.
        """
        state = self._state
        state.recent_signatures.append(signature)
        threshold = max(1, self.bounds.no_progress_threshold)
        if len(state.recent_signatures) >= threshold:
            recent = state.recent_signatures[-threshold:]
            if len(set(recent)) == 1:
                state.recent_signatures.clear()
                return True
        return False

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self._state.started_at

    def as_dict(self) -> dict[str, Any]:
        return {
            "bounds": {
                "max_iterations": self.bounds.max_iterations,
                "max_runtime_seconds": self.bounds.max_runtime_seconds,
                "max_commands": self.bounds.max_commands,
                "max_repair_attempts": self.bounds.max_repair_attempts,
                "no_progress_threshold": self.bounds.no_progress_threshold,
            },
            "used": {
                "iterations": self._state.iteration,
                "commands": self._state.commands,
                "repairs": self._state.repairs,
                "elapsed_seconds": round(self.elapsed_seconds(), 3),
            },
        }
