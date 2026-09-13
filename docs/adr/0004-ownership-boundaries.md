# ADR-0004 — Ownership Boundaries

- Status: Accepted
- Date: 2026-09-12
- Supersedes: —

## Context

Phase 0 is executed by parallel agent sessions and a parallel subagent wave (architecture, contracts, DevOps, QA, documentation). `AGENTS.md` requires that integration across sessions must not overwrite unknown work, that subagent responsibilities be non-overlapping and contract-bounded, and that the orchestrator remain responsible for the final result even when work is delegated.

The repository already contains `apps/api/` — Phase 1 FastAPI work being built in the same working tree by a separate session. Uncontrolled parallel writes are the main risk in this phase: two agents editing the same file will silently destroy each other's evidence. A decision on who may touch which path is therefore a prerequisite for every subsequent phase.

## Decision

The project adopts a two-session execution model with explicit file-level ownership:

- **Session A — foundation / contracts / architecture** owns:
  - `packages/contracts`
  - `packages/agent-runtime`
  - `docs/adr`
- **Session B — governance / quality / validation** owns:
  - `scripts`
  - `tests`
  - CI configuration (`.github`)
  - the web health path under `apps/web`
- **Phase 1 infrastructure session** owns:
  - `apps/api` — existing FastAPI work; never treated as a Phase 0 deliverable of this session.

Integration rules that apply across sessions:

1. An agent must not overwrite a file whose content it has not inspected and whose ownership it does not hold.
2. Files that both sessions legitimately need are treated as shared and edited minimally — changes limited to what the session's contract requires.
3. A session that discovers unexpected content in a path it does not own must leave it untouched and report it to the orchestrator rather than moving or "fixing" it.
4. Shared coordination artifacts (`AGENTS.md`, `README.md`, `Progress.md`, governing documents under `Project Spec/`) are not rewritten by agent sessions without orchestrator instruction.

Assignments for each parallel wave are recorded in the subagent contracts issued by the orchestrator; this ADR fixes the boundary model the contracts follow.

## Consequences

### Positive
- Parallel execution is safe: each session has a disjoint mutation scope, so no two agents can legitimately claim the same file.
- `apps/api` progress from the Phase 1 session is preserved because it is outside every other session's scope.
- Integration disputes are reduced to a clear rule ("that path is not yours") instead of judgment calls.
- The ownership map doubles as a structure map that future phases consult before writing.

### Negative / Trade-offs
- The model depends on the orchestrator issuing correct, non-overlapping contracts in every wave.
- A few files are genuinely shared, requiring the "edit minimally" discipline, which adds a review step at integration.
- If a session deviates from its boundary, detection is reactive (at integration) unless the phase gate also checks scope.

## Rejected alternatives

- **One session owning everything sequentially.** Rejected: it serializes independent work, directly contradicting the mandatory parallel-delegation rule and wasting the parallel wave.
- **"Everyone may edit anything, conflicts resolved later."** Rejected: it guarantees silent overwrites of evidence, contradicts the non-overlap rule, and would lose Phase 1 API work.
- **Copy-based isolation (each session works on a fork, blind-merged later).** Rejected: forks mask overlapping edits until merge time, generate large reconciliation effort, and make integration-time conflicts harder to attribute than a strict per-path ownership map.

## Verification

- The phase-gate script includes a scope check on the paths this phase was authorized to create; files outside the session boundary are not modified by Phase 0 work.
- The integration wave compares each session's reported files against the ownership map and reports any overreach to the orchestrator.
- `docs/adr/README.md` and this ADR serve as the written boundary contract that later subagent instructions reference.
- CI runs the same quality gates from a clean state, so an accidental cross-session change surfaces as a reviewable diff.