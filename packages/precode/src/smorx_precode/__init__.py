"""Phase 7 — Define + Analyze.

Turns a human request into an immutable, testable verification contract
before any coding begins. The package owns the pre-coding domain:

- change definition (7.1) — normalize and validate a human request;
- intent compilation (7.2) — ADD / REPLACE / PRESERVE / PERFORMANCE / SECURITY;
- constitutional constraint resolution (7.3);
- the Intent Ledger and its immutable lock (7.4);
- the Semantic Impact Map (7.5);
- the Verification Plan (7.6) and its immutable lock (7.7);
- the pre-coding context and the lock gate (7.7) that Phase 8 consumes.

The package depends on the real ``smorx_contracts`` schemas and persists
through the real ``smorx_behavior`` ORM models and versioning service. It
never fabricates state and never silently mutates a locked object.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - static typing only
    from smorx_precode.change_definition import (
        ChangeDefinition,
        ChangeDefinitionError,
        ChangeDefinitionResult,
        TaskDefinitionError,
        define_change,
        get_change_definition,
    )
    from smorx_precode.impact import (
        SemanticImpactError,
        build_semantic_impact,
        get_semantic_impact,
        lock_semantic_impact,
    )
    from smorx_precode.intent_compiler import (
        AmbiguityError,
        IntentCompilerError,
        compile_intent,
    )
    from smorx_precode.intent_ledger import (
        ConstitutionMapperError,
        IntentLedgerError,
        IntentLedgerLockedError,
        build_intent_ledger,
        get_intent_ledger,
        lock_intent_ledger,
        resolve_constraints,
    )
    from smorx_precode.lock_gate import (
        PreCodingContext,
        PreCodingGateError,
        pre_coding_gate,
    )
    from smorx_precode.verification_plan import (
        VerificationPlanError,
        build_verification_plan,
        get_verification_plan,
        lock_verification_plan,
    )

__all__ = [
    "AmbiguityError",
    "ChangeDefinition",
    "ChangeDefinitionError",
    "ChangeDefinitionResult",
    "ConstitutionMapperError",
    "IntentCompilerError",
    "IntentLedgerError",
    "IntentLedgerLockedError",
    "PreCodingContext",
    "PreCodingGateError",
    "SemanticImpactError",
    "TaskDefinitionError",
    "VerificationPlanError",
    "build_intent_ledger",
    "build_semantic_impact",
    "build_verification_plan",
    "compile_intent",
    "define_change",
    "get_change_definition",
    "get_intent_ledger",
    "get_semantic_impact",
    "get_verification_plan",
    "lock_intent_ledger",
    "lock_semantic_impact",
    "lock_verification_plan",
    "pre_coding_gate",
    "resolve_constraints",
]

_MODULE_EXPORTS: dict[str, tuple[str, ...]] = {
    "ChangeDefinition": ("change_definition", "ChangeDefinition"),
    "ChangeDefinitionError": ("change_definition", "ChangeDefinitionError"),
    "ChangeDefinitionResult": ("change_definition", "ChangeDefinitionResult"),
    "TaskDefinitionError": ("change_definition", "TaskDefinitionError"),
    "define_change": ("change_definition", "define_change"),
    "get_change_definition": ("change_definition", "get_change_definition"),
    "AmbiguityError": ("intent_compiler", "AmbiguityError"),
    "IntentCompilerError": ("intent_compiler", "IntentCompilerError"),
    "compile_intent": ("intent_compiler", "compile_intent"),
    "ConstitutionMapperError": ("intent_ledger", "ConstitutionMapperError"),
    "resolve_constraints": ("intent_ledger", "resolve_constraints"),
    "IntentLedgerError": ("intent_ledger", "IntentLedgerError"),
    "IntentLedgerLockedError": ("intent_ledger", "IntentLedgerLockedError"),
    "build_intent_ledger": ("intent_ledger", "build_intent_ledger"),
    "get_intent_ledger": ("intent_ledger", "get_intent_ledger"),
    "lock_intent_ledger": ("intent_ledger", "lock_intent_ledger"),
    "SemanticImpactError": ("impact", "SemanticImpactError"),
    "build_semantic_impact": ("impact", "build_semantic_impact"),
    "get_semantic_impact": ("impact", "get_semantic_impact"),
    "lock_semantic_impact": ("impact", "lock_semantic_impact"),
    "VerificationPlanError": ("verification_plan", "VerificationPlanError"),
    "build_verification_plan": ("verification_plan", "build_verification_plan"),
    "get_verification_plan": ("verification_plan", "get_verification_plan"),
    "lock_verification_plan": ("verification_plan", "lock_verification_plan"),
    "PreCodingContext": ("lock_gate", "PreCodingContext"),
    "PreCodingGateError": ("lock_gate", "PreCodingGateError"),
    "pre_coding_gate": ("lock_gate", "pre_coding_gate"),
}


def __getattr__(name: str) -> object:
    module_name, attribute = _MODULE_EXPORTS.get(name) or ("", None)  # type: ignore[assignment]
    if attribute is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    module = importlib.import_module(f"{__name__}.{module_name}")
    return getattr(module, attribute)
