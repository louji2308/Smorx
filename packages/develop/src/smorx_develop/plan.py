"""Phase 8.4 — Explicit Development Plan.

Before modifying any file, the Coding Agent must produce an explicit plan
(master prompt §8.4): interpretation, affected components and files,
implementation strategy, tests to run, completion criteria, expected risk,
and expected verification. The plan is validated for completeness — a plan
without completion criteria or test targets is rejected, so the loop cannot
descend into unanchored editing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["DevelopmentPlan", "DevelopmentPlanError", "build_development_plan"]

_VALID_RISKS: frozenset[str] = frozenset({"LOW", "MEDIUM", "HIGH"})


class DevelopmentPlanError(Exception):
    """Raised when a development plan is incomplete or malformed."""


@dataclass(frozen=True)
class DevelopmentPlan:
    """The explicit, validated plan the Coding Agent must produce first."""

    interpretation: str
    affected_components: tuple[str, ...]
    affected_files: tuple[str, ...]
    implementation_strategy: str
    tests_to_run: tuple[str, ...]
    completion_criteria: tuple[str, ...]
    expected_risk: str
    expected_verification: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "interpretation": self.interpretation,
            "affected_components": list(self.affected_components),
            "affected_files": list(self.affected_files),
            "implementation_strategy": self.implementation_strategy,
            "tests_to_run": list(self.tests_to_run),
            "completion_criteria": list(self.completion_criteria),
            "expected_risk": self.expected_risk,
            "expected_verification": list(self.expected_verification),
        }


def _require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise DevelopmentPlanError(f"development plan field {field_name!r} must be non-empty")
    return cleaned


def build_development_plan(
    *,
    interpretation: str,
    affected_components: list[str],
    affected_files: list[str],
    implementation_strategy: str,
    tests_to_run: list[str],
    completion_criteria: list[str],
    expected_risk: str = "MEDIUM",
    expected_verification: list[str] | None = None,
) -> DevelopmentPlan:
    """Validate and return the explicit plan; raises on incompleteness.

    Required by contract (§8.4): interpretation, strategy, at least one
    affected file, at least one test to run, at least one completion
    criterion. ``expected_risk`` must be LOW/MEDIUM/HIGH. The plan is a
    pure value — the Coding Agent produces it before any mutation and the
    loop records it on the run's trace.
    """
    cleaned_interpretation = _require_non_empty(interpretation, "interpretation")
    cleaned_strategy = _require_non_empty(implementation_strategy, "implementation_strategy")

    components = tuple(item.strip() for item in affected_components if item.strip())
    files = tuple(item.strip() for item in affected_files if item.strip())
    tests = tuple(item.strip() for item in tests_to_run if item.strip())
    criteria = tuple(item.strip() for item in completion_criteria if item.strip())
    verification = tuple(item.strip() for item in (expected_verification or []) if item.strip())

    if not files:
        raise DevelopmentPlanError(
            "development plan must name at least one affected file (no blind editing)"
        )
    if not tests:
        raise DevelopmentPlanError(
            "development plan must name at least one test to run (no unanchored editing)"
        )
    if not criteria:
        raise DevelopmentPlanError(
            "development plan must declare at least one completion criterion"
        )
    risk = expected_risk.strip().upper()
    if risk not in _VALID_RISKS:
        raise DevelopmentPlanError(
            f"expected_risk must be one of {sorted(_VALID_RISKS)}, got {expected_risk!r}"
        )

    return DevelopmentPlan(
        interpretation=cleaned_interpretation,
        affected_components=components,
        affected_files=files,
        implementation_strategy=cleaned_strategy,
        tests_to_run=tests,
        completion_criteria=criteria,
        expected_risk=risk,
        expected_verification=verification,
    )
