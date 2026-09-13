# ADR-0003 — Agent State Machine

- Status: Accepted
- Date: 2026-09-12
- Supersedes: —

## Context

`Project Spec/IMPLEMENTATION_PLAN.md` Phase 0.3 requires that the agent states be represented in code rather than only in UI copy. The minimum set is CREATED, INSPECTED, PLANNED, EXECUTING, OBSERVED, FAILED, ITERATING, VERIFIED, and BLOCKED. `AGENTS.md` treats `BLOCKED` as a legitimate state that is not equivalent to success, and requires that the agent be able to continue, retry, rollback, stop, or block.

The Academy judges a system on whether it can reason from *actual* executed behavior. An unenforced state model — states as display strings only — would allow a workflow to claim progress it did not have, violating the invariant that model assertions are never authoritative over execution evidence.

## Decision

The executable state machine lives in `packages/agent-runtime` (package `smorx_runtime`). It defines exactly nine states:

```text
CREATED
INSPECTED
PLANNED
EXECUTING
OBSERVED
FAILED
ITERATING
VERIFIED
BLOCKED
```

The legal transitions are the exact transitions defined by the Phase 0 contract recorded in the master contracts (see ADR-0002). The machine raises an exception on any invalid transition attempt; it never silently ignores an illegal move.

The transition model includes:

- the forward workflow path CREATED → INSPECTED → PLANNED → EXECUTING → OBSERVED with iteration through FAILED and ITERATING back into EXECUTING;
- the success path OBSERVED → VERIFIED;
- the terminal BLOCKED state, entered from any active workflow state when a policy, safety, evidence, or no-progress condition stops execution;
- `VERIFIED → BLOCKED`, which exists for post-verification policy blocks (for example a certificate or merge gate refuses to proceed), keeping BLOCKED distinct from success;
- retry/rollback transitions that move a run back to a permitted earlier state for a bounded repair cycle.

BLOCKED is terminal and is a first-class outcome; a workflow that terminates in BLOCKED must not be reported as successful.

## Consequences

### Positive
- State transitions are machine-checked: invalid sequences (for example jumping straight from CREATED to VERIFIED) are impossible rather than merely unrecommended.
- The state model supports observability: every agent run, subagent run, and phase can be inspected at an exact state with a trace of how it arrived there.
- Bounded iteration is natural to express (failed executions → ITERATING → EXECUTING with loop counters enforced by the runtime).
- The separation of VERIFIED and BLOCKED preserves the human-control requirement and the "no progress" discipline.

### Negative / Trade-offs
- A state machine that rejects invalid transitions is more rigid than a free-form workflow; some orchestration flows must be expressed explicitly as legal paths.
- Keeping the nine states and their transition table in sync with the master contract requires discipline when contracts evolve.
- New states require a contract update (a new contract version), not a one-line string addition.

## Rejected alternatives

- **Free-form status string field on run objects.** Rejected: nothing would prevent a workflow from reporting VERIFIED without passing through OBSERVED, making fake success states possible and unenforceable.
- **Implementing the states only in the UI.** Rejected explicitly by the implementation plan: states represented in UI copy cannot govern backend behavior and would let the frontend display success the backend never earned.
- **A single end-to-end scripted flow with no intermediate states.** Rejected: it has no failure, retry, or block branches and violates the safe-stopping and failure-is-information invariants.

## Verification

- Phase 0 baseline tests under `tests/unit` exercise every legal transition from the contract and assert that each one produces the expected next state.
- Invalid-transition tests assert that disallowed transitions raise, including direct jumps (for example CREATED → VERIFIED) and transitions from terminal states.
- Loop-bound tests verify that ITERATING cycles stop after the configured maximum repair attempts and transition to BLOCKED under the no-progress rule.
- The phase-gate script reads the state machine contract and verifies it imports and its transition table matches the contract.
- `packages/agent-runtime` is type-checked with the package quality gates defined in ADR-0006.