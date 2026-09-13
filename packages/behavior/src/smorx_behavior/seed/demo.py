"""Deterministic demo seed dataset for the behavioral persistence layer.

Phase 2 (implementation plan section "Integration Wave"): this is the
documented demo/scenario fixture — explicitly NOT production behavior and NOT
real repository execution evidence. The dataset is:

- **deterministic** — every governed key id is ``uuid5``-derived from a fixed
  namespace and fixed tokens, so seed output is identical on every run;
  evidence identity is content-addressed (fixed SHA-256 hashes);
- **idempotent** — re-running against a populated database reuses existing
  rows instead of duplicating them, returning identical key ids;
- **clearly marked** as demo data via ``Project.meta`` and the seed package
  docstrings (AGENTS.md section 39: a reproducible test fixture is not a fake
  production success path).

Scenario (implementation plan): project "Payments API" owns the change
exposing Change #184; the task "AUTH-017" requires the token-refresh endpoint
to reject forged requests; historical replay "Ghost #221" and persisted
failure "F-183" are preserved as historical evidence; a certificate binds the
evidence + behavioral delta + change, and a memory update closes the loop.

Evidence rows are recorded through
``smorx_behavior.evidence.service.record_evidence`` (the canonical entry
point) with fixed content hashes; when that service is not yet importable the
seed falls back to ``smorx_behavior.repo.base.ensure_evidence``.
"""

from __future__ import annotations

import argparse
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import (
    AgentRun,
    Behavior,
    BehavioralDelta,
    CandidatePatch,
    Certificate,
    Change,
    Claim,
    ConsequentialEvent,
    EventKind,
    EvidenceType,
    Execution,
    Failure,
    FailureKind,
    Ghost,
    IntentAlignment,
    IntentItem,
    IntentLedger,
    MemoryKind,
    MemoryUpdate,
    Project,
    RepairPackage,
    Repository,
    Run,
    SubagentRun,
    Task,
    VerificationCase,
    VerificationPlan,
)
from smorx_behavior.repo.base import digest, ensure_evidence

__all__ = ["SEED_NAMESPACE", "DemoReport", "build_seed", "main"]

#: Fixed UUID namespace for every deterministic seed identity (never changes).
SEED_NAMESPACE = uuid.UUID("2e2f0c8a-8a3b-4c5d-9e6f-1b2c3d4e5f61")

#: Fixed timestamps so seeded rows carry identical observables each run.
T0 = datetime(2026, 6, 14, 8, 0, 0, tzinfo=UTC)
T1 = datetime(2026, 6, 14, 8, 12, 0, tzinfo=UTC)
T2 = datetime(2026, 6, 14, 8, 45, 0, tzinfo=UTC)
T3 = datetime(2026, 6, 14, 9, 5, 0, tzinfo=UTC)
T4 = datetime(2026, 6, 14, 9, 40, 0, tzinfo=UTC)

try:  # canonical evidence entry point (landed by the evidence agent)
    from smorx_behavior.evidence.service import record_evidence

    EVIDENCE_BACKEND = "smorx_behavior.evidence.service.record_evidence"
except ImportError:  # pragma: no cover - only until the evidence agent lands
    record_evidence = None  # type: ignore[assignment]
    EVIDENCE_BACKEND = "smorx_behavior.repo.base.ensure_evidence (fallback)"


def _id(token: str) -> uuid.UUID:
    """Return the deterministic primary key for ``token``."""
    return uuid.uuid5(SEED_NAMESPACE, token)


def _record_evidence(
    session: Session,
    *,
    content_hash: str,
    evidence_type: EvidenceType,
    occurred_at: datetime,
    source: str,
    provenance: str,
    artifact: str,
    machine_result: dict[str, Any],
    task: Task | None = None,
    run: Run | None = None,
    agent_run: AgentRun | None = None,
    subagent_run: SubagentRun | None = None,
    execution: Execution | None = None,
    verification_case: VerificationCase | None = None,
    claim: Claim | None = None,
) -> Any:
    """Record one evidence row through the canonical service when available."""
    bindings = {
        "task_id": task.id if task is not None else None,
        "run_id": run.id if run is not None else None,
        "agent_run_id": agent_run.id if agent_run is not None else None,
        "subagent_run_id": subagent_run.id if subagent_run is not None else None,
        "execution_id": execution.id if execution is not None else None,
        "verification_case_id": (verification_case.id if verification_case is not None else None),
        "claim_id": claim.id if claim is not None else None,
    }
    if record_evidence is not None:
        return record_evidence(
            session,
            evidence_type=evidence_type,
            occurred_at=occurred_at,
            source=source,
            provenance=provenance,
            artifact=artifact,
            machine_result=machine_result,
            content_hash=content_hash,
            **bindings,
        )
    return ensure_evidence(
        session,
        content_hash=content_hash,
        type=evidence_type.value if isinstance(evidence_type, Enum) else evidence_type,
        occurred_at=occurred_at,
        source=source,
        provenance=provenance,
        artifact=artifact,
        machine_result=machine_result,
        **bindings,
    )


@dataclass(frozen=True)
class DemoReport:
    """Stable, machine-readable outcome of :func:`build_seed`."""

    scenario: str
    project_id: uuid.UUID
    repository_id: uuid.UUID
    change_id: uuid.UUID
    task_id: uuid.UUID
    run_id: uuid.UUID
    agent_run_id: uuid.UUID
    subagent_run_ids: tuple[uuid.UUID, ...]
    behavior_id: uuid.UUID
    ghost_id: uuid.UUID
    failure_id: uuid.UUID
    claim_id: uuid.UUID
    delta_id: uuid.UUID
    certificate_id: uuid.UUID
    memory_update_id: uuid.UUID
    evidence_ids: tuple[uuid.UUID, ...]
    evidence_hashes: tuple[str, ...]
    counts: dict[str, int]
    evidence_backend: str

    def key_tokens(self) -> dict[str, Any]:
        """Return the scenario tokens and their resolved ids/hashes."""
        return {
            "project": "Payments API",
            "change": "184",
            "task": "AUTH-017",
            "ghost": "Ghost #221",
            "failure": "F-183",
            "change_id": self.change_id,
            "task_id": self.task_id,
            "ghost_id": self.ghost_id,
            "failure_id": self.failure_id,
            "certificate_id": self.certificate_id,
            "evidence_hashes": list(self.evidence_hashes),
            "evidence_backend": self.evidence_backend,
        }

    def summary(self) -> str:
        """Render a compact human-readable report for ``--print``."""
        tokens = self.key_tokens()
        lines = [
            f"scenario={self.scenario}",
            f"evidence_backend={self.evidence_backend}",
            "tokens: " + ", ".join(f"{k}={v}" for k, v in tokens.items()),
            f"counts: {self.counts}",
        ]
        return "\n".join(lines)


def build_seed(session: Session) -> DemoReport:
    """Seed (or reuse) the deterministic demo scenario and return its report.

    Idempotent: any row whose deterministic id already exists is reused
    unchanged, so a second run returns identical key ids without duplicates.
    The caller owns the transaction boundary; this function commits.
    """
    total_rows = 0

    def row(cls: type[Any], token: str, **attrs: Any) -> Any:
        """Get-or-create a row by its deterministic id, flushing for FKs."""
        nonlocal total_rows
        total_rows += 1
        key = _id(token)
        existing = session.get(cls, key)
        if existing is not None:
            return existing
        instance = cls(id=key, **attrs)
        session.add(instance)
        session.flush()
        return instance

    # ---- governance + delivery graph -------------------------------------
    project = row(
        Project,
        "demo/project/payments-api",
        name="Payments API",
        slug="payments-api",
        description="Demo scenario: AUTH-017 token-refresh hardening (Change #184).",
        meta={"seed": "demo", "scenario": "AUTH-017", "demo_data": True},
    )
    repository = row(
        Repository,
        "demo/repo/payments-api",
        project=project,
        name="smorx/payments-api",
        url="https://github.com/smorx/payments-api",
        default_branch="main",
        vcs="git",
        meta={"seed": "demo"},
    )
    change = row(
        Change,
        "demo/change/184",
        repository=repository,
        external_id="184",
        commit_sha=digest("seed/change/184/commit")[:40],
        author="coding-agent",
        title="AUTH-017 token refresh must reject forged requests",
        description="Harden the refresh-token endpoint against forged request acceptance.",
        status="MERGED",
        changed_at=T3,
        version=1,
        locked=False,
    )
    behavior = row(
        Behavior,
        "demo/behavior/token-refresh",
        repository=repository,
        origin_change=change,
        name="auth token refresh",
        description="Refresh-token rotation and forged-request rejection.",
        category="SECURITY",
        protected=True,
        signature="auth/token/refresh",
        discovered_at=T0,
        version=1,
        locked=False,
    )
    task = row(
        Task,
        "demo/task/AUTH-017",
        project=project,
        repository=repository,
        change=change,
        title="AUTH-017 - token refresh must reject forged requests",
        description="A forged refresh token (signed with an out-of-tenant key) is accepted and rotates state.",
        status="VERIFIED",
        priority="HIGH",
        requested_by="Platform Security",
        acceptance_criteria=[
            "A forged refresh token returns 401",
            "Tenant isolation is preserved across refresh",
            "Replayed Ghost #221 scenario passes",
        ],
        version=1,
        locked=False,
    )
    intent_ledger = row(
        IntentLedger,
        "demo/intent-ledger/AUTH-017",
        project=project,
        task=task,
        title="AUTH-017 intentional change ledger",
        source="HUMAN",
        status="SATISFIED",
        owner_scope="USER_INTENT",
        created_by="platform-security",
        version=1,
        locked=True,
    )
    intent_item = row(
        IntentItem,
        "demo/intent-item/AUTH-017/reject-forged",
        intent_ledger=intent_ledger,
        task=task,
        statement="The token-refresh endpoint MUST reject forged/expired refresh tokens.",
        kind="CONSTRAINT",
        priority="CRITICAL",
        status="SATISFIED",
        authorized=True,
        source_ref="ticket/AUTH-017",
    )

    # ---- execution graph ---------------------------------------------------
    run = row(
        Run,
        "demo/run/AUTH-017",
        task=task,
        kind="AGENT",
        status="COMPLETED",
        summary="Full AUTH-017 engineer loop: inspect, plan, code, test, repair, verify.",
        started_at=T0,
        finished_at=T4,
        environment={"provider": "nebius", "sandbox": "token-factory", "runtime": "sqlite-demo"},
    )
    agent_run = row(
        AgentRun,
        "demo/agent-run/orchestrator/AUTH-017",
        run=run,
        role="ORCHESTRATOR",
        model="nvidia/nemotron-4-340b-instruct",
        provider="nebius-token-factory",
        status="COMPLETED",
        state="VERIFIED",
        iterations=5,
        max_iterations=8,
        duration_ms=21400,
        token_usage={"total_tokens": 38210, "completion_tokens": 12055},
        plan={
            "steps": ["inspect", "plan", "code", "test", "repair", "reverify"],
            "exit": "certify",
        },
    )
    subagent_archaeology = row(
        SubagentRun,
        "demo/subagent/archaeology/AUTH-017",
        agent_run=agent_run,
        name="Failure Archaeology Agent",
        responsibility="Extract execution trace and persist Failure F-183 evidence.",
        status="COMPLETED",
        inputs={"crash_context": "run/exec-1", "sandbox": "token-factory"},
        outputs={"failure_id": "F-183", "classification": "F3_INTEGRATION"},
        confidence=0.92,
        evidence_ref="evidence://demo/f-183/execution-trace",
        started_at=T0,
        finished_at=T1,
    )
    subagent_verification = row(
        SubagentRun,
        "demo/subagent/verification/AUTH-017",
        agent_run=agent_run,
        name="Independent Verification Agent",
        responsibility="Replay Ghost #221 and adversarial forged-token scenarios.",
        status="COMPLETED",
        inputs={"plan_id": str(_id("demo/verification-plan/AUTH-017"))},
        outputs={"ghost_221_lab": "PASS", "adversarial_14_lab": "PASS"},
        confidence=0.97,
        evidence_ref="evidence://demo/ghost-221/replay",
        started_at=T2,
        finished_at=T3,
    )
    subagent_certification = row(
        SubagentRun,
        "demo/subagent/certification/AUTH-017",
        agent_run=agent_run,
        name="Certification Agent",
        responsibility="Bind change/evidence/delta/intent into the final certificate.",
        status="COMPLETED",
        inputs={"change_id": str(_id("demo/change/184"))},
        outputs={"certificate_key": digest("seed/certificate/change/184/AUTH-017")},
        confidence=0.95,
        evidence_ref="evidence://demo/auth-017/certificate-binding",
        started_at=T3,
        finished_at=T4,
    )

    # ---- archaeology: ghost + historical failure ---------------------------
    ghost = row(
        Ghost,
        "demo/ghost/221",
        repository=repository,
        behavior=behavior,
        source_change=change,
        name="Ghost #221",
        description="Replay of the forged-refresh-token historical scenario.",
        hypothetical=True,
        status="PASSED",
        payload={
            "scenario": "forged_refresh_rotation",
            "before": "FAIL",
            "after": "PASS",
            "exit_code_before": 1,
            "exit_code_after": 0,
            "evidence": digest("seed/evidence/ghost-221/replay")[:16],
        },
        version=1,
    )

    # ---- verification contract ---------------------------------------------
    verification_plan = row(
        VerificationPlan,
        "demo/verification-plan/AUTH-017",
        change=change,
        task=task,
        intent_ledger=intent_ledger,
        title="AUTH-017 verification contract",
        strategy={
            "modules": ["historical_ghost_replay", "adversarial_scenario", "static_analysis"],
            "independent": True,
        },
        verification_contract={
            "ghost": ["221"],
            "acceptance": task.acceptance_criteria,
        },
        status="COMPLETED",
        owner_scope="VERIFICATION_CONTRACT",
        created_by="verification-planner",
        version=1,
        locked=True,
    )
    vc_ghost = row(
        VerificationCase,
        "demo/verification-case/ghost-221",
        verification_plan=verification_plan,
        change=change,
        name="Historical Ghost Replay #221",
        kind=EvidenceType.HISTORICAL_GHOST_REPLAY,
        description="Re-run the forged-refresh-token historical scenario against the candidate.",
        method="pytest replay fixture reusing Ghost #221 payload",
        expected="forged refresh rejected (401)",
        threshold=0.0,
        status="PASSED",
        independent=True,
        owning_module="historical_ghost_replay",
        version=1,
        locked=False,
    )
    vc_adversarial = row(
        VerificationCase,
        "demo/verification-case/adversarial-refresh",
        verification_plan=verification_plan,
        change=change,
        name="Adversarial forged-refresh-token",
        kind=EvidenceType.ADVERSARIAL_SCENARIO,
        description="Attempt to rotate state with a cross-tenant forged refresh token.",
        method="adversarial tenant-switch harness",
        expected="all forged attempts rejected",
        threshold=0.0,
        status="PASSED",
        independent=True,
        owning_module="adversarial_scenario",
        version=1,
        locked=False,
    )
    row(
        VerificationCase,
        "demo/verification-case/static-token-refresh",
        verification_plan=verification_plan,
        change=change,
        name="Static analysis token-refresh path",
        kind=EvidenceType.STATIC_ANALYSIS,
        description="Static scan of the refresh handler for signature-check bypasses.",
        method="static analyzer over src/auth/token_refresh.py",
        expected="no critical findings",
        threshold=1.0,
        status="PASSED",
        independent=True,
        owning_module="static_analysis",
        version=1,
        locked=False,
    )

    # ---- development plane ---------------------------------------------------
    patch_1 = row(
        CandidatePatch,
        "demo/candidate/AUTH-017/1",
        change=change,
        task=task,
        agent_run=agent_run,
        base_commit=digest("seed/change/184/base-commit")[:40],
        patch_ref="candidates/AUTH-017/patch-1.diff",
        diff='--- a/src/auth/token_refresh.py\n+++ b/src/auth/token_refresh.py\n-payload.claims["tenant"]\n+verify_sig(payload)\n',
        files_changed=["src/auth/token_refresh.py"],
        summary="Candidate #1: naive tenant claim trust; F-183 observed.",
        status="FAILED",
        candidate_index=1,
        proposed_by="coding-agent",
        owner_scope="DEVELOPMENT_OUTPUT",
        version=1,
        locked=False,
    )
    patch_2 = row(
        CandidatePatch,
        "demo/candidate/AUTH-017/2",
        change=change,
        task=task,
        agent_run=agent_run,
        base_commit=digest("seed/change/184/base-commit")[:40],
        patch_ref="candidates/AUTH-017/patch-2.diff",
        diff="--- a/src/auth/token_refresh.py\n+++ b/src/auth/token_refresh.py\n+verify_sig(payload, issuer, forbidden_tenants)\n",
        files_changed=["src/auth/token_refresh.py", "tests/test_auth_017.py"],
        summary="Candidate #2: verifies signature and issuer before tenant wiring.",
        status="VERIFIED",
        candidate_index=2,
        proposed_by="coding-agent",
        owner_scope="DEVELOPMENT_OUTPUT",
        version=1,
        locked=False,
    )
    execution_1 = row(
        Execution,
        "demo/execution/AUTH-017/1",
        run=run,
        agent_run=agent_run,
        change=change,
        candidate_patch=patch_1,
        verification_case=vc_adversarial,
        sandbox_id="token-factory-sbx-017-1",
        kind="TEST",
        command="pytest tests/test_auth_017.py::test_forged_refresh_token_accepted -q",
        cwd="/workspace/smorx/payments-api",
        exit_code=1,
        stdout="1 test, 1 failed\n",
        stderr="AssertionError: forged token accepted\n",
        duration_ms=3920,
        status="FAILED",
        started_at=T1,
        finished_at=T1,
        environment={"provider": "nebius", "sandbox": "token-factory", "runtime": "sqlite-demo"},
        machine_result={"tests_total": 1, "tests_failed": 1, "exit_code": 1},
    )
    execution_2 = row(
        Execution,
        "demo/execution/AUTH-017/2",
        run=run,
        agent_run=agent_run,
        change=change,
        candidate_patch=patch_2,
        verification_case=vc_ghost,
        sandbox_id="token-factory-sbx-017-2",
        kind="TEST",
        command="pytest tests/test_auth_017.py -q",
        cwd="/workspace/smorx/payments-api",
        exit_code=0,
        stdout="42 passed\n",
        stderr="",
        duration_ms=4180,
        status="PASSED",
        started_at=T3,
        finished_at=T3,
        environment={"provider": "nebius", "sandbox": "token-factory", "runtime": "sqlite-demo"},
        machine_result={"tests_total": 42, "tests_failed": 0, "exit_code": 0},
    )

    # ---- evidence (canonical service, fixed content hashes) -----------------
    claim = row(
        Claim,
        "demo/claim/AUTH-017/forged-rejected",
        task=task,
        statement="Token refresh rejects forged AUTH-017 requests.",
        kind="BEHAVIORAL",
        status="VERIFIED",
        confidence=0.97,
        owner_type="CERTIFICATE",
        version=1,
        locked=True,
    )
    evidence_test = _record_evidence(
        session,
        content_hash=digest("seed/evidence/auth-017/test-result"),
        evidence_type=EvidenceType.TEST_RESULT,
        occurred_at=T3,
        source="tests/test_auth_017.py",
        provenance="execution://demo/run/AUTH-017/exec-2 -> claim",
        artifact="artifacts/auth-017/pytest-report.json",
        machine_result={"tests_passed": 42, "tests_failed": 0, "exit_code": 0},
        task=task,
        run=run,
        agent_run=agent_run,
        execution=execution_2,
        verification_case=vc_ghost,
        claim=claim,
    )
    evidence_failure = _record_evidence(
        session,
        content_hash=digest("seed/evidence/f-183/execution-trace"),
        evidence_type=EvidenceType.EXECUTION_TRACE,
        occurred_at=T1,
        source="nebius-sandbox",
        provenance="execution://demo/run/AUTH-017/exec-1 -> failure F-183",
        artifact="artifacts/f-183/trace.json",
        machine_result={"exit_code": 1, "classification": "F3_INTEGRATION", "failure": "F-183"},
        task=task,
        run=run,
        agent_run=agent_run,
        execution=execution_1,
    )
    evidence_ghost = _record_evidence(
        session,
        content_hash=digest("seed/evidence/ghost-221/replay"),
        evidence_type=EvidenceType.HISTORICAL_GHOST_REPLAY,
        occurred_at=T3,
        source="verify",
        provenance="verify://demo/ghost-221 -> claim",
        artifact="artifacts/ghost-221/replay.json",
        machine_result={"scenario": "ghost-221", "before_exit": 1, "after_exit": 0, "exit_code": 0},
        task=task,
        run=run,
        agent_run=agent_run,
        execution=execution_2,
        verification_case=vc_ghost,
        claim=claim,
    )
    evidence_adversarial = _record_evidence(
        session,
        content_hash=digest("seed/evidence/auth-017/adversarial"),
        evidence_type=EvidenceType.ADVERSARIAL_SCENARIO,
        occurred_at=T3,
        source="verify",
        provenance="verify://demo/adversarial-refresh -> claim",
        artifact="artifacts/auth-017/adversarial.json",
        machine_result={"attempts": 100, "forged_accepted": 0, "exit_code": 0},
        task=task,
        run=run,
        agent_run=agent_run,
        verification_case=vc_adversarial,
        claim=claim,
    )
    evidence_binding = _record_evidence(
        session,
        content_hash=digest("seed/evidence/auth-017/certificate-binding"),
        evidence_type=EvidenceType.CERTIFICATE_BINDING,
        occurred_at=T4,
        source="certification",
        provenance="certify://demo/certificate/AUTH-017 <- claim + delta + change",
        artifact="artifacts/auth-017/certificate-binding.json",
        machine_result={"certificate_key": digest("seed/certificate/change/184/AUTH-017")},
        task=task,
        run=run,
        agent_run=agent_run,
        claim=claim,
    )
    evidence_decision = _record_evidence(
        session,
        content_hash=digest("seed/evidence/auth-017/model-decision"),
        evidence_type=EvidenceType.MODEL_DECISION,
        occurred_at=T2,
        source="nemotron",
        provenance="model://demo/orchestrator/decision-3",
        artifact="artifacts/auth-017/decision.json",
        machine_result={
            "decision": "repair required for F-183",
            "rationale": "exit_code 1; forged refresh token accepted",
            "model": "nvidia/nemotron-4-340b-instruct",
        },
        task=task,
        run=run,
        agent_run=agent_run,
    )

    # ---- failure + repair -----------------------------------------------------
    failure = row(
        Failure,
        "demo/failure/F-183",
        execution=execution_1,
        task=task,
        run=run,
        candidate_patch=patch_1,
        evidence=evidence_failure,
        classification=FailureKind.F3_INTEGRATION,
        message="F-183: forged refresh token accepted; tenant claim trusted without signature check.",
        probable_cause="candidate trusted payload claims without verifying signature/issuer",
        next_action="repair: verify signature and issuer before tenant wiring (candidate #2)",
        severity="HIGH",
        iteration=1,
        resolved=True,
        occurred_at=T1,
    )
    row(
        RepairPackage,
        "demo/repair/AUTH-017/F-183",
        failure=failure,
        task=task,
        candidate_patch=patch_2,
        evidence=evidence_decision,
        attempt=1,
        iteration=1,
        description="Structural repair package derived from Failure F-183 evidence.",
        patch_ref="candidates/AUTH-017/patch-2.diff",
        status="REVERIFIED",
        started_at=T2,
        finished_at=T3,
        version=1,
    )

    # ---- claims / delta / alignment / certificate / memory ---------------------
    delta = row(
        BehavioralDelta,
        "demo/delta/AUTH-017/token-refresh",
        task=task,
        change=change,
        claim=claim,
        behavior=behavior,
        execution=execution_2,
        evidence=evidence_test,
        metric="forged_token_acceptance_rate",
        baseline_value="3 failures / 100 attempts",
        candidate_value="0 / 100",
        magnitude=3.0,
        direction="DECREASED",
        category="SECURITY",
        description="Forged refresh tokens are rejected after repair; tenant isolation restored.",
        observed=True,
        owner_scope="OBSERVED_DIFFERENCE",
        version=1,
    )
    alignment = row(
        IntentAlignment,
        "demo/intent-alignment/AUTH-017",
        intent_item=intent_item,
        task=task,
        claim=claim,
        change=change,
        evidence=evidence_ghost,
        status="ALIGNED",
        verdict="AUTHORIZED",
        rationale="Behavioral delta lies inside the authorized AUTH-017 constraint.",
        score=0.99,
        verified_by="independent-verification",
        version=1,
        locked=True,
    )
    certificate = row(
        Certificate,
        "demo/certificate/AUTH-017",
        task=task,
        project=project,
        claim=claim,
        verification_plan=verification_plan,
        intent_alignment=alignment,
        certificate_key=digest("seed/certificate/change/184/AUTH-017"),
        status="CERTIFIED",
        owner_scope="CERTIFICATION",
        signature=digest("seed/certificate/signature/AUTH-017")[:40],
        evidence_hash=evidence_test.hash,
        payload={
            "change": "184",
            "task": "AUTH-017",
            "failure": "F-183",
            "ghost": "221",
            "bound_evidence": [
                evidence_test.hash,
                evidence_ghost.hash,
                evidence_adversarial.hash,
                evidence_binding.hash,
            ],
            "behavioral_delta_id": str(delta.id),
        },
        issued_at=T4,
        version=1,
        locked=True,
    )
    delta.certificate = certificate
    session.flush()

    memory = row(
        MemoryUpdate,
        "demo/memory/AUTH-017/certified",
        project=project,
        certificate=certificate,
        task=task,
        evidence=evidence_binding,
        kind=MemoryKind.CERTIFICATION,
        summary="Certified AUTH-017 refresh hardening closes the behavioral memory loop.",
        content={
            "change": "184",
            "task": "AUTH-017",
            "failure": "F-183",
            "ghost": "221",
            "delta": {"metric": delta.metric, "direction": delta.direction},
            "certificate_key": certificate.certificate_key,
        },
        applied=True,
        created_by="memory-evolution-agent",
        memory_ref=digest("seed/memory/AUTH-017/certified")[:32],
    )

    # ---- structured trace events (implementation plan 2.4) -------------------
    row(
        ConsequentialEvent,
        "demo/event/evidence-recorded/AUTH-017",
        entity_type="Evidence",
        entity_id=evidence_test.id,
        event_type=EventKind.EVIDENCE_RECORDED,
        occurred_at=T3,
        actor="orchestrator",
        payload={"evidence_hash": evidence_test.hash, "task": "AUTH-017"},
        provenance="trace://demo/run/AUTH-017/event/1",
        task_id=task.id,
        run_id=run.id,
        sequence=1,
        hash=digest("seed/event/evidence-recorded/AUTH-017"),
    )
    row(
        ConsequentialEvent,
        "demo/event/certification/AUTH-017",
        entity_type="Certificate",
        entity_id=certificate.id,
        event_type=EventKind.CERTIFICATION,
        occurred_at=T4,
        actor="orchestrator",
        payload={"certificate_key": certificate.certificate_key, "status": "CERTIFIED"},
        provenance="trace://demo/run/AUTH-017/event/2",
        task_id=task.id,
        run_id=run.id,
        sequence=2,
        hash=digest("seed/event/certification/AUTH-017"),
    )
    row(
        ConsequentialEvent,
        "demo/event/memory-update/AUTH-017",
        entity_type="MemoryUpdate",
        entity_id=memory.id,
        event_type=EventKind.MEMORY_UPDATE,
        occurred_at=T4,
        actor="memory-evolution-agent",
        payload={"memory_ref": memory.memory_ref, "applied": True},
        provenance="trace://demo/run/AUTH-017/event/3",
        task_id=task.id,
        run_id=run.id,
        sequence=3,
        hash=digest("seed/event/memory-update/AUTH-017"),
    )

    session.commit()

    evidence_rows = [
        evidence_test,
        evidence_failure,
        evidence_ghost,
        evidence_adversarial,
        evidence_binding,
        evidence_decision,
    ]
    return DemoReport(
        scenario="payments-api/AUTH-017",
        project_id=project.id,
        repository_id=repository.id,
        change_id=change.id,
        task_id=task.id,
        run_id=run.id,
        agent_run_id=agent_run.id,
        subagent_run_ids=(
            subagent_archaeology.id,
            subagent_verification.id,
            subagent_certification.id,
        ),
        behavior_id=behavior.id,
        ghost_id=ghost.id,
        failure_id=failure.id,
        claim_id=claim.id,
        delta_id=delta.id,
        certificate_id=certificate.id,
        memory_update_id=memory.id,
        evidence_ids=tuple(row_.id for row_ in evidence_rows),
        evidence_hashes=tuple(row_.hash for row_ in evidence_rows),
        counts={"rows": total_rows, "evidence": len(evidence_rows)},
        evidence_backend=EVIDENCE_BACKEND,
    )


def main(argv: Sequence[str] | None = None) -> DemoReport:
    """Seed the demo scenario into a sqlite database; ``--print`` reports it."""
    parser = argparse.ArgumentParser(
        prog="smorx-behavior-seed",
        description="Seed the deterministic Phase 2 demo scenario into a sqlite database.",
    )
    parser.add_argument(
        "--database",
        default="sqlite:///./demo-seed.sqlite",
        help="SQLAlchemy sqlite URL (default: sqlite:///./demo-seed.sqlite)",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        default=False,
        help="Print the demo report after seeding.",
    )
    args = parser.parse_args(argv)

    engine = create_sync_engine(args.database)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        report = build_seed(session)
    if args.print:
        print(report.summary())
    return report


if __name__ == "__main__":
    main()
