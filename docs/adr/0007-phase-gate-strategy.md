# ADR-0007 — Phase-Gate Strategy

- Status: Accepted
- Date: 2026-09-12
- Supersedes: —

## Context

Master invariant I12 (`Phase gates are mandatory`) and `AGENTS.md` section 44 state that a phase is not "done" because code exists; it is done only when its implementation, tests, integration checks, evidence, and exit criteria pass. The Phase 0 exit gate in the implementation plan requires the repository to boot cleanly, contracts compile, state-machine tests pass, and the basic frontend/backend health path work.

Without a machine-executable gate, phase completion is a subjective claim made by an agent, which is exactly the kind of assertion the system is built to reject. A gate that is part of the agent's self-report rather than an independent check would not establish trust.

## Decision

The phase gate is the script `scripts/phase_gate.py`, executed by the orchestrator after implementation and testing are complete. Its output is one of two machine-readable states:

- `PHASE_0_PASS` — every required check in the gate passed.
- `PHASE_0_BLOCKED` — one or more checks failed, and the output includes the concrete failure list with reasons.

A phase is not complete when the gate script exists or runs. A phase is complete only when all of the following are satisfied:

1. Implementation required by the phase is present and does not alter the boundaries set by the contracts.
2. The quality gates defined in ADR-0006 pass.
3. The relevant unit and integration tests pass.
4. Required evidence (test output, execution trace, registry check) exists and is machine-readable.
5. Exit criteria listed in the phase section of `IMPLEMENTATION_PLAN.md` are met.
6. The phase gate emits `PHASE_0_PASS` (or `PHASE_1_PASS`, `PHASE_2_PASS`, etc., for later phases).

`BLOCKED` is a legitimate terminal status for a phase. It is not success and must not be reframed as such. A blocked phase must remain blocked until the cause is identified, corrected, and re-gated; rewriting the gate to report PASS is a contract violation.

Phase gates are sequential documents: the ADR index table in `docs/adr/README.md` is updated when a new gate ADR is added, and the superseding relationship is recorded there when a gate replaces an older one.

## Consequences

### Positive
- Phase completion is objective and machine-checked rather than a subjective report from the agent.
- Failure reasons are surfaced with the gate result, so a blocked phase points directly to the unmet condition.
- The same gate structure scales across all later phases: Phase 1 gate reads the same pattern and emits `PHASE_1_PASS` or `PHASE_1_BLOCKED`.
- The gate can be run independently of an agent session by CI or a reviewer, making it evidence rather than self-attestation.

### Negative / Trade-offs
- Writing a machine-readable gate is more effort than a human-written status report.
- A rigid gate may initially reject work that is partially complete, which requires the agent to complete the work rather than report partial progress as pass.
- Phase gate scripting must stay in sync with the implementation plan's exit criteria; drift would make the gate a lie.

## Rejected alternatives

- **"Tests pass" as the sole gate.** Rejected: "tests pass" is the model asserting that tests passed; the authoritative evidence is the machine output of the test runner, and a gate that only inspects exit codes without checking evidence, registry, and health has incomplete exit criteria.
- **Agent self-reporting completion.** Rejected explicitly by the master invariants: a model statement is not authoritative; this is the same problem as "tests pass" applied to the whole phase.
- **A single combined status flag set by the orchestrator after manual inspection.** Rejected: it restores subjectivity and makes the gate dependent on the orchestrator being correct; an independent machine-executable check avoids that dependency.

## Verification

- `scripts/phase_gate.py` is itself verified: Phase 0 baseline tests exercise the gate and confirm it emits `PHASE_0_PASS` for a compliant repository and `PHASE_0_BLOCKED` with reasons for a known noncompliant state.
- The CI workflow invokes the phase gate after the quality gates and blocks downstream work on a BLOCKED result.
- The ADR index (`docs/adr/README.md`) is the machine-readable record that this gate strategy is accepted; a change to the gate mechanism requires updating or superseding this ADR.