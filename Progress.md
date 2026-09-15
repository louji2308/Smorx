# Progress — Software Evolution Intelligence System

## Current Phase
- Phase: 11 — Certification (re-verify, certificate, integrity, archaeology, memory, merge gate) AND 12 — Full System Integration + Demo Reliability (`IMPLEMENTATION_PLAN.md` §11, §12) — COMPLETE, plus `apps/web` white-theme UI redesign wave (user-requested) — IN PROGRESS
- Status: Phase 11/12 COMPLETE (gates 11/12 PASS, full suite 653 passed). UI redesign advancing; Tailwind content-glob root cause fixed. Baseline commit+push `5e90a86` done (2026-09-15); charcoal "Ink" chrome wave COMPLETE+committed (`de01245`, `b6f3360`, `622d696`); font system swap IN PROGRESS.

## Charcoal "Ink" interaction-chrome wave — plan + execution (2026-09-15)
- User directive: turn buttons and active/moving tabs **charcoal black**, keep all per-tab **icon colours**; professional/startup-grade polish; inspect every button/pill/spacing/icon; do NOT use common dark colors (no `#000`, slate-900, zinc-900).
- Research grounding (web): Linear/Vercel/Stripe dashboard discipline — single interaction accent, hairline borders over shadows, crafted hover/focus/pressed microstates, charcoal CTA like Vercel `#171717` (but distinct), 4/8px grid, semantic colors reserved for meaning.
- **Chosen signature charcoal — cool blue-graphite "ink"** (`#1F2430`) married to the existing blue-leaning neutral ramp; NOT a generic dark. Tokens: `--color-ink #1F2430`, hover `#2A3038`, active/pressed `#141922`, tint `#EEF0F3`, soft `#D8DCE2`, muted `#5B6478`, focus `rgb(31 36 48 / 0.16)`.
- **Architecture of change — repoint the accent family once, cascade everywhere:** `--color-accent-primary/hover/secondary/tint/soft`, `--shadow-focus`, `::selection`, Tailwind `accent.*`, `brandColor`. This automatically converts `.btn--primary`, `.input:focus`, `.rf-node--selected`, selected card borders (Claim/EvidenceItem/ExecutionEvent/TestResult/ProvenanceLink/GraphNode), Govern/Constitution chips+checkbox, AppShell loading/empty chrome, Discover segmented active.
- **Moving tabs:** `.nav-item--active` + `Navigation.tsx` inline style → charcoal-tinted bg + ink text; **icon keeps its stage color**. Logo tile charcoal. TopContextBar pill icons stay colored.
- **Component hex literals → ink/muted:** `ArchaeologyLaunch` (Behaviors chip, progress bar), `AnalyzeTab` pills L210/242 + "Running…" L386, `DefineTab` L319, `DevelopTab` selected chip L272 + "Running…" L487, `DecideTab` stepper L45 + Authorized chip L362. Standing rule: "Running…" → muted; progress/primary fills → ink; accent chips → ink-tinted.
- **Semantic/identity colors kept untouched:** `stageColors` (per-tab icons), `DiscoverTab stepColors`, trust badges, behavioral-object graph colors, per-tab DEV tints, green completed checks, danger red.
- **Spacing/microstate polish:** standardize icon↔label gaps (buttons `gap-2`, pills `gap-1.5`, nav `gap-3`), pill padding `px-3 py-1`, uniform `120ms` transitions, add pressed state on primary — only where inconsistent.
- Execution: three parallel subagents (non-overlapping ownership) — A: tokens+cascade+shell chrome; B: Discover/Govern/Define/Analyze; C: Develop/Verify/Decide/Certify + `ui/*`. Each runs `npx tsc --noEmit`. Then browser verification (DevTools MCP) + screenshots + commit.

### Charcoal wave — integration + verification (2026-09-15)
- Three parallel subagents completed cleanly (all `npx tsc --noEmit` exit 0):
  - **Agent A** (`globals.css`, `tailwind.config.ts`, `design-tokens.ts`, `shell/Navigation.tsx`): accent tokens repointed to ink (`#1F2430`/`#2A3038`/`#5B6478`/`#EEF0F3`/`#D8DCE2`) + added `--color-ink*` ramp; `--shadow-focus` + `::selection` charcoal; `.btn--primary` ink fill + hover + new `:active` pressed state (`#141922`); `.nav-item--active` charcoal tint `rgb(31 36 48 / 0.07)`; **active nav keeps stage icon color** (`colors.icon`); logo tile charcoal via `brandColor`. `TopContextBar`/`AppShell` cascade only, no edits.
  - **Agent B** (`ArchaeologyLaunch`, `AnalyzeTab`): Behaviors chip → ink-tinted; Source step icon → ink; Running… → muted; progress %/bar → ink; Analyze claim pills L210/242 → ink-tinted; Running… L386 → muted. `DefineTab` L319 Running… → muted. `GovernTab`/`ConstitutionWorkspace`/`DiscoverTab`/`BehavioralKnowledgeGraph`: cascade/wayfinding, no edits.
  - **Agent C** (`DevelopTab`, `DecideTab`): Develop selected run chip → ink, Running… → muted; Decide authorize step + Authorized chip → ink. **Technical fix:** `phase.color + '10'/'55'/'15'` hex-alpha concat would break with a `var()` phase → converted to `color-mix(in srgb, …)` (visually identical). `VerifyTab`/`CertifyTab`/`ui/*`: cascade only, no edits.
- **Orchestrator decisions (kept indigo deliberately — SEMANTIC graph object-type colors, not interaction chrome):** `design-tokens.ts` `behavioralObjectColors.BEHAVIOR`, `BehavioralKnowledgeGraph.tsx` L60/L379 (Behavior node-type + legend), `ArchaeologyEvidenceWorkspace.tsx` L24 (Behaviors evidence category). These parallel green=INVARIANT/red=INCIDENT and are meaning-coded, per the "keep semantic colors" rule.
- **Dev-server restart required** (config change) — stale `bg-accent-primary` still emitted `rgb(74 108 247)` until Tailwind regenerated. Restarted `next dev`, verified compiled rule + live styles.
- **Browser verification (DevTools MCP):** active nav item bg `rgba(31,36,48,0.07)` with icon `rgb(124,92,224)` (Govern violet preserved); primary buttons `rgb(31,36,48)` white text; logo tile `#1F2430`; segmented active `rgb(31,36,48)` white; Analyze ink pills `rgb(31,36,48)` on `rgb(238,240,243)` with `rgb(216,220,226)` border; Develop sandbox run executed live → 6/6 PASSED (semantic green), PATCH chip `rgb(31,36,48)`; Verify suite executed live → fusion 206/1/0 (green/red/secondary); Decide "Authorizing change" phase `rgb(31,36,48)` + `color-mix` states correct; Certify seal button `rgb(31,36,48)`; **console 0 messages**. Evidence: `docs/smorx-charcoal-ink.png`, `docs/smorx-charcoal-verify.png`, `docs/smorx-charcoal-certify.png`.

## Font system swap — DM Sans / Ubuntu / Gruppo / JetBrains Mono (2026-09-15)
- User directive (iterated): replace Inter + Space Grotesk; then explicitly chose **Corben** for small/body, but reported the result **too heavy**; final instruction → **DM Sans** for small/body. Medium text → **Ubuntu**; very-large text → **Gruppo** (prewire only — no landing/hero page exists yet); mono not in swap set → **JetBrains Mono kept** (code/technical).
- Mapping applied: `--font-sans` → DM Sans (weights 400/500/700; body/small/UI/pills/nav); `--font-display` → Ubuntu (page h1 titles, section headings); new `--font-brand` → Gruppo (very-large role; currently used ONLY for the "Smorx" wordmark, weight 400, tracking 0.12em, uppercase); `--font-mono` → JetBrains Mono (unchanged). Added `.font-brand` utility + Tailwind `brand` family.
- **Weight reduction (#2 complaint):** `font-synthesis: none` on `body` (stops browser-synthesized bold on the light 400-first stack); typography weight tokens lowered 700/600 → 500 (`--text-display/title/heading/subheading--font-weight`); `.btn` `font-medium` → `font-normal`; `.nav-item` `font-medium` → `font-normal`; `.nav-item--active` `font-semibold` → `font-medium`; `.pill` `font-semibold` → `font-medium`.
- Files: `app/layout.tsx` (next/font imports + html classes), `app/globals.css` (font tokens, weights, `.font-display` 0.01em, `.font-brand`, body `letter-spacing: 0.015em`, `font-synthesis: none`), `tailwind.config.ts` (fontFamily sans/display/brand/mono), `shell/Navigation.tsx` (Smorx h1 → `font-brand`).
- Slight letter-spacing per user follow-up ("slightly leave space between fonts"): body `0.015em`, `.font-display` `0.01em` (was `-0.01em`).
- Browser verification (DevTools MCP): body computed `"DM Sans"`, nav `"DM Sans" @ 500`, buttons `"DM Sans" @ 400`; wordmark `Gruppo`; page title `Ubuntu @ 700`; mono `JetBrains Mono`; **console 0 messages**. Typecheck exit 0.

## "Box inside a box" visual cleanup — nested gray rows flattened (2026-09-15)
- User directive: stop rendering unnecessary nested boxes — inner rows (gray `--color-surface-subtle` + border) nested inside white `surface-card`s looked like box-in-box across tabs. Desired behavior: inner content shares the card's white background, exactly like the Analyze tab (content flat on the card).
- Applied by three parallel subagents (non-overlapping file ownership) with a shared contract — flatten ONLY the default/idle state of nested gray rows; keep ALL running/active/done/hover state branches, colored icon chips, accent bars, dots, pills, real file/code chips, top-level grid cards:
  - Agent A — `discover/ArchaeologyLaunch.tsx` (Project Context ×4, Readiness ×6, Investigation Scope idle branch, What-Is-Investigated ×6), `BehavioralKnowledgeGraph.tsx` (RelationshipPanel row), `define/DefineTab.tsx` (chip row, acceptance rows, phases idle branch). `ArchaeologyEvidenceWorkspace.tsx` + `DiscoverTab.tsx`: already flat / segmented control correctly, no change.
  - Agent B — `analyze/AnalyzeTab.tsx` (phase idle branch → `border-transparent` to match repo's existing flat-row convention), `verify/VerifyTab.tsx` (Total Skipped box), `decide/DecideTab.tsx` (Affected Claim + Change Scope rows in Repair Package).
  - Agent C — `develop/DevelopTab.tsx` (3 execution-event rows, outcome icon box → tinted `DEV.tint` chip, sandbox trace rows; KEPT per-file code chips), `certify/CertifyTab.tsx` (`BoundField` helper used by all 6 bound-artifact/evidence boxes).
- Verification: `npx tsc --noEmit` exit 0 in all three agents. Browser (DevTools MCP): Discover Project Context 4 rows compute `background-color: rgba(0,0,0,0)`, `border-width 0`, `box-shadow none` inside the white `.surface-card` (`rgb(255,255,255)`); Certify bound-artifact boxes transparent; **console 0 messages**. Evidence: `docs/smorx-discover-flat.png`.
- Uncommitted with the rest of `apps/web` (pending user approval, AGENTS.md §32).

## Flat professional UI — gradients removed (2026-09-14)
- User directive: "never use the purple and blue gradient anywhere." Removed **every** blue/purple/indigo/neutral gradient and decorative blur elements from `apps/web` (verified via source grep + DevTools: **0 elements with `background-image: gradient`** on the rendered page):
  - `globals.css` — `.btn--primary` linear-gradient → solid `#4f46e5` (hover `#4338ca`, softer shadow).
  - `Navigation.tsx` — brand logo `from-indigo-500 to-purple-600` → solid `bg-indigo-600`.
  - `DiscoverTab.tsx` — segmented active gradient → solid `bg-indigo-600 text-white shadow-sm`.
  - `TopContextBar.tsx` — constitution badge gradient → flat `bg-violet-50`.
  - `PlaceholderTab.tsx` — hero redesigned flat: white `surface-card`, thin colored leader line, solid tint icon tile, muted status bar; **removed blur-2xl decorative circles and gradient backgrounds** (the 'common/AI look').
  - `ArchaeologyLaunch.tsx` — progress bar gradient → solid `bg-indigo-600`.
  - `AppShell.tsx` — EmptyState icon gradient → flat `bg-indigo-50`.
- Professionalization: color now used only as restrained solid tints (single-tab identity + indigo primary action); flat surfaces/borders carry hierarchy; typography stays on the 3-tier system.
- Browser verification (DevTools MCP): hero card `background-image: none` (white, `borderRadius 16px`, blue-50 leader + icon tile, smoke status bar); brand icon & segmented active = solid `#4f46e5`, white text, no gradient; **console 0 messages**. Evidence: `docs/smorx-professional-flat-ui.png`.
- Uncommitted (pending user approval) with the rest of the `apps/web` redesign.

## Typography upgrade wave — professional 3-tier type system (2026-09-14)
- User request: "better fonts like professionals use, different styles properly." Installed a three-tier professional type system in `apps/web`:
  - **Inter** (sans) — UI/body/navigation (already loaded via `next/font/google`, kept).
  - **Space Grotesk** (display) — page titles (`JourneyPage` h1), brand wordmark ("Smorx"), placeholder hero headings; `letter-spacing: -0.01em`.
  - **JetBrains Mono** (mono) — all code/pre/`font-mono` plus KPI stat numerals (36px, semibold, `tabular-nums`) in `ConstitutionWorkspace` (32/7/3/0) and `ArchaeologyLaunch` stat cards.
- Files: `app/layout.tsx` (load `Space_Grotesk` + `JetBrains_Mono`, variables `--font-display`/`--font-mono` on `<html>`), `tailwind.config.ts` (`fontFamily.display`/`mono` added; display falls back through sans), `app/globals.css` (font tokens + `text-rendering: optimizeLegibility`, `.font-mono`/`code`/`pre` get `tabular-nums`, `.font-display` utility), `Navigation.tsx`, `AppShell.tsx`, `PlaceholderTab.tsx` (`font-display`), `GovernTab` stats, `ArchaeologyLaunch` stats.
- Browser verification (DevTools MCP): body computed `Inter`; `h1` page titles + brand computed `Space Grotesk` (font-status `loaded`); code/stat numerals computed `JetBrains Mono` + `font-variant-numeric: tabular-nums`; **console 0 messages**; fonts fetched via Google Fonts at dev time (network OK). Evidence: `docs/smorx-fonts-devtools-verify.png`.
- No package.json changes (all via `next/font/google`, self-hosted at build). Uncommitted (pending user approval), along with the rest of the UI redesign.

## White-theme UI redesign wave — `apps/web` (2026-09-14, session continuation)
- Root cause of the reported "tabs/text/icons/buttons not properly arranged" layout found and fixed: `apps/web/tailwind.config.ts` content globs did not include `./src/**/*`, so Tailwind never generated utility classes used inside `src/` (e.g. `w-[260px]`, `.w-full`, `flex-shrink-0`, `h-[60px]`). Sidebar rendered 144px (spec 260px) and header 427px (spec 60px) as a result. Fixed content globs; **dev-server restart required**; verified compiled CSS now contains `w-[260px]`/`w-full`/`fs0`/`h-[60px]` and live layout metrics: nav **260px**, header **60px**, content **660px**, hero card 1228×379, feature grid 3×399px, Discover 2-col grid 808/394px, segmented buttons 3×402px.
- Applied the v0 design reference (chat `lT2u5gsVJaI`, plan approved; preview still generating at time of writing) directly in-repo: white theme with soft per-tab colors (Discover indigo, Govern violet, Define blue, Analyze sky, Develop teal, Verify amber, Decide orange, Certify pink), thin Lucide icons `strokeWidth 1.75`, pill shapes, smoke-grey accents, centered hero + feature cards.
- Files rewritten: `app/globals.css` (light tokens, pastel trust badges, `.surface-card`, `.btn` pill, `.nav-item`, `.pill`, `.drawer`, light React Flow), `app/layout.tsx` (`bg-[#f3f4f6] text-[#111827]`), `app/page.tsx` (metadata), `tailwind.config.ts` (light palette + content globs), `src/components/shell/Navigation.tsx` (260px sidebar, per-tab color mapping is tabColor; fixed `{Icon}`→`{tabIcons[tab.id]}` dead-code bug), `TopContextBar.tsx`, `AppShell.tsx` (JourneyPage/Section/EmptyState/LoadingState/ErrorState), `PlaceholderTab.tsx` (hero + feature cards; removed duplicated description), `DiscoverTab.tsx`, `ArchaeologyLaunch.tsx` (colored stat cards, readiness, scope steps).
- Contrast/theme fixes this wave: `--color-surface` changed `#ffffff`→`#f7f8fa` (nested surfaces inside white cards were white-on-white across 60+ components); behavioral object colors bumped `-400`→`-600` in `design-tokens.ts`, `ArchaeologyEvidenceWorkspace.tsx`, `BehavioralKnowledgeGraph.tsx`; TopContextBar pill/sub-label accents `-400`→`-500`.
- Browser verification (DevTools MCP, page 1): console **0 messages** (no runtime errors); nested surface computes `rgb(247,248,250)`; Discovery launch view + Archaeology Evidence Workspace (7 categories, search, findings list) + Knowledge Graph (React Flow 1221×518, 13 nodes, 14 edges) all render; Govern workspace full claims table renders (32 Protected / 7 Observed / 3 Hypotheses / 0 Conflicts); archaeology re-run completed end-to-end in-browser (trust→OBSERVED, currentStage Govern, completedStages [Discover, Govern], activeTab Define, constitution 32/42 intact) — persistence intact.
- Evidence: `docs/smorx-white-discover-launch.png`, `docs/smorx-white-define-hero.png`, `docs/smorx-define-tab-devtools.png`, `docs/smorx-white-theme-v2.png`.
- Uncommitted: `apps/web/*` (outputs of the UI redesign). Commit only after user approval (AGENTS.md §32).

## Phase 11/12 — First session wave: chaining + orchestrate + replay/reliability + failure inject (2026-09-14)
- Locked design: reconcile the scaffolded workflow tests with the LANDED modules rather than re-adding fakes. Real scenario-based `run_e2e_workflow` retained; ADDED `workflow_id`, `DEFAULT_PHASES` (12), `PHASE_EVENT_KINDS`, `run_phases`, deterministic-evidence caching, hash-chained run events, replay hash-chain validation, `idempotency_guard`, `cleanup_stale_sandboxes`, run-based resume+reset, `TEST_FAILURE` + `CONFLICTING_EVIDENCE` injection as REAL functionality; REWROTE tests to drive the real system (no `install_certification_fakes`).
- `packages/workflow/src/smorx_workflow/chaining.py` (orchestrator-created): `canonical_payload`, `event_digest` (sha256 over entity/seq/payload, excludes occurred_at), `next_sequence` (run_id XOR task_id scope). Shared by orchestrate/replay/reliability/failure_inject.
- `orchestrate.py` rewritten (subagent A returned empty; rewritten directly in-session): `DemoScenario(+run_token="e2e/run/AUTH-017")`, `OrchestrationResult(+state/completed_phases/replayable/evidence_hashes)`, `build_demo_scenario`, `cache_deterministic_evidence`/`read_cached_deterministic_evidence` (CACHE ConsequentialEvents, workflow_id(f"cache/{key}")), `run_e2e_workflow` (default evidence_reader returns `scenario.verification_evidence`, blocks honestly at reverify on empty reader / BLOCKED at decide when `require_certification=False`), `run_phases`, `_record_event` (run-bound, sequence+digest hash), terminal Run status (COMPLETED/BLOCKED + finished_at).
- `replay.py` + `reliability.py` (subagent B): `ordered_events(session, run)` run-scoped ascending; `replay_from_evidence_graph` with hash-chain validation (missing hash / stored vs recomputed mismatch at sequence N / scope / evidence digest); `resume_workflow` (validate chain → resume from reverify → complete to MERGED; idempotent when completed; refuses tampered chain and out-of-segment targets); `reset_workflow` (policy-gated `allow_destructive`, deletes run-scoped Evidence/Failure/Execution/ConsequentialEvent, run→QUEUED+`demo_reset`); `idempotency_guard(session, *, task, phase)`; `cleanup_stale_sandboxes(dry_run)`.
- `failure_inject.py` (subagent C): 10 `FailureInjectionMode`s incl. TEST_FAILURE + CONFLICTING_EVIDENCE; `inject_failure` with deterministic ids (idempotent re-injection), real Execution/Failure/Evidence/ConsequentialEvent rows, EVENT per mode, POLICY_BLOCK/NO_PROGRESS blocked-event paths, triple-failure no-progress fingerprint.
- Wave D (subagent rewrite): `workflow_helpers.py` (no fakes; `make_run` idempotent on `workflow_id("e2e/run/AUTH-017")`), `test_workflow_{orchestrate,replay,reliability,failure_inject}.py`, `test_certification_merge_gate.py` rewritten against REAL modules. `test_certification_merge_gate` "modules unavailable" case uses CPython's documented `None`-in-`sys.modules` import halt (the gate degrades to `allowed=False`, not a verification stub). Result: **47 passed**, mypy clean (6 files).
- Wave E (subagent rewrite): `scripts/phase_gate.py` extended with Phase 11/12 — `PHASE11_PATHS`, `PHASE12_PATHS`, test suites, mypy targets, `_check_phase11/12_{structure,imports,quality}`, `finalize_phase1112`, `evaluate_phase11/12`, CLI `--phase 11|12`; `_SRC_PATHS` + `_build_mypy_env` include certification+workflow; `ci.yml` installs `-e packages/certification -e packages/workflow`, mypy targets extended, gate steps `--phase 11`/`--phase 12` added; `test_phase_gate.py` +4 tests (21 total).
- Quality cleanup in-session: `ruff check --fix` + `ruff format` on certification/workflow/packages + rewritten tests; manual SIM102/SIM103 in `alignment.py`; mypy fix in `reliability.py` (loop var reuse); 20 lint errors fixed → all clean.
- Gate evidence (2026-09-14): `python scripts/phase_gate.py --phase 11` → **PHASE_11_PASS** (exit 0); `--phase 12` → **PHASE_12_PASS** (exit 0). Structure + 17 contracts + imports + joint phase1112 tests (exit 0) + quality (ruff check+format+mypy clean) + env all PASS.
- Full suite: `pytest tests/unit tests/integration tests/security` → **653 collected, exit 0** (all green after rewrite; previously the 4 workflow scaffold files failed at collection).

## Session Coordination Record (2026-09-13) — Phase 11/12 orchestration session
- This session owns Phase 11 (`packages/certification`, module `smorx_certification`: re-verify, intent alignment, certificate generation + integrity, merge gate, failure archaeology, memory pipeline) and Phase 12 (`packages/workflow`, module `smorx_workflow`: E2E orchestration, state replay, failure injection, demo reliability, performance).
- A parallel session owns Phase 9/10 (`packages/verification` — independent verification modules + Candidate Patch #2/behavioral delta/intent alignment/repair). This session will NOT modify `packages/verification`, `packages/evidence`, `packages/ui`, or `apps/web/app/*`.
- Coordination is file-based (append-only Progress entries + disjoint file ownership). Subagent-spawn tooling (`task`) IS available in this opencode environment, so genuine parallel delegation is used for implementation.
- Baseline verified at session start: `pytest tests/unit tests/integration tests/security` → **516 passed** green; git status showed only `apps/web` uncommitted changes; no Phase 9/10 artifacts had landed yet.
- Contract-bounded approach: Phase 11/12 modules consume the real `smorx_contracts`, `smorx_behavior` ORM entities (Certificate, IntentAlignment, BehavioralDelta, CandidatePatch, Claim, MemoryUpdate, Failure, Ghost, VerificationCase), evidence/provenance traversal helpers, versioning lock policy (ADR-0005), and the deterministic demo seed (`smorx_behavior.seed.demo`, Payments API / AUTH-017 / Ghost #221 / F-183 / Change #184). Re-verification is a port: it consumes real Evidence rows; where Phase 9/10 modules have not yet landed it asserts BLOCKED on missing verification evidence rather than fabricating it. Certification only when re-verification evidence present AND unexplained changes = 0 AND critical unauthorized changes = 0; otherwise NON_CERTIFIABLE/REPAIR_REQUIRED (I2, I7, §18/§19).
- Placement decision: new packages `packages/certification` + `packages/workflow` follow the established per-phase package convention (precode, develop); disjoint from Phase 9/10's `packages/verification`.

## Phase 6 backend wiring — Discover + Govern behavior adapter live in `apps/api` (2026-09-13)
- Objective: make the Phase 6 (Discover + Govern) surfaces derive from the REAL `smorx_behavior` persistence layer — no fabricated values, honest zero-counts, evidence-bound activation (AGENTS.md §3/§13/§39).
- Ownership: strictly `apps/api` (verified via `git status --porcelain`); `packages/*` and `apps/web` untouched.
- Landed (fused from contract-bounded work): `apps/api/app/behavior/{__init__,contract,database,adapter}.py` + `apps/api/app/api/behavior_routes.py`; wiring in `apps/api/app/{settings,deps,main}.py` (`behavior_database_url`/`behavior_auto_seed` settings, `sqlalchemy>=2.0` + `aiosqlite`); `apps/api/.env.example` comment updated to describe the deterministic seeded fixture at `<repo-root>/demo-seed.sqlite`.
- Contract frozen (formatting-only changes): `BehaviorAdapter` protocol + DTOs; `ActivateResult.status ∈ {ACTIVE, ALREADY_ACTIVE, NOT_DRAFTED}` with `message`; graph node positions typed `dict[str, float]` (JSON emits `0.0`, not int).
- URL anchor: `DEFAULT_BEHAVIOR_DATABASE_URL` derived from `Path(__file__).resolve().parents[4]` via `.as_posix()` → `sqlite:///C:/Users/LOUJAN B/Smorx/demo-seed.sqlite`; runtime `exists: True`. Legacy `sqlite:///./demo-seed.sqlite` remains only as a read-only CLI default in `packages/behavior/seed/demo.py` (package not modified).
- Real integration verification against `demo-seed.sqlite`: project "Payments API", change external_id "184". Behaviors: 1 ("auth token refresh") / ghosts: 1 / evidence: 6; graph edges all resolve to existing targets; constitution initially `claim_count=0`, `protected=1`; readiness `ready=False`, `met_count=2`; `activate()` → `NOT_DRAFTED` (zero Constitution rows — no fabrication, AGENTS.md §3); after inserting a real Constitution + ConstitutionClaim → `ACTIVE`, re-activate → `ALREADY_ACTIVE`, `claim_count=1`.
- Auto-seed: only when no behavior rows exist (fixture with 1 behavior present ⇒ no re-seed).
- Quality gates: `ruff check --fix` (5 fixes: I001 ×2, W292 ×3 incl. contract.py) → "All checks passed!" (exit 0); mypy (7 source files; file-level `# mypy: disable-error-code="import-untyped"` in database.py/adapter.py) → "Success: no issues found in 7 source files" (exit 0); full suite `pytest` → **138 passed (23.47s)**; adapter unit file `tests/test_behavior_adapter.py` → **10 passed (10.12s)** (authoritative via `cmd /c` — PowerShell mangles pytest's summary line with `-q`).
- Open decisions (recorded, not silently resolved): (1) `smorx_behavior` activation uses `ACTIVE` while `ConstitutionStatus` enum is `DRAFT|RATIFIED|SUPERSEDED` — column is `String(40)` so `ACTIVE` persists; package not modified; escalate if the drift must be reconciled. (2) `py.typed` marker for `packages/behavior` is a follow-up, not this wave. (3) Constitution content generation deferred — activation honestly reports `NOT_DRAFTED` until real rows exist. (4) Port mismatch known: `apps/web/next.config.mjs` proxies `127.0.0.1:8000` but `apps/api/run_server.ps1` serves `8099` — frontend-facing caveat only.
- Commit: pending user approval (AGENTS.md §32).

## Phase 9 → 10 — Verification-to-Decision Delta Chain (tests landed, 2026-09-13)
- Contributes to the parallel Phase 9/10 session's ledger: green tests for the phase-10 decision chain over the real phase-9 verification wave.
- `tests/unit/test_delta_core.py` (21 tests): handoff admits only COMPLETED + `VERIFICATION_RESULT_V1` (error names offending state/contract — negative cases covered); deltas classify UNCHANGED/ALTERED/ADDED/UNEXPLAINED deterministically (evidence is decisive: no evidence ⇒ UNEXPLAINED even with a SUPPORTING claim — fixed a test-side assumption by adding an evidence record); intent alignment CONSTRAINT/REQUIREMENT/SECURITY/PERFORMANCE mappings; decision gates BLOCKED/INSUFFICIENT_EVIDENCE/REPAIR_REQUIRED (CONFLICTING, CONTRADICTING, UNEXPLAINED delta, non-AUTHORIZED verdict, FAILED module)/ELIGIBLE_TO_CONTINUE with `allow_merge` T/F; evidence-bound repair loop (no-progress at iteration 2, `LoopBounds(max_iterations=1)` → 1 iteration, blocked_reason contains "no-progress", repair skips when not REPAIR_REQUIRED); repair never certifies.
- `tests/integration/test_phase9_phase10_flow.py` (2 tests): REAL six-module wave (`run_verification_wave`) over real tempdirs + real subprocesses. Clean path: COMPLETED + SUPPORTING/INSUFFICIENT, all modules PASSED, ghost record `regression_reproduced is False`, evidence rows persisted via `record_evidence` and bound to claim1, handoff + `require_candidate_id`, deltas ADDED with deterministic id, alignment AUTHORIZED 0.9, decision ELIGIBLE_TO_CONTINUE (`allow_merge=True`). Regression path: candidate probe prints `REGRESSION reproduced` ⇒ claim1 CONFLICTING, HIGH ghost evidence, FAILED module, deltas ALTERED, REPAIR_REQUIRED; `run_repair_loop` persists RepairPackage rows (status CREATED, evidence-bound) + new CandidatePatch rows (index>=2, `patch_ref.startswith("repair_loop:")`, PROPOSED) while Candidate Patch #1 stays untouched — never CERTIFIED.
- Documented boundary (module-verification behavior, not test bug): each verification module binds evidence to `claim_ids[0]` only; a second claim fuses INSUFFICIENT and classifies UNEXPLAINED when included in the delta set. Integration tests compute deltas on the evidence-eligible claim and additionally demonstrate the full-set gap.
- Test-side fixes made during verification: `CertinceDecision` → `CertificationDecision` typo (replace-all); claim-`d` test now provides evidence before asserting ADDED.
- Result: `python -m pytest tests/unit/test_delta_core.py tests/integration/test_phase9_phase10_flow.py -q` → **23 passed** (2.1s). Full-suite collection still shows 4 PRE-EXISTING failures in the parallel Phase 11/12 session's `tests/unit/test_workflow_*.py` (ImportError: `workflow_id`/`DEFAULT_PHASES` missing from `smorx_workflow.orchestrate` — `packages/workflow` untracked in-tree work, out of this session's scope).
- Ruff: `ruff check` + `ruff format` clean at **line-length 100** (per-package `pyproject.toml` convention) for both files.

## Phase 9/10 — Gate & CI Completion (2026-09-13)

- Re-verified 2026-09-14: `python scripts/phase_gate.py --phase 9 --json` → `PHASE_9_PASS` (exit 0), `--phase 10 --json` → `PHASE_10_PASS` (exit 0). Gate checks green: phase structure presence, all 17 contracts validated, phase 9/10 imports resolvable, phase910 tests exit 0 (68 tests), phase quality (ruff check + format + mypy clean for `packages/verification` and `packages/verification`+`packages/delta` respectively), environment.
- Test evidence: `python -m pytest tests/unit/test_phase_gate.py tests/unit/test_verification_trust.py tests/unit/test_verification_wave.py tests/unit/test_delta_core.py tests/integration/test_phase9_phase10_flow.py -q` → **85 passed** (17 phase-gate contract tests + 68 phase9/10 validation + integration tests).
- Quality: `ruff check scripts/phase_gate.py scripts/quality_gate.py` → all checks passed; `ruff format --check` → both already formatted.
- CI (`ci.yml`): job installs `-e packages/verification -e packages/delta`; `python -m mypy packages/verification` and `python -m mypy packages/verification packages/delta` (gate-bounded targets); `python scripts/phase_gate.py --phase 9` / `--phase 10` steps gate both phases in CI.
- Gate evidence note: gate `--json` emits per-check results inline only (`evidence` field is `{}`); no evidence file is written by the gate itself.

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

---

## Post-restart Full-Stack + Browser Verification (2026-09-14) — WEB RESTART + LIVE CDP EVIDENCE
- Context: Phase 11/12 committed as `9f77b96` (`feat(workflow): finalize phase 11/12 gate infrastructure`). `apps/web` changes kept uncommitted (parallel session). Full-stack was restarted cleanly and verified live in headless Chrome, server-side active-tab state → UI.

## Restart Evidence
- API: `apps/api/run_server.ps1` (uvicorn, port 8099) restarted; pid 24416 (listening pid); `/health` → 200 `{"status":"ok"}`.
- Web: `npm run dev` on port 3000 with `API_BASE_URL=http://127.0.0.1:8099`; Next.js 15.5.25 "Ready in 37.3s"; proxy `/api/health` → 200 `{"status":"ok"}`.
- Chrome: headless CDP on 9222 (Chrome/152.0.7977.84), navigated to `http://localhost:3000`, title "Smorx — Software Evolution Intelligence System".

## Stale-State Investigation
- Persisted zustand state (`smorx-app-state`) held `currentStage:"Govern"`, `completedStages:["Discover","Govern"]`, `trustStatus:"PROTECTED"` while UI showed `activeTab:"Discover"` and no `Proceed to Define` — a state/UI mismatch from pre-restart play.
- Resolution: removed the persisted key via CDP and reloaded → clean initial state `currentStage:"Discover"`, `completedStages:[]`, `trustStatus:"HISTORICAL"`, only Discover enabled. Milestone confirmed via `cdp-diagnose.mjs` (Proceed-to-Define NOT FOUND, Discover active) — expected, not a regression.

## Live Journey Evidence (cdp-journey2 + cdp-final + cdp-govern-check + cdp-reactivate)
- Discover: initial (Discover enabled; Govern…Certify + Back disabled) → `Run Software Archaeology` → Trust HISTORICAL→OBSERVED, Govern unlocked, Stage metric = Discover.
- Govern: workspace → `Activate Constitution` → activation screen (readiness 4/5, "Human approval required LOCKED") → activate → `Constitution Ratified` (readiness 5/5), Trust OBSERVED→PROTECTED, `Proceed to Define` appears, Define unlocked.
- Define: placeholder renders; Analyze/Develop/Verify/Decide/Certify stay correctly disabled (stage-lock works).
- Persistence: reload → store retains `currentStage:"Govern"`, `completedStages:["Discover","Govern"]`, `trustStatus:"PROTECTED"`; on the ratified view `Proceed to Define` is reachable (activation click is idempotent, 4/5→5/5 readiness reflects the human-approval gate).
- Runtime health: 0 exceptions, 0 bad responses, 0 network failures across all interactions; only console noise = 2× React DevTools dev-mode info; `/favicon.ico` 404 harmless. Screenshots in `%TEMP%\opencode\shots-journey\*.png` + `shot-govern-ratified.png`.

## Notes
- Chrome DevTools MCP was configured but not connected this session; raw CDP fallback used for evidence. State-lock wiring (`Navigation.tsx` `isTabAvailable`) is authoritative per source inspection + gate tests.

## Color Theme Plan & Glass Morphism Wave (2026-09-14)

### Role-based color usage plan (roles → hex → where → where NOT)
| Role | Hex(es) | Where to use | Where NOT to use |
|---|---|---|---|
| Canvas (smoke) | `#f5f7fb` | page region only | never on cards/panels |
| Surface elevated | `#ffffff` | cards, panels, drawers, popovers | never as page background |
| Surface subtle | `#eef1f8` | inset areas, placeholders, status strips | never as elevated surface |
| Border hairline | `#e3e8f2` | hairlines, dividers | never as accent |
| Border strong | `#c2cdde` | strong lines, graph grid dots | never on text |
| Text primary/secondary/muted/inverse | `#172033` / `#46536b` / `#8a94a8` / `#ffffff` | all body/heading/label copy | never as background fills |
| Accent (single action) | `#4a6cf7` base, `#3a56d6` hover, `#edf1fe` tint, `#dce4fd` soft | primary buttons, active tabs, focus/borders, progress | never as arbitrary decoration |
| Trust/semantic | observed `#5b6478`, protected `#0e9f6e`, locked `#7c5ce0`, unverified `#c08a17`, violated `#d8493c`, repair `#e07b4a`, certified `#14936b`, historical `#8a94a8` | trust badges, status chips, semantic icons | never for wayfinding alone |
| State | active `#0e9f6e`, pending `#d89a24`, failed `#d8493c`, blocked `#e98c4e`, draft `#8a94a8` | workflow/readiness status | never as text on primary buttons |
| Stage hues (wayfinding only) | Discover `#5b66e8`, Govern `#7c5ce0`, Define `#3d86f4`, Analyze `#22a7d4`, Develop `#1eaf8c`, Verify `#d89a24`, Decide `#e98c4e`, Certify `#db5f9c` | active tab, step dots, tiny tinted surfaces (`stageColors` in `src/lib/design-tokens.ts`) | never as full-page color, never as brand |
| Behavioral constants | BEHAVIOR `#4a6cf7`, INVARIANT `#0e9f6e`, INCIDENT `#d8493c`, DEPENDENCY `#c08a17`, RISK_ZONE `#e98c4e`, GHOST `#7c5ce0` | behavioral graph nodes/legend, archaeology stats | never outside behavioral context |

### Glass morphism placement policy
- Accretion layers only: header/TopContextBar strip, drawers + backdrop, popovers — these float above data.
- NEVER on data surfaces (cards, tables, graph canvas, evidence lists) or body backgrounds.
- Accretion layers stay translucent smoke/white with palette hairlines; no unapproved blur beyond the defined layers.

### Rules
1. One accent — the `#4a6cf7` family is the only action color; everything else is semantic or neutral.
2. Color = role. A color carrying no meaning must be neutral (text/surface tokens). No raw out-of-palette hexes in components.
3. Prefer tokens (`var(--color-*)`, `bg-accent-primary`, stage/brand constants) over raw hex literals; arbitrary-value `[#...]` only with documented palette hexes.
4. Stage hues are wayfinding-only and never express action or trust semantics.

### Files & verification
- This wave edited (palette enforcement): `src/components/discover/DiscoverTab.tsx`, `src/components/discover/ArchaeologyLaunch.tsx`, `src/components/discover/BehavioralKnowledgeGraph.tsx`, `src/components/shell/Navigation.tsx`, `src/components/shell/PlaceholderTab.tsx`. Color literals only — no logic, text, or layout changed.
- Owned files handled by parallel agents (not edited here): `app/globals.css` (Agent A — legacy status-badge raw hex block ~lines 174–244 pending migration), `src/components/shell/AppShell.tsx` (Agent B — EmptyState `bg-red-50/border-red-100/text-red-500`), `src/components/shell/TopContextBar.tsx` (Agent B — out-of-palette `#6a4ed0`, `#5b44b8`, fallback `#6b7280`).
- Out-of-scope / non-`.tsx` leftovers for orchestrator: `app/page.module.css` is orphaned dead code (not imported; dark-theme legacy hexes — recommend deletion); `tailwind.config.ts` `surface.borderStrong: '#d3dae7'` conflicts with documented border-strong `#c2cdde` (the latter is declared in `globals.css`) — value currently dormant (no class uses it).
- Verification: `npx tsc --noEmit` → exit 0. Post-fix audits — legacy `text|bg|border-<palette>-NNN` class audit: 0 in writable scope (only owned `AppShell.tsx` remains); raw-hex audit in writable scope: only documented palette hexes remain (design-tokens.ts canonical block + stage/brand/behavioral constants). Archaeology smoke-test status is to be verified by the orchestrator.