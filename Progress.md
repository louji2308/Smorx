# Progress — Software Evolution Intelligence System

## Current Phase
- Phase: 2 — Behavioral Data Model & Persistence (`IMPLEMENTATION_PLAN.md` §2, L586–711)
- Step: Phase 2 start — Wave 1 dispatch
- Status: EXECUTING

## Latest Orchestrator Decision
- Decision: Phase 2 implementation homes are `packages/behavior` (SQLAlchemy models + DB infra + persistence) and `packages/contracts` (`smorx_contracts`: 17 master contracts, versioning, evidence event schema per ADR-0002/ADR-0005). Tests live in root `tests/unit` + `tests/integration`. DB target = Supabase PostgreSQL; tests run on SQLite (`aiosqlite`) with dialect-agnostic models and PG-native DDL emitted via Alembic. Supabase wiring deferred until `DATABASE_URL`/`SUPABASE_DATABASE_URL` is provided by the user.
- Reason: ADR-0001 L27 reserves `/behavior` ("Behavioral model and behavioral knowledge"); ADR-0002 fixes contracts home + registry surface; plan §2 deliverables = PostgreSQL schema, migration system, repository/data-access layer, evidence event schema, seed/demo data.
- Evidence: `IMPLEMENTATION_PLAN.md` L586–711 (re-read this session); ADR-0001 L27; ADR-0002; ADR-0005; ADR-0007; `pytest.ini`; `conftest.py`; `scripts/phase_gate.py` (`_check_contracts` expects `CONTRACT_NAMES`/`get_registry`/`registry.validate`/`registry.schema_for`/`sample_instance`; `_check_contract_tests` runs `tests/unit/test_contracts`).

## Parallel Agent Wave — Wave 1 (dispatched, results pending)
- Agent A — Database/Infra: `packages/behavior/pyproject.toml`, `src/smorx_behavior/db/{naming,base,types,mixins,settings,engine}.py`, Alembic scaffolding (`alembic.ini`, `migrations/env.py`, `script.py.mako`, `migrations/versions/`), `packages/behavior/{.env.example,README.md}`, root test wiring (add `packages/behavior/src` to `pytest.ini` + `conftest.py`). Owns NO entity models, NO migration content.
- Agent B — Behavioral Model: `src/smorx_behavior/models/{enums.py, entities, __init__.py}` implementing all 30 plan entities + §2.4 `consequential_event` table. Imports Base/mixins/types/naming from Agent A's fixed API. Tests `tests/unit/test_models.py`.
- Agent C — Contracts & Event Schema: `packages/contracts` (`pyproject.toml`, `schemas/*.schema.json`, `src/smorx_contracts` incl. `CONTRACT_NAMES`, registry, `validate_contract`, `sample_instance`, `versioning`, evidence event schema). Tests `tests/unit/test_contracts/` (exact path the gate runs).
- Integration result: pending

## Implementation Changes
- Baseline (pre-existing, uncommitted Phase 0/1 artifacts on `main`): `apps/`, `packages/agent-runtime`, `packages/contracts` (empty until Wave 1), `docs/`, `tests/`, `scripts/`, `conftest.py`, `pytest.ini`, `.github/`, modified `.gitignore`.
- Wave 1 changes: pending

## Tests
- Unit: pending (Wave 1 agents each run their own)
- Integration: pending (Wave 2)
- E2E: pending (post-Phase 2)
- Chrome DevTools: N/A this phase (no browser surface; Phase 3+)
- Sandbox: N/A (Nebius wiring is later-phase; no mocks introduced)

## Blockers / Risks
- No Supabase `DATABASE_URL` — Supabase wiring deferred per user-chosen SQLite-test approach; re-ask at report.
- Root `README.md` is a 20-byte UTF-16 binary; skipped (note to user).
- No commit approval received — do not commit (AGENTS.md §32); pre-existing artifacts remain uncommitted.
- Gate `_check_quality` currently mypys `packages/contracts` + `packages/agent-runtime` only; extend to `packages/behavior` at fusion.

## Next Action
Dispatch Wave 1 (3 parallel subagents), review outputs, generate Alembic `0001_initial` from `Base.metadata`, dispatch Wave 2 (Evidence/Provenance, Versioning, Persistence/Seed/Test), integrate, run gates/tests, write 8-section report, update docs, ask user for `SUPABASE_DATABASE_URL` + commit approval.

---

# Phase 1 — Nebius + NVIDIA Infrastructure Layer (separate workstream)

## Current Phase
- Phase: 1 — Nebius + NVIDIA Infrastructure (`apps/api`)
- Step: Independent adversarial review findings applied (M1–M4 + high-value minors)
- Status: VERIFYING

## Latest Orchestrator Decision
- Decision: Apply the mandated review findings before the phase gate. M1 (health probe semantics + base image), M2 (evidence-bound `machine_verifiable`), M3 (logging formatter KeyError on foreign records), M4 (RetryPolicy not wired into live inference path).
- Reason: Review verdict was CONDITIONAL — fixes are required before the gate can pass.
- Evidence: adversarial review report; `pytest tests` 109 passed; `ruff check` clean; `mypy --strict` clean (33 files).

## Review Fixes Applied
- M1 — Sandbox health probe: probe image now `settings.sandbox_base_image` (`python:3.11-slim`, was hardcoded `ubuntu:latest`); missing-provisioned image (`ContreeImageNotFoundError`/`NotFoundError`) reports `DEGRADED` (API reachable, image not imported) instead of `UNHEALTHY`; proof path uses the configured base image. Locked by `test_health_reports_degraded_when_probe_image_missing`.
- M2 — `machine_verifiable` is now evidence-bound: `model_participated` requires the exact `INFRA_OK` token (`.strip().upper() == "INFRA_OK"`), `execution_authoritative` requires `exit_code == 0` and `SUCCEEDED`; `machine_verifiable = both`.
- M3 — `configure_logging` formatter no longer KeyErrors on third-party records: `_TraceFieldFilter` injects default trace fields (`event`, `request_id`, `run_id`, `operation_id`) before formatting. Locked by `test_configured_handler_formats_foreign_records`.
- M4 — `RetryPolicy` (transient-only: provider_unavailable/timeout/rate_limit) now wraps the live `chat_completion` SDK call via `_create_once`. Locked by retry + no-retry-on-auth tests.
- M1 (redaction): double pattern supports `nebius_api_key`-style underscore-prefixed keys and quoted values; verified live.
- Provider error text in 502 detail and timeout tails now run through `redact_secrets`.
- Timeout boundary uses strict `>` (no false timeout at `==`).
- Checkpoint no longer fabricates a server uuid when the SDK returns `None` (raises `SandboxExecutionError`).
- `sandbox_poll_secs` now wired into `ContreeConfig.operation_poll_secs_min`.
- Status detail uses `exc.message` (no cosmetic `[configuration_failure]` prefix).
- Docs/OpenAPI gated off in production (`app_env == "production"`). Locked by `test_docs_hidden_in_production`.

## Tests
- Unit: 109 passed (`pytest tests -q`; modules: config, errors, obs, retry, token_factory, router, nemotron, sandbox_adapter, proof, api)
- Ruff: `ruff check app tests` — All checks passed
- Mypy: `mypy --explicit-package-bases app tests` — no issues (33 files)
- Runtime: live uvicorn on 8099 — `/health` 200, `/api/v1/infra/status` clean detail, `/proof` 503 config, prod docs 404/404
- Chrome DevTools: N/A (API-only phase)

## Blockers / Risks
- No Nebius credentials provided — real inference + real sandbox E2E still gated (NEBIUS_API_KEY, NEBIUS_AI_PROJECT/NEBIUS_PROJECT_ID).
- ConTree base-image availability (`python:3.11-slim` vs `ubuntu:latest`) unproven until a real sandbox project exists.

## Next Action
Ask user for Nebius credentials; then run real integration tests + E2E proof; write docs (README UTF-8 rewrite, `docs/phase1-infrastructure.md`); phase-gate report.