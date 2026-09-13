"""Append-only audit trail for every policy/execution decision.

Phase 4 ``smorx_tools.audit``: an immutable :class:`AuditRecord` per event and
an insertion-ordered :class:`AuditTrail` ledger. The control plane records one
record per authorization and one per execution, so every consequential
invocation is attributable (``Task -> Decision -> Tool -> Result``) and the
duplicate-execution guard can inspect prior ``EXECUTED`` decisions.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AuditDecision(StrEnum):
    """Authoritative disposition of one audit event."""

    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
    REVIEW = "REVIEW"
    BLOCKED = "BLOCKED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class AuditRecord:
    """One immutable, attributable audit event."""

    audit_id: str
    recorded_at: datetime
    invocation_id: str
    request_id: str
    action_id: str
    agent_id: str
    task_id: str
    tool_name: str
    decision: AuditDecision
    reasons: tuple[str, ...] = ()
    risk_level: str = "low"
    resource_kind: str = "TOOL"
    resource_ref: str = ""
    exit_code: int | None = None
    outcome_classification: str = ""
    status: str = ""
    result_summary: str = ""


class AuditTrail:
    """Append-only in-memory ledger of audit records (insertion-ordered)."""

    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def record(self, record: AuditRecord) -> AuditRecord:
        """Append ``record`` (identity returned; the trail never mutates it)."""
        self._records.append(record)
        return record

    def records(self) -> tuple[AuditRecord, ...]:
        """All records in insertion order."""
        return tuple(self._records)

    def has_invocation(self, invocation_id: str) -> bool:
        """Whether any record carries ``invocation_id``."""
        return any(record.invocation_id == invocation_id for record in self._records)

    def has_action(self, action_id: str, tool_name: str) -> bool:
        """Whether any record exists for the ``action_id`` + ``tool_name`` pair."""
        return any(
            record.action_id == action_id and record.tool_name == tool_name
            for record in self._records
        )

    def by_tool(self, tool_name: str) -> tuple[AuditRecord, ...]:
        """Records for ``tool_name`` in insertion order."""
        return tuple(record for record in self._records if record.tool_name == tool_name)

    def by_agent(self, agent_id: str) -> tuple[AuditRecord, ...]:
        """Records for ``agent_id`` in insertion order."""
        return tuple(record for record in self._records if record.agent_id == agent_id)

    def summary(self) -> dict[str, object]:
        """JSON-serializable summary: total, per-decision counts, per-tool counts."""
        decision_counts = Counter(record.decision.value for record in self._records)
        tool_counts = Counter(record.tool_name for record in self._records)
        return {
            "total": len(self._records),
            "decisions": dict(sorted(decision_counts.items())),
            "tools": dict(sorted(tool_counts.items())),
        }
