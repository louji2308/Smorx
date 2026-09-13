# Test directories for the Software Evolution Intelligence System

Quality gates run from the repository root using the root ``pytest.ini``
and the root ``conftest.py``.

## Directory layout

| Directory       | Purpose                                                      |
|-----------------|--------------------------------------------------------------|
| ``unit/``       | Fast, isolated component tests (our ``env_check``, ``phase_gate``; plus other agents' unit tests as they land) |
| ``integration/``| Component-to-component tests (API ↔ runtime, contracts ↔ agent, etc.) |
| ``e2e/``        | Full-agent journey tests requiring the backend to be running |
| ``security/``   | Security-focused scans and policy verification               |
| ``evaluation/`` | Judging / evaluation metrics for the hackathon demo          |

## Running tests

```bash
# All unit tests
python -m pytest tests/unit -q

# Only the governance tests we own
python -m pytest tests/unit/test_env_check.py tests/unit/test_phase_gate.py -q

# Full suite (quality gate step)
python scripts/quality_gate.py --skip-web
```

## Import rules

- ``smorx_contracts`` and ``smorx_runtime`` are importable via ``pytest.ini``
  ``pythonpath`` and via the root ``conftest.py`` which defensively adds
  ``packages/*/src`` to ``sys.path``.
- Tests for scripts under ``scripts/`` can import the governance modules
  directly because ``conftest.py`` also places ``scripts/`` on ``sys.path``.
- Do **not** hardcode a ``pip install`` dependency on the parallel packages;
  use ``pytest.importorskip("smorx_contracts")`` when a test requires a
  package that may not yet exist in a parallel execution wave.