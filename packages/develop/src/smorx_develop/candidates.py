"""Phase 8.11 — Candidate patches and evidence-based comparison.

A candidate is what the Coding Agent delivers; it is NEVER certified here
(I7). Where justified, multiple candidates run in isolation and are
compared using actual machine evidence — model preference alone is
insufficient (§8.11).

Selection rule: a candidate may be selected only when it passes all its
executions. Candidates are ranked by (passed, pass_ratio, fewer failures,
shorter total duration). Ties are broken by candidate index for
determinism. When every candidate fails, no selection is made and the
comparison reports BLOCKED with the evidence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from smorx_develop.agent import LoopResult
from smorx_develop.execution import ExecutionStats

__all__ = ["CandidateComparison", "CandidatePatchRecord", "build_candidate", "compare_candidates"]


@dataclass(frozen=True)
class CandidatePatchRecord:
    """One candidate's identity, trace, and machine evidence."""

    candidate_id: str
    candidate_index: int
    label: str
    loop_id: str
    sandbox_id: str
    sandbox_backend: str
    final_state: str
    result: LoopResult
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.final_state == "CANDIDATE_PASSED"

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_index": self.candidate_index,
            "label": self.label,
            "loop_id": self.loop_id,
            "sandbox_id": self.sandbox_id,
            "sandbox_backend": self.sandbox_backend,
            "final_state": self.final_state,
            "loop": self.result.as_dict(),
            "evidence": dict(self.evidence),
        }


def build_candidate(
    *,
    candidate_index: int,
    label: str,
    result: LoopResult,
    sandbox_id: str,
    sandbox_backend: str,
    evidence: dict[str, Any] | None = None,
) -> CandidatePatchRecord:
    """Wrap a finished loop result into a candidate record."""
    if candidate_index < 1:
        raise ValueError("candidate_index starts at 1")
    stats = ExecutionStats(result.executions).as_dict()
    return CandidatePatchRecord(
        candidate_id=f"cand-{uuid.uuid4().hex[:12]}",
        candidate_index=candidate_index,
        label=label,
        loop_id=result.loop_id,
        sandbox_id=sandbox_id,
        sandbox_backend=sandbox_backend,
        final_state=result.final_state,
        result=result,
        evidence={"execution_stats": stats, **(evidence or {})},
    )


@dataclass(frozen=True)
class CandidateComparison:
    """Objective, evidence-based comparison outcome."""

    selected_candidate_id: str | None
    outcome: str  # SELECTED | ALL_FAILED | NO_CANDIDATES
    detail: str
    ranked: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "selected_candidate_id": self.selected_candidate_id,
            "outcome": self.outcome,
            "detail": self.detail,
            "ranked": [dict(item) for item in self.ranked],
        }


def _rank_key(candidate: CandidatePatchRecord) -> tuple[int, int, float, float, int]:
    """Rank: completion first, then fewer failures, then faster total
    execution, then the deterministic candidate index."""
    stats = ExecutionStats(candidate.result.executions)
    return (
        0 if candidate.passed else 1,
        stats.failed,
        sum(record.duration_seconds for record in candidate.result.executions),
        -stats.passed,
        candidate.candidate_index,
    )


def compare_candidates(
    candidates: list[CandidatePatchRecord],
) -> CandidateComparison:
    """Compare candidates using actual evidence; never model preference."""
    if not candidates:
        return CandidateComparison(
            selected_candidate_id=None,
            outcome="NO_CANDIDATES",
            detail="no candidates were produced",
            ranked=(),
        )
    ranked = sorted(candidates, key=_rank_key)
    ranked_view = tuple(
        {
            "candidate_id": candidate.candidate_id,
            "candidate_index": candidate.candidate_index,
            "label": candidate.label,
            "final_state": candidate.final_state,
            "execution_stats": ExecutionStats(candidate.result.executions).as_dict(),
            "termination": candidate.result.termination.as_dict(),
        }
        for candidate in ranked
    )
    best = ranked[0]
    if not best.passed:
        return CandidateComparison(
            selected_candidate_id=None,
            outcome="ALL_FAILED",
            detail="every candidate failed; no selection is made (evidence-based rule)",
            ranked=ranked_view,
        )
    return CandidateComparison(
        selected_candidate_id=best.candidate_id,
        outcome="SELECTED",
        detail=f"candidate {best.candidate_index} ({best.label}) selected: "
        f"{best.final_state} with machine-captured passing executions",
        ranked=ranked_view,
    )
