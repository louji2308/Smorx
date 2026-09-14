"""Certificate generation binding proof to implementation (11.3, AGENTS §19).

Builds a :class:`Certificate` row whose deterministic ``certificate_key``
binds the Change -> Claim -> Behavioral Deltas -> Verification Evidence ->
Candidate Implementation -> Intent -> Protected Behaviors chain, and computes
a machine-verifiable ``evidence_hash`` over the canonical binding payload.

The canonical binding payload is shared with the integrity module
(:func:`smorx_certification.integrity.canonical_certificate_payload`), so the
same hash is recomputable from real persisted rows at verification time.

Contracts enforced:

* **No evidence, no certification**: a certificate reaches ``CERTIFIED``
  only when ``alignment_aligned`` is True and at least one real verification
  evidence row is supplied.  Otherwise the certificate stays ``DRAFT``
  (an honest block, never a fabricated pass).
* The certificate key is deterministic:
  ``digest("certificate", task_id, claim_id)[:64]``.
* Idempotency: re-building for the same key returns the existing row.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from smorx_behavior.evidence.service import record_evidence
from smorx_behavior.models import (
    BehavioralDelta,
    CandidatePatch,
    Certificate,
    CertificateStatus,
    Change,
    Claim,
    ConsequentialEvent,
    EventKind,
    Evidence,
    EvidenceType,
    Task,
)
from smorx_behavior.repo.base import digest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from smorx_certification.integrity import (
    canonical_certificate_payload,
    compute_integrity_hash,
)

__all__ = [
    "CertificateBundle",
    "CertificateRecord",
    "build_certificate",
]


@dataclass
class CertificateRecord:
    """Stable, JSON-safe view of the persisted certificate row."""

    certificate_id: uuid.UUID
    certificate_key: str
    status: str
    evidence_hash: str | None
    issued_at: datetime | None


@dataclass
class CertificateBundle:
    """Certificate row view plus the canonical binding payload."""

    certificate: CertificateRecord
    binding: dict[str, Any]


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
    """Persist one certification observability event."""
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


def _observed_deltas(session: Session, task: Task) -> list[BehavioralDelta]:
    """Return the task's observed behavioral deltas in stable order."""
    return list(
        session.scalars(
            select(BehavioralDelta)
            .where(
                BehavioralDelta.task_id == task.id,
                BehavioralDelta.observed.is_(True),
            )
            .order_by(BehavioralDelta.created_at.asc(), BehavioralDelta.id.asc())
        )
    )


def build_certificate(
    session: Session,
    *,
    task: Task | None,
    change: Change | None,
    claim: Claim | None,
    candidate_patch: CandidatePatch | None,
    alignment_aligned: bool,
    verification_evidence: Sequence[Evidence],
    environment: dict[str, Any] | None = None,
    dependency_state: dict[str, Any] | None = None,
    issued_at: datetime | None = None,
) -> CertificateBundle:
    """Build the certificate binding the change to implementation evidence.

    Raises ``ValueError`` when ``task``, ``claim``, or ``candidate_patch``
    are ``None``.  The certificate is ``CERTIFIED`` only when
    ``alignment_aligned`` is True and ``verification_evidence`` is non-empty;
    otherwise it is persisted as ``DRAFT`` (honest block).
    """
    if task is None:
        raise ValueError("build_certificate requires a Task; task is None")
    if claim is None:
        raise ValueError("build_certificate requires a Claim; claim is None")
    if candidate_patch is None:
        raise ValueError("build_certificate requires a CandidatePatch; candidate_patch is None")

    verification_rows = list(verification_evidence or [])
    certifiable = alignment_aligned and bool(verification_rows)

    certificate_key = digest("certificate", str(task.id), str(claim.id))[:64]

    existing = session.scalar(
        select(Certificate).where(Certificate.certificate_key == certificate_key)
    )
    if existing is not None:
        return CertificateBundle(
            certificate=CertificateRecord(
                certificate_id=existing.id,
                certificate_key=existing.certificate_key,
                status=existing.status,
                evidence_hash=existing.evidence_hash,
                issued_at=existing.issued_at,
            ),
            binding=dict(existing.payload) if existing.payload else {},
        )

    certificate = Certificate(
        task_id=task.id,
        project_id=task.project_id,
        claim_id=claim.id,
        certificate_key=certificate_key,
        status=CertificateStatus.DRAFT.value,
        owner_scope="CERTIFICATION",
        payload={},
    )
    session.add(certificate)
    session.flush()

    # Bind every observed delta under this task onto the certificate so the
    # traversal exposes the behavioral-delta edge (AGENTS.md section 19).
    for delta in _observed_deltas(session, task):
        delta.certificate_id = certificate.id

    record_evidence(
        session,
        evidence_type=EvidenceType.CERTIFICATE_BINDING,
        occurred_at=issued_at or datetime.now(UTC),
        source="certification",
        provenance=(
            f"certify://{certificate_key} <- change {str(change.id) if change else 'n/a'} "
            f"+ claim {claim.id!s} + delta"
        ),
        artifact=f"artifacts/certificates/{certificate_key[:16]}/binding.json",
        machine_result={
            "certificate_key": certificate_key,
            "status": "CERTIFIED" if certifiable else "DRAFT",
            "bound_evidence": [str(row.id) for row in verification_rows],
        },
        content_hash=digest("certificate-binding", certificate_key),
        task_id=task.id,
        claim_id=claim.id,
    )

    # Set the final status and issue timestamp BEFORE computing the canonical
    # payload so the stored binding matches the row state at verification time.
    certificate.status = (
        CertificateStatus.CERTIFIED.value if certifiable else CertificateStatus.DRAFT.value
    )
    certificate.issued_at = datetime.now(UTC) if issued_at is None else issued_at

    payload: dict[str, Any] = canonical_certificate_payload(session, certificate)
    if environment:
        payload["environment"] = dict(environment)
    if dependency_state:
        payload["dependency_state"] = dict(dependency_state)
    certificate.payload = payload
    certificate.evidence_hash = compute_integrity_hash(payload)

    _record_event(
        session,
        entity_type="Certificate",
        entity_id=certificate.id,
        event_type=EventKind.CERTIFICATION,
        task_id=task.id,
        actor="certification",
        payload={
            "certificate_key": certificate.certificate_key,
            "status": certificate.status,
            "evidence_hash": certificate.evidence_hash,
        },
    )

    session.flush()
    return CertificateBundle(
        certificate=CertificateRecord(
            certificate_id=certificate.id,
            certificate_key=certificate.certificate_key,
            status=certificate.status,
            evidence_hash=certificate.evidence_hash,
            issued_at=certificate.issued_at,
        ),
        binding=dict(certificate.payload or {}),
    )
