"""Continuous behavioral memory (implementation plan phase 11, section 11.8).

The memory pipeline closes the certification loop: a change may enter
behavioral memory only *after* its certificate reaches ``CERTIFIED``.  It
persists a ``CERTIFICATION`` memory update describing the certified behavior
and applies the preserved ``FAILURE_ARCHAEOLOGY`` summary so future tasks can
query what the system learned (failure F-183, ghost replay #221, the
behavioral delta, and the certificate binding).

Contracts enforced:

* The pipeline refuses non-``CERTIFIED`` certificates and never fabricates
  content: every field is derived from real rows (``certificate_traversal``)
  or from a real :class:`ArchaeologyRecord`.
* Idempotency: ``memory_ref`` is a deterministic digest, so re-running the
  pipeline for the same certificate returns the same ``MemoryUpdate`` rows
  (get-or-create semantics).
* Application is observable through a ``MEMORY_UPDATE`` consequential event
  per memory entry.
* ``memory_for_task`` returns a task's memory updates in deterministic order.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from smorx_behavior.evidence.provenance import certificate_traversal
from smorx_behavior.models import (
    Certificate,
    CertificateStatus,
    ConsequentialEvent,
    EventKind,
    Evidence,
    MemoryKind,
    MemoryUpdate,
    Task,
)
from smorx_behavior.repo.base import digest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from smorx_certification.archaeology import (
    ArchaeologyRecord,
    archaeology_memory_key,
)

__all__ = ["MemoryPipeline", "MemoryRecord", "memory_for_task", "run_memory_pipeline"]


@dataclass
class MemoryRecord:
    """Outcome of one memory-pipeline run."""

    memory_update_ids: list[str]
    applied: bool
    certificate_id: uuid.UUID
    summary: str


@dataclass
class MemoryPipeline:
    """Session-bound facade over :func:`run_memory_pipeline`."""

    session: Session

    def run(
        self,
        *,
        certificate: Certificate,
        task: Task,
        archaeology: ArchaeologyRecord,
    ) -> MemoryRecord:
        """Run the pipeline with ``change=None`` (change not required for memory)."""
        return run_memory_pipeline(
            self.session,
            certificate=certificate,
            task=task,
            change=None,
            archaeology=archaeology,
        )


def _get_or_create_memory(
    session: Session,
    *,
    memory_ref: str,
    kind: str,
    summary: str,
    content: dict[str, Any],
    certificate: Certificate,
    task: Task,
    evidence: Evidence | None,
) -> MemoryUpdate:
    """Return the existing ``MemoryUpdate`` for ``memory_ref`` or create one.

    On creation ``applied`` is set to ``True``.  When the row already exists
    (created by archaeology or a previous pipeline run) ``applied`` is set to
    ``True`` -- ensuring the pipeline can mark the archaeology summary as
    applied after certification.
    """
    existing = session.scalar(select(MemoryUpdate).where(MemoryUpdate.memory_ref == memory_ref))
    if existing is not None:
        existing.applied = True
        return existing
    row = MemoryUpdate(
        project_id=task.project_id,
        certificate_id=certificate.id,
        task_id=task.id,
        evidence_id=evidence.id if evidence is not None else None,
        kind=kind,
        summary=summary,
        content=content,
        applied=True,
        created_by="memory-evolution",
        memory_ref=memory_ref,
    )
    session.add(row)
    session.flush()
    return row


def _certificate_evidence(session: Session, traversal: dict[str, Any]) -> Evidence | None:
    """Resolve a certificate-bound evidence row from the traversal map."""
    evidence_rows = list(traversal.get("evidence") or [])
    target: dict[str, Any] | None = None
    for item in evidence_rows:
        if item.get("type") == "CERTIFICATE_BINDING":
            target = item
            break
    if target is None and evidence_rows:
        target = evidence_rows[0]
    if target is None:
        return None
    try:
        return session.get(Evidence, uuid.UUID(str(target["id"])))
    except (TypeError, ValueError):
        return None


def _record_event(
    session: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    event_type: EventKind,
    task_id: uuid.UUID,
    actor: str,
    payload: dict[str, Any],
) -> None:
    """Persist one memory-pipeline observability event (trace model A2.4)."""
    sequence = int(
        session.scalar(
            select(func.count())
            .select_from(ConsequentialEvent)
            .where(ConsequentialEvent.task_id == task_id)
        )
        or 0
    )
    session.add(
        ConsequentialEvent(
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
    )
    session.flush()


def run_memory_pipeline(
    session: Session,
    *,
    certificate: Certificate | None,
    task: Task | None,
    change: Any,
    archaeology: ArchaeologyRecord | None,
) -> MemoryRecord:
    """Run the memory update pipeline (11.8) and return the outcome.

    Raises ``ValueError`` for ``None`` certificate, task, or archaeology.
    Returns ``applied=False`` when the certificate has not reached
    ``CERTIFIED`` yet (honest block, not a fabrication).
    """
    if certificate is None:
        raise ValueError("run_memory_pipeline requires a real Certificate; certificate is None")
    if task is None:
        raise ValueError("run_memory_pipeline requires a real Task; task is None")
    if archaeology is None:
        raise ValueError("run_memory_pipeline requires an ArchaeologyRecord; archaeology is None")
    if certificate.status != CertificateStatus.CERTIFIED.value:
        return MemoryRecord(
            memory_update_ids=[],
            applied=False,
            certificate_id=certificate.id,
            summary=(
                f"memory pipeline blocked: certificate {certificate.certificate_key} "
                f"has status {certificate.status}; memory is written only after CERTIFIED"
            ),
        )

    traversal = certificate_traversal(certificate)
    certificate_key = str(traversal["certificate"]["certificate_key"])
    deltas: list[dict[str, Any]] = list(traversal.get("deltas") or [])
    delta: dict[str, Any] = deltas[0] if deltas else {}
    delta_fields: dict[str, str | None] = {
        "metric": delta.get("metric"),
        "direction": delta.get("direction"),
    }

    evidence = _certificate_evidence(session, traversal)
    ghost_summary = ", ".join(archaeology.ghost_ids) or "n/a"
    metric_display = delta_fields["metric"] or "n/a"
    direction_display = delta_fields["direction"] or "n/a"
    future_context = (
        f"Future changes must preserve the certified behavior of {certificate_key} "
        f"and keep {archaeology.failure_code} (ghost {ghost_summary}) "
        f"closed; delta {metric_display} -> {direction_display}."
    )

    certification_content: dict[str, Any] = {
        "change": str(change.id) if change is not None else None,
        "task": str(task.id),
        "certificate_key": certificate_key,
        "certificate_status": certificate.status,
        "failure_code": archaeology.failure_code,
        "ghost_replay": list(archaeology.ghost_ids),
        "delta": dict(delta_fields),
        "future_context": future_context,
    }

    certification_summary = (
        f"Certified task {task.id}: {certificate_key} is CERTIFIED with failure "
        f"{archaeology.failure_code} preserved, ghost {ghost_summary}, "
        f"delta {metric_display} {direction_display}."
    )
    cert_ref = digest(certificate_key, "CERTIFICATION", str(task.id), archaeology.failure_code)[:32]
    cert_memory = _get_or_create_memory(
        session,
        memory_ref=cert_ref,
        kind=MemoryKind.CERTIFICATION.value,
        summary=certification_summary,
        content=certification_content,
        certificate=certificate,
        task=task,
        evidence=evidence,
    )

    archaeology_content = dict(archaeology.to_dict())
    archaeology_content["certificate_key"] = certificate_key
    archaeology_content["delta"] = dict(delta_fields)
    archaeology_content["future_context"] = future_context
    arch_ref = archaeology_memory_key(archaeology)
    archaeology_memory = _get_or_create_memory(
        session,
        memory_ref=arch_ref,
        kind=MemoryKind.FAILURE_ARCHAEOLOGY.value,
        summary=(
            f"Applied preserved failure archaeology {archaeology.failure_code} "
            f"under {certificate_key}."
        ),
        content=archaeology_content,
        certificate=certificate,
        task=task,
        evidence=evidence,
    )

    for memory_row in (cert_memory, archaeology_memory):
        _record_event(
            session,
            entity_type="MemoryUpdate",
            entity_id=memory_row.id,
            event_type=EventKind.MEMORY_UPDATE,
            task_id=task.id,
            actor="memory-evolution",
            payload={
                "memory_ref": memory_row.memory_ref,
                "applied": memory_row.applied,
                "kind": memory_row.kind,
            },
        )

    session.flush()
    return MemoryRecord(
        memory_update_ids=[str(cert_memory.id), str(archaeology_memory.id)],
        applied=True,
        certificate_id=certificate.id,
        summary=certification_summary,
    )


def memory_for_task(session: Session, task: Task) -> list[MemoryUpdate]:
    """Return every memory update for ``task`` in deterministic order."""
    return list(
        session.scalars(
            select(MemoryUpdate)
            .where(MemoryUpdate.task_id == task.id)
            .order_by(MemoryUpdate.created_at.asc(), MemoryUpdate.id.asc())
        )
    )
