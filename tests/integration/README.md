# Integration tests

Component-to-component tests that exercise the boundary between two
real modules (e.g. API ↔ runtime, contracts ↔ orchestrator).

These tests require that the local packages are installed or available
on ``sys.path`` (the root ``pytest.ini`` ``pythonpath`` handles this).

Run:
```bash
python -m pytest tests/integration -q
```