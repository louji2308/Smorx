"""Phase 12 — Workflow: Full System Integration + Demo Reliability.

Implements the end-to-end orchestration and reliability layer:

- E2E orchestration driver: runs the complete lifecycle through real
  packages using the deterministic demo scenario (12.1);
- state replay: replay from the stored run/evidence graph (12.4);
- failure injection: test failure, timeout, tool failure, policy block,
  conflicting evidence, no progress (12.5);
- demo reliability: resume, reset, phase replay, stale sandbox cleanup,
  idempotent endpoints, demo data isolation (12.6);
- performance: cache deterministic evidence, avoid redundant model calls,
  performance baseline (12.3).

The workflow consumes real certification and memory outputs from Phase 11;
it never certifies anything itself.
"""

from typing import Any

__all__ = [
    "DEFAULT_PHASES",
    "PHASE_EVENT_KINDS",
    "DemoScenario",
    "FailureInjectionMode",
    "InjectedFailure",
    "InjectionResult",
    "OrchestrationResult",
    "ReliabilityReport",
    "ReplayResult",
    "WorkflowError",
    "build_demo_scenario",
    "cache_deterministic_evidence",
    "cleanup_stale_sandboxes",
    "idempotency_guard",
    "inject_failure",
    "ordered_events",
    "read_cached_deterministic_evidence",
    "replay_from_evidence_graph",
    "reset_workflow",
    "resume_workflow",
    "run_e2e_workflow",
    "run_phases",
    "workflow_id",
]


def __getattr__(name: str) -> Any:
    if name in {
        "DEFAULT_PHASES",
        "DemoScenario",
        "OrchestrationResult",
        "PHASE_EVENT_KINDS",
        "WorkflowError",
        "build_demo_scenario",
        "cache_deterministic_evidence",
        "read_cached_deterministic_evidence",
        "run_e2e_workflow",
        "run_phases",
        "workflow_id",
    }:
        from smorx_workflow import orchestrate

        return getattr(orchestrate, name)
    if name in {
        "ReplayResult",
        "ordered_events",
        "replay_from_evidence_graph",
    }:
        from smorx_workflow import replay

        return getattr(replay, name)
    if name in {
        "ReliabilityReport",
        "cleanup_stale_sandboxes",
        "idempotency_guard",
        "resume_workflow",
        "reset_workflow",
    }:
        from smorx_workflow import reliability

        return getattr(reliability, name)
    if name in {
        "FailureInjectionMode",
        "InjectedFailure",
        "InjectionResult",
        "inject_failure",
    }:
        from smorx_workflow import failure_inject

        return getattr(failure_inject, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
