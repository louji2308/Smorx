"""Phase 11 — Certification: Re-verification, Certificate, Memory.

Implements the certification layer on top of the Phase 9/10 verification
and repair outputs:

- re-verification engine: runs verification modules against Candidate Patch
  #2 under locked conditions; publishes before/after proof (FAIL -> PASS);
  blocks if locked conditions are not met (11.1);
- final intent alignment: consumes behavioral deltas + intent ledger;
  computes unexplained changes and critical unauthorized changes;
  returns CERTIFIABLE or NON_CERTIFIABLE (11.2);
- certificate generator: binds Change -> Commit -> Intent -> Protected
  Behaviors -> Behavioral Delta -> Verification Evidence -> Candidate
  Implementation -> Environment -> Dependency State -> Certificate Identity;
  machine-verifiable hash (11.3);
- certificate integrity: tamper detection, validation (11.4);
- merge gate: PASS only when certified + review requirements satisfied (11.5);
- failure archaeology: persist F-183, Ghost #221, claims, root-cause,
  repair, verification evidence (11.6);
- memory update pipeline: certified change -> new behavioral evidence ->
  updated knowledge -> preserved failure -> future context (11.7).

Model assertions never replace machine results; certification is
evidence-bound and machine-verifiable.
"""

from typing import Any

__all__ = [
    "AlignmentVerdict",
    "ArchaeologyRecord",
    "CertificateBundle",
    "CertificateIntegrityError",
    "CertificateRecord",
    "MemoryPipeline",
    "MemoryRecord",
    "MergeGateError",
    "MergeGateVerdict",
    "ReVerificationReport",
    "ReVerificationResult",
    "build_certificate",
    "compute_integrity_hash",
    "evaluate_alignment",
    "evaluate_merge_gate",
    "persist_archaeology",
    "run_memory_pipeline",
    "run_reverification",
    "verify_certificate_integrity",
]


def __getattr__(name: str) -> Any:
    if name in {
        "ReVerificationReport",
        "ReVerificationResult",
        "run_reverification",
    }:
        from smorx_certification import reverify

        return getattr(reverify, name)
    if name in {
        "AlignmentVerdict",
        "evaluate_alignment",
    }:
        from smorx_certification import alignment

        return getattr(alignment, name)
    if name in {
        "CertificateBundle",
        "CertificateRecord",
        "build_certificate",
    }:
        from smorx_certification import certificate

        return getattr(certificate, name)
    if name in {
        "CertificateIntegrityError",
        "compute_integrity_hash",
        "verify_certificate_integrity",
    }:
        from smorx_certification import integrity

        return getattr(integrity, name)
    if name in {
        "MergeGateError",
        "MergeGateVerdict",
        "evaluate_merge_gate",
    }:
        from smorx_certification import merge_gate

        return getattr(merge_gate, name)
    if name in {
        "ArchaeologyRecord",
        "persist_archaeology",
    }:
        from smorx_certification import archaeology

        return getattr(archaeology, name)
    if name in {
        "MemoryPipeline",
        "MemoryRecord",
        "run_memory_pipeline",
    }:
        from smorx_certification import memory

        return getattr(memory, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
