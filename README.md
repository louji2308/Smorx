# Software Evolution Intelligence System (Smorx)

The Software Evolution Intelligence System is an end-to-end software-engineering
orchestration platform built around a single invariant: the agent proposes, a
sandbox executes, execution evidence establishes what actually happened,
independent verification decides what can be trusted, intent authorization and
certification bind the proof to the implementation, and behavioral memory
preserves what was learned. The system is being implemented as one product with
eight journey tabs (Discover, Govern, Define, Analyze, Develop, Verify, Decide,
Certify) and contextual inspectors rather than a collection of disconnected
apps.

This README describes the current, real state of the repository. Features that
are planned but not yet implemented are explicitly marked as such; nothing here
describes a capability that does not yet exist.

## Repository layout

```
apps/api/               Phase 1 infrastructure: FastAPI service, Nebius Token Factory
                        routing, NVIDIA Nemotron model routing, proof-of-execution,
                        ConTree sandbox adapter.
apps/web/               Phase 0 scaffold: Next.js UI. Product journeys are planned
                        for later phases.
packages/contracts/     Shared contracts (pydantic schemas, registry, versioning).
packages/behavior/      Phase 2 behavioral data model: ORM entities, persistence,
                        evidence/provenance, versioning/immutability, repository
                        layer, deterministic demo seed.
packages/agent-runtime/ Phase 3 orchestrator runtime (module smorx_runtime): agents,
                        capabilities, task graph and waves, telemetry, orchestrator,
                        tool gateway protocol.
packages/tools/         Phase 4 tool layer + policy/control plane (module smorx_tools):
                        tool registry, execution, policies, audit trail, human and
                        sandbox control, repository/file handlers, control plane.
packages/precode/       Phase 7 Define+Analyze (module smorx_precode): change
                        definition, intent compilation, constitutional constraints,
                        intent ledger + lock, semantic impact map, verification
                        planner + lock, pre-coding context and lock gate.
packages/develop/       Phase 8 Develop (module smorx_develop): pre-coding handoff,
                        execution barrier, repository inspection, development plan,
                        sandbox workflow, coding-agent loop, execution capture with
                        the F1-F10 failure taxonomy, bounded repair, candidate
                        comparison, hash-chained execution traces.
packages/evidence/      Reserved (required by the structure gate; not yet created).
packages/verification/  Phase 9 Independent Verification (module smorx_verification):
                        six real verification modules (static analysis, differential
                        execution, historical ghost replay, metamorphic checks,
                        adversarial scenarios, mutation testing) that emit
                        claim-level evidence; independent trust/provenance layering
                        and a dedicated VerificationActor whose actor_run_id differs
                        from the source agent run.
packages/delta/         Phase 10 Verify to Decide (module smorx_delta): handoff that
                        only admits COMPLETED VERIFICATION_RESULT_V1 results, Candidate
                        Patch #2 with the original preserved untouched, deterministic
                        behavioral-delta classification, intent alignment, decision
                        gates with allow_merge, and an evidence-bound repair loop.
packages/certification/ Phase 11 Certification (module smorx_certification):
                        intent-alignment evaluation, independent re-verification
                        (evidence port), certificate generation with integrity hash,
                        failure archaeology, behavioral memory pipeline, and the
                        merge gate that only authorizes MERGED on real evidence.
packages/workflow/      Phase 12 Workflow + Demo Reliability (module smorx_workflow):
                        E2E orchestration driver over the AUTH-017 demo scenario,
                        hash-chained run events, state replay with tamper detection,
                        ten-mode failure injection, and demo reliability (resume,
                        reset, stale-sandbox cleanup, idempotency guards).
packages/ui/            Reserved (required by the structure gate; not yet created).
scripts/                quality_gate.py, phase_gate.py, env_check.py, validate_env.py,
                        scan_secrets.py, audit_deps.py, verify_migration.py.
tests/unit/             Unit test suites (current phases).
tests/integration/      Integration suites (lifecycle, certificate, references,
                        Phase 3/4 trust chain).
tests/security/         Adversarial guardrail suite (20 scenarios, Phase 3/4).
tests/e2e/              Reserved for later-phase end-to-end suites.
tests/evaluation/       Reserved for later-phase evaluation harnesses.
docs/adr/               Architecture decision records ADR-0001 .. ADR-0008.
infrastructure/docker/  Planned (referenced by the structure gate; reference
                        artifacts only - real provisioning is blocked on credentials).
infrastructure/nebius/  Planned (referenced by the structure gate; reference
                        artifacts only - real provisioning is blocked on credentials).
```

## Implemented capabilities by phase

- **Phase 0 - Repository structure and gate machinery**: contracts, ADR process,
  environment/secret/dependency checks, `scripts/quality_gate.py`, and
  `scripts/phase_gate.py`. The Phase 0 gate remains BLOCKED only on reserved
  structure gaps that later phases create (`packages/evidence`,
  `packages/ui`, `infrastructure/docker`, `infrastructure/nebius`).
- **Phase 1 - Nebius + NVIDIA infrastructure layer** (`apps/api`): FastAPI service
  with Token Factory inference routing, Nemotron model routing across three
  tiers, evidence-bound `machine_verifiable`, proof-of-execution, and a ConTree
  sandbox adapter with honest health states. Implemented and tested
  (109 unit tests), but real Nebius inference and sandbox execution are blocked
  on credentials; until they are provided, live inference/proof paths return
  configured errors rather than fabricating success.
- **Phase 2 - Behavioral data model and persistence** (`packages/behavior`):
  31-table schema (Alembic migration `4be282d73a12`), evidence service with
  content-addressed dedup, provenance traversal, versioning/immutability per
  ADR-0005, repository/catalog layer, and a deterministic demo seed. Tested
  against SQLite; migration verified in sync with the metadata. Gate:
  `PHASE_2_PASS`.
- **Phase 3 - Parallel orchestration runtime** (`packages/agent-runtime`,
  module `smorx_runtime`): `AgentSpec`/`Assignment` and the specialist
  capability catalog (CODING / VERIFICATION / EVIDENCE / REPAIR), `TaskGraph`
  with INDEPENDENT / DEPENDENT / RECONCILER / SERIALIZED task kinds,
  `ParallelWaveEngine` with real (measured) concurrency and cancellation,
  `SingleAgentScheduler`, parallelism telemetry (high-water + cross-task
  overlap), the orchestrator state machine with retry, failed-specialist
  replacement, no-progress blocking and bounded control, and
  `OrchestrationReport`. Gate: `PHASE3_GATE: PASS` (3 CODING agents + one
  RECONCILER ran with `parallelism_high_water=3` and real wall-clock overlap).
- **Phase 4 - Tool layer + policy/control plane** (`packages/tools`, module
  `smorx_tools`): tool registry and specs, real subprocess execution
  (`CommandRunner.run_python`), failure classification, policy engine with
  BLOCK / DENY / REQUIRE_REVIEW / ALLOW decisions, immutable audit trail,
  human-in-the-loop control (request/approve/deny/abort/pause), repository and
  file handlers, and `ControlPlane` as the single `CapabilityGateway`
  enforcement path (authorize -> policy -> duplicate-execution guard -> human
  approval -> execute -> audit). Sandbox operations honestly report
  `UNAVAILABLE` when no provider is bound; nothing is faked. Gate:
  `PHASE4_GATE: PASS`.
- **Adversarial guardrails**: 20-scenario security suite in
  `tests/security/test_adversarial_guardrails.py` covering unknown/unauthorized
  tools, timeouts and nonzero exits classified from real execution, evidence
  mismatches, contradictory findings, partial/cancelled waves, duplicate
  invocations, retry-budget and no-progress blocking, serialized exclusivity,
  policy BLOCK, honest `UNAVAILABLE`, audit-attribution integrity, stale-result
  rejection, and invalid state transitions.
- **Phase 7 - Define + Analyze** (`packages/precode`, module `smorx_precode`):
  change definition that rejects incomplete requests (critical requirements are
  never inferred), five-dimension intent compilation (ADD/REPLACE/PRESERVE/
  PERFORMANCE/SECURITY, ambiguity rejected, implicit PRESERVE guard),
  constitutional constraint resolution against the locked Behavioral
  Constitution (REPLACE conflicts surfaced with explicit-authorization risk
  notes), the Intent Ledger with a permanent single-flip lock and ADR-0005
  version bumps, the structured Semantic Impact Map (behaviors, components,
  dependencies, data flows, risk zones, Ghosts - a bare file list is rejected),
  the coverage-validated Verification Plan, and the pre-coding lock gate that
  produces the machine-readable PRE_CODING_CONTEXT and refuses to PASS unless
  every required object is valid and locked. Gate: `PHASE_7_PASS`.
- **Phase 8 - Develop / Coding Agent / Real Sandbox Loop** (`packages/develop`,
  module `smorx_develop`): pre-coding handoff with exact-version binding and
  forward-supersession stale-context rejection, the execution barrier (BLOCK on
  any failed condition - locked intent/impact/plan, version identity, explicit
  authorization), structured repository inspection, validated development plans,
  the sandbox workflow (real provider delegation when a `SandboxPort` is bound;
  an honestly labeled disposable local workspace otherwise; refusal to fabricate
  when neither is permitted), controlled attributed file mutations, real command
  execution with exit-code authority, the F1-F10 failure taxonomy, the bounded
  EXECUTE->OBSERVE->CLASSIFY->DIAGNOSE->DECIDE->MODIFY->RE-EXECUTE loop
  (repairs require a diagnosis; unauthorized repairs are denied by policy;
  success requires passing machine records; iteration/runtime/command/repair/
  no-progress bounds BLOCK), evidence-based multi-candidate comparison, and
  hash-chained attributable execution traces. The output is a CANDIDATE, never
  certified. Gate: `PHASE_8_PASS`.
- **Phase 9 - Independent Verification** (`packages/verification`, module
  `smorx_verification`): six real verification modules (static analysis,
  differential execution, historical ghost replay, metamorphic checks,
  adversarial scenarios, mutation testing) that emit claim-level evidence; trust
  layering from static analysis through the independent trust and provenance
  layers; a `VerificationActor` whose `actor_run_id` differs from the source
  agent run (the coding decision never verifies itself), and evidence binding so
  claims are only as strong as the execution evidence behind them. Gate:
  `PHASE_9_PASS`.
- **Phase 10 - Verify to Decision** (`packages/delta`, module `smorx_delta`):
  handoff that only admits COMPLETED `VERIFICATION_RESULT_V1` results, Candidate
  Patch #2 with the original Candidate Patch preserved untouched, deterministic
  behavioral-delta classification (UNCHANGED/ALTERED/ADDED/UNEXPLAINED; no
  evidence => UNEXPLAINED even with a SUPPORTING claim), intent alignment across
  CONSTRAINT/REQUIREMENT/SECURITY/PERFORMANCE, the decision gates (BLOCKED /
  INSUFFICIENT_EVIDENCE / REPAIR_REQUIRED / ELIGIBLE_TO_CONTINUE) with
  `allow_merge` only on ELIGIBLE_TO_CONTINUE, and an evidence-bound repair loop.
  Gate: `PHASE_10_PASS`.
- **Combined Phase 7->8 integration**: the full chain (request -> locks ->
  context -> handoff -> barrier -> sandbox -> fail -> diagnose -> repair ->
  passing candidate -> trace integrity) runs against real database rows and
  real subprocess executions in `tests/integration/test_phase7_phase8_flow.py`.
- **Phase 11 - Certification** (`packages/certification`, module
  `smorx_certification`): intent-alignment evaluation that is structurally
  distinct from behavioral delta (security-critical or protected behaviors
  must be covered by authorized intent), independent re-verification as an
  evidence port (BLOCKED on missing evidence, never fabricated), certificate
  generation whose integrity hash binds the certificate to its canonical
  payload over real rows (tampering breaks integrity), failure archaeology
  (failure is preserved as behavioral memory), the behavioral memory pipeline
  (closes the loop), and the merge gate that authorizes MERGED only when the
  candidate is verified, the certificate is certified and integrity-intact,
  alignment is certifiable, and every protected behavior is authorized - it
  degrades to ``allowed=False`` when the integrity import is unavailable
  instead of raising. Gate: `PHASE_11_PASS`.
- **Phase 12 - Workflow + Demo Reliability** (`packages/workflow`, module
  `smorx_workflow`): the end-to-end orchestration driver over the real
  AUTH-017 demo scenario (12 ordered phases with hash-chained, run-bound
  ConsequentialEvent records), deterministic-evidence caching (idempotent),
  state replay with hash-chain validation (tamper detection, expected-hash
  matching), run-scoped event ordering, ten-mode failure injection (real
  Execution/Failure/Evidence rows, idempotent re-injection, no-progress
  triple-failure fingerprint), and demo reliability: idempotency guards,
  resume-from-verified-chain (refuses tampered chains and out-of-segment
  targets), policy-gated reset, and stale-sandbox cleanup. Gate:
  `PHASE_12_PASS`.

## Setup

Requirements: Python 3.11.

```bash
python -m venv .venv
.venv\Scripts\activate                    # Windows
source .venv/bin/activate                 # POSIX
pip install -e packages/contracts packages/behavior packages/agent-runtime packages/tools packages/precode packages/develop packages/verification packages/delta packages/certification packages/workflow
```

The editable packages are `smorx-contracts`, `smorx-behavior`,
`smorx-runtime`, `smorx-tools`, `smorx-precode`, `smorx-develop`,
`smorx-verification`, `smorx-delta`, `smorx-certification`, and
`smorx-workflow` (each declared in its
`pyproject.toml`).
The API service keeps its own virtualenv under `apps/api/.venv`.

Tooling: `ruff` (lint + format), `mypy --strict`, `pytest` (root `pytest.ini`
and `conftest.py`). Install them into the working virtualenv as needed.

## Quality gate and phase gates

Run the full repository quality gate (env check, secret scan, dependency audit,
format, lint, typecheck, unit tests, build, web build):

```bash
python scripts/quality_gate.py
```

Run a machine-executable phase gate:

```bash
python scripts/phase_gate.py --phase 0
python scripts/phase_gate.py --phase 2
python scripts/phase_gate.py --phase 7
python scripts/phase_gate.py --phase 8
python scripts/phase_gate.py --phase 9
python scripts/phase_gate.py --phase 10
python scripts/phase_gate.py --phase 11
python scripts/phase_gate.py --phase 12
```

The gate CLI supports phases 0, 2, 3, 4, 7, 8, 9, 10, 11 and 12 and emits
`PHASE_N_PASS` or `PHASE_N_BLOCKED` with a machine-readable evidence map (exit
code 0 only for PASS). Phase 3 and Phase 4 were gated both through their
dedicated end-to-end runs (`PHASE3_GATE: PASS`, `PHASE4_GATE: PASS`) and
through the machine gate: `python scripts/phase_gate.py --phase 3` →
`PHASE_3_PASS`, `python scripts/phase_gate.py --phase 4` → `PHASE_4_PASS`.
Phases 7 and 8 gate as `PHASE_7_PASS` / `PHASE_8_PASS`, phases 9 and 10
gate as `PHASE_9_PASS` / `PHASE_10_PASS`, and phases 11 and 12 gate as
`PHASE_11_PASS` / `PHASE_12_PASS`.

## Tests

Current full suite (Phase 11/12 completion state):

```bash
python -m pytest tests/unit tests/integration tests/security   # 653 passed
```

- Unit: 597 tests.
- Integration: 29 tests (Phase 3/4 trust chain, lifecycle/certificate/reference,
  Phase 7->8 flow, and Phase 9/10 verify-to-decision flow).
- Security: 27 adversarial scenarios (the 20-scenario Phase 3/4 suite plus the
  7-scenario Phase 7 pre-coding suite).
- Phase 11/12 targeted run: **47 passed** (8 orchestrate, 10 replay, 11
  reliability, 9 failure inject, 9 merge gate) over real certification and
  workflow modules with no fakes or stubs.
- Phase 9/10 targeted run: **85 passed** (17 phase-gate contract tests, 28
  verification trust, 17 verification wave, 21 delta core, 2 integration
  flow), covering the real six-module verification wave and the
  verify-to-decision chain.

Earlier-phase suites, run individually:

```bash
python -m pytest tests/unit
python -m pytest tests/integration
python -m pytest tests/security
# Phase 1 API suite: run from the apps/api directory with the API's own
# virtualenv (its dependencies differ from the repository root venv)
#   .venv\Scripts\python -m pytest tests    # Windows
#   .venv/bin/python -m pytest tests        # POSIX
```

## Environment variables

The API service documents its configuration in `apps/api/.env.example`; the
behavior package documents its database configuration in
`packages/behavior/.env.example`. Copy the relevant file to `.env` and fill in
real values. Never commit a real `.env`.

| Variable | Purpose | Current state |
|---|---|---|
| `APP_ENV` / `SMORX_APP_ENV` | Runtime environment (`development` / `production`); `SMORX_APP_ENV` is read first by the scripts, `APP_ENV` is the `.env.example` name | Optional; defaults to `development` |
| `NEBIUS_API_KEY` | Nebius Token Factory inference authentication | Missing; live inference blocked until provided |
| `NEBIUS_INFERENCE_BASE_URL` | Inference base URL | Default `https://api.tokenfactory.nebius.com/v1` |
| `NEBIUS_AI_PROJECT` / `NEBIUS_PROJECT_ID` | Project id scoping sandbox namespaces (either is accepted) | Missing; real sandbox execution blocked until provided |
| `CONTREE_BASE_URL` | ConTree sandbox instance base URL | Default set in `.env.example` |
| `DATABASE_URL` | Persistence URL for `packages/behavior` (default file SQLite; Supabase PostgreSQL via `postgresql+asyncpg://...`) | Supabase value pending; not exercised against real PostgreSQL |

Additional model-routing, timeout, retry, and health-check variables are
documented in `apps/api/.env.example`.

## Known limitations

- Real Nebius sandbox and inference endpoints are not yet bound because no
  credentials have been provided. `UNAVAILABLE` responses for sandbox
  operations are intentional honesty, not a bug (AGENTS.md section 3).
  The Phase 8 coding-agent loop is proven end to end on the honestly labeled
  LOCAL_WORKSPACE backend; the PROVIDER backend (the Nebius path) is
  implemented and typed but requires credentials to exercise.
- The Phase 7/8 UI journeys (Change Definition through Candidate Patch) are
  not yet mounted: they are built against the persistent shell from Phases 5/6
  and are the next work item once the shell lands.
- Supabase PostgreSQL has not been exercised; persistence is tested against
  SQLite per the confirmed SQLite-test-first decision.
- The web UI and the `packages/evidence` and `packages/ui` packages are
  reserved for later phases; the product journeys and certification UI are
  planned, not yet implemented.
- `infrastructure/docker` and `infrastructure/nebius` contain reference/planned
  artifacts only; real provisioning is blocked on credentials.
- The working tree is uncommitted pending explicit commit approval
  (AGENTS.md section 32).