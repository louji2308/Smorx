# Security tests

Security-focused tests covering credential isolation, sandbox policy
enforcement, prompt/tool injection vectors, and dependency risk.

Key security invariants from ``Requirements & Contract.md`` sections
18–19 are exercised here.

Run:
```bash
python -m pytest tests/security -q
```