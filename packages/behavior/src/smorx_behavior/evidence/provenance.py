"""Evidence lineage and certification traversal (phase 2, steps 2.2/2.3).

Traversal helpers operate over real ORM objects attached to a live session
and use explicit ``joinedload``/``selectinload`` strategies so lineage, claim
chains, and the certificate binding map never degrade into N+1 queries
(AGENTS.md sections 17/19/24). All lookups are read-only; no rows are
created or mutated here.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import (
    Session,
    joinedload,
    object_session,
    selectinload,
)

from smorx_behavior.models import (
    BehavioralDelta,
    Certificate,
    Claim,
    Evidence,
    MemoryUpdate,
)

__all__ = [
    "certificate_traversal",
    "claim_evidence_chain",
    "evidence_to_certificate_path",
    "provenance_path",
]


def _session_of(obj: Any) -> Session:
    """Return the live session owning ``obj`` or fail with a clear message."""
    session = object_session(obj)
    if session is None:
        raise ValueError(
            f"{type(obj).__name__} is not attached to a live session; "
            "traversal requires a session-bound ORM instance"
        )
    return session


def provenance_path(evidence: Evidence) -> dict[str, Any]:
    """Return the execution lineage ``evidence -> task -> run -> agent_run
    -> subagent_run`` as an ordered list of record ids and kinded nodes.

    The lineage is structural (via the FK chain), so ordering is fixed by
    the model rather than by timestamps.
    """
    session = _session_of(evidence)
    row = session.scalar(
        select(Evidence)
        .options(
            joinedload(Evidence.task),
            joinedload(Evidence.run),
            joinedload(Evidence.agent_run),
            joinedload(Evidence.subagent_run),
        )
        .where(Evidence.id == evidence.id)
    )
    if row is None:
        raise ValueError(f"evidence {evidence.id} not found in session")

    nodes: list[dict[str, Any]] = [{"kind": "evidence", "id": row.id, "type": row.type}]
    if row.task is not None:
        nodes.append({"kind": "task", "id": row.task.id, "title": row.task.title})
    if row.run is not None:
        nodes.append({"kind": "run", "id": row.run.id, "status": row.run.status})
    if row.agent_run is not None:
        nodes.append({"kind": "agent_run", "id": row.agent_run.id, "role": row.agent_run.role})
    if row.subagent_run is not None:
        nodes.append(
            {"kind": "subagent_run", "id": row.subagent_run.id, "name": row.subagent_run.name}
        )

    return {
        "evidence_id": row.id,
        "ids": [node["id"] for node in nodes],
        "nodes": nodes,
    }


def evidence_to_certificate_path(evidence: Evidence) -> dict[str, Any]:
    """Return the certification path ``evidence -> claim -> behavioral_deltas
    -> certificates`` with ordered step records and a verdict string.

    The verdict is derived from the strongest certificate status reachable
    from the evidence's claim (CERTIFIED > ISSUED > DRAFT > REVOKED) or
    ``NO_CERTIFICATE`` when no certificate is linked. When the evidence is
    not bound to a claim the path ends at the evidence with verdict
    ``UNLINKED``.
    """
    session = _session_of(evidence)
    row = session.scalar(
        select(Evidence).options(joinedload(Evidence.claim)).where(Evidence.id == evidence.id)
    )
    if row is None:
        raise ValueError(f"evidence {evidence.id} not found in session")

    steps: list[dict[str, Any]] = [{"kind": "evidence", "id": row.id, "type": row.type}]
    claim = row.claim
    if claim is None:
        return {"evidence_id": row.id, "steps": steps, "verdict": "UNLINKED"}

    steps.append({"kind": "claim", "id": claim.id, "statement": claim.statement})

    loaded = session.scalar(
        select(Claim)
        .options(
            selectinload(Claim.behavioral_deltas).joinedload(BehavioralDelta.certificate),
            selectinload(Claim.certificates),
        )
        .where(Claim.id == claim.id)
    )
    if loaded is None:
        return {"error": f"claim {claim.id} no longer resolves"}
    deltas = sorted(loaded.behavioral_deltas, key=lambda d: (d.created_at, d.id))
    certificates = sorted(loaded.certificates, key=lambda c: (c.created_at, c.id))

    for delta in deltas:
        steps.append(
            {
                "kind": "behavioral_delta",
                "id": delta.id,
                "direction": delta.direction,
                "category": delta.category,
            }
        )
    for certificate in certificates:
        steps.append(
            {
                "kind": "certificate",
                "id": certificate.id,
                "key": certificate.certificate_key,
                "status": certificate.status,
            }
        )

    return {
        "evidence_id": row.id,
        "steps": steps,
        "verdict": _certificate_verdict(certificates),
        "delta_directions": [delta.direction for delta in deltas],
    }


def _certificate_verdict(certificates: list[Certificate]) -> str:
    """Rank the reachable certificate statuses into a single verdict string."""
    statuses = {certificate.status for certificate in certificates}
    if "REVOKED" in statuses:
        return "REVOKED"
    if "CERTIFIED" in statuses:
        return "CERTIFIED"
    if "ISSUED" in statuses:
        return "ISSUED"
    if statuses:
        return "DRAFT"
    return "NO_CERTIFICATE"


def claim_evidence_chain(claim: Claim) -> list[Evidence]:
    """Return every evidence row supporting ``claim`` in stable order."""
    session = _session_of(claim)
    return list(
        session.scalars(
            select(Evidence)
            .options(joinedload(Evidence.task), joinedload(Evidence.claim))
            .where(Evidence.claim_id == claim.id)
            .order_by(Evidence.created_at.asc(), Evidence.id.asc())
        ).all()
    )


def certificate_traversal(certificate: Certificate) -> dict[str, Any]:
    """Return a JSON-serializable binding map rooted at ``certificate``.

    The map binds the certificate to its linked evidence (via behavioral
    deltas, the claim's evidence chain, and memory-update references), the
    claim, behavioral deltas, and memory updates, preserving the
    certificate -> evidence -> claims -> deltas -> memory_updates traversal
    described in AGENTS.md section 19.
    """
    session = _session_of(certificate)
    row = session.scalar(
        select(Certificate)
        .options(
            joinedload(Certificate.claim).selectinload(Claim.evidence_items),
            selectinload(Certificate.behavioral_deltas).joinedload(BehavioralDelta.claim),
            selectinload(Certificate.behavioral_deltas).joinedload(BehavioralDelta.evidence),
            selectinload(Certificate.memory_updates).joinedload(MemoryUpdate.evidence),
        )
        .where(Certificate.id == certificate.id)
    )
    if row is None:
        raise ValueError(f"certificate {certificate.id} not found in session")

    claim = row.claim
    deltas = sorted(row.behavioral_deltas, key=lambda d: (d.created_at, d.id))
    memory_updates = sorted(row.memory_updates, key=lambda m: (m.created_at, m.id))

    evidence_by_id: dict[uuid.UUID, Evidence] = {}
    for delta in deltas:
        if delta.evidence is not None:
            evidence_by_id[delta.evidence.id] = delta.evidence
    if claim is not None:
        for item in claim.evidence_items:
            evidence_by_id[item.id] = item
    for update in memory_updates:
        if update.evidence is not None:
            evidence_by_id[update.evidence.id] = update.evidence
    evidence_rows = sorted(evidence_by_id.values(), key=lambda e: (e.created_at, e.id))

    def _iso(value: Any) -> str | None:
        return value.isoformat() if value is not None else None

    def _oid(value: uuid.UUID | None) -> str | None:
        return str(value) if value is not None else None

    return {
        "certificate": {
            "id": str(row.id),
            "certificate_key": row.certificate_key,
            "status": row.status,
            "owner_scope": row.owner_scope,
            "evidence_hash": row.evidence_hash,
            "issued_at": _iso(row.issued_at),
        },
        "claim": (
            {
                "id": str(claim.id),
                "statement": claim.statement,
                "status": claim.status,
            }
            if claim is not None
            else None
        ),
        "deltas": [
            {
                "id": str(delta.id),
                "metric": delta.metric,
                "direction": delta.direction,
                "category": delta.category,
                "observed": delta.observed,
                "evidence_id": _oid(delta.evidence_id),
            }
            for delta in deltas
        ],
        "evidence": [
            {
                "id": str(item.id),
                "type": item.type,
                "source": item.source,
                "artifact": item.artifact,
                "provenance": item.provenance,
                "hash": item.hash,
                "claim_id": _oid(item.claim_id),
                "verification_case_id": _oid(item.verification_case_id),
                "machine_result": item.machine_result,
            }
            for item in evidence_rows
        ],
        "memory_updates": [
            {
                "id": str(update.id),
                "kind": update.kind,
                "summary": update.summary,
                "applied": update.applied,
                "evidence_id": _oid(update.evidence_id),
            }
            for update in memory_updates
        ],
    }
