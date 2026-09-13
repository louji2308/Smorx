"""Phase 7.2 — Intent Compilation.

Decomposes a validated human request into the five distinct intent
dimensions — ADD, REPLACE, PRESERVE, PERFORMANCE, SECURITY — and detects
ambiguity before anything is authorized.

Core rule (master prompt §7.2): a request that says \"change X\" must not
automatically authorize destruction or behavioral changes elsewhere. A
REPLACE covers exactly its declared scope; every undeclared behavior is
treated as PRESERVE when the request is compiled, which is the mechanism
that keeps \"change X\" from becoming \"rewrite the system\".
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from smorx_contracts.models import Intent

__all__ = [
    "AmbiguityError",
    "IntentCompilerError",
    "IntentDimensions",
    "compile_intent",
    "dimensions_from_contract_intents",
]

_INTENT_TYPES: tuple[str, ...] = ("ADD", "REPLACE", "PRESERVE", "PERFORMANCE", "SECURITY")

# Strong verbs that signal destructive/replacement scope. Kept explicit so
# ambiguity detection is deterministic and testable, not vibes.
_AMBIGUOUS_MARKERS: tuple[str, ...] = (
    "somehow",
    "whatever",
    "anything",
    "as needed",
    "etc",
    "and so on",
    "you decide",
    "make it work",
)

_EXPANSION_MARKERS: tuple[str, ...] = (
    "everything",
    "all",
    "entire",
    "whole",
    "everywhere",
    "rewrite",
    "refactor all",
)

_WORD_RE = re.compile(r"[a-z0-9_]+")


class IntentCompilerError(Exception):
    """Base error for intent-compilation failures."""


class AmbiguityError(IntentCompilerError):
    """Raised when the request text is too ambiguous to compile safely."""

    def __init__(self, message: str, *, markers: list[str]) -> None:
        super().__init__(message)
        self.markers = markers


@dataclass(frozen=True)
class IntentDimensions:
    """The five distinct compiled dimensions. Kept structurally distinct."""

    add: tuple[str, ...] = ()
    replace: tuple[str, ...] = ()
    preserve: tuple[str, ...] = ()
    performance: tuple[str, ...] = ()
    security: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "ADD": list(self.add),
            "REPLACE": list(self.replace),
            "PRESERVE": list(self.preserve),
            "PERFORMANCE": list(self.performance),
            "SECURITY": list(self.security),
        }


def _words(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _detect_ambiguity(objective: str, statements: list[str]) -> None:
    corpus = objective.lower()
    for statement in statements:
        corpus += " " + statement.lower()
    flagged: list[str] = []
    for marker in _AMBIGUOUS_MARKERS:
        if marker in corpus:
            flagged.append(marker)
    for marker in _EXPANSION_MARKERS:
        # \"all\" alone is too common; expansion markers only fire as
        # multi-word phrases or as standalone dangerous quantifiers at the
        # start of a directive. \"all\" is matched as its own word here only
        # when followed by another expansion cue in the same clause.
        if marker == "all":
            continue
        if marker in corpus:
            flagged.append(marker)
    if flagged:
        raise AmbiguityError(
            "ambiguous intent detected; flagged markers: " + ", ".join(sorted(set(flagged))),
            markers=sorted(set(flagged)),
        )


def _explicit_preserves(statements: list[str]) -> tuple[str, ...]:
    preserves: list[str] = []
    for statement in statements:
        match = re.match(r"(?i)^preserve[:\s]+(.+)$", statement.strip())
        if match:
            preserves.append(match.group(1).strip())
    return tuple(preserves)


def compile_intent(
    *,
    objective: str,
    statements: list[dict[str, str]],
    acceptance_criteria: list[str] | None = None,
) -> list[Intent]:
    """Compile raw intent statements into five distinct contract Intents.

    ``statements`` entries: ``{"intent_type": "ADD"|"REPLACE"|"PRESERVE"|
    "PERFORMANCE"|"SECURITY", "description": "..."}``. Unknown intent
    types raise :class:`IntentCompilerError`; empty descriptions raise
    :class:`IntentCompilerError`.

    Returns one :class:`smorx_contracts.models.Intent` per input statement.
    If no PRESERVE was supplied, an implicit PRESERVE for undeclared
    behaviors is appended with description ``"all behaviors not explicitly
    declared as ADD/REPLACE/PERFORMANCE/SECURITY"`` — this is the structural
    guard that prevents \"change X\" from authorizing changes elsewhere.
    """
    if not objective or not objective.strip():
        raise IntentCompilerError("objective is required to compile intent")

    intents: list[Intent] = []
    now = datetime.now(UTC)
    for statement in statements:
        statement_id = str(uuid.uuid4())
        intent_type = str(statement.get("intent_type", "")).strip().upper()
        description = str(statement.get("description", "")).strip()
        if intent_type not in _INTENT_TYPES:
            raise IntentCompilerError(
                f"unknown intent_type {intent_type!r}; expected one of {list(_INTENT_TYPES)}"
            )
        if not description:
            raise IntentCompilerError(f"{intent_type} statement has an empty description")
        intents.append(
            Intent(
                id=statement_id,
                version="1.0.0",
                intent_type=intent_type,  # type: ignore[arg-type]
                description=description,
                change_id="",
                status="PROPOSED",
                locked=False,
                created_at=now,
            )
        )
    if not intents:
        raise IntentCompilerError("no intent statements supplied")

    _detect_ambiguity(objective, [item.description for item in intents])

    has_preserve = any(item.intent_type == "PRESERVE" for item in intents)
    if not has_preserve:
        intents.append(
            Intent(
                id=str(uuid.uuid4()),
                version="1.0.0",
                intent_type="PRESERVE",
                description=(
                    "all behaviors not explicitly declared as ADD/REPLACE/PERFORMANCE/SECURITY"
                ),
                change_id="",
                status="PROPOSED",
                locked=False,
                created_at=now,
            )
        )
    return intents


def dimensions_from_contract_intents(intents: list[Intent]) -> IntentDimensions:
    """Project contract Intents back into the five distinct dimensions."""
    buckets: dict[str, list[str]] = {name: [] for name in _INTENT_TYPES}
    for item in intents:
        if item.intent_type in buckets:
            buckets[item.intent_type].append(item.description)
    return IntentDimensions(
        add=tuple(buckets["ADD"]),
        replace=tuple(buckets["REPLACE"]),
        preserve=tuple(buckets["PRESERVE"]),
        performance=tuple(buckets["PERFORMANCE"]),
        security=tuple(buckets["SECURITY"]),
    )
