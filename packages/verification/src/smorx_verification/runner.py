"""Phase 9 — verification runner (orchestrates the module wave).

Builds one ModuleContext per module from a shared run configuration, executes
the configured modules concurrently, collects every module's OWN evidence, fuses
it at claim level, and emits the Phase 9 -> Phase 10 contract
(:class:`VerificationResult`). ``state == COMPLETED`` is the only state Phase
10 may consume; BLOCKED and INSUFFICIENT_EVIDENCE stop the pipeline
(AGENTS.md §10, §16, §17).
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable, Coroutine, Sequence
from dataclasses import dataclass, field
from typing import Any

from smorx_precode.verification_plan import VerificationPlanRef
from sqlalchemy.orm import Session

from smorx_verification.adversarial import run_adversarial_scenarios
from smorx_verification.boundary import VerificationActor
from smorx_verification.context import ModuleContext
from smorx_verification.contracts import (
    EvidenceRecord,
    ModuleOutcome,
    ModuleStatus,
    ModuleType,
    VerificationResult,
    now_utc,
)
from smorx_verification.differential import run_differential_execution
from smorx_verification.evidence import EvidenceCollector
from smorx_verification.fusion import fuse_claim_evidence
from smorx_verification.ghost_replay import run_historical_ghost_replay
from smorx_verification.metamorphic import run_metamorphic_checks
from smorx_verification.mutation import run_mutation_testing
from smorx_verification.static_analysis import run_static_analysis

__all__ = [
    "VerificationRunConfig",
    "run_verification_wave",
]

ModuleRunner = Callable[[ModuleContext], Coroutine[Any, Any, ModuleOutcome]]

_MODULE_RUNNERS: dict[ModuleType, ModuleRunner] = {
    ModuleType.STATIC_ANALYSIS: run_static_analysis,
    ModuleType.DIFFERENTIAL_EXECUTION: run_differential_execution,
    ModuleType.HISTORICAL_GHOST_REPLAY: run_historical_ghost_replay,
    ModuleType.METAMORPHIC_CHECK: run_metamorphic_checks,
    ModuleType.ADVERSARIAL_SCENARIO: run_adversarial_scenarios,
    ModuleType.MUTATION_TEST: run_mutation_testing,
}

_ALL_MODULES: tuple[ModuleType, ...] = tuple(_MODULE_RUNNERS)


@dataclass(frozen=True)
class VerificationRunConfig:
    """Configuration for one verification wave."""

    session: Session
    plan: VerificationPlanRef
    actor: VerificationActor
    candidate_root: str
    baseline_root: str | None = None
    run_id: str | None = None
    claim_ids: tuple[uuid.UUID, ...] = ()
    modules: tuple[ModuleType, ...] = _ALL_MODULES
    settings: dict[str, Any] = field(default_factory=dict)
    source: str = "verification_wave"

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan_id": str(self.plan.verification_plan_id),
            "plan_version": self.plan.version,
            "actor": self.actor.as_dict(),
            "candidate_root": self.candidate_root,
            "baseline_root": self.baseline_root,
            "run_id": self.run_id,
            "claim_ids": [str(claim_id) for claim_id in self.claim_ids],
            "modules": [module.value for module in self.modules],
            "source": self.source,
        }


def _overall_state(outcomes: Sequence[ModuleOutcome], evidence_count: int) -> str:
    """Derive the run state from module terminals.

    BLOCKED when any module could not act (missing baseline, etc.);
    INSUFFICIENT_EVIDENCE when nothing produced evidence; otherwise COMPLETED
    (PASSED and FAILED are both legitimate completed verifications — a failed
    module is real evidence, not a pipeline defect).
    """
    if any(outcome.status == ModuleStatus.BLOCKED for outcome in outcomes):
        return "BLOCKED"
    if evidence_count == 0:
        return "INSUFFICIENT_EVIDENCE"
    return "COMPLETED"


async def run_verification_wave(
    config: VerificationRunConfig,
) -> VerificationResult:
    """Execute the configured modules, fuse evidence, and emit the contract.

    Modules run concurrently; each reports its own status and evidence. The
    run is bounded by each module's own LoopBounds (timeouts come from the
    change budget). No module mutation of the candidate is possible through
    this path (the trust boundary is enforced by the boundary module).
    """
    run_id = config.run_id or f"verif-{uuid.uuid4()}"
    modules = tuple(module for module in config.modules if module in _MODULE_RUNNERS)
    outcomes: list[ModuleOutcome] = []
    evidence_records: list[EvidenceRecord] = []

    collector = EvidenceCollector(
        session=config.session,
        run_id=run_id,
        source=config.source,
    )

    async def _run_one(module_type: ModuleType) -> ModuleOutcome:
        context = ModuleContext(
            actor=config.actor,
            claim_ids=config.claim_ids,
            candidate_root=config.candidate_root,
            verification_case_id=config.plan.verification_plan_id,
            baseline_root=config.baseline_root,
            collector=collector,
            settings=config.settings,
        )
        outcome = await _MODULE_RUNNERS[module_type](context)
        return outcome

    outcomes = list(await asyncio.gather(*(_run_one(module) for module in modules)))
    evidence_records = list(collector.records)
    verdicts, _addressed, contradictions = fuse_claim_evidence(
        tuple(evidence_records),
        claim_ids=config.claim_ids,
    )

    summary_parts = [f"{outcome.module_type.value}={outcome.status.value}" for outcome in outcomes]
    state = _overall_state(tuple(outcomes), len(evidence_records))
    summary = (
        f"verification run {run_id}: {state}; "
        f"{len(evidence_records)} evidence record(s); " + ", ".join(summary_parts)
    )

    return VerificationResult(
        candidate_id=config.candidate_root,
        verification_plan_id=config.plan.verification_plan_id,
        plan_version=config.plan.version,
        run_id=run_id,
        change_id=config.plan.change_id,
        task_id=config.plan.task_id or uuid.uuid4(),
        modules=tuple(outcomes),
        evidence=tuple(evidence_records),
        claims=verdicts,
        contradictions=contradictions,
        state=state,
        summary=summary,
        timestamp=now_utc(),
    )
