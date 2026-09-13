"""Specialist capability catalog for the parallel multi-agent runtime.

Each specialist role in the Software Evolution Intelligence System owns a
distinct responsibility (``Requirements & Contract.md`` section 6 and
``IMPLEMENTATION_PLAN.md`` phase 3).  :data:`CAPABILITY_CATALOG` binds every
:class:`SpecialistCapability` to a description, the tool prefixes it may use,
and the plan phases that require it so the orchestrator can resolve which
specialists to delegate per phase (see :func:`capabilities_for_phase`).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SpecialistCapability(StrEnum):
    """The nine non-overlapping specialist roles a sub-agent may hold."""

    ARCHAEOLOGY = "ARCHAEOLOGY"
    KNOWLEDGE = "KNOWLEDGE"
    INTENT = "INTENT"
    IMPACT = "IMPACT"
    CODING = "CODING"
    VERIFICATION = "VERIFICATION"
    EVIDENCE = "EVIDENCE"
    REPAIR = "REPAIR"
    CERTIFICATION = "CERTIFICATION"


@dataclass(frozen=True)
class AgentCapability:
    """Declaration of one specialist role in the catalog.

    ``allowed_tool_prefixes`` entries are exact tool names (for example
    ``"command.run"``) or dotted prefixes terminated by ``"."`` (for example
    ``"file."`` matches ``file.read``).  An empty ``required_for_phase`` means
    the role is available in every phase.
    """

    capability: SpecialistCapability
    description: str
    allowed_tool_prefixes: tuple[str, ...]
    required_for_phase: tuple[str, ...] = ()


CAPABILITY_CATALOG: dict[SpecialistCapability, AgentCapability] = {
    SpecialistCapability.ARCHAEOLOGY: AgentCapability(
        capability=SpecialistCapability.ARCHAEOLOGY,
        description=(
            "Recover and interpret historical failure evidence; ghost-replay "
            "past executions to surface recurring behavioral defects."
        ),
        allowed_tool_prefixes=("evidence.", "file.read", "repository.inspect", "command.run"),
        required_for_phase=("6", "9", "10"),
    ),
    SpecialistCapability.KNOWLEDGE: AgentCapability(
        capability=SpecialistCapability.KNOWLEDGE,
        description=(
            "Gather and synthesize repository, contract, and external knowledge "
            "to ground task understanding and planning."
        ),
        allowed_tool_prefixes=("file.read", "repository.inspect", "web.", "contracts."),
    ),
    SpecialistCapability.INTENT: AgentCapability(
        capability=SpecialistCapability.INTENT,
        description=(
            "Assess whether a proposed behavioral change is authorized by intent, "
            "governing contracts, and protected behaviors."
        ),
        allowed_tool_prefixes=("file.read", "repository.inspect", "contracts.", "evidence."),
        required_for_phase=("10",),
    ),
    SpecialistCapability.IMPACT: AgentCapability(
        capability=SpecialistCapability.IMPACT,
        description=(
            "Analyze semantic impact: which behaviors, modules, and claims a "
            "change affects and what the behavioral delta means."
        ),
        allowed_tool_prefixes=("file.read", "repository.inspect", "evidence.", "graph."),
        required_for_phase=("7",),
    ),
    SpecialistCapability.CODING: AgentCapability(
        capability=SpecialistCapability.CODING,
        description=(
            "Plan and perform repository mutations; run builds and tests in the "
            "actual sandbox and observe real execution results."
        ),
        allowed_tool_prefixes=("file.", "command.run", "test.run", "sandbox."),
        required_for_phase=("8",),
    ),
    SpecialistCapability.VERIFICATION: AgentCapability(
        capability=SpecialistCapability.VERIFICATION,
        description=(
            "Run independent verification: static analysis, differential "
            "execution, metamorphic checks, and adversarial scenarios."
        ),
        allowed_tool_prefixes=("test.run", "command.run", "evidence.", "verify."),
        required_for_phase=("9", "11"),
    ),
    SpecialistCapability.EVIDENCE: AgentCapability(
        capability=SpecialistCapability.EVIDENCE,
        description=(
            "Capture, normalize, deduplicate, and fuse execution evidence so "
            "claims bind to real observations rather than model assertions."
        ),
        allowed_tool_prefixes=("evidence.", "file.read"),
    ),
    SpecialistCapability.REPAIR: AgentCapability(
        capability=SpecialistCapability.REPAIR,
        description=(
            "Diagnose classified failures and apply bounded, evidence-driven "
            "repair patches followed by re-test."
        ),
        allowed_tool_prefixes=("file.", "command.run", "test.run", "sandbox."),
        required_for_phase=("10",),
    ),
    SpecialistCapability.CERTIFICATION: AgentCapability(
        capability=SpecialistCapability.CERTIFICATION,
        description=(
            "Bind verified claims, behavioral deltas, and evidence into "
            "certificates that authorize merge and continuous memory."
        ),
        allowed_tool_prefixes=("evidence.", "certificate.", "repository.inspect", "contracts."),
        required_for_phase=("11",),
    ),
}


def capability_for(name: SpecialistCapability) -> AgentCapability:
    """Return the catalog entry for a capability, or a helpful :class:`KeyError`."""
    try:
        return CAPABILITY_CATALOG[name]
    except KeyError as exc:
        available = ", ".join(member.value for member in SpecialistCapability)
        raise KeyError(f"unknown specialist capability {name!r}; available: {available}") from exc


def capabilities_for_phase(phase: str) -> tuple[SpecialistCapability, ...]:
    """Return capabilities applicable to a plan phase, in catalog order.

    A role is applicable when ``phase`` is listed in its ``required_for_phase``
    or when the role declares no phase requirement (universal role, for
    example :class:`SpecialistCapability.EVIDENCE`).
    """
    return tuple(
        entry.capability
        for entry in CAPABILITY_CATALOG.values()
        if not entry.required_for_phase or phase in entry.required_for_phase
    )
