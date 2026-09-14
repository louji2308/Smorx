"""Failure archaeology: preserved, queryable failure history (11.4, AGENTS §14/15/19).

:func:`persist_archaeology` assembles an :class:`ArchaeologyRecord` that binds
a preserved ``Failure`` row (e.g. F-183) to its Ghost replay (e.g. #221), the
supporting Claims, the RepairPackages, and the Evidence chain (execution
traces, decision evidence, and claim/verification evidence) under a Task.

Contracts enforced:

* The original failure history is read-only evidence (AGENTS.md section 15).
  This module never rewrites ``Failure.message``, ``probable_cause``,
  ``next_action``, ``classification``, ``severity`` or ``resolved``; it only
  reads them, so the preserved row stays identical after the call.
* Missing references are reported honestly as ``gaps`` in the record -- never
  fabricated into real rows.
* The archaeology is observable through ``ConsequentialEvent`` rows
  (FAILURE_CLASSIFIED, REPAIR, REVERIFICATION) that reference the failure,
  and through an optional, *unapplied* ``MemoryUpdate`` row of kind
  FAILURE_ARCHAEOLOGY whose application is owned by the memory pipeline only
  after the certificate reaches CERTIFIED (11.7/11.8).
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, TypeVar

from smorx_behavior.evidence.provenance import claim_evidence_chain
from smorx_behavior.models import (
    Claim,
    ConsequentialEvent,
    EventKind,
    Evidence,
    Failure,
    Ghost,
    MemoryKind,
    MemoryUpdate,
    RepairPackage,
    Task,
)
from smorx_behavior.repo.base import digest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

__all__ = [
    "ArchaeologyRecord",
    "archaeology_memory_key",
    "persist_archaeology",
]

_FAILURE_CODE_RE = re.compile(r"\b(F-\d{1,6})\b")


class _Identified(Protocol):
    """Anything with a stable ``id`` identity column (the shared pk mixin)."""

    id: uuid.UUID


ModelT = TypeVar("ModelT", bound=_Identified)


@dataclass
class ArchaeologyRecord:
    """Structured, preserved archaeology for one classified failure.

    Id lists hold string ids referencing real rows. ``gaps`` records every
    claimed reference that could not be resolved (honest, never fabricated).
    """

    failure_id: uuid.UUID
    failure_code: str
    classification: str
    message: str
    probable_cause: str
    next_action: str
    severity: str
    ghost_ids: list[str] = field(default_factory=list)
    claim_ids: list[str] = field(default_factory=list)
    repair_package_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    resolved: bool = False
    verification_evidence_ids: list[str] = field(default_factory=list)
    gaps: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict form used as ``MemoryUpdate`` content.

        Returns a fresh dictionary; the record itself is never mutated.
        """
        return {
            "failure_id": str(self.failure_id),
            "failure_code": self.failure_code,
            "classification": self.classification,
            "message": self.message,
            "probable_cause": self.probable_cause,
            "next_action": self.next_action,
            "severity": self.severity,
            "ghost_ids": list(self.ghost_ids),
            "claim_ids": list(self.claim_ids),
            "repair_package_ids": list(self.repair_package_ids),
            "evidence_ids": list(self.evidence_ids),
            "resolved": self.resolved,
            "verification_evidence_ids": list(self.verification_evidence_ids),
            "gaps": {key: list(values) for key, values in self.gaps.items()},
        }


def archaeology_memory_key(archaeology: ArchaeologyRecord) -> str:
    """Return the deterministic ``memory_ref`` for the FAILURE_ARCHAEOLOGY entry.

    Shared with the memory pipeline so get-or-create semantics deduplicate the
    archaeology summary that both modules may persist.
    """
    return digest(
        str(archaeology.failure_id),
        "FAILURE_ARCHAEOLOGY",
        archaeology.failure_code,
        ",".join(archaeology.ghost_ids),
    )[:32]


def _as_id_str(value: Any) -> str:
    """Render ``value`` as a stable string id for gap reporting."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if hasattr(value, "id"):
        return str(value.id)
    return str(value)


def _resolve(session: Session, value: Any, model: type[ModelT]) -> ModelT | None:
    """Bind ``value`` (instance, UUID, or UUID string) to a session row.

    Returns ``None`` when the reference cannot be resolved; the caller reports
    the unresolved reference as a gap instead of fabricating a row.
    """
    if value is None:
        return None
    if isinstance(value, model):
        return session.get(model, value.id)
    if isinstance(value, uuid.UUID):
        return session.get(model, value)
    if isinstance(value, str):
        try:
            return session.get(model, uuid.UUID(value))
        except ValueError:
            return None
    return None


def _derive_failure_code(message: str) -> str:
    """Extract the F-<n> code embedded in the preserved failure message.

    The failure model has no dedicated code column; the historical evidence
    carries the code in the message. When no code is embedded the code is
    reported as ``UNKNOWN`` rather than invented.
    """
    match = _FAILURE_CODE_RE.search(message or "")
    if match is not None:
        return match.group(1)
    return "UNKNOWN"


def _record_event(
    session: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    event_type: EventKind,
    task_id: uuid.UUID,
    actor: str,
    payload: dict[str, Any],
) -> ConsequentialEvent:
    """Persist one archaeology observability event (trace model A2.4)."""
    sequence = int(
        session.scalar(
            select(func.count())
            .select_from(ConsequentialEvent)
            .where(ConsequentialEvent.task_id == task_id)
        )
        or 0
    )
    event = ConsequentialEvent(
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type.value,
        occurred_at=datetime.now(UTC),
        actor=actor,
        payload=payload,
        provenance=None,
        task_id=task_id,
        sequence=sequence,
        hash=None,
    )
    session.add(event)
    session.flush()
    return event


def persist_archaeology(
    session: Session,
    *,
    task: Task | None,
    failure_row: Any,
    ghost_rows: Any,
    claim_rows: Any,
    repair_packages: Any,
    execution_evidence: Any,
    persist_summary: bool = True,
) -> ArchaeologyRecord:
    """Assemble and persist the archaeology for a preserved failure (11.4).

    Reads the real ORM rows and builds the record without mutating them. The
    original failure history is preserved exactly; every referenced Ghost,
    Claim, RepairPackage and Evidence is resolved honestly, with unresolved
    references reported as ``gaps``. Observability events are recorded and an
    unapplied FAILURE_ARCHAEOLOGY memory summary is optionally persisted.

    Raises ``ValueError`` when ``task`` or ``failure_row`` are missing or the
    failure reference does not resolve to a persisted row.
    """
    if task is None:
        raise ValueError("persist_archaeology requires a Task; task is None")
    if failure_row is None:
        raise ValueError(
            "persist_archaeology requires a preserved Failure row; failure_row is None"
        )
    failure = _resolve(session, failure_row, Failure)
    if failure is None:
        raise ValueError("failure_row does not resolve to a persisted Failure row")

    record = ArchaeologyRecord(
        failure_id=failure.id,
        failure_code=_derive_failure_code(failure.message),
        classification=failure.classification,
        message=failure.message,
        probable_cause=failure.probable_cause or "",
        next_action=failure.next_action or "",
        severity=failure.severity,
        resolved=failure.resolved,
    )

    for ref in list(ghost_rows or []):
        ghost_row = _resolve(session, ref, Ghost)
        if ghost_row is None:
            record.gaps.setdefault("ghost_ids", []).append(_as_id_str(ref))
        else:
            record.ghost_ids.append(str(ghost_row.id))

    resolved_claims: list[Claim] = []
    for ref in list(claim_rows or []):
        claim_row = _resolve(session, ref, Claim)
        if claim_row is None:
            record.gaps.setdefault("claim_ids", []).append(_as_id_str(ref))
        else:
            resolved_claims.append(claim_row)
            record.claim_ids.append(str(claim_row.id))

    for ref in list(repair_packages or []):
        repair_row = _resolve(session, ref, RepairPackage)
        if repair_row is None:
            record.gaps.setdefault("repair_package_ids", []).append(_as_id_str(ref))
        else:
            record.repair_package_ids.append(str(repair_row.id))

    bound_ids: list[str] = []
    if failure.evidence_id is not None:
        failure_evidence = session.get(Evidence, failure.evidence_id)
        if failure_evidence is not None:
            bound_ids.append(str(failure_evidence.id))
    for ref in list(execution_evidence or []):
        evidence_row = _resolve(session, ref, Evidence)
        if evidence_row is None:
            record.gaps.setdefault("evidence_ids", []).append(_as_id_str(ref))
        elif str(evidence_row.id) not in bound_ids:
            bound_ids.append(str(evidence_row.id))
    record.evidence_ids = bound_ids

    verified_ids: list[str] = []
    seen: set[uuid.UUID] = set()
    for claim in resolved_claims:
        for evidence in claim_evidence_chain(claim):
            if evidence.id not in seen:
                seen.add(evidence.id)
                verified_ids.append(str(evidence.id))
    verification_rows = list(
        session.scalars(
            select(Evidence).where(
                Evidence.task_id == task.id,
                Evidence.verification_case_id.is_not(None),
            )
        )
    )
    for evidence in verification_rows:
        if evidence.id not in seen:
            seen.add(evidence.id)
            verified_ids.append(str(evidence.id))
    record.verification_evidence_ids = verified_ids

    _record_event(
        session,
        entity_type="Failure",
        entity_id=failure.id,
        event_type=EventKind.FAILURE_CLASSIFIED,
        task_id=task.id,
        actor="failure-archaeology",
        payload={
            "failure_code": record.failure_code,
            "classification": record.classification,
        },
    )
    if record.repair_package_ids:
        _record_event(
            session,
            entity_type="Failure",
            entity_id=failure.id,
            event_type=EventKind.REPAIR,
            task_id=task.id,
            actor="failure-archaeology",
            payload={"repair_package_ids": list(record.repair_package_ids)},
        )
    if record.verification_evidence_ids:
        _record_event(
            session,
            entity_type="Failure",
            entity_id=failure.id,
            event_type=EventKind.REVERIFICATION,
            task_id=task.id,
            actor="failure-archaeology",
            payload={"verification_evidence_ids": list(record.verification_evidence_ids)},
        )

    if persist_summary:
        memory_ref = archaeology_memory_key(record)
        existing = session.scalar(select(MemoryUpdate).where(MemoryUpdate.memory_ref == memory_ref))
        if existing is None:
            session.add(
                MemoryUpdate(
                    project_id=task.project_id,
                    task_id=task.id,
                    kind=MemoryKind.FAILURE_ARCHAEOLOGY.value,
                    summary=(
                        f"Preserved failure archaeology for {record.failure_code}: {record.message}"
                    ),
                    content=record.to_dict(),
                    applied=False,
                    created_by="failure-archaeology",
                    memory_ref=memory_ref,
                )
            )
    session.flush()
    return record
