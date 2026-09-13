# ADR-0001 — Repository Structure

- Status: Accepted
- Date: 2026-09-12
- Supersedes: —

## Context

The system is one product with eight journey tabs (Discover, Govern, Define, Analyze, Develop, Verify, Decide, Certify) and twenty-one product moments, built by multiple parallel agent sessions. `Project Spec/IMPLEMENTATION_PLAN.md` Phase 0.1 requires a clean monorepo or clearly separated application structure with explicit ownership boundaries, and states that exact folder names may be adjusted during implementation but ownership boundaries must remain explicit.

Without an explicit, predefined layout, parallel workstreams would produce overlapping or contradictory directory conventions. The governing documents also recommend against building custom substitutes for managed primitives, so the structure must support a thin Next.js client, a FastAPI backend, reusable packages, and real Nebius/NVIDIA infrastructure without conflating concerns.

## Decision

Phase 0 establishes a monorepo with the following top-level structure:

```text
/apps
  /web              Next.js / React / TypeScript / Tailwind web application (thin client)
  /api              FastAPI backend (owned by the Phase 1 infrastructure session)

/packages
  /contracts        Master contracts: JSON Schema + Python pydantic models (smorx_contracts)
  /agent-runtime    Executable agent state machine and run primitives (smorx_runtime)
  /tools            Tool definitions and policy-controlled tool registry (reserved)
  /evidence         Evidence collection and normalization (reserved)
  /behavior         Behavioral model and behavioral knowledge (reserved)
  /verification     Independent verification modules (reserved)
  /ui               Shared UI component library (reserved)

/infrastructure
  /docker           Container tooling
  /nebius           Nebius configuration, Token Factory, and sandbox setup

/tests
  /unit
  /integration
  /e2e
  /security
  /evaluation

/docs                 Engineering documentation and ADRs
/scripts              Root-level engineering scripts, including phase_gate.py
/.github              CI workflow configuration
```

Phase 0 creates real content in `packages/contracts`, `packages/agent-runtime`, `scripts`, `tests/unit`, `docs/adr`, the web health path under `apps/web`, and READMEs under `infrastructure/`. The remaining packages (`tools`, `evidence`, `behavior`, `verification`, `ui`) are reserved placeholders for later phases; they must not accumulate premature implementation.

## Consequences

### Positive
- One system, not disconnected applications: every surface maps to a clear home, matching the single-product product contract.
- Cross-language contracts have a dedicated home (`packages/contracts`) that two runtime languages (Python, TypeScript) can consume.
- Parallel agent sessions have disjoint mutation scopes, which makes the two-session execution model safe.
- The structure mirrors the implementation plan, so Phase 0.1 compliance is directly checkable.
- Reserved packages make later phase boundaries visible before they are implemented.

### Negative / Trade-offs
- Monorepo tooling and workspace management add initial configuration overhead.
- Draining reserved placeholder packages adds ceremony for later phases.
- Many packages are empty at the end of Phase 0, which can look incomplete to an outside reviewer until later phases land.

## Rejected alternatives

- **Single flat application (one app containing frontend, backend, and logic).** Rejected: a single Flask/Next mixed bundle would couple the thin client, the application API, and the intelligence layer, violating the architecture contract that separates the UI from the intelligence layer and making independent verification harder.
- **Multiple independent repositories (one per service).** Rejected: cross-repository contract drift would undermine the master-contract architecture, complicate the shared evidence/claim model, and conflict with the requirement that this is one persistent product accumulating state.
- **Custom execution platform instead of Nebius primitives.** Rejected at the repository level by structuring `infrastructure/nebius` around the Nebius Token Factory Sandbox rather than inventing a Docker-based execution substitute, per the tech-stack directive not to build custom execution VMs or sandbox orchestration from scratch.

## Verification

- Phase 0 phase-gate script `scripts/phase_gate.py` includes a repository-structure check asserting the required top-level and phase-0 directories exist.
- Phase 0 unit tests under `tests/unit` assert that reserved packages contain only permitted placeholder content.
- The CI workflow under `.github` mirrors these checks on every push.
- `docs/adr/README.md` maintains the canonical ADR index; a structural change must be recorded as a new ADR, not silently applied.