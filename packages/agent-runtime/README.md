# smorx-runtime

Agent runtime for the **Software Evolution Intelligence System** (Nebius × NVIDIA Global AI Hackathon — Track 1).

This package contains the mandatory **agent state machine** and the
**bounded execution-loop controls**.  It depends only on the Python standard
library and pydantic v2 and has **no runtime dependency on any other project
package**.

---

## Modules

### `smorx_runtime.state`

The explicit, auditable agent state machine defined in *Requirements & Contract.md*
section 3.

```python
from smorx_runtime.state import AgentState, AgentStateMachine, TRANSITIONS
```

**States** (a `StrEnum`):

| State | Meaning |
|---|---|
| `CREATED` | Task exists; no code executed yet. |
| `INSPECTED` | Repository, files, tests, and environment understood. |
| `PLANNED` | Interpretation, strategy, and validation strategy exist. |
| `EXECUTING` | Agent is performing a concrete action. |
| `OBSERVED` | Action completed; machine-readable results exist. |
| `FAILED` | Expected condition not met. |
| `ITERATING` | Agent decides another action from observed evidence. |
| `VERIFIED` | All acceptance criteria have supporting evidence. |
| `BLOCKED` | Agent cannot safely continue. |

**Transition table** (`TRANSITIONS` dict — authoritative):

```
CREATED  → INSPECTED
INSPECTED → PLANNED
PLANNED  → EXECUTING
EXECUTING → OBSERVED | FAILED
OBSERVED → ITERATING | VERIFIED
FAILED   → ITERATING | BLOCKED
ITERATING → EXECUTING
VERIFIED → BLOCKED
BLOCKED  → (none)
```

Terminal states (`VERIFIED`, `BLOCKED`) can only leave through the single
allowed outgoing edge; `BLOCKED` has no outgoing edges.

### `smorx_runtime.loop_controls`

Validated, environment-overridable bounds for the autonomous agent execution
loop (*Requirements & Contract.md* section 10, LOOP-CONTRACT-01).

```python
from smorx_runtime.loop_controls import (
    LoopControls,
    NoProgressDetector,
    IterationBudget,
)
```

#### Development-safe defaults

| Field | Default |
|---|---|
| `max_iterations` | 25 |
| `max_runtime_seconds` | 7200.0 |
| `max_command_count` | 200 |
| `max_repair_attempts` | 5 |
| `no_progress_threshold` | 3 |
| `tool_timeouts_seconds` | `{"*": 120.0}` |
| `per_agent_timeout_seconds` | 1800.0 |
| `total_phase_timeout_seconds` | 14400.0 |

#### Production profile (`LoopControls.for_env("production")`)

Intentionally conservative — an uncontrolled loop is never acceptable in
production.

| Field | Production value |
|---|---|
| `max_iterations` | 8 |
| `max_runtime_seconds` | 1800.0 |
| `max_command_count` | 60 |
| `max_repair_attempts` | 2 |
| `no_progress_threshold` | 2 |
| `tool_timeouts_seconds` | `{"*": 60.0}` |
| `per_agent_timeout_seconds` | 600.0 |
| `total_phase_timeout_seconds` | 3600.0 |

---

## Environment overrides

All overrides use the `SMORX_LOOP_` prefix:

| Variable | Type |
|---|---|
| `SMORX_LOOP_MAX_ITERATIONS` | int ≥ 1 |
| `SMORX_LOOP_MAX_RUNTIME_SECONDS` | float > 0 |
| `SMORX_LOOP_MAX_COMMAND_COUNT` | int ≥ 1 |
| `SMORX_LOOP_MAX_REPAIR_ATTEMPTS` | int ≥ 0 |
| `SMORX_LOOP_NO_PROGRESS_THRESHOLD` | int ≥ 2 |
| `SMORX_LOOP_TOOL_TIMEOUTS_SECONDS` | JSON object (e.g. `{"run": 5.0}`) |
| `SMORX_LOOP_PER_AGENT_TIMEOUT_SECONDS` | float > 0 |
| `SMORX_LOOP_TOTAL_PHASE_TIMEOUT_SECONDS` | float > 0 |

Ordering constraints (`repair ≤ iterations`, `no_progress ≤ iterations`,
`per_agent ≤ total_phase`) are enforced when mixing base values with
environment overrides.  Invalid values raise `LoopControlError`.

---

## Development

This package lives under `packages/agent-runtime/` with a standard `src`
layout:

```
packages/agent-runtime/
├── pyproject.toml
├── README.md
└── src/
    └── smorx_runtime/
        ├── __init__.py
        ├── state.py
        └── loop_controls.py
```

### Tests

```bash
python -m pip install --no-build-isolation --no-deps -e packages/agent-runtime
python -m pytest tests/unit/test_state_machine.py tests/unit/test_loop_controls.py -q
```

### Linting

```bash
ruff check packages/agent-runtime tests/unit/test_state_machine.py tests/unit/test_loop_controls.py
ruff format --check packages/agent-runtime tests/unit/test_state_machine.py tests/unit/test_loop_controls.py
```

### Type checking

```bash
mypy packages/agent-runtime --strict --config-file packages/agent-runtime/pyproject.toml
```

The bundled pydantic v2 mypy plugin (`pydantic.mypy`) is configured in the
package `[tool.mypy]` section.  The `pydantic.v2.mypy` plugin path requires
the separate `pydantic-mypy` package; if it is installed the plugin name can
be swapped in `pyproject.toml`.
