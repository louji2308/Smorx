# Unit tests

Fast, isolated component tests that run without external services or live
APIs. Every component should have at least one unit test that verifies
its public contract.

Governance unit tests owned by Subagent C:

- ``test_env_check.py`` – validates ``env_check`` public API under
  controlled ``environ`` dicts and temporary directory fixtures.
- ``test_phase_gate.py`` – exercises the pure helpers
  (``structure_checks``, ``finalize_phase0``) against fake repo
  structures without requiring the parallel packages to be present.

Run:
```bash
python -m pytest tests/unit -q
```