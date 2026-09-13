# smorx-contracts

Master contract package for the Software Evolution Intelligence System
(ADR-0002, ADR-0005).

Contains:

- `schemas/<name>.schema.json` — one versioned JSON Schema (Draft 2020-12) per
  master contract (exactly 17) plus the supplementary
  `consequential_event.schema.json` (§2.4 structured event schema).
- `smorx_contracts` — Python package providing the `ContractRegistry`, pydantic
  v2 runtime models for every contract, standalone semver versioning helpers,
  and deterministic `sample_instance(name)` demo/seed payloads.

Public surface (`smorx_contracts`):

- `CONTRACT_NAMES` — the 17 master contract names, in registry order.
- `get_registry()` — singleton `ContractRegistry`.
- `validate_contract(name, obj) -> bool` — registry validation, raises on
  invalid instances or unknown names.
- `sample_instance(name) -> dict` — minimal valid instance per contract.
- `ConsequentialEvent` — pydantic model for structured consequential events.
- `versioning` — `validate_version`, `bump_major/minor/patch`,
  `is_compatible`, `immutable_key`.

Registry semantics:

- Validate is pydantic-model driven (runtime canonical); JSON Schemas are the
  cross-language (TypeScript) source of truth and stay synchronized by the
  registry tests.
- Cross-reference checks: `evidence` must reference a `claim` (+ optional
  related task/run/artifact); `certificate` must reference verification
  evidence, change identity, commit, and a behavioral delta; `tool_invocation`
  must reference an `action` and may carry an embedded `execution_result`.
- Unknown contract names are rejected with a clear error.
- `tool_invocation.execution_result` is declared loosely in the JSON Schema;
  its structure is enforced at runtime against the `execution_result` model.

The registry resolves schemas from the source-tree `schemas/` directory by
default; install-time package-data wiring is deferred to a later phase.