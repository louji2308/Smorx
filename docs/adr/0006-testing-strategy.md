# ADR-0006 — Testing Strategy

- Status: Accepted
- Date: 2026-09-12
- Supersedes: —

## Context

`Project Spec/IMPLEMENTATION_PLAN.md` Phase 0.6 requires development quality gates as a minimum: formatter, linter, type checking, test runner, build command, environment validation, secret scanning, and dependency audit. `AGENTS.md` demands three validation layers where applicable — unit/contract, integration, and runtime/evidence — and treats test evidence as authoritative over model assertions. The Phase 0 exit gate requires that contracts compile, state-machine tests pass, and the basic frontend/backend health path works.

The repo spans multiple packages and a FastAPI backend; each package is Python-first in Phase 0. Without a single, project-wide testing and quality convention, each agent session would introduce its own ad-hoc checks and the "quality gates" promised by the plan would not exist as runnable truth.

## Decision

Testing is organized into a layered top-level `/tests` tree:

```text
/tests
  /unit          contract, state-machine, loop-bound, versioning, phase-gate tests
  /integration   cross-package and backend integration
  /e2e           full journey and browser-level flows (Chrome DevTools)
  /security      adversarial and security-focused checks
  /evaluation    model/agent trajectory and evidence evaluation
```

Conventions established by Phase 0:

- A root `pytest.ini` sets `pythonpath` to the package src directories so `smorx_contracts` and `smorx_runtime` are importable from the root without per-test sys.path hacks.
- **ruff** is the linter and formatter for packages (linity conventions as configured in the package quality tooling).
- **mypy in strict mode with the pydantic v2 plugin** checks the packages; strict typing is required for contract and state-machine code where correctness is load-bearing.
- `quality_gate.py` (root-level script) composes the gates: format check, lint, type check, unit tests, environment validation, secret scan, dependency audit, and build (where a build exists for the phase). Any failing gate reports concrete failure reasons rather than a bare nonzero exit.
- CI (`.github`) mirrors exactly the same gates as `quality_gate.py` so that local and CI behavior do not diverge.

Phase 0 baseline tests cover: contracts (all seventeen registry entries plus schema/model validation), state transitions (valid and invalid), loop bounds (iteration caps, no-progress → BLOCKED), environment validation (required configuration present), and the phase-gate decision logic.

## Consequences

### Positive
- One convention across sessions: any agent can run the same quality command locally and in CI and compare results.
- Layered tests map to the required validation layers (unit/contract, integration, runtime/evidence).
- Strict mypy with the pydantic plugin catches contract-model errors before runtime.
- CI mirrors local gates, so "passes locally" is meaningful to automated checking.
- The configurable quality_gate.py gives the orchestrator a single control point for quality policy.

### Negative / Trade-offs
- Strict typing (mypy strict) is initially slower to satisfy and will reject some expedient code that later phases might otherwise write.
- A layered test tree is larger than a single test folder and requires every phase to place tests deliberately.
- Running the full gate (lint + type + unit + audits) on every change is slower than running only unit tests.

## Rejected alternatives

- **Per-package test folders only (no top-level /tests).** Rejected: it would scatter the Phase 0 baseline tests, make the whole-repo view harder to assess, and weaken the integration/e2e layers that span packages.
- **No static typing; rely on runtime tests alone.** Rejected: the contract and state-machine code is exactly where type errors are most expensive, and runtime tests alone miss cross-language contract drift.
- **One opaque CI script that prints "passed".** Rejected: AGENTS.md requires evidence-rich results and failure reasons; an aggregate score without per-gate detail is not reviewable evidence.

## Verification

- The phase gate runs `quality_gate.py` and requires every composed gate to pass (exit zero) with machine-readable reasons before `PHASE_0_PASS`.
- `tests/unit` baseline tests must pass in a clean environment; running them from the repo root without pre-installed test path configuration is part of the acceptance check.
- CI executes the same gates and a single failing gate fails the workflow.
- This ADR's claims are only that the gates exist and run; test result counts are recorded in execution evidence (test output, CI logs), not asserted here.