"""Purpose-specific query builders for the behavioural catalog.

Phase 2 (implementation plan step 2.5, deliverable "repository/data access
layer"). These queries answer the questions the UI and AI consumers need
later, keeping ownership chains authoritative:

- ``tasks_for_change`` — the tasks owned by a change,
- ``evidence_for_change`` — every evidence row reachable from a change
  through its task/run/execution/verification-case/claim bindings,
- ``certificate_for_change`` — certificates bound through a task or its
  verification plan,
- ``memory_for_change`` — memory updates bound through a task or its
  certificate,
- ``lifecycle`` — the full owned graph rooted at a change for the Phase 2
  exit gate ("full lifecycle representable and queryable without losing
  ownership, version, provenance, or historical evidence").

All queries are read-only, empty-safe (``IN ()`` degenerates to an
exclusion), and return stable ordering by primary key.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from smorx_behavior.models import (
    AgentRun,
    BehavioralDelta,
    CandidatePatch,
    Certificate,
    Change,
    Claim,
    Evidence,
    Execution,
    Failure,
    Ghost,
    IntentAlignment,
    MemoryUpdate,
    RepairPackage,
    Run,
    SubagentRun,
    Task,
    VerificationCase,
    VerificationPlan,
)

__all__ = [
    "certificate_for_change",
    "evidence_for_change",
    "lifecycle",
    "memory_for_change",
    "tasks_for_change",
]


def _by_id_order(rows: list[Any]) -> list[Any]:
    """Order any rows by primary key so results are reproducible."""
    return sorted(rows, key=lambda row: row.id)


def _unique(rows: list[Any]) -> list[Any]:
    """Deduplicate ORM rows by primary key, preserving stable ordering."""
    return _by_id_order(list({row.id: row for row in rows}.values()))


def tasks_for_change(session: Session, change_id: uuid.UUID) -> list[Task]:
    """Return the tasks owned by ``change_id`` in stable order."""
    rows = session.scalars(select(Task).where(Task.change_id == change_id)).all()
    return _by_id_order(list(rows))


def evidence_for_change(session: Session, change_id: uuid.UUID) -> list[Evidence]:
    """Return every evidence row reachable from ``change_id``.

    A change owns evidence through several legal paths: evidence bound to one
    of its tasks, to one of its executions, to one of its verification cases,
    or to a claim that belongs to one of its tasks. The union is deduplicated
    by primary key.
    """
    rows: list[Evidence] = []
    rows += list(
        session.scalars(
            select(Evidence)
            .join(Task, Evidence.task_id == Task.id)
            .where(Task.change_id == change_id)
        ).all()
    )
    rows += list(
        session.scalars(
            select(Evidence)
            .join(Execution, Evidence.execution_id == Execution.id)
            .where(Execution.change_id == change_id)
        ).all()
    )
    rows += list(
        session.scalars(
            select(Evidence)
            .join(
                VerificationCase,
                Evidence.verification_case_id == VerificationCase.id,
            )
            .where(VerificationCase.change_id == change_id)
        ).all()
    )
    rows += list(
        session.scalars(
            select(Evidence)
            .join(Claim, Evidence.claim_id == Claim.id)
            .join(Task, Claim.task_id == Task.id)
            .where(Task.change_id == change_id)
        ).all()
    )
    return _unique(rows)


def certificate_for_change(session: Session, change_id: uuid.UUID) -> list[Certificate]:
    """Return the certificates bound to ``change_id``.

    A certificate reaches a change through its task binding or through its
    verification plan's change binding; the union is deduplicated.
    """
    rows: list[Certificate] = []
    rows += list(
        session.scalars(
            select(Certificate)
            .join(Task, Certificate.task_id == Task.id)
            .where(Task.change_id == change_id)
        ).all()
    )
    rows += list(
        session.scalars(
            select(Certificate)
            .join(
                VerificationPlan,
                Certificate.verification_plan_id == VerificationPlan.id,
            )
            .where(VerificationPlan.change_id == change_id)
        ).all()
    )
    return _unique(rows)


def memory_for_change(session: Session, change_id: uuid.UUID) -> list[MemoryUpdate]:
    """Return the memory updates bound to ``change_id``.

    A memory update reaches a change through its task binding or through the
    certificate's task binding; the union is deduplicated.
    """
    rows: list[MemoryUpdate] = []
    rows += list(
        session.scalars(
            select(MemoryUpdate)
            .join(Task, MemoryUpdate.task_id == Task.id)
            .where(Task.change_id == change_id)
        ).all()
    )
    rows += list(
        session.scalars(
            select(MemoryUpdate)
            .join(Certificate, MemoryUpdate.certificate_id == Certificate.id)
            .join(Task, Certificate.task_id == Task.id)
            .where(Task.change_id == change_id)
        ).all()
    )
    return _unique(rows)


def lifecycle(session: Session, *, change_id: uuid.UUID) -> dict[str, list[Any]]:
    """Return the full owned lifecycle graph rooted at ``change_id``.

    The result is a dict keyed by node kind. The chain traversed by the
    Phase 2 exit gate is: project -> repository -> change -> task -> run ->
    agent_run -> subagent_run -> execution -> evidence -> claim ->
    behavioral_delta -> certificate -> memory_update, with failures, ghosts,
    verification plans, candidate patches, and repair packages attached.
    """
    change = session.get(Change, change_id)
    if change is None:
        raise ValueError(f"change {change_id} not found")
    repository = change.repository
    project = repository.project

    tasks = tasks_for_change(session, change_id)
    task_ids = [task.id for task in tasks]

    runs = (
        list(session.scalars(select(Run).where(Run.task_id.in_(task_ids))).all())
        if task_ids
        else []
    )
    run_ids = [run.id for run in runs]

    agent_runs = (
        list(session.scalars(select(AgentRun).where(AgentRun.run_id.in_(run_ids))).all())
        if run_ids
        else []
    )
    agent_run_ids = [agent_run.id for agent_run in agent_runs]

    subagent_runs = (
        list(
            session.scalars(
                select(SubagentRun).where(SubagentRun.agent_run_id.in_(agent_run_ids))
            ).all()
        )
        if agent_run_ids
        else []
    )

    executions = _by_id_order(
        list(
            session.scalars(
                select(Execution).where(
                    or_(
                        Execution.run_id.in_(run_ids) if run_ids else False,
                        Execution.change_id == change_id,
                    )
                )
            ).all()
        )
    )

    claims = (
        list(session.scalars(select(Claim).where(Claim.task_id.in_(task_ids))).all())
        if task_ids
        else []
    )

    deltas = _by_id_order(
        list(
            session.scalars(
                select(BehavioralDelta).where(BehavioralDelta.change_id == change_id)
            ).all()
        )
    )
    alignments = _by_id_order(
        list(
            session.scalars(
                select(IntentAlignment).where(IntentAlignment.change_id == change_id)
            ).all()
        )
    )
    failures = (
        _by_id_order(
            list(session.scalars(select(Failure).where(Failure.task_id.in_(task_ids))).all())
        )
        if task_ids
        else []
    )
    ghosts = _by_id_order(
        list(session.scalars(select(Ghost).where(Ghost.repository_id == repository.id)).all())
    )
    plans = _by_id_order(
        list(
            session.scalars(
                select(VerificationPlan).where(VerificationPlan.change_id == change_id)
            ).all()
        )
    )
    patches = _by_id_order(
        list(
            session.scalars(
                select(CandidatePatch).where(CandidatePatch.change_id == change_id)
            ).all()
        )
    )
    repairs = (
        _by_id_order(
            list(
                session.scalars(
                    select(RepairPackage).where(RepairPackage.task_id.in_(task_ids))
                ).all()
            )
        )
        if task_ids
        else []
    )

    return {
        "projects": _by_id_order([project]),
        "repositories": _by_id_order([repository]),
        "changes": [change],
        "tasks": tasks,
        "runs": _by_id_order(runs),
        "agent_runs": _by_id_order(agent_runs),
        "subagent_runs": _by_id_order(subagent_runs),
        "executions": executions,
        "evidence": evidence_for_change(session, change_id),
        "claims": _by_id_order(claims),
        "behavioral_deltas": deltas,
        "intent_alignments": alignments,
        "certificates": certificate_for_change(session, change_id),
        "memory_updates": memory_for_change(session, change_id),
        "failures": failures,
        "ghosts": ghosts,
        "verification_plans": plans,
        "candidate_patches": patches,
        "repair_packages": repairs,
    }
