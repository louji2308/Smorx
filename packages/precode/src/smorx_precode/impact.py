"""Phase 7.5 — Semantic Impact Map.

Builds the structured Semantic Impact Map for a task and persists it in the
real ``SemanticImpact`` entity. The map is deliberately NOT a generic file
list (master prompt §7.5): it carries

- impacted behaviors and protected behaviors,
- impacted code components (functions/modules) and artifacts (files),
- dependency and data-flow edges,
- risk zones and historical Ghosts,
- the impact relationships between those nodes.

Analysis is evidence-first: every node is seeded from a structured
inspection payload supplied by the caller (in production this comes from
the real repository/archaeology inspection; in tests from deterministic
fixtures). This module never invents affected files to look thorough.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from smorx_behavior.models import SemanticImpact
from smorx_behavior.repo import base as repo_base
from smorx_behavior.versioning.lock import lock as versioning_lock
from sqlalchemy.orm import Session

__all__ = [
    "ImpactNode",
    "ImpactRelationship",
    "SemanticImpactError",
    "SemanticImpactMap",
    "build_semantic_impact",
    "get_semantic_impact",
    "lock_semantic_impact",
]


class SemanticImpactError(Exception):
    """Base error for semantic-impact failures."""


@dataclass(frozen=True)
class ImpactNode:
    """One node of the impact map. ``kind`` discriminates node types."""

    kind: str  # BEHAVIOR | COMPONENT | FILE | DEPENDENCY | DATA_FLOW | RISK_ZONE | GHOST
    ref: str
    protected: bool = False
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "ref": self.ref, "protected": self.protected, "note": self.note}


@dataclass(frozen=True)
class ImpactRelationship:
    """A directed relationship between two map nodes."""

    source_ref: str
    relation: str  # IMPACTS | DEPENDS_ON | FLOWS_INTO | PROTECTS | HISTORY_FOR
    target_ref: str
    rationale: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_ref": self.source_ref,
            "relation": self.relation,
            "target_ref": self.target_ref,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class SemanticImpactMap:
    """Structured impact view persisted into the SemanticImpact entity."""

    task_id: uuid.UUID
    semantic_impact_id: uuid.UUID
    version: int
    locked: bool
    status: str
    nodes: tuple[ImpactNode, ...]
    relationships: tuple[ImpactRelationship, ...]

    def impacted_refs(self, kinds: set[str] | None = None) -> tuple[str, ...]:
        refs = [node.ref for node in self.nodes if kinds is None or node.kind in kinds]
        return tuple(refs)

    def protected_refs(self) -> tuple[str, ...]:
        return tuple(node.ref for node in self.nodes if node.protected)

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": str(self.task_id),
            "semantic_impact_id": str(self.semantic_impact_id),
            "version": self.version,
            "locked": self.locked,
            "status": self.status,
            "nodes": [node.as_dict() for node in self.nodes],
            "relationships": [rel.as_dict() for rel in self.relationships],
        }


_NODE_KINDS: frozenset[str] = frozenset(
    {"BEHAVIOR", "COMPONENT", "FILE", "DEPENDENCY", "DATA_FLOW", "RISK_ZONE", "GHOST"}
)
_RELATIONS: frozenset[str] = frozenset(
    {"IMPACTS", "DEPENDS_ON", "FLOWS_INTO", "PROTECTS", "HISTORY_FOR"}
)


def _validate_nodes(nodes: list[ImpactNode]) -> None:
    seen: set[str] = set()
    for node in nodes:
        if node.kind not in _NODE_KINDS:
            raise SemanticImpactError(
                f"unknown impact node kind {node.kind!r}; expected one of {sorted(_NODE_KINDS)}"
            )
        if not node.ref.strip():
            raise SemanticImpactError("impact node ref must be non-empty")
        if node.ref in seen:
            raise SemanticImpactError(f"duplicate impact node ref {node.ref!r}")
        seen.add(node.ref)


def _validate_relationships(
    nodes: list[ImpactNode], relationships: list[ImpactRelationship]
) -> None:
    refs = {node.ref for node in nodes}
    for rel in relationships:
        if rel.relation not in _RELATIONS:
            raise SemanticImpactError(
                f"unknown impact relation {rel.relation!r}; expected one of {sorted(_RELATIONS)}"
            )
        if rel.source_ref not in refs or rel.target_ref not in refs:
            raise SemanticImpactError(
                f"impact relationship {rel.source_ref!r} -> {rel.target_ref!r} "
                "references an unknown node"
            )


def build_semantic_impact(
    session: Session,
    *,
    task_id: uuid.UUID,
    intent_item_ids: list[uuid.UUID] | None = None,
    nodes: list[ImpactNode],
    relationships: list[ImpactRelationship],
    description: str | None = None,
) -> SemanticImpactMap:
    """Validate and persist the structured impact map for ``task_id``.

    ``nodes`` and ``relationships`` are structured inputs derived from a
    real inspection of the target repository. Validation rules:

    - every node kind/ref must be well-formed and unique;
    - every relationship endpoint must be an existing node;
    - at least one BEHAVIOR node must be present (impact is behavioral,
      not a bare file list).

    Raises :class:`SemanticImpactError` on any violation.
    """
    _validate_nodes(nodes)
    _validate_relationships(nodes, relationships)
    if not any(node.kind == "BEHAVIOR" for node in nodes):
        raise SemanticImpactError(
            "semantic impact map requires at least one BEHAVIOR node; "
            "a generic file list is not an impact map"
        )

    scope: dict[str, Any] = {
        "nodes": [node.as_dict() for node in nodes],
        "relationships": [rel.as_dict() for rel in relationships],
    }
    row = SemanticImpact(
        task_id=task_id,
        intent_item_id=intent_item_ids[0] if intent_item_ids else None,
        description=description,
        scope=scope,
        impacted_behaviors=[node.ref for node in nodes if node.kind == "BEHAVIOR"],
        impacted_artifacts=[node.ref for node in nodes if node.kind in {"FILE", "COMPONENT"}],
        status="DRAFT",
        owner_scope="IMPACT",
        version=1,
        locked=False,
    )
    repo_base.save(session, row)
    return SemanticImpactMap(
        task_id=task_id,
        semantic_impact_id=row.id,
        version=row.version,
        locked=row.locked,
        status=row.status,
        nodes=tuple(nodes),
        relationships=tuple(relationships),
    )


def _map_from_row(row: SemanticImpact) -> SemanticImpactMap:
    scope = row.scope or {}
    nodes = tuple(
        ImpactNode(
            kind=str(node["kind"]),
            ref=str(node["ref"]),
            protected=bool(node.get("protected", False)),
            note=str(node.get("note", "")),
        )
        for node in scope.get("nodes", [])
    )
    relationships = tuple(
        ImpactRelationship(
            source_ref=str(rel["source_ref"]),
            relation=str(rel["relation"]),
            target_ref=str(rel["target_ref"]),
            rationale=str(rel.get("rationale", "")),
        )
        for rel in scope.get("relationships", [])
    )
    return SemanticImpactMap(
        task_id=row.task_id,
        semantic_impact_id=row.id,
        version=row.version,
        locked=row.locked,
        status=row.status,
        nodes=nodes,
        relationships=relationships,
    )


def get_semantic_impact(session: Session, task_id: uuid.UUID) -> SemanticImpactMap:
    """Load the (single) impact map for a task, raising when absent."""
    rows = repo_base.list_(session, SemanticImpact, task_id=task_id)
    if not rows:
        raise SemanticImpactError(f"no semantic impact map exists for task {task_id}")
    return _map_from_row(rows[0])


def lock_semantic_impact(session: Session, task_id: uuid.UUID) -> SemanticImpactMap:
    """Lock the task's impact map; the lock is permanent (I9)."""
    rows = repo_base.list_(session, SemanticImpact, task_id=task_id)
    if not rows:
        raise SemanticImpactError(f"no semantic impact map exists for task {task_id}")
    row = rows[0]
    if not row.locked:
        versioning_lock(session, row)
        row.status = "LOCKED"
        session.flush()
    return _map_from_row(row)
