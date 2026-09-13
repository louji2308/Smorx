# ADR-0002 — Contract Architecture

- Status: Accepted
- Date: 2026-09-12
- Supersedes: —

## Context

`Project Spec/IMPLEMENTATION_PLAN.md` Phase 0.2 requires typed schemas for the seventeen master contracts: task, action, tool_invocation, execution_result, failure, evidence, claim, behavioral_object, intent, verification_plan, candidate_patch, behavioral_delta, repair_package, certificate, agent_run, subagent_run, and phase_gate. `Requirements & Contract.md` treats these contracts as executable architectural laws: every request, decision, execution result, evidence item, and certificate must be representable in a machine-validated form.

The system crosses language boundaries — Python (FastAPI, packages) and TypeScript (Next.js client) — and the contracts must be the same truth in both worlds. Any drift between the languages would break the evidence chain (task → decision → tool call → result) and certification binding.

## Decision

Master contracts live in `packages/contracts` and exist in two machine-readable representations:

1. **JSON Schema files** under `packages/contracts/schemas/` — one versioned schema file per contract (cross-language, language-agnostic, the canonical source of truth).
2. **Python pydantic v2 models** in the `smorx_contracts` package (src layout under `packages/contracts/`) — generated or kept in synchronization with the JSON Schemas so the backend and package code validate real objects at runtime.

A **ContractRegistry** in `smorx_contracts` enforces the set of exactly seventeen named contracts: it validates that each contract name resolves to a schema and a pydantic model, and that required cross-references (for example evidence→claim, certificate→verification evidence) are present.

TypeScript bindings for the frontend are intentionally deferred to later phases. They can be generated from the same JSON Schemas when the web application needs them; no parallel hand-maintained TypeScript contract definitions are created.

The contract package name that the implementation plan establishes is `smorx_contracts`; versioning of the schema files follows ADR-0005.

## Consequences

### Positive
- One source of truth: JSON Schemas are the canonical definition, pydantic models and future TypeScript types are derived from them, preventing cross-language drift.
- Registry enforcement makes a missing or renamed contract fail fast at import/validation time rather than surfacing as a runtime mismatch.
- Machine-readable schemas support the verification family (static analysis, differential execution, mutation testing) and phase-gate checks that read contract definitions programmatically.
- Runtime validation (pydantic v2) means invalid evidence, un-attributable tool results, or malformed claims are rejected before they enter the evidence chain.

### Negative / Trade-offs
- Maintaining JSON Schema + pydantic models in sync requires generation or discipline in the package build.
- The registry adds a small validation layer that every contract consumer must be aware of.
- Frontend type benefits are deferred until TypeScript bindings are generated in a later phase.

## Rejected alternatives

- **Hand-written TypeScript interfaces maintained in parallel** from Phase 0. Rejected: two hand-maintained contract definitions virtually guarantee drift, and the frontend does not consume contracts until later phases; generated bindings from JSON Schema are strictly cheaper and drift-proof.
- **Python-only contract definitions (no JSON Schema).** Rejected: it would make the contracts unreadable to the TypeScript client, CI tooling, and any non-Python automation, and would lock the architecture to one runtime language.
- **Single unstructured dataclass/Dict contract set.** Rejected: it would forfeit runtime validation and cross-language readability and would make the ContractRegistry and evidence-chain guarantees unenforceable.

## Verification

- Unit tests under `tests/unit` (Phase 0 baseline) validate that the ContractRegistry resolves all seventeen named contracts and rejects unknown names.
- Schema validation tests instantiate realistic payloads (for example a tool_invocation with a result, a failure with classification) and confirm pydantic models accept the valid forms and reject invalid ones.
- The phase gate calls the registry to confirm all seventeen contracts are registered before reporting PASS.
- Compatibility of schema versions is checked through the versioning mechanics described in ADR-0005.