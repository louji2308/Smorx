# ADR-0005 — Versioning and Immutability

- Status: Accepted
- Date: 2026-09-12
- Supersedes: —

## Context

Track 1 master invariant I9 (`Locked objects stay locked`) requires that the Behavioral Constitution, Intent Ledger, Semantic Impact Map, and Verification Plan remain immutable once downstream work begins, unless the workflow deliberately creates a new version. `Project Spec/IMPLEMENTATION_PLAN.md` Phase 0.5 requires defining how locked objects receive versions and how downstream references are tied to exact versions, and Phase 2.5 extends the same rule to all locked objects.

The purpose of immutability is trust: certification, evidence traversal, and intent alignment only mean something if the account of *what was true at the time* cannot silently change. If an object could be silently mutated after it was locked, every certificate that references it would become untrustworthy.

## Decision

Locked objects — including the Claim protected state, VerificationPlan, Intent, and Certificate — are immutable references. The decision line is:

- **New version, new identity.** Creating a new version produces a brand-new object with a new id, `version = previous + 1`, and explicit links: `parent_version` pointing to the object it derives from and `supersedes` pointing at the version it replaces.
- **No silent mutation.** Once locked, no attribute of the locked state may change in place. There is no "edit the locked object" operation.
- **Enforcement mechanism.** `smorx_contracts.versioning` provides `VersionedObject.lock()` and `VersionedObject.new_version()`. `lock()` permanently seals the current state and makes in-place mutation impossible; `new_version()` is the only path to a different state and it always yields a new identity.
- **Downstream references are version-tied.** Any object that references a locked object binds to that exact version id, so the reference can be traversed deterministically (for example Certificate → Claim → Behavioral Delta → Experiment → Execution Trace → Code/Environment).
- **Contract schemas are semver-versioned.** JSON Schema contract files under `packages/contracts/schemas/` carry semantic versions, and the ContractRegistry performs compatibility checks when a new schema version is registered (a breaking field removal or rename must be a major-version change).

## Consequences

### Positive
- Trust properties hold structurally: a certificate cannot be attached to a mutated account of intent or verification evidence.
- The full version history of a locked object remains inspectable, supporting failure archaeology and behavioral memory.
- Parallel reference readers never observe torn or changing state because each reference pins an exact version.
- Enforcing immutability in the shared contract layer means both Python and future TypeScript consumers inherit the rule.

### Negative / Trade-offs
- Creating a new version is more ceremony than mutating, so some workflows require an explicit "intent to version" step.
- The version trail grows over time and must be queried with the right version id to avoid misreading history as truth.
- Compatibility checks in the registry add a constraint on schema evolution that must be handled deliberately.
- The demo narrative must avoid implying that "updating intent" is the same as "correcting history"; a documented new version is the only legal path.

## Rejected alternatives

- **Mutable locked objects (edits allowed, change history logged).** Rejected: it makes the historical object depend on the integrity of a change log rather than the object identity itself, and it blurs the line between a new version and a mutation.
- **Copy-on-write with the same id.** Rejected: keeping the same identity across changes silently breaks every downstream reference and certificate binding; identity must change with version to keep the evidence traversal trustworthy.
- **No versioning — one canonical object per concept.** Rejected explicitly by the master invariants and the implementation plan: it makes "locked" meaningless because nothing would prevent later overwrite, and it fails Phase 0.5 and Phase 2.5 requirements.

## Verification

- Phase 0 baseline tests in `tests/unit` cover lock immutability: attempting to mutate a locked object raises.
- Versioning tests assert that `new_version()` yields a new id, incremented version, and correct `parent_version` / `supersedes` links, and that the old object remains unchanged.
- Registry compatibility tests register a schema at an incompatible version and assert the registry rejects it.
- The phase gate verifies that the versioning module imports and its behavior matches the contract before reporting PASS.