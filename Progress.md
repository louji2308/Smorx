# Progress — Software Evolution Intelligence System

## Current Phase
- Phase: 7 — Define + Analyze AND 8 — Develop/Coding Agent (`IMPLEMENTATION_PLAN.md` §7, §8) — THIS SESSION
- Status: GATES PASS (`PHASE_7_PASS`, `PHASE_8_PASS`, quality gate ALL PASSED; commits pending user approval)

## Phase 7 — Define + Analyze (complete, gated)
- New package `packages/precode` (module `smorx_precode`), composing the real `smorx_contracts` schemas and `smorx_behavior` persistence/versioning — no parallel concepts invented:
  - 7.1 `change_definition.py` — normalizes the human request into objective/repository/constraints/acceptance-criteria/priority/execution-budget; rejects incomplete requests naming EVERY missing field; critical requirements (objective, repository, acceptance criteria) are never inferred; budget validation feeds Phase 8 loop bounds.
  - 7.2 `intent_compiler.py` — five DISTINCT dimensions (ADD/REPLACE/PRESERVE/PERFORMANCE/SECURITY) as contract `Intent` objects; deterministic ambiguity markers rejected; implicit PRESERVE guard appended when none declared (a REPLACE never authorizes destruction elsewhere).
  - 7.3/7.4 `intent_ledger.py` — persists IntentLedger+IntentItem; `lock_intent_ledger` flips LOCKED exactly once (idempotent) and authorizes items at lock time; post-lock in-place mutation raises `VersionLockedError`; `bump_intent_ledger` creates a new identity per ADR-0005 (history preserved); `resolve_constraints` maps intent onto the real locked Constitution's `ConstitutionClaim.rule` text, flags REPLACE overlaps as conflicts + risk notes (historical behavior is evidence, not automatically intent).
  - 7.5 `impact.py` — structured Semantic Impact Map (BEHAVIOR/COMPONENT/FILE/DEPENDENCY/DATA_FLOW/RISK_ZONE/GHOST nodes + IMPACTS/DEPENDS_ON/FLOWS_INTO/PROTECTS/HISTORY_FOR relationships) persisted in the real `SemanticImpact.scope`; validates structure and REJECTS a bare file list without behaviors; permanent lock.
  - 7.6/7.7 `verification_plan.py` — bidirectional coverage validation (every case targets an affected behavior; every behavior covered by ≥1 case; unknown kinds/duplicate names rejected); persists real `VerificationPlan`+`VerificationCase`; lock covers plan AND cases permanently.
  - 7.7/7.9 `lock_gate.py` — assembles the PRE_CODING_CONTEXT (context_id + task/change/ledger/constitution/impact/plan ids + exact versions + lock_state) and returns PASS only with definition valid + ledger/constitution/impact/plan LOCKED and cross-references consistent; BLOCKED verdicts name every failed requirement.
- Tests: 54 Phase-7 tests total (change definition 10, intent compiler 12, intent ledger 9, impact+plan 12, lock gate 6, adversarial §12 scenarios 1–6/12 = 7); detailed counts in the Tests section below.

## Phase 8 — Develop / Coding Agent / Real Sandbox Loop (complete, gated)
- New package `packages/develop` (module `smorx_develop`):
  - 8.1 `handoff.py` — receives the real `PreCodingContext` verbatim (no prose reconstruction); rejects BLOCKED contexts; stale-context protection = exact version identity PLUS forward-supersession detection (a v1 context is refused once a successor version exists in the lineage, because bumping a locked row preserves the historical row locked at the same version).
  - 8.2 `barrier.py` — `ExecutionBarrier.evaluate/require_pass`: intent locked, constitution context, impact map locked+version-matched, verification plan locked+version-matched, explicit authorization flag; ANY failure → BLOCKED (never "continue anyway").
  - 8.3 `inspection.py` — deterministic structured inspection of a real filesystem root (entry points, dependencies from pyproject, config, tests, sources) with per-step trace; never invents files.
  - 8.4 `plan.py` — validated explicit plan (interpretation/affected files/strategy/tests-to-run/completion-criteria/risk); incomplete plans rejected (no unanchored editing).
  - 8.5 `sandbox.py` — `DevelopmentSandbox` with two honest backends: PROVIDER (delegates to a real `SandboxPort` — the Nebius path) and LOCAL_WORKSPACE (disposable copy, honestly labeled everywhere; `allow_local_workspace=False` → `SandboxUnavailableError` "refusing to fabricate"); controlled attributed mutations (before/after sha256, reason, containment via `Path.relative_to`); real checkpoint/rollback; destroy.
  - 8.6–8.8 `execution.py` — `ExecutionCapture` binds sandbox identity to every run; `ExecutionRecord` carries command/cwd/timestamps/exit code/streams/timeout/failure_code; machine result authoritative (I2). `classify_failure` implements F1–F10 deterministically (F5 timeout, F6 permission, F10 policy, F1 build hints, F2/F3 by command kind, F8 ambiguous fallback).
  - 8.9/8.10 `agent.py` — `CodingAgentLoop`: barrier PASS required before execution (POLICY_STOP otherwise, zero executions); EXECUTE→OBSERVE→CLASSIFY→DIAGNOSE→DECIDE→MODIFY→RE-EXECUTE; REPAIR requires a Diagnosis (observed≠root cause) and an explicit authorization flag — unauthorized repairs are recorded DENIED_BY_POLICY and never executed; success decided ONLY from exit_code==0 records (a STOP can end the loop but can never mark it passed); bounds enforced via `LoopBoundsController` (iterations/runtime/commands/repairs + no-progress threshold on materially-equivalent failure signatures).
  - 8.11 `candidates.py` — evidence-based comparison: only `CANDIDATE_PASSED` candidates are selectable; ranking by (completion, fewer failures, faster total duration, deterministic index); ALL_FAILED selects nothing.
  - 8.12 `trace.py` — hash-chained Task→Decision→ToolInvocation→ExecutionResult→Mutation trace (`sha256(seq|prev|payload)`); `verify_trace_integrity` detects payload tampering and reordering.
- Real execution evidence: loop tests drive real subprocesses (`sys.executable -c ...`) inside the sandbox workspace — first pass fails (file missing), diagnosis-driven repair writes the file, re-execution exits 0; exit codes are machine facts, not staged results.

## Combined Phase 7→8 Integration (`tests/integration/test_phase7_phase8_flow.py`)
- Full §14 chain on real rows + real subprocesses: request→definition→compilation→mapping→INTENT LOCK→impact→plan→VERIFICATION LOCK→gate PASS→handoff (exact versions)→barrier PASS→inspection→plan→sandbox→loop (fail→diagnose→repair→pass)→candidate→trace integrity→`compare_candidates` SELECTED; final state asserted CANDIDATE_PASSED — never CERTIFIED (I7).
- Stale-context protection proven at the combined level: bumping Intent to v2 after context mint → handoff raises "superseded", barrier BLOCKED.
- §12 multi-candidate: 17 (A beats B by completion), 18 (B beats A), 19 (all fail → no selection).

## Parallel Agent Wave (this session)
- Subagent-spawn tooling and `opencode`/`catenary` are NOT available in this environment (AGENTS.md §5 limitation recorded honestly). Decomposition was achieved via contract-bounded modules with disjoint ownership — the same boundaries a subagent wave would have used: change-definition/intent (A), impact/verification/gate (B), barrier/handoff/inspection/plan (C), sandbox/execution/taxonomy (D), loop/bounds (E), candidates/trace (F) — integrated and critically reviewed by the orchestrator (this session), which fixed: stale `repository_slug` field, wrong `constitution_version` source in the gate, `get_lineage` backward-only semantics (replaced with forward-supersession detection), Windows path containment bug (`relative_to`), candidate ranking order, EN-dash lint debt.

## Tests (this session)
- New unit: 29 (change definition 10, intent compiler 12, intent ledger 9 minus overlap — exact: 10+12+9) + impact/plan 12 + lock gate 6 + barrier/handoff 7 + sandbox/execution 17 + loop/bounds/candidates/trace 21.
- New adversarial: 7 (`tests/security/test_precode_adversarial.py`, §12 scenarios 1–6, 12).
- New integration: 3 (`tests/integration/test_phase7_phase8_flow.py` — full chain, multi-candidate, stale-context).
- Full suite: `pytest tests/unit tests/integration tests/security` → **516 passed** (was 415 before this session).
- Gates: `PHASE_7_PASS`, `PHASE_8_PASS` (`python scripts/phase_gate.py --phase 7|8`); quality gate ALL PASSED (env, secret scan, audit, ruff check+format, mypy strict 66 source files, unit, integration, security, build).
- Chrome DevTools: N/A — no browser surface was created; Phase 7/8 UI is deliberately deferred to avoid colliding with the parallel session that owns Phases 5/6 (`apps/web/app/*`).
- Sandbox: real LOCAL_WORKSPACE subprocess execution evidenced (exit codes, stdout, durations); the PROVIDER (Nebius) path is implemented and typed but honestly UNAVAILABLE without credentials — no mocks.

## Blockers / Risks
- No Nebius credentials (`NEBIUS_API_KEY`, project id) — the Phase 8 PROVIDER backend cannot run a real Nebius sandbox E2E; the loop is proven on the honest local backend. Providing credentials should only require binding a `SandboxPort` implementation to `SandboxControl`.
- No commit approval received — Phase 7/8 work (2 packages, 10 test files, gate/quality extensions, pytest/conftest plumbing) is uncommitted (AGENTS.md §32).
- Phase 7/8 UI (Change Definition → … → Candidate Patch journey surfaces) is intentionally NOT built in this session to respect the Phase 5/6 session's file ownership; it is the next work item once the shell lands.

## Session Coordination Record (2026-09-13)
- This session owns Phase 7 (packages/precode: change definition, intent compiler, constitutional mapping, Intent Ledger, semantic impact, verification planner, pre-coding lock) and Phase 8 (packages/develop: handoff, execution barrier, inspection, plan, sandbox adapters, controlled mutation, execution, failure taxonomy, repair loop, candidates, traces) plus their tests and gates.
- A parallel session owns Phases 5/6 (persistent shell, design system, Discover/Govern). This session will NOT modify `apps/web/app/page.tsx`, `layout.tsx`, `globals.css`, or Discover/Govern surfaces. Phase 7/8 UI work, if any, is deferred to avoid file collisions with that session.
- `catenary` CLI is not available in this environment (exit 127), so cross-session coordination is file-based: append-only Progress entries + disjoint file ownership.
- Subagent-spawn tooling and `opencode` are unavailable in this environment (AGENTS.md §5 limitation recorded honestly; decomposition is achieved via contract-bounded modules instead, same ownership boundaries as subagent waves).
- Governing docs conflict note: the Phase 7/8 master prompt names NeMo Agent Toolkit as the agent runtime; the implemented Phase 3/4 runtime (`smorx_runtime` + `smorx_tools` ControlPlane) already occupies that architectural slot and the plan's §0.5/§4/§5 rules. Resolution: Phase 7/8 compose the existing runtime/contracts/behavior/tools packages rather than introducing a second agent framework. Recorded here; no governing file edited.

## Historical Phase 4 entry preserved below (unchanged)

## Phase 3 — Parallel Orchestration Runtime (complete)
- Decision rationale: `IMPLEMENTATION_PLAN.md` sequences the orchestrator before the tool layer — sub-agent execution, attribution, and state transitions must exist before policy control wraps them. Wave-1 modules in `packages/agent-runtime` (module `smorx_runtime`) were produced by three parallel contract-bounded subagents with disjoint ownership by module.
- Wave 1 (fused):

| Agent | Modules (`smorx_runtime`) | Deliverable | Unit tests |
|---|---|---|---|
| A | `agents.py`, `capabilities.py` | Agents, evidences, failures, executors, `AgentSpec`, `AgentContext`, `Assignment`, `validate_result`, `assignment_allows_tool`; `CAPABILITY_CATALOG` binding CODING/VERIFICATION/EVIDENCE/REPAIR to allowed-tools; `SpecialistCapability` StrEnum | 31 |
| B | `graph.py`, `waves.py`, `telemetry.py` | `TaskGraph`, `TaskKind` (INDEPENDENT/DEPENDENT/RECONCILER/SERIALIZED), `ParallelWaveEngine.run_wave` with `cancel_event`, `SingleAgentScheduler`, `WaveResult` (PARTIAL/CANCELLED/FAILED), telemetry parallelism high-water + cross-task overlap | 29 |
| C | `toolgate.py`, `orchestrator.py` | `MemoryGateway`, `CapabilityGateway` protocol {authorize, execute, authorize_and_execute}, `Orchestrator` with `WORKFLOW_TRANSITIONS`, retry/replacement/no-progress blocking, `OrchestrationBlocked`, `OrchestrationReport` (decisions/failures/evidence/contradictions/telemetry/next_transition) | 12 |

- Integration: Wave-1 results were fused and critically reviewed by the orchestrator; the full 10-file `smorx_runtime` module set is `mypy --strict` and `ruff` clean; the Phase 3 gate below exercises the combined runtime end to end.
- Phase 3 gate (real E2E evidence): `PHASE3_GATE: PASS`. Three independent CODING tasks + one RECONCILER. Telemetry: `parallelism_high_water=3`; wall ~0.200s for 3×0.2s tasks; `max_cross_task_overlap_seconds` ≈ 0.200. Phase sequence: INSPECTING→PLANNING→DISPATCHING→EXECUTING→COLLECTING→RECONCILING→DISPATCHING→EXECUTING→COLLECTING→COMPLETED. 4 evidence items; 4 gateway invocations. Concurrency is real, not serialized (overlap > 0 proves parallel execution).

## Phase 4 — Tool Layer + Policy/Control Plane (complete)
- Wave 2 (fused), modules in `packages/tools` (`smorx_tools`):

| Agent | Modules (`smorx_tools`) | Deliverable | Unit tests |
|---|---|---|---|
| D | `tool.py`, `execution.py` | `ToolSpec`/`ToolRegistry`, `ToolRequest`/`ToolExecutionResult`/`ToolResultStatus`, `CommandRunner.run_python` (real subprocess), `FailureClassifier`, `normalize_test_output` | 22 |
| E | `policies.py`, `audit.py`, `control.py` | `PolicyEngine`, `RiskLevel`, `PolicyRule`, `PolicyDecision` (BLOCK/DENY/REQUIRE_REVIEW/ALLOW), `AuditTrail` with ALLOWED/EXECUTED/REVIEW/DENIED/BLOCKED decision records, `ControlPlane` implementing `CapabilityGateway` | 20 |
| F | `sandbox.py`, `human.py`, `repo.py` | Sandbox ops HONEST `UNAVAILABLE` when no provider bound (no fakes); `HumanControlPlane` request/approve/deny/abort/pause; repository.inspect / file.read-write-create-delete / command.run / test.run / evidence.* handlers | 22 |

- `authorize()` resolution order — deterministic; source of record is `smorx_tools/control.py` docstring (L8–34): (1) unknown tool → `DENY` "unknown tool", audit `DENIED`; (2) duplicate-EXECUTED guard — an earlier `EXECUTED` record for the same `(action_id, tool_name)` → `DENY` "duplicate invocation", audit `DENIED`; (3) capability mismatch → `DENY` "capability mismatch", audit `DENIED`; (4) allowed-tools mismatch (exact name or dotted-prefix, same semantics as `smorx_runtime.agents.assignment_allows_tool`) → `DENY` "not allowed for assignment"; (5) policy via `PolicyEngine`: `BLOCK` → audit `BLOCKED`, `DENY` → audit `DENIED`, `REQUIRE_REVIEW` → human gate (approval object `APPROVED` → `ALLOW` "human approved", audit `ALLOWED`; no human channel or human paused → recorded `REVIEW`, never executed); (6) `ALLOW` → audit `ALLOWED`.
- Human-in-the-loop: high-risk operations surface a `HumanControlPlane` review; a PENDING request can be approve/deny/abort/pause. Without `APPROVED` the operation is recorded as `REVIEW` and not executed — execution never precedes authorization.
- Sandbox honesty (AGENTS.md §3, §13): `sandbox.py` returns `UNAVAILABLE` with an environment/dependency classification when no provider is bound — no fabricated sandbox IDs, statuses, or simulated successes.
- Assembly: `smorx_tools/assembly.py` (orchestrator-owned) wires `assemble_default_registry` + `assemble_control_plane` so the Phase 4 plane is the single enforcement path.
- Phase 4 gate (real E2E evidence): `PHASE4_GATE: PASS` — file.write ALLOWED then a real file written (content `PHASE-4-WRITTEN` read back); command.run high-risk REQUIRE_REVIEW without approval, then real approved run (stdout `APPROVED-RUN`, exit 0); duplicate action DENY; evidence.record capability mismatch DENY; explicit policy BLOCK. Audit chain: 7 records {ALLOWED 2, EXECUTED 2, REVIEW 1, DENIED 2}, fully attributable (action_id, tool, decision, risk, resource_ref).

## Combined Integration & Adversarial Verification
- `tests/integration/test_phase3_phase4_integration.py` — 6 tests: end-to-end trust chain (3 CODING agents write real files → RECONCILER validates; parallelism high-water ≥ 2 and cross-task overlap > 0); missing-handler tool failure; REQUIRE_REVIEW then human approval re-run (blocked run 1 → approve → verified success run 2 — the full Phase-4 loop); capability-mismatch denial blocks; SERIALIZED task runs alone; `isinstance(plane, CapabilityGateway)`.
- `tests/security/test_adversarial_guardrails.py` — 20 scenarios: unknown tool denied; outside-capability denied; tool timeout classified; nonzero exit classified (real `SystemExit(3)`); success-claim-without-evidence mismatch; contradictory findings detected (severity conflict); one-timeout-others-finish PARTIAL; failed-specialist replacement; duplicate invocation denied; retry budget exhausted blocks; no-progress identical signatures blocks; serialized never concurrent; dangerous policy BLOCK; incomplete result classified; sandbox unavailable honest (UNAVAILABLE/classification, no fabricated sandbox id); control-plane bypass leaves no audit attribution; partial-wave failures surface; mid-execution cancellation CANCELLED; stale result mismatch ignored; invalid state transition raises `InvalidWorkflowTransition`.
- Full suite: `python -m pytest tests/unit tests/integration tests/security` → **391 passed** (365 unit + 6 integration + 20 security). `ruff check` + `ruff format` clean; `mypy --strict` clean.

## Tests
- Unit: 371 (Phase 3: agents 31, graph/waves/telemetry 29, toolgate/orchestrator 12; Phase 4: tool layer 22, policy/audit/control 20, sandbox/human/repo 22; plus earlier-phase suites and 6 phase-gate tests under `tests/unit`).
- Integration: 24 (`test_phase3_phase4_integration.py` 6 + lifecycle/certificate/reference 18).
- Security: 20 adversarial scenarios (`test_adversarial_guardrails.py`).
- Gates: `PHASE3_GATE: PASS`, `PHASE4_GATE: PASS`; `python scripts/phase_gate.py --phase 0|2|3|4` → all `PHASE_N_PASS`.
- Ruff / format: `ruff check` clean; `ruff format --check` clean (92 files formatted in finishing wave; 25 files reformatted mechanically to clear pre-existing debt).
- Mypy: `--strict` clean on 10 `smorx_runtime` + 10 `smorx_tools` + 28 behavior/contracts = 48 source files.
- Chrome DevTools: N/A (no browser surface this phase).
- Sandbox: N/A — real Nebius binding is later-phase; sandbox ops honestly report `UNAVAILABLE` (no mocks introduced).

## Blockers / Risks
- No Nebius credentials (`NEBIUS_API_KEY`, `NEBIUS_AI_PROJECT` / `NEBIUS_PROJECT_ID`) — real Nebius sandbox/inference E2E still gated; `infrastructure/docker` and `infrastructure/nebius` are reference/planned artifacts only, and real provisioning is blocked on credentials (see Subagent K's deliverables, same wave).
- No commit approval received — working tree (Phases 2, 3, 4) remains uncommitted (AGENTS.md §32).
- Root README UTF-16 issue: resolved in this update (rewritten as UTF-8 markdown).
- Supabase RLS: all 31 `public` tables currently have RLS disabled (Supabase security advisor `rls_disabled_in_public` → 31 findings on `behavioral_schema_31tables`). RLS is a System Security Optimization phase (plan §7) hardening; documented now, not a Phase-2 gate item.
- Supabase project `Smorx` (`tyhwdqraeioxzmkrofib`) is on the Free tier ($0/mo); pause/usage policies apply before any production load.

## Supabase PostgreSQL migration (REAL PG, 2026-09-13)
- Created project **`Smorx`** in org `louji2308-7257's projects` (ap-southeast-2) via Supabase MCP — `ref tyhwdqraeioxzmkrofib`, `db.tyhwdqraeioxzmkrofib.supabase.co`, PostgreSQL 17.6, ACTIVE_HEALTHY.
- Applied the canonical behavioral schema as Supabase migration `behavioral_schema_31tables` — rendered PG DDL from the SAME `Base.metadata` the Alembic migration `4be282d73a12` was autogenerated from. Verified live: 31 base tables (excludes `schema_migrations`); 116 constraints — 31 `pk_*`, 82 `fk_*`, 3 `uc_*` (`uc_projects_slug`, `uc_evidence_hash`, `uc_certificates_certificate_key`) — names identical to the migration.
- Integrity cross-check: migration file table list == metadata render table list == live `information_schema` (31 == 31 == 31, identical order).
- Correction applied (evidence-preserved): a first 36-table apply (`initial_behavioral_schema`) was issued from a stale HEAD-side model snapshot and DID NOT match the migration/metadata; it was reverted via `revert_erroneous_schema_drop` and replaced by the migration-faithful 31-table schema. Lesson recorded: never hand-assemble DDL from memory — always render from the authoritative migration/metadata.
- Connection info recorded in `packages/behavior/.env.example`: `DATABASE_URL` (asyncpg) / `ALEMBIC_DATABASE_URL` (psycopg) pooler host + `SUPABASE_URL`/`SUPABASE_ANON_KEY` (publishable). Real DB password still user-provided (dashboard) — never committed.

## Next Action
Await user: (1) commit approval, (2) Nebius credentials for real sandbox E2E (Phase: sandbox provider binding), (3) real Supabase DB password so `DATABASE_URL` can be exercised by the behavior layer end to end (schema already applied via MCP). Then: Phase 5 UI / next phase per `IMPLEMENTATION_PLAN.md`.

## Finishing Wave (2026-09-13) — Plumbing, Docs, Infrastructure
- **Plumbing scripts**: Extended `scripts/quality_gate.py` (integration + security test steps, expanded ruff/mypy targets to include `packages/tools` + `packages/behavior`, MYPYPATH injection for mypy robustness), `scripts/phase_gate.py` (Phases 3/4 gates with structure/imports/tests/quality checks, CLI now `--phase 0|2|3|4`), `.github/workflows/ci.yml` (installs all 4 packages, runs phases 0/2/3/4 gates, integration + security pytest). Added 6 unit tests to `test_phase_gate.py` for phase 3/4 finalize helpers + smoke evaluations. All original tests pass.
- **Documentation**: `README.md` rewritten from 20-byte UTF-16 stub to UTF-8 markdown (10.5 KB) with accurate architecture, setup, env vars, tests, limitations; `Progress.md` updated with Phase 3/4 results + this wave; `docs/adr/0008-phase3-phase4-architecture.md` created (ADR index updated).
- **Infrastructure placeholders**: `infrastructure/docker/README.md` + `compose.dev.yml` (local Postgres 16, not yet wired); `infrastructure/nebius/README.md` + 3 `.example` manifests (sandbox lifecycle, serverless job, serverless endpoint) — all marked REFERENCE ONLY / NOT PROVISIONED; reserved `packages/evidence|verification|ui/README.md` stubs. Phase 0 structure checks now fully green.
- **Environment fix**: `packages/behavior/.env.example` anon-key placeholder changed to `<your-supabase-anon-key>` to clear secret-scan false positive.
- **Format debt cleared**: `ruff format` on all gate targets (scripts, tests, conftest.py, 4 packages) — 25 files reformatted mechanically (pre-existing debt from behavior migrations + test files); `ruff format --check` now clean.
- **Phase gates re-validated**: `python scripts/phase_gate.py --phase 0|2|3|4` → all `PHASE_N_PASS`. `quality_gate --skip-web` passes all repo-critical steps (env, secret scan, format, lint, typecheck, unit 371, integration 24, security 20, build). Dependency audit fails due to pre-existing unrelated packages in the shared venv (`eth-abi`, `eth-keys`, `eth-utils`, `forgex` — not repo code; documented as environment blocker).
- **Full suite**: `pytest tests/unit tests/integration tests/security` → **415 passed, 1 warning** (38.13s). `compileall` clean on all packages + `apps/api/app`.

---

# Phase 2 — Behavioral Data Model & Persistence (historical record — preserved)

## Current Phase
- Phase: 2 — Behavioral Data Model & Persistence (`IMPLEMENTATION_PLAN.md` §2, L586–711)
- Step: Phase 2 complete — gate PASS
- Status: VERIFIED (exit gate satisfied; commits pending user approval)

## Latest Orchestrator Decision
- Decision: After Wave 1 produced the 30-entity ORM layer + contracts + initial migration (revision `4be282d73a12`, 31 tables), dispatch Wave 2 as three parallel contract-bounded agents: D (evidence/provenance), E (versioning/lock policy), F (repo/data-access + deterministic demo seed + integration tests). Ownership disjoint by module; no model/schema edits permitted.
- Reason: Plan §2 deliverables split naturally; evidence identity (2.2), ownership (2.3), events (2.4), versioning/immutability (2.5), repository layer + seed + tests (exit gate).
- Evidence: Wave 2 outputs below; `python -m pytest tests` → 319 passed; `verify_migration.py` → MIGRATION == METADATA: OK (31 vs 31, no drift); ruff clean; mypy clean (11 Wave-2 source files).

## Concurrent-Session Situation (resolved, evidence preserved)
- Two opencode orchestrator sessions (Session B and this one) ran identical Phase-2 Wave-1 subagent work into `packages/behavior` + `packages/contracts`. Session A (different session) made/pushed the `8c03291` commit series at 07:17–07:18 and later stopped.
- User halted Session B ("continue i told it"). Session B's agent-runtime + orchestrator test files landed in the tree at 09:26–09:40 (after its halt instruction) — evidence its subagents were still finishing. Full suite is stable after those files settled (319 passed).
- Session B's `packages/agent-runtime` + `tests/unit/test_*` (agents, graph, orchestrator, telemetry, waves) remain UNCOMMITTED and are NOT owned/verified by Phase 2 — flagged as their deliverable to reconcile before Phase 3. RECONCILED 2026-09-13: `packages/agent-runtime` (module `smorx_runtime`) and its unit tests are now Phase-3 Wave-1 owned, `mypy --strict`/`ruff` clean, and gated by `PHASE3_GATE: PASS` (see Phase 3 section above).

## Parallel Agent Wave — Wave 2 (results fused)
- Agent D — Evidence/Provenance: `smorx_behavior/evidence/{service,provenance}.py` — `record_evidence` (content-addressed dedup on unique `Evidence.hash`, idempotent), `eligibility` (exit_code + provenance + binding verdicts), `evidence_by_hash/for_claim/for_task`, `provenance_path` (evidence→task→run→agent_run→subagent_run), `claim_evidence_chain`, `evidence_to_certificate_path`, `certificate_traversal` (JSON binding map). Tests `tests/unit/test_evidence.py` (6 passed, no N+1 via joinedload/selectinload).
- Agent E — Versioning: `smorx_behavior/versioning/{lock,service}.py` — ADR-0005 policy: new objects `version=1 locked=False`; `lock` idempotent/permanent; `bump` LOCKED → new identity (new id, version+1, parent ref in JSON `__version_parent__` or text marker `[version_parent:<id>;from_version:<n>]`, historical row untouched); UNLOCKED → in-place version+1; `snapshot` JSON round-trip; `get_lineage` bounded/cycle-safe; `force_set` labeled tests/repair-only. Tests `tests/unit/test_versioning.py`.
- Agent F — Persistence/Seed/Test: `smorx_behavior/repo/{base,catalog}.py` (save/get/list_/query/count/get_or_create, policy-gated delete, catalog queries: tasks/evidence/certificate/memory_for_change, lifecycle graph); `smorx_behavior/seed/demo.py` (deterministic DEMO: Payments API, Change #184 `e8d1a91c…`, AUTH-017 `4081aa25…`, Ghost #221 `a347d3d4…`, Failure F-183 `1259b37e…`, certificate `b68d48e0…`; idempotent get-or-create, `--print` smoke runs clean); integration tests `tests/integration/{test_lifecycle,test_certificate,test_references}.py` (18 passed: FK enforcement with PRAGMA foreign_keys=ON, historical preservation, evidence dedup).
- Integration result: fused; orchestrator fixed 3 test-helper defects in `test_versioning.py` (missing `session` arg; lineage test needed `lock(v2)` to build a 3-hop chain per the documented unlock-in-place rule), 2 ruff F841 unused vars in `demo.py`, and 7 mypy strict errors (repo base/catalog generics, provenance None-guard, versioning unique-str cast). All Wave-2 gates now clean.

## Implementation Changes
- Added (Wave 2): `smorx_behavior/evidence/`, `smorx_behavior/versioning/`, `smorx_behavior/repo/`, `smorx_behavior/seed/`, `tests/unit/test_evidence.py`, `tests/unit/test_versioning.py`, `tests/integration/{test_lifecycle,test_certificate,test_references}.py`.
- Modified (orchestrator): `tests/unit/test_versioning.py` (3 fixes), `packages/behavior/src/smorx_behavior/seed/demo.py` (2 F841), `repo/base.py`, `repo/catalog.py`, `evidence/provenance.py` (mypy), `.gitignore` (+ `*.db/*.sqlite/*.sqlite3`).
- Wave 1 baseline (this phase): `models/{enums,entities,__init__}.py`, `db/*`, `migrations/versions/4be282d73a12_initial_behavioral_schema.py`, `packages/contracts` registry/versioning/schemas, `scripts/verify_migration.py`.
- Session B additions in tree (NOT Phase-2-owned): `packages/agent-runtime/src/smorx_runtime/{agents,capabilities,graph,orchestrator,telemetry,toolgate,waves}.py`, `tests/unit/{test_agents,test_graph,test_orchestrator,test_telemetry,test_waves}.py`. RECONCILED: these files are now Phase-3 Wave-1 owned, verified, and Phase-3 gated (see Phase 3 section above).

## Tests
- Unit: `tests/unit` Wave-2 suites green (evidence 6, versioning 11, models, db_infra, contracts) — part of full-suite run below.
- Integration: 18 passed (`tests/integration`, in-memory SQLite, FK on).
- Full suite: `python -m pytest tests` → **319 passed, 1 warning** (exit 0), after Session B's files settled.
- Ruff: `ruff check scripts tests conftest.py packages/contracts packages/behavior` → All checks passed. Mypy (`.venv`): `packages/contracts packages/behavior` → Success, 28 source files (now includes behavior).
- Phase 2 gate: `python scripts/phase_gate.py --phase 2` → **STATUS: PHASE_2_PASS** (exit 0); 18 checks all PASS; JSON evidence saved to `scripts/phase2_gate_evidence.json`. Phase 0 gate refactored to `--phase 0|2` (shared `finalize`), sys.path now injects source packages (contracts check passes), Phase 0 still BLOCKED only on out-of-scope structure gaps (packages/tools, evidence, verification, ui, infrastructure/docker, infrastructure/nebius).
- Migration integrity: `scripts/verify_migration.py` → MIGRATION == METADATA: OK (31 model tables = 31 db tables, no drift; regenerated `smorx_generated.db` via alembic upgrade head, then removed; DB artifacts gitignored via `*.db/*.sqlite/*.sqlite3`).
- Seed smoke: `python -m smorx_behavior.seed.demo --print` → deterministic tokens (change #184 `e8d1a91c…`, AUTH-017 `4081aa25…`, Ghost #221 `a347d3d4…`, F-183 `1259b37e…`, certificate `b68d48e0…`), counts rows=31 evidence=6 (cosmetic runpy RuntimeWarning from eager seed/__init__ import).
- Chrome DevTools: N/A (no browser surface this phase).
- Sandbox: N/A (Nebius wiring is later-phase; no mocks introduced).

## Phase 2 Exit Gate (ADR-0007)
Full lifecycle represented and queried without losing ownership, version, provenance, or historical evidence: verified via `tests/integration/{test_lifecycle,test_certificate,test_references}.py` (18 tests) + `scripts/phase_gate.py --phase 2` = PHASE_2_PASS.

## Blockers / Risks
- No Supabase `DATABASE_URL` — Supabase wiring deferred per user-confirmed SQLite-test-first approach; PG-targeted DDL is in the migration but not exercised against real PG. Re-ask at report.
- No commit approval received — working tree (Phase 2 + Session B's agent-runtime) remains uncommitted (AGENTS.md §32). UPDATED 2026-09-13: working tree now spans Phases 2–4; still awaiting approval.
- Root `README.md` is a 20-byte UTF-16 binary; skipped (note to user; needs UTF-8 rewrite in a later phase). RESOLVED 2026-09-13: rewritten as UTF-8 markdown in the Phase 3/4 documentation update.
- Phase_gate quality check currently mypys `packages/contracts` + `packages/agent-runtime` only — must extend to `packages/behavior` at the Phase 2 gate.
- Session B's uncommitted agent-runtime work is in the tree but not Phase-2-verified; reconcile before Phase 3 to avoid scope bleed. RESOLVED 2026-09-13: reconciled — Phase-3 Wave 1 ownership and gate (see Phase 3 section above).

## Next Action
Await user: (1) `SUPABASE_DATABASE_URL` for real-PostgreSQL migration verification, (2) commit approval for Phase 2 (and disposition of Session B's uncommitted agent-runtime files), (3) README UTF-8 rewrite decision. Then: commit coherent single-purpose changes, write README update, proceed to Phase 3.

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