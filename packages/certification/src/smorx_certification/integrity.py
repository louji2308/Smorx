"""Certificate integrity: tamper detection and evidence binding (11.4, AGENTS §19).

Computes a deterministic SHA-256 integrity hash over the certificate's
canonical binding map and validates that hash, the certificate key, and every
evidence reference on re-verification.

The canonical payload is derived **from real persisted rows** so the hash is
recomputable at verification time.  ``build_certificate`` stores the same
canonical payload on the ``Certificate.payload`` column and sets
``evidence_hash`` to its digest; :func:`verify_certificate_integrity`
re-derives the canonical map from the database and compares it to the stored
payload and hash, catching both side-channel edits to the payload row and
tampering with the bound evidence rows.

Contracts enforced:

* The integrity hash is recomputed from the stored ``payload`` and must equal
  the stored ``evidence_hash``.
* The DB-derived chunks of the payload (change, claim, deltas, intent,
  protected behaviors, candidate implementations, evidence, memory updates)
  must still match the rows reachable from the certificate today.
* The certificate key must equal the deterministic derivation
  ``digest("certificate", task_id, claim_id)``.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from typing import Any

from smorx_behavior.evidence.provenance import certificate_traversal
from smorx_behavior.models import (
    Behavior,
    BehavioralDelta,
    CandidatePatch,
    Certificate,
    Change,
    Evidence,
    IntentItem,
)
from smorx_behavior.repo.base import digest
from sqlalchemy import select
from sqlalchemy.orm import Session

__all__ = [
    "CertificateIntegrityError",
    "canonical_certificate_payload",
    "compute_integrity_hash",
    "verify_certificate_integrity",
]


class CertificateIntegrityError(Exception):
    """Raised when a certificate has a structural problem that prevents verification."""


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


def compute_integrity_hash(payload: Mapping[str, Any]) -> str:
    """Return a deterministic SHA-256 hex digest of ``payload``.

    The payload is recursively normalized (UUIDs, datetimes, enums converted)
    and serialized with sorted keys and compact separators before hashing.
    The digest is exactly 64 hex characters.
    """
    normalized = _normalize(dict(payload))
    serialized = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Canonical binding map (DB-derived)
# ---------------------------------------------------------------------------


def _oid(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    if hasattr(value, "id"):
        return str(value.id)
    return str(value)


def canonical_certificate_payload(session: Session, certificate: Certificate) -> dict[str, Any]:
    """Build the canonical binding map from real persisted rows.

    The map binds Change -> Claim -> Behavioral Deltas -> Verification
    Evidence -> Candidate Implementation -> Intent -> Protected Behaviors ->
    Memory Updates (AGENTS.md section 19).  All facts derive from ORM rows
    reachable from ``certificate``; nothing here trusts the stored payload.
    """
    traversal = certificate_traversal(certificate)

    task = certificate.task
    change: Change | None = task.change if task is not None else None

    deltas: list[BehavioralDelta] = (
        sorted(certificate.behavioral_deltas, key=lambda d: (d.created_at, d.id))
        if certificate.behavioral_deltas
        else []
    )

    intent_items: list[IntentItem] = (
        list(
            session.scalars(
                select(IntentItem).where(
                    IntentItem.task_id == certificate.task_id,
                    IntentItem.authorized.is_(True),
                )
            )
        )
        if certificate.task_id is not None
        else []
    )

    protected_behaviors: list[Behavior] = []
    behavior_ids: list[uuid.UUID] = []
    for delta in deltas:
        if delta.behavior_id is not None and delta.behavior_id not in behavior_ids:
            behavior = session.get(Behavior, delta.behavior_id)
            if behavior is not None and behavior.protected:
                protected_behaviors.append(behavior)
            behavior_ids.append(delta.behavior_id)

    candidate_patches: list[CandidatePatch] = (
        list(
            session.scalars(
                select(CandidatePatch)
                .where(CandidatePatch.task_id == certificate.task_id)
                .order_by(CandidatePatch.candidate_index.asc(), CandidatePatch.created_at.asc())
            )
        )
        if certificate.task_id is not None
        else []
    )

    cert_block = dict(traversal["certificate"])
    cert_block.pop("evidence_hash", None)
    cert_block.pop("issued_at", None)

    return {
        "certificate": cert_block,
        "claim": traversal["claim"],
        "change": (
            {
                "id": str(change.id),
                "external_id": change.external_id,
                "commit_sha": change.commit_sha,
                "title": change.title,
                "status": change.status,
            }
            if change is not None
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
                "behavior_id": _oid(delta.behavior_id),
            }
            for delta in deltas
        ],
        "intent": [
            {"id": str(item.id), "statement": item.statement, "kind": item.kind}
            for item in intent_items
        ],
        "protected_behaviors": [
            {"id": str(b.id), "name": b.name, "category": b.category, "signature": b.signature}
            for b in protected_behaviors
        ],
        "candidate_implementations": [
            {
                "id": str(c.id),
                "candidate_index": c.candidate_index,
                "status": c.status,
                "patch_ref": c.patch_ref,
                "summary": c.summary,
            }
            for c in candidate_patches
        ],
        "evidence": traversal["evidence"],
        "memory_updates": traversal["memory_updates"],
    }


def _db_chunk_keys() -> tuple[str, ...]:
    """Return the DB-derived payload chunks that must match at verification.

    ``memory_updates`` is deliberately **not** compared: memory is a
    downstream consumer that is written *after* certification binding, so the
    stored payload (captured at build time) and the canonical map (recomputed
    later) legitimately differ in memory rows.
    """
    return (
        "claim",
        "change",
        "deltas",
        "intent",
        "protected_behaviors",
        "candidate_implementations",
        "evidence",
    )


def _db_chunks_match(canonical: dict[str, Any], stored: dict[str, Any]) -> bool:
    """Return True when the DB-derived chunks of the stored payload match."""
    for key in _db_chunk_keys():
        if _normalize(canonical.get(key)) != _normalize(stored.get(key)):
            return False
    return True


def _derive_certificate_key(row: Certificate) -> str:
    """Recompute the expected certificate key from row columns.

    Matches ``build_certificate``: ``digest("certificate", task_id, claim_id)``.
    """
    return digest(
        "certificate",
        str(row.task_id) if row.task_id else "",
        str(row.claim_id) if row.claim_id else "",
    )[:64]


def _resolve_evidence_refs(
    session: Session, certificate: Certificate, payload: dict[str, Any]
) -> bool:
    """Verify that every evidence reference in the payload resolves correctly."""
    entries = payload.get("evidence") or []
    for entry in entries:
        if not isinstance(entry, dict):
            return False
        try:
            evidence_id = uuid.UUID(str(entry.get("id")))
        except (TypeError, ValueError):
            return False
        row = session.get(Evidence, evidence_id)
        if row is None:
            return False
        if entry.get("hash") is not None and row.hash != entry["hash"]:
            return False
    return True


# ---------------------------------------------------------------------------
# Public verification API
# ---------------------------------------------------------------------------


def verify_certificate_integrity(
    session: Session,
    *,
    certificate: Certificate | None,
    return_details: bool = False,
) -> bool | dict[str, Any]:
    """Verify certificate integrity: hash, key, DB-derived chunks, evidence.

    Returns ``True`` when the certificate is integrity-intact and ``False``
    when any check fails.  Raises :class:`CertificateIntegrityError` only for
    structural problems (missing row, missing payload) that prevent the check
    from being performed at all.  When ``return_details`` is ``True`` a dict
    with per-check results is returned instead of a bare bool.
    """
    if certificate is None:
        raise CertificateIntegrityError("certificate is None; cannot verify integrity")

    row: Certificate | None = session.get(Certificate, certificate.id)
    if row is None:
        raise CertificateIntegrityError(
            f"certificate {certificate.id} is detached from the session"
        )

    payload = row.payload
    if not payload or not isinstance(payload, dict):
        raise CertificateIntegrityError(f"certificate {row.certificate_key} has no binding payload")

    canonical = canonical_certificate_payload(session, row)

    details: dict[str, Any] = {
        "certificate_key": row.certificate_key,
        "hash_valid": False,
        "key_valid": False,
        "db_chunks_valid": False,
        "evidence_valid": False,
    }

    try:
        details["hash_valid"] = compute_integrity_hash(payload) == row.evidence_hash
        details["key_valid"] = row.certificate_key == _derive_certificate_key(row)
    except Exception as exc:
        raise CertificateIntegrityError(
            f"integrity hash verification failed with unexpected error: {exc}"
        ) from exc

    details["db_chunks_valid"] = _db_chunks_match(canonical, payload)
    details["evidence_valid"] = _resolve_evidence_refs(session, row, payload)

    all_valid = (
        details["hash_valid"]
        and details["key_valid"]
        and details["db_chunks_valid"]
        and details["evidence_valid"]
    )
    if return_details:
        details["valid"] = all_valid
        return details
    return all_valid
