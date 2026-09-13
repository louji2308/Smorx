# Evaluation tests

Metrics and evaluation harness for the hackathon demo journey.
These tests produce quantitative evidence for judging:

- agent-loop completion rate
- iteration count before verification
- execution trace completeness
- certificate provenance chain integrity
- time-to-verified-result

Run:
```bash
python -m pytest tests/evaluation -q
```