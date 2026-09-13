"""Phase 8 — Develop / Coding Agent / Real Sandbox Loop.

Implements the autonomous software-engineering loop on top of the Phase 7
pre-coding lock:

- pre-coding handoff and the execution barrier (8.1/8.2);
- structured repository inspection (8.3);
- explicit development plan (8.4);
- sandbox workflow with an honest UNAVAILABLE when no provider is bound (8.5);
- candidate patch workflow through controlled tools (8.6);
- machine-authoritative execution capture (8.7);
- the F1-F10 failure taxonomy with diagnosis-before-repair (8.8/8.9);
- bounded iterative repair (8.10) and evidence-based candidate
  comparison (8.11);
- attributable execution traces (8.12).

Model assertions never replace machine results; the candidate is never
certified here.
"""

from typing import Any

__all__ = [
    "BarrierError",
    "BarrierVerdict",
    "CandidateComparison",
    "CandidatePatchRecord",
    "CodingAgentError",
    "CodingAgentLoop",
    "Decision",
    "DecisionDirective",
    "DevelopmentPlan",
    "DevelopmentPlanError",
    "ExecutionBarrier",
    "ExecutionTrace",
    "HandoffError",
    "HandoffRecord",
    "InspectionError",
    "InspectionResult",
    "LoopBounds",
    "LoopResult",
    "build_candidate",
    "build_development_plan",
    "build_trace",
    "compare_candidates",
    "inspect_repository",
    "pre_coding_handoff",
    "verify_trace_integrity",
]


def __getattr__(name: str) -> Any:
    if name in {
        "BarrierError",
        "BarrierVerdict",
        "ExecutionBarrier",
    }:
        from smorx_develop import barrier

        return getattr(barrier, name)
    if name in {"HandoffError", "HandoffRecord", "pre_coding_handoff"}:
        from smorx_develop import handoff

        return getattr(handoff, name)
    if name in {"InspectionError", "InspectionResult", "inspect_repository"}:
        from smorx_develop import inspection

        return getattr(inspection, name)
    if name in {"DevelopmentPlan", "DevelopmentPlanError", "build_development_plan"}:
        from smorx_develop import plan

        return getattr(plan, name)
    if name in {
        "CandidateComparison",
        "CandidatePatchRecord",
        "build_candidate",
        "compare_candidates",
    }:
        from smorx_develop import candidates

        return getattr(candidates, name)
    if name in {"ExecutionTrace", "build_trace", "verify_trace_integrity"}:
        from smorx_develop import trace

        return getattr(trace, name)
    if name in {
        "CodingAgentError",
        "CodingAgentLoop",
        "Decision",
        "DecisionDirective",
        "LoopResult",
    }:
        from smorx_develop import agent

        return getattr(agent, name)
    if name in {"LoopBounds"}:
        from smorx_develop import bounds

        return getattr(bounds, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
