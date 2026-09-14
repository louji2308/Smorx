"""Phase 10 — Structured repair package (evidence-bound).

Builds the machine-readable repair contract that the Coding Agent receives.
This is a pure, deterministic builder — no session required, no side effects.

The repair package is the structured input to the repair loop (§10.4-10.6).
It never certifies; it never mutates Candidate Patch #1.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

__all__ = [
    "RepairPackageRecord",
    "RepairPlanError",
    "build_repair_package",
]


class RepairPlanError(Exception):
    """Raised when repair package inputs violate the schema contract."""


@dataclass(frozen=True)
class RepairPackageRecord:
    """Structured repair contract matching repair_package.schema.json (v1.0.0).

    Immutable, evidence-bound.  Never certifies.  Never mutates Candidate Patch #1.
    """

    id: str
    failure_id: str
    expected_behavior: str
    observed_behavior: str
    affected_claim_id: str
    required_outcome: str
    created_at: str
    version: str = "1.0.0"
    evidence_ids: tuple[str, ...] = ()
    suspected_path: str = ""
    acceptance_criteria: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Serialise to a dict that satisfies repair_package.schema.json."""
        return {
            "id": self.id,
            "version": self.version,
            "failure_id": self.failure_id,
            "expected_behavior": self.expected_behavior,
            "observed_behavior": self.observed_behavior,
            "affected_claim_id": self.affected_claim_id,
            "evidence_ids": list(self.evidence_ids),
            "suspected_path": self.suspected_path,
            "required_outcome": self.required_outcome,
            "acceptance_criteria": list(self.acceptance_criteria),
            "constraints": list(self.constraints),
            "created_at": self.created_at,
        }


def build_repair_package(
    *,
    failure_id: str,
    affected_claim_id: str,
    expected_behavior: str,
    observed_behavior: str,
    evidence_ids: tuple[str, ...],
    required_outcome: str,
    suspected_path: str = "",
    acceptance_criteria: tuple[str, ...] = (),
    constraints: tuple[str, ...] = (),
) -> RepairPackageRecord:
    """Build an evidence-bound repair package (pure, no session).

    Raises ``RepairPlanError`` on contract violations
    (repair_package.schema.json / minItems 1 on evidence_ids).
    """
    if not evidence_ids:
        raise RepairPlanError(
            "evidence_ids must be non-empty (repair_package.schema.json minItems 1)"
        )
    if not required_outcome:
        raise RepairPlanError("required_outcome must be non-empty")
    if not affected_claim_id:
        raise RepairPlanError("affected_claim_id must be non-empty")
    now = datetime.now(UTC).isoformat()
    return RepairPackageRecord(
        id=uuid.uuid4().hex,
        failure_id=failure_id,
        expected_behavior=expected_behavior,
        observed_behavior=observed_behavior,
        affected_claim_id=affected_claim_id,
        evidence_ids=evidence_ids,
        suspected_path=suspected_path,
        required_outcome=required_outcome,
        acceptance_criteria=acceptance_criteria,
        constraints=constraints,
        created_at=now,
    )
