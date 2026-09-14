"""Phase 9.1 — Trust boundary.

The verifier must NOT inherit authority from the Coding Agent. Every
verification wave runs under an explicit actor identity distinct from the
``agent_run_id`` that produced the candidate; any handoff that would let the
verifier reuse the coding agent's authority is rejected. The verifier may not
mutate the candidate patch without explicit authorization (independent
investigation must remain independent of the coding decision, AGENTS.md §16).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "TrustBoundaryError",
    "VerificationActor",
    "authorize_verification_actor",
    "guard_candidate_mutation",
]


class TrustBoundaryError(Exception):
    """Raised when the verifier attempts to cross the trust boundary."""


@dataclass(frozen=True)
class VerificationActor:
    """Identity under which one verification wave acts.

    ``source_agent_run_id`` is the coding-agent run that produced the
    candidate. The verifier's own identity (``actor_run_id``) must differ from
    it: the coding agent's capabilities, tokens, and history are NOT available
    to verification.
    """

    actor_run_id: str
    role: str = "INDEPENDENT_VERIFIER"
    source_agent_run_id: str | None = None
    labels: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "actor_run_id": self.actor_run_id,
            "role": self.role,
            "source_agent_run_id": self.source_agent_run_id,
            "labels": dict(self.labels),
        }


def authorize_verification_actor(
    *,
    actor_run_id: str,
    source_agent_run_id: str | None,
    role: str = "INDEPENDENT_VERIFIER",
) -> VerificationActor:
    """Create a verifier identity, rejecting coding-agent inheritance.

    Rules:
    - ``actor_run_id`` is required and must match a fresh id: it can never
      equal ``source_agent_run_id`` (no authority inheritance).
    - when a source coding-agent run is named, the verifier records it as
      provenance but is still a separate actor.
    """
    actor_run_id = actor_run_id.strip()
    if not actor_run_id:
        raise TrustBoundaryError("verifier requires a non-empty actor_run_id")
    if source_agent_run_id and source_agent_run_id.strip() == actor_run_id:
        raise TrustBoundaryError(
            "verifier actor_run_id must differ from the coding-agent "
            "source_agent_run_id; the verifier never inherits coding authority"
        )
    return VerificationActor(
        actor_run_id=actor_run_id,
        role=role,
        source_agent_run_id=source_agent_run_id,
    )


def guard_candidate_mutation(
    *, candidate_id: str, authorized: bool, actor: VerificationActor
) -> None:
    """Block candidate mutation unless explicitly authorized.

    The verifier inspects the candidate; it does not edit it. Mutating the
    candidate is the Coding Agent's act and requires an explicit
    ``authorized`` flag plus a separated verifier identity.
    """
    if not authorized:
        raise TrustBoundaryError(
            f"verifier {actor.actor_run_id} attempted to mutate candidate "
            f"{candidate_id!r} without authorization"
        )


def _stable_uuid(seed: str) -> uuid.UUID:
    import hashlib

    return uuid.UUID(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32])
