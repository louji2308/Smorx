"""Evidence recording and claim-eligibility service (phase 2, step 2.2).

Owned facts:

- ``record_evidence`` is the single durable entry point for observations. It
  maps directly onto the real ``smorx_behavior.models.Evidence`` table and
  never adds columns. Deduplication is content-addressed: ``Evidence.hash``
  is unique, so re-recording a payload with the same hash returns the
  existing row (idempotent) instead of raising or duplicating. When
  ``content_hash`` is omitted, a SHA-256 hex digest is derived from a stable
  JSON serialization (recursively sorted keys) of the canonical payload, so
  the digest is fully deterministic from the recorded content.
- ``eligibility`` encodes the claim-support admission rule (AGENTS.md
  sections 10/16): evidence may support a claim only when its machine result
  carries an ``exit_code``, it has non-empty ``provenance``, and it is bound
  to a ``claim`` or ``verification_case``. It returns the verdict plus the
  human-readable reasons for rejection.

This module performs no network or file I/O; every operation is bounded to
the caller-supplied SQLAlchemy session, which owns the transaction (callers
decide when to commit).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from smorx_behavior.models import Evidence, EvidenceType

__all__ = [
    "compute_content_hash",
    "eligibility",
    "evidence_by_hash",
    "evidence_for_claim",
    "evidence_for_task",
    "record_evidence",
]


def _normalize(value: Any) -> Any:
    """Recursively coerce a payload value into a stable, JSON-safe form."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {key: _normalize(v) for key, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _canonical_payload(
    *,
    evidence_type: EvidenceType | str,
    occurred_at: datetime | None,
    source: str | None,
    provenance: str | None,
    artifact: str | None,
    machine_result: dict | None,
) -> dict[str, Any]:
    """Stable JSON-serializable identity payload for an evidence record."""
    return {
        "type": _normalize(evidence_type),
        "occurred_at": _normalize(occurred_at),
        "source": _normalize(source),
        "provenance": _normalize(provenance),
        "artifact": _normalize(artifact),
        "machine_result": _normalize(machine_result),
    }


def compute_content_hash(
    *,
    evidence_type: EvidenceType | str,
    occurred_at: datetime | None = None,
    source: str | None = None,
    provenance: str | None = None,
    artifact: str | None = None,
    machine_result: dict | None = None,
) -> str:
    """Return the deterministic SHA-256 hex digest for an evidence payload.

    The digest covers the canonical content fields (type, occurred_at,
    source, provenance, artifact, machine_result) serialized to JSON with
    recursively sorted keys. Optional binding columns (task/run/claim/... FKs)
    are deliberately excluded so the same observation recorded against
    different runs deduplicates to one row.
    """
    payload = _canonical_payload(
        evidence_type=evidence_type,
        occurred_at=occurred_at,
        source=source,
        provenance=provenance,
        artifact=artifact,
        machine_result=machine_result,
    )
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def record_evidence(
    session: Session,
    *,
    evidence_type: EvidenceType | str,
    occurred_at: datetime | None = None,
    source: str | None = None,
    provenance: str | None = None,
    artifact: str | None = None,
    machine_result: dict | None = None,
    content_hash: str | None = None,
    task_id: uuid.UUID | None = None,
    run_id: uuid.UUID | None = None,
    agent_run_id: uuid.UUID | None = None,
    subagent_run_id: uuid.UUID | None = None,
    execution_id: uuid.UUID | None = None,
    verification_case_id: uuid.UUID | None = None,
    claim_id: uuid.UUID | None = None,
) -> Evidence:
    """Record an evidence row, deduplicating on ``Evidence.hash``.

    If a row with the resolved ``hash`` already exists it is returned as-is
    (idempotent, never raises). When ``content_hash`` is None the digest is
    computed via :func:`compute_content_hash`. The row is flushed so ``id``
    materializes and the unique constraint is enforced eagerly; the caller
    owns the transaction boundary (commit/rollback).
    """
    if content_hash is None:
        content_hash = compute_content_hash(
            evidence_type=evidence_type,
            occurred_at=occurred_at,
            source=source,
            provenance=provenance,
            artifact=artifact,
            machine_result=machine_result,
        )

    existing = session.scalar(select(Evidence).where(Evidence.hash == content_hash))
    if existing is not None:
        return existing

    type_value = evidence_type.value if isinstance(evidence_type, Enum) else evidence_type
    row = Evidence(
        type=type_value,
        occurred_at=occurred_at,
        source=source,
        provenance=provenance,
        artifact=artifact,
        machine_result=machine_result or {},
        hash=content_hash,
        task_id=task_id,
        run_id=run_id,
        agent_run_id=agent_run_id,
        subagent_run_id=subagent_run_id,
        execution_id=execution_id,
        verification_case_id=verification_case_id,
        claim_id=claim_id,
    )
    session.add(row)
    session.flush()
    return row


def eligibility(evidence: Evidence) -> tuple[bool, list[str]]:
    """Evaluate whether ``evidence`` is admissible for claim support.

    Admissible means: the machine result carries a present non-null
    ``exit_code``, provenance is non-blank, and the row is bound to a
    ``claim_id`` or ``verification_case_id``. Returns
    ``(admissible, reasons)`` where ``reasons`` lists every failed rule.
    """
    reasons: list[str] = []

    machine_result = evidence.machine_result if isinstance(evidence.machine_result, dict) else {}
    if "exit_code" not in machine_result or machine_result.get("exit_code") is None:
        reasons.append("machine_result has no exit_code")

    provenance = (evidence.provenance or "").strip()
    if not provenance:
        reasons.append("provenance is empty")

    if evidence.claim_id is None and evidence.verification_case_id is None:
        reasons.append("no claim_id or verification_case_id binding")

    return (not reasons, reasons)


def evidence_by_hash(session: Session, content_hash: str) -> Evidence | None:
    """Return the evidence row whose unique ``hash`` is ``content_hash``."""
    return session.scalar(select(Evidence).where(Evidence.hash == content_hash))


def _ordered_statement(stmt: Any) -> Any:
    """Append the stable evidence ordering (created_at, then id)."""
    return stmt.order_by(Evidence.created_at.asc(), Evidence.id.asc())


def evidence_for_claim(session: Session, claim_id: uuid.UUID) -> list[Evidence]:
    """Return all evidence rows bound to ``claim_id`` in stable order."""
    return list(
        session.scalars(
            _ordered_statement(select(Evidence).where(Evidence.claim_id == claim_id))
        ).all()
    )


def evidence_for_task(session: Session, task_id: uuid.UUID) -> list[Evidence]:
    """Return all evidence rows bound to ``task_id`` in stable order."""
    return list(
        session.scalars(
            _ordered_statement(select(Evidence).where(Evidence.task_id == task_id))
        ).all()
    )
