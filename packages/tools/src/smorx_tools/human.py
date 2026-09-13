"""Explicit human approval / pause / abort control plane.

Phase 4 ``smorx_tools.human`` is the gate every high-risk operation must pass
before the control plane may execute it. The :class:`HumanControlPlane` exposes
the structural ``is_paused`` / ``can_execute`` / ``approval_for`` surface that
``smorx_tools.control`` relies on (through its ``ApprovalGate`` protocol), and
all approval lifecycle runs on UTC clocks with bounded expiry.

Expiry semantics: an *active* (``PENDING`` or ``APPROVED``) request whose
``expires_at`` is in the past is treated as ``EXPIRED``. A ``_prune`` helper
marks those on every read path; ``is_approved_for`` therefore returns ``False``
for expired approvals, while ``approval_for`` always returns the (possibly
pruned) latest matching request so the caller decides how to react.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class ControlState(StrEnum):
    """Lifecycle state of the human control plane."""

    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    ABORTED = "ABORTED"
    COMPLETED = "COMPLETED"


class ApprovalStatus(StrEnum):
    """Lifecycle status of a single approval request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"


class ApprovalError(Exception):
    """Raised when an approval lifecycle transition is not allowed."""


@dataclass(frozen=True)
class ApprovalRequest:
    """An immutable, attributable human-approval request."""

    approval_id: str
    requested_at: datetime
    action_id: str
    tool_name: str
    reason: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    expires_at: datetime | None = None
    decided_at: datetime | None = None
    decided_by: str = ""


class HumanControlPlane:
    """Explicit human approval/pause/abort model.

    High-risk operations must pass through this gate before the control plane
    may execute them.
    """

    def __init__(self, *, default_expiry_seconds: float = 300.0) -> None:
        self._default_expiry_seconds: float = default_expiry_seconds
        self._state: ControlState = ControlState.RUNNING
        self._requests: list[ApprovalRequest] = []

    @property
    def state(self) -> ControlState:
        """Current control-plane state."""
        return self._state

    def pause(self) -> None:
        """Transition ``RUNNING -> PAUSED``; while paused ``is_paused()`` is True."""
        if self._state is ControlState.ABORTED:
            raise ApprovalError("cannot pause: control plane is ABORTED")
        self._state = ControlState.PAUSED

    def resume(self) -> None:
        """Transition ``PAUSED -> RUNNING``."""
        if self._state is ControlState.ABORTED:
            raise ApprovalError("cannot resume: control plane is ABORTED")
        if self._state is not ControlState.PAUSED:
            return
        self._state = ControlState.RUNNING

    def abort(self) -> None:
        """Transition to ``ABORTED`` (terminal)."""
        self._state = ControlState.ABORTED

    def is_paused(self) -> bool:
        """``True`` only while the control plane is PAUSED."""
        return self._state is ControlState.PAUSED

    def can_execute(self) -> bool:
        """``True`` only while the control plane is RUNNING."""
        return self._state is ControlState.RUNNING

    def request_approval(
        self,
        *,
        action_id: str,
        tool_name: str,
        reason: str = "",
        ttl_seconds: float | None = None,
    ) -> ApprovalRequest:
        """Open a new PENDING approval request with a unique id and bounded TTL."""
        ttl = self._default_expiry_seconds if ttl_seconds is None else ttl_seconds
        requested_at = datetime.now(UTC)
        request = ApprovalRequest(
            approval_id=uuid.uuid4().hex,
            requested_at=requested_at,
            action_id=action_id,
            tool_name=tool_name,
            reason=reason,
            status=ApprovalStatus.PENDING,
            expires_at=requested_at + timedelta(seconds=ttl),
        )
        self._requests.append(request)
        return request

    def _prune(self) -> None:
        """Mark active (PENDING/APPROVED) requests past expiry as EXPIRED."""
        now = datetime.now(UTC)
        for index, request in enumerate(self._requests):
            is_active = request.status in (ApprovalStatus.PENDING, ApprovalStatus.APPROVED)
            if is_active and request.expires_at is not None and request.expires_at <= now:
                self._requests[index] = replace(request, status=ApprovalStatus.EXPIRED)

    def approval_for(self, action_id: str, tool_name: str) -> ApprovalRequest | None:
        """Return the latest matching request (ANY status, pruned), or ``None``.

        This satisfies the structural ``ApprovalGate`` protocol consumed by
        ``smorx_tools.control``.
        """
        self._prune()
        matching = [
            request
            for request in self._requests
            if request.action_id == action_id and request.tool_name == tool_name
        ]
        if not matching:
            return None
        return matching[-1]

    def pending_approvals(self) -> tuple[ApprovalRequest, ...]:
        """All requests currently awaiting a human decision."""
        self._prune()
        return tuple(
            request for request in self._requests if request.status is ApprovalStatus.PENDING
        )

    def approve(self, approval_id: str, *, by: str = "human") -> ApprovalRequest:
        """Transition a PENDING request to APPROVED (else ``ApprovalError``)."""
        return self._decide(approval_id, ApprovalStatus.APPROVED, by)

    def deny(self, approval_id: str, *, by: str = "human") -> ApprovalRequest:
        """Transition a PENDING request to DENIED (else ``ApprovalError``)."""
        return self._decide(approval_id, ApprovalStatus.DENIED, by)

    def _decide(self, approval_id: str, status: ApprovalStatus, by: str) -> ApprovalRequest:
        for index, request in enumerate(self._requests):
            if request.approval_id != approval_id:
                continue
            if request.status is not ApprovalStatus.PENDING:
                raise ApprovalError(f"approval {approval_id} is {request.status}, not PENDING")
            decided = replace(
                request,
                status=status,
                decided_at=datetime.now(UTC),
                decided_by=by,
            )
            self._requests[index] = decided
            return decided
        raise ApprovalError(f"no approval request with id {approval_id}")

    def is_approved_for(self, action_id: str, tool_name: str) -> bool:
        """``True`` when the latest matching request is APPROVED and unexpired."""
        request = self.approval_for(action_id, tool_name)
        if request is None:
            return False
        return request.status is ApprovalStatus.APPROVED
