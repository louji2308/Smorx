# Architecture Decision Records — Index

Architecture Decision Records (ADRs) in this directory record accepted engineering decisions for the Software Evolution Intelligence System. Every ADR follows the same structure:

- Context — the problem the decision addresses and its constraints.
- Decision — the chosen approach, precisely and operationally.
- Consequences — positive effects and trade-offs.
- Rejected alternatives — options considered and rejected.
- Verification — how the decision is enforced in the repository.

ADR numbering is sequential and never reused. A numbering gap indicates a superseded record (the superseding record lists it in "Supersedes").

## ADR index

| ID | Title | Status | Date | Supersedes |
|----|-------|--------|------|------------|
| ADR-0001 | Repository Structure | Accepted | 2026-09-12 | — |
| ADR-0002 | Contract Architecture | Accepted | 2026-09-12 | — |
| ADR-0003 | Agent State Machine | Accepted | 2026-09-12 | — |
| ADR-0004 | Ownership Boundaries | Accepted | 2026-09-12 | — |
| ADR-0005 | Versioning and Immutability | Accepted | 2026-09-12 | — |
| ADR-0006 | Testing Strategy | Accepted | 2026-09-12 | — |
| ADR-0007 | Phase-Gate Strategy | Accepted | 2026-09-12 | — |

## Status definitions

- **Accepted** — the decision has been adopted and implementation is expected to follow it.
- Superseded records remain in place for history; a dependent decision records the superseding ADR in its header.

## Supersession policy

Phase 0 decisions are the original records for the repository structure, contract architecture, agent state machine, ownership boundaries, versioning and immutability, testing strategy, and phase-gate strategy. Later ADRs that replace or refine any of these MUST reference the superseded ADR in their header and retain the original record.