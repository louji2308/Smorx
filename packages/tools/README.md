# smorx-tools

Policy-controlled tool layer for the Software Evolution Intelligence System
(implementation plan phase 4).

* `smorx_tools.tool` — tool registry, request/result contracts, failure taxonomy.
* `smorx_tools.execution` — bounded command execution and deterministic failure classification.
* `smorx_tools.policies` — risk-graded policy engine (`ALLOW` / `DENY` / `REQUIRE_REVIEW` / `BLOCK`).
* `smorx_tools.control` — the `ControlPlane` that implements the runtime
  `CapabilityGateway` seam so agents can never execute host operations outside
  the policy + audit boundary.
* `smorx_tools.audit` — append-only audit trail binding decision → policy → execution → result.
* `smorx_tools.sandbox` — Nebius sandbox port with honest `UNAVAILABLE` semantics when no provider is bound.
* `smorx_tools.human` — human approval / pause / resume / abort control.
* `smorx_tools.repo` — path-safe repository toolkit with attributable mutations.
* `smorx_tools.assembly` — assembles the default `ToolRegistry` from the built-in tools.