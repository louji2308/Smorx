"""Phase 7 unit tests — intent compilation (§7.2).

Covers: ADD/REPLACE/PRESERVE/PERFORMANCE/SECURITY stay distinct; unknown
dimensions rejected; implicit PRESERVE guard prevents scope expansion;
ambiguity markers rejected; empty statements rejected.
"""

from __future__ import annotations

import pytest
from smorx_precode.intent_compiler import (
    AmbiguityError,
    IntentCompilerError,
    compile_intent,
    dimensions_from_contract_intents,
)


def _statements(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"intent_type": kind, "description": text} for kind, text in pairs]


def test_five_dimensions_stay_distinct() -> None:
    intents = compile_intent(
        objective="Add rate limiting",
        statements=_statements(
            ("ADD", "rate limiter middleware"),
            ("PERFORMANCE", "p95 latency under 50ms"),
            ("SECURITY", "no secrets in responses"),
            ("PRESERVE", "existing checkout flow"),
        ),
    )
    kinds = {intent.intent_type for intent in intents}
    assert kinds == {"ADD", "PERFORMANCE", "SECURITY", "PRESERVE"}
    dimensions = dimensions_from_contract_intents(intents)
    assert dimensions.add == ("rate limiter middleware",)
    assert dimensions.performance == ("p95 latency under 50ms",)
    assert dimensions.security == ("no secrets in responses",)
    assert dimensions.preserve == ("existing checkout flow",)


def test_replace_does_not_authorize_destruction_elsewhere() -> None:
    """A REPLACE is bounded to its declared scope (master prompt §7.2)."""
    intents = compile_intent(
        objective="Replace the auth token cache",
        statements=_statements(("REPLACE", "swap auth token cache implementation")),
    )
    preserves = [item for item in intents if item.intent_type == "PRESERVE"]
    assert len(preserves) == 1
    assert "not explicitly declared" in preserves[0].description
    replace_items = [item for item in intents if item.intent_type == "REPLACE"]
    assert replace_items[0].description == "swap auth token cache implementation"


def test_unknown_intent_type_is_rejected() -> None:
    with pytest.raises(IntentCompilerError) as excinfo:
        compile_intent(
            objective="obj",
            statements=_statements(("MAYBE", "sort of add a thing")),
        )
    assert "unknown intent_type" in str(excinfo.value)


def test_empty_description_is_rejected() -> None:
    with pytest.raises(IntentCompilerError):
        compile_intent(objective="obj", statements=_statements(("ADD", "   ")))


def test_no_statements_is_rejected() -> None:
    with pytest.raises(IntentCompilerError):
        compile_intent(objective="obj", statements=[])


def test_empty_objective_is_rejected() -> None:
    with pytest.raises(IntentCompilerError):
        compile_intent(objective="  ", statements=_statements(("ADD", "thing")))


@pytest.mark.parametrize(
    ("objective", "statement"),
    [
        ("Fix it somehow", "add caching"),
        ("Add something or whatever", "add caching"),
        ("Do X", "make it work as needed"),
        ("Clean up the codebase etc", "add typing"),
    ],
)
def test_ambiguity_markers_are_rejected(objective: str, statement: str) -> None:
    with pytest.raises(AmbiguityError) as excinfo:
        compile_intent(objective=objective, statements=_statements(("ADD", statement)))
    assert excinfo.value.markers


def test_explicit_preserve_is_kept_verbatim() -> None:
    intents = compile_intent(
        objective="Improve error pages",
        statements=_statements(
            ("ADD", "friendly error pages"),
            ("PRESERVE", "public API status codes"),
        ),
    )
    preserves = [item.description for item in intents if item.intent_type == "PRESERVE"]
    assert preserves == ["public API status codes"]
