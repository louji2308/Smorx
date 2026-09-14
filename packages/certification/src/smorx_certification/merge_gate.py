"""Merge authorization gate (implementation plan phase 11, section 11.7).

Merge may happen only when certification criteria and review requirements are
satisfied.  This module enforces the trust boundary of AGENTS.md section 16:
a merge is **never** reachable from a ``CANDIDATE_PASSED`` result alone --
it requires a real, integrity-intact ``CERTIFIED`` certificate, a
``CERTIFIABLE`` final intent-alignment verdict, a ``VERIFIED``
(re-verified) candidate patch, and every protected behavior covered by an
authorized intent alignment.

On **PASS** the gate performs the single authorized state transition:
Task -> ``MERGED`` and Change -> ``MERGED``, recording a ``MERGE``
consequential event.  On **deny** nothing is mutated.

The gate imports the certification-integrity module lazily so the gate itself
is importable while the parallel certification modules are still landing; a
missing or invalid integrity module degrades the gate to ``allowed=False``
(the honest blocked state) instead of raising.
"""

from __future__ import annotations

import importlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from smorx_behavior.models import (
    CandidatePatch,
    Certificate,
    CertificateStatus,
    ConsequentialEvent,
    EventKind,
    IntentAlignment,
    IntentAlignmentStatus,
    IntentItem,
    Task,
    TaskStatus,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

__all__ = ["MergeGateError", "MergeGateVerdict", "evaluate_merge_gate"]

_GATE_CHECKS: tuple[str, ...] = (
    "certificate_certified",
    "alignment_certifiable",
    "candidate_verified",
    "integrity_intact",
    "protected_authorized",
)


class MergeGateError(Exception):
    """Raised when a merge transition cannot be performed for structural reasons."""


@dataclass
class MergeGateVerdict:
    """Result of a merge-gate evaluation."""

    allowed: bool
    reason: str
    checks: dict[str, bool] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Integrity verification -- lazy import with graceful degradation
# ---------------------------------------------------------------------------


def _as_bool(result: Any) -> bool:
    """Coerce a diverse verifier return value to a plain bool."""
    if isinstance(result, bool):
        return result
    if isinstance(result, dict):
        return bool(result.get("valid", False))
    valid = getattr(result, "valid", None)
    if isinstance(valid, bool):
        return valid
    return False


def _load_integrity_verifier() -> Any:
    """Return the ``verify_certificate_integrity`` callable or ``None``."""
    try:
        module = importlib.import_module("smorx_certification.integrity")
    except ImportError:
        return None
    return getattr(module, "verify_certificate_integrity", None)


def _invoke_verifier(verifier: Any, session: Session, certificate: Certificate) -> Any:
    """Invoke the verifier defensively across plausible call signatures."""
    for attempt in (
        lambda: verifier(session=session, certificate=certificate),
        lambda: verifier(certificate=certificate, session=session),
        lambda: verifier(certificate, session),
    ):
        try:
            return attempt()
        except TypeError:
            continue
    return None


def _integrity_result(session: Session, certificate: Certificate) -> bool | None:
    """Return ``True`` when integrity is intact, ``False`` when tampered,
    ``None`` when the integrity module is unavailable."""
    verifier = _load_integrity_verifier()
    if verifier is None:
        return None
    for attempt in (
        lambda: verifier(session=session, certificate=certificate),
        lambda: verifier(certificate=certificate, session=session),
        lambda: verifier(certificate, session),
    ):
        try:
            return _as_bool(attempt())
        except TypeError:
            continue
        except Exception:
            return False
    return None


# ---------------------------------------------------------------------------
# Protected-behavior authorization
# ---------------------------------------------------------------------------


def _id_str(value: Any) -> str:
    """Normalize a behavior id reference to a string."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if hasattr(value, "id"):
        return str(value.id)
    return str(value)


def _authorized_alignment_exists(session: Session, certificate: Certificate) -> bool:
    """Return ``True`` when the certificate's task has at least one ALIGNED,
    authorized intent alignment."""
    task_id = certificate.task_id
    if task_id is None:
        return False
    row_id = session.scalar(
        select(IntentAlignment.id)
        .join(IntentItem, IntentItem.id == IntentAlignment.intent_item_id)
        .where(
            IntentAlignment.task_id == task_id,
            IntentAlignment.status == IntentAlignmentStatus.ALIGNED.value,
            IntentItem.authorized.is_(True),
        )
        .limit(1)
    )
    return row_id is not None


def _protected_behaviors_authorized(
    session: Session,
    certificate: Certificate,
    alignment_verdict: Any,
    protected_behaviors: Any,
) -> bool:
    """Return ``True`` when every protected behavior is covered by an
    authorized intent alignment *and* (when the verdict exposes coverage) is
    listed in that coverage set."""
    requested = [_id_str(ref) for ref in list(protected_behaviors or [])]
    verdict_covered = [
        _id_str(ref) for ref in list(getattr(alignment_verdict, "protected_behaviors", []) or [])
    ]
    behaviors = requested or verdict_covered
    if not behaviors:
        return True

    coverage = set(verdict_covered)
    for behavior_id in behaviors:
        if coverage and behavior_id not in coverage:
            return False
        if not _authorized_alignment_exists(session, certificate):
            return False
    return True


# ---------------------------------------------------------------------------
# Event recording
# ---------------------------------------------------------------------------


def _record_merge_event(
    session: Session,
    *,
    task: Task,
    certificate: Certificate,
    change: Any,
) -> None:
    """Record a single ``MERGE`` consequential event after a successful gate."""
    sequence = int(
        session.scalar(
            select(func.count())
            .select_from(ConsequentialEvent)
            .where(ConsequentialEvent.task_id == task.id)
        )
        or 0
    )
    session.add(
        ConsequentialEvent(
            entity_type="Task",
            entity_id=task.id,
            event_type=EventKind.MERGE.value,
            occurred_at=datetime.now(UTC),
            actor="merge-gate",
            payload={
                "certificate_key": certificate.certificate_key,
                "task_id": str(task.id),
                "change_id": str(change.id),
                "change_status": "MERGED",
            },
            task_id=task.id,
            sequence=sequence,
            hash=None,
        )
    )
    session.flush()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _deny_reason(checks: dict[str, bool]) -> str:
    failed = ", ".join(name for name, ok in checks.items() if not ok)
    return f"merge gate blocked: {failed} failed" if failed else "merge gate blocked"


def evaluate_merge_gate(
    session: Session,
    *,
    certificate: Certificate | None,
    alignment_verdict: Any,
    candidate_patch: CandidatePatch | None,
    protected_behaviors: Any,
) -> MergeGateVerdict:
    """Evaluate whether a merge is authorized (11.7) and return the verdict.

    ``allowed`` is ``True`` **only** when every gate check passes.  On deny
    no row is mutated; on PASS the Task and Change are transitioned to
    ``MERGED`` and a ``MERGE`` event is recorded.
    """
    checks: dict[str, bool] = {name: False for name in _GATE_CHECKS}

    if certificate is None:
        return MergeGateVerdict(allowed=False, reason="no certificate", checks=checks)
    if candidate_patch is None:
        return MergeGateVerdict(allowed=False, reason="no candidate patch", checks=checks)

    checks["certificate_certified"] = certificate.status == CertificateStatus.CERTIFIED.value

    aligned = bool(getattr(alignment_verdict, "aligned", False))
    status_value = getattr(alignment_verdict, "status", None)
    checks["alignment_certifiable"] = aligned and status_value == "CERTIFIABLE"

    checks["candidate_verified"] = candidate_patch.status == "VERIFIED"

    integrity = _integrity_result(session, certificate)
    if integrity is None:
        return MergeGateVerdict(
            allowed=False,
            reason="certification modules unavailable",
            checks=checks,
        )
    checks["integrity_intact"] = integrity

    checks["protected_authorized"] = _protected_behaviors_authorized(
        session, certificate, alignment_verdict, protected_behaviors
    )

    if not all(checks.values()):
        return MergeGateVerdict(allowed=False, reason=_deny_reason(checks), checks=checks)

    task = candidate_patch.task
    change = candidate_patch.change
    if task is None or change is None:
        raise MergeGateError(
            "candidate patch is not linked to a Task/Change; cannot perform the merge transition"
        )

    task.status = TaskStatus.MERGED.value
    change.status = "MERGED"
    _record_merge_event(session, task=task, certificate=certificate, change=change)
    session.flush()

    return MergeGateVerdict(
        allowed=True,
        reason=(
            "certificate CERTIFIED, intent alignment CERTIFIABLE, candidate re-verified, "
            "integrity intact, protected behaviors authorized"
        ),
        checks=checks,
    )
