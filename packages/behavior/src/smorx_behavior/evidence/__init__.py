"""Evidence recording, eligibility, and provenance traversal services.

Phase 2 (implementation plan step 2.2): a thin service layer over the real
``smorx_behavior.models`` ORM tables. It enforces content-addressed
deduplication, the claim-support eligibility gate, ordered evidence lookups,
and eager-loaded lineage/certification traversal without any schema changes.
"""

from smorx_behavior.evidence.provenance import (
    certificate_traversal,
    claim_evidence_chain,
    evidence_to_certificate_path,
    provenance_path,
)
from smorx_behavior.evidence.service import (
    compute_content_hash,
    eligibility,
    evidence_by_hash,
    evidence_for_claim,
    evidence_for_task,
    record_evidence,
)

__all__ = [
    "certificate_traversal",
    "claim_evidence_chain",
    "compute_content_hash",
    "eligibility",
    "evidence_by_hash",
    "evidence_for_claim",
    "evidence_for_task",
    "evidence_to_certificate_path",
    "provenance_path",
    "record_evidence",
]
