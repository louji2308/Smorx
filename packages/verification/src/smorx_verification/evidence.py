"""Phase 9.8 — Evidence collection.

Each verification module emits its OWN evidence (``EvidenceRecord``); the
system never reduces verification to one opaque score. Records are persisted
through the real behavioral ``record_evidence`` service so the evidence chain
stays content-addressed, deduplicated, and traversable from claim to
certificate (AGENTS.md §17/§19/§24).
"""

from __future__ import annotations

import uuid
from typing import Any

from smorx_behavior.evidence.service import eligibility, record_evidence
from smorx_behavior.models import EvidenceType
from sqlalchemy.orm import Session

from smorx_verification.contracts import EvidenceRecord, ModuleType

__all__ = ["EvidenceCollector"]


def _evidence_type(module_type: ModuleType | str) -> EvidenceType:
    value = module_type.value if isinstance(module_type, ModuleType) else str(module_type)
    try:
        return EvidenceType(value)
    except ValueError:
        return EvidenceType.RUNTIME_OBSERVATION


class EvidenceCollector:
    """Durable evidence sink for one verification run.

    ``emit``/``emit_machine`` persist through the behavioral evidence service
    and return an :class:`EvidenceRecord` carrying the machine result, exit
    code, source, and provenance required by the claim-eligibility rule. Callers
    (each verification module) own their records; the collector never scores or
    sums them into a facade.
    """

    def __init__(self, *, session: Session, run_id: str, source: str) -> None:
        self._session = session
        self._run_id = run_id
        self._source = source
        self._records: list[EvidenceRecord] = []

    @property
    def records(self) -> tuple[EvidenceRecord, ...]:
        return tuple(self._records)

    def emit(
        self,
        *,
        module_type: ModuleType | str,
        claim_id: uuid.UUID | str,
        source: str,
        provenance: str,
        machine_result: dict[str, Any],
        exit_code: int,
        severity: str = "INFO",
        artifact: str = "",
        verification_case_id: uuid.UUID | None = None,
    ) -> EvidenceRecord:
        """Persist one module-emitted evidence record and return its view.

        ``machine_result`` must carry the raw machine observation; the claim
        binding (claim_id or verification_case_id) is required by the
        eligibility rule (AGENTS.md §10).
        """
        claim_uuid = claim_id if isinstance(claim_id, uuid.UUID) else uuid.UUID(str(claim_id))
        row = record_evidence(
            self._session,
            evidence_type=_evidence_type(module_type),
            source=source or self._source,
            provenance=provenance,
            artifact=artifact or None,
            machine_result={**machine_result, "module": str(module_type)},
            claim_id=claim_uuid,
            verification_case_id=verification_case_id,
            run_id=uuid.UUID(self._run_id) if self._is_uuid(self._run_id) else None,
        )
        admissible, reasons = eligibility(row)
        record = EvidenceRecord(
            evidence_type=module_type,
            claim_id=claim_uuid,
            source=row.source or source,
            provenance=row.provenance or provenance,
            artifact=row.artifact or artifact,
            machine_result=row.machine_result or machine_result,
            exit_code=exit_code,
            severity=severity,
            evidence_id=row.id,
            module_status="ELIGIBLE" if admissible else f"INELIGIBLE:{','.join(reasons)}",
        )
        self._records.append(record)
        self._session.flush()
        return record

    @staticmethod
    def _is_uuid(value: str) -> bool:
        try:
            uuid.UUID(value)
        except ValueError:
            return False
        return True
