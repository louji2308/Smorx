# ADR-0008 — Phase 3/4 Orchestration and Control-Plane Architecture

- Status: Accepted
- Date: 2026-09-13
- Supersedes: —

## Context

The system must execute software-engineering work as a coordinated flow of
parallel specialist subagents, with every consequential mutation attributable
to a decision and an execution, and with a trust boundary between "the agent
proposes" and "the mutation lands". The implementation plan sequences the
orchestration runtime before the tool layer: sub-agent execution, attribution,
and state transitions must exist before policy control wraps them. Two
requirements are otherwise in tension: agents need real tool access to produce
real artifacts, and the system must guarantee that unauthorized or unattributed
actions never happen.

Without a policy-enforced tool plane, an agent with tool access can mutate the
repository with no audit record and no human gate, which contradicts the
project contract that every consequential mutation is attributable and that
safe stopping (continue/retry/rollback/stop/block) is mandatory.

## Decision

Phase 3 (orchestration runtime) and Phase 4 (tool/control plane) are accepted
together as one architectural decision:

- **Phase 3 — orchestrator runtime** (`packages/agent-runtime`, module
  `smorx_runtime`): agents and specialist capabilities (CODING /
  VERIFICATION / EVIDENCE / REPAIR) bound to allowed tools; a `TaskGraph` with
  INDEPENDENT, DEPENDENT, RECONCILER, and SERIALIZED task kinds (SERIALIZED
  tasks always run alone); a `ParallelWaveEngine` that executes ready tasks
  concurrently with cancellation; `SingleAgentScheduler`; telemetry that
  measures real parallelism (high-water and cross-task overlap, not assumed
  concurrency); the orchestrator state machine with bounded retry,
  failed-specialist replacement, no-progress blocking, and
  `OrchestrationReport` as the evidence-shaped outcome.
- **Phase 4 — tool layer + control plane** (`packages/tools`, module
  `smorx_tools`): a tool registry with real handlers, real subprocess
  execution and failure classification, a policy engine (BLOCK / DENY /
  REQUIRE_REVIEW / ALLOW), an immutable audit trail, a human control plane
  (request/approve/deny/abort/pause), repository/file handlers, and
  `ControlPlane` as the single `CapabilityGateway` enforcement path with a
  deterministic authorization resolution order: unknown tool -> duplicate-
  EXECUTED guard -> capability mismatch -> allowed-tools mismatch -> policy
  (with human approval for REQUIRE_REVIEW) -> ALLOW. Every decision is audited.
- **Sandbox honesty**: sandbox operations return `UNAVAILABLE` with an
  environment/dependency classification when no provider is bound, rather than
  fabricating sandbox ids or simulated successes.
- **Adversarial guardrail stance**: the tool plane and orchestrator are
  exercised against a dedicated adversarial suite (unknown tools, capability
  bypasses, duplicate invocations, retry/no-progress exhaustion, partial and
  cancelled waves, audit-attribution integrity, and stale-result rejection).

## Consequences

### Positive
- Every consequential mutation is attributable through an immutable audit
  record (action_id, tool, decision, risk, resource_ref).
- `SUCCEEDED` requires supporting evidence (`validate_result`); the control
  plane maps `SUCCEEDED`/`FAILED`/`TIMEOUT`/`DENIED`/`BLOCKED`/`UNAVAILABLE`
  to audit decisions, so a success claim without real execution is structurally
  a mismatch.
- No-progress and retry budgets block instead of looping, giving the system a
  deterministic stop/block path.
- High-risk operations require human approval; without an approval object the
  operation is recorded as REVIEW and never executed.
- Real concurrency is measured, not assumed: the Phase 3 gate demonstrates
  `parallelism_high_water=3` with wall-clock overlap greater than zero.
- The future Nebius sandbox binding attaches a real sandbox-control provider
  by injection behind the same `CapabilityGateway` seam — no API change.

### Negative / Trade-offs
- Two subsystems (orchestrator and control plane) must stay in sync: the
  `CapabilityGateway` protocol is the contract at the seam and is checked
  structurally in tests.
- Policy enforcement adds a mandatory authorization hop in front of every tool
  call; this is deliberate latency in exchange for attribution and control.
- Honest `UNAVAILABLE` responses mean the system cannot demonstrate real
  sandbox execution until a provider is actually bound — faster to demo but
  correct.

## Rejected alternatives

- **Agents executing tools directly, without a policy gateway.** Rejected: no
  audit trail, no capability enforcement, no human gate, and no trust boundary
  between proposal and mutation.
- **Simulated sandbox execution to keep the demo green.** Rejected by
  AGENTS.md section 3: execution results are authoritative over model
  assertions, and a fabricated sandbox is a production mock, not a test fixture.
- **Serialized execution pretending to be parallel.** Rejected: telemetry
  measures actual overlap, and the Phase 3 gate proves concurrency rather than
  reporting it.

## Verification

- Unit suites: 31 (agents/capabilities) + 29 (graph/waves/telemetry) + 12
  (toolgate/orchestrator); 22 (tool/execution) + 20 (policy/audit/control) + 22
  (sandbox/human/repo).
- Integration: `tests/integration/test_phase3_phase4_integration.py` (6 tests),
  including the full end-to-end trust chain (3 CODING agents write real files,
  RECONCILER validates, audit trail attributes every step) and the full
  Phase-4 human-approval loop (blocked run 1 -> approve -> verified run 2).
- Adversarial: `tests/security/test_adversarial_guardrails.py` (20 scenarios).
- Gates: `PHASE3_GATE: PASS` and `PHASE4_GATE: PASS` with the named
  concurrency and audit-chain evidence recorded in `Progress.md`.
- Static: `ruff check` + `ruff format` clean; `mypy --strict` clean on 10
  `smorx_runtime` and 10 `smorx_tools` files.
- Full suite at documentation time: 391 passed (365 unit + 6 integration + 20
  security).