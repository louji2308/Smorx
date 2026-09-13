# Phase 1 — Nebius + NVIDIA Infrastructure Layer

Phase 1 of the Software Evolution Intelligence System delivers the **Nebius and NVIDIA infrastructure layer** for the Track 1 (tools/agents) submission. It is implemented as `apps/api` (FastAPI) and is the execution backbone that later phases (agent runtime, verification, certification) build upon.

Scope of this document:

- What Phase 1 provides
- Architecture and modules
- Configuration contract (environment variables)
- Live verification evidence
- Known limitations and remaining work

---

## What Phase 1 provides

The infrastructure layer exposes two real provider adapters behind typed ports and a small runtime that proves the full path end to end:

| Capability | Provider | Real integration |
|---|---|---|
| Model inference (OpenAI-compatible chat, model catalog, retry policy) | Nebius Token Factory | Yes — live model catalog + chat verified 2026-09-13 |
| Sandboxed code execution (git-branchable state, checkpoints, rollback) | Nebius ConTree (`contree_sdk`) | Credentialed + API authenticated; permission grant pending (see Limitations) |
| Nemotron model routing (nano / super / ultra tiers) | NVIDIA Nemotron via Token Factory | Yes — all three configured model IDs verified on-platform |
| Health + proof endpoints (`/api/v1/infra/*`) | FastAPI | Yes — live over uvicorn |

The invariants this layer enforces:

- **No mocks in production paths** — both providers are wired through the real SDKs (`openai`, `contree_sdk`).
- **No evidence, no success** — `machine_verifiable` is evidence-bound: `model_participated` requires the exact `INFRA_OK` token, `execution_authoritative` requires `exit_code == 0` with `SUCCEEDED`.
- **Failures are observable** — every failure path returns a classified error (configuration / infrastructure categories) with a consistent JSON envelope.
- **Secrets never leave the sandbox** — key material is redacted in logs, errors, and detail payloads.

---

## Architecture

```
apps/api/
├── app/
│   ├── api/routes.py            # /, /health, /api/v1/infra/status, POST /api/v1/infra/proof
│   ├── contracts.py             # typed port payloads (ModelRequest/Response, Sandbox, Checkpoint, …)
│   ├── deps.py                  # dependency wiring (Settings, AgentRuntime, ProofPathService)
│   ├── errors.py                # ConfigurationError, InfrastructureError + category model
│   ├── main.py                  # FastAPI app factory (docs gated off in production)
│   ├── observability.py         # TraceContext, log_event, redact_secrets
│   ├── runtime/
│   │   ├── service.py           # AgentRuntime.health() — fuses provider reports
│   │   └── proof.py             # ProofPathService — real inference → real sandbox → verdict
│   ├── model/
│   │   ├── router.py            # Nemotron tier routing (nano/super/ultra)
│   │   └── nemotron.py          # OpenAI-compatible chat completion wrapper
│   └── providers/
│       ├── token_factory/
│       │   ├── client.py        # Token Factory OpenAI-compatible client
│       │   └── retry.py         # transient-only RetryPolicy (provider/timeout/rate-limit)
│       └── sandbox/
│           ├── port.py          # SandboxExecutionPort (abstract surface)
│           └── adapter.py       # ContreeSandboxAdapter — real contree_sdk binding
├── tests/                       # 109 offline tests (no network)
└── pyproject.toml               # ruff/mypy-strict/pytest config
```

### Ports & adapters

Both providers are consumed behind typed ports so test doubles are explicit and production wiring is unambiguous:

- `ModelPort` → `TokenFactoryClient` (real) / `FakeTokenFactoryClient` (tests)
- `SandboxExecutionPort` → `ContreeSandboxAdapter` (real) / `FakeSandbox` (tests)

`ContreeSandboxAdapter` (`app/providers/sandbox/adapter.py`) maps ConTree primitives:

| Port operation | ConTree mapping |
|---|---|
| `create_sandbox` | `images.use(base_image)` (lazy handle) |
| `run_command` | `image.run(...).wait()` (durable child state when `disposable=False`) |
| `read_file` / `write_file` / `list_files` | `image.read / apply_files / ls` |
| `checkpoint` | durable `shell="true"` run → immutable server state uuid |
| `rollback` | `images.use(checkpoint_id)` |
| `destroy` | local handle discard (server keeps durable states until GC) |

---

## Configuration contract

Copy `apps/api/.env.example` to `apps/api/.env` and fill real values. `.env` is gitignored — never commit it.

| Variable | Purpose |
|---|---|
| `NEBIUS_API_KEY` | Token Factory API key (create at https://tokenfactory.nebius.com/project/api-keys). Used for **both** inference and ConTree sandbox IAM auth. |
| `NEBIUS_AI_PROJECT` / `NEBIUS_PROJECT_ID` | ConTree project id (aliases; `nebius_project` prefers `NEBIUS_AI_PROJECT`). Required for sandbox namespace scoping. |
| `NEBIUS_INFERENCE_BASE_URL` | `https://api.tokenfactory.nebius.com/v1` |
| `CONTREE_BASE_URL` | `https://api.tokenfactory.nebius.com/sandboxes` |
| `NEMOTRON_MODEL_NANO/_SUPER/_ULTRA` | Nemotron model IDs for the three routing tiers (verified on-platform, see below) |
| `MODEL_TIMEOUT_SECONDS`, `MODEL_MAX_RETRIES`, `MODEL_RETRY_BACKOFF_FACTOR` | Inference timeouts / retry budget |
| `SANDBOX_TIMEOUT_SECONDS`, `COMMAND_TIMEOUT_SECONDS`, `SANDBOX_POLL_SECS`, `OUTPUT_TRUNCATE_AT` | Sandbox execution policy |
| `APP_ENV` | `development` (docs/OpenAPI on) or `production` (docs gated off) |
| `INFRA_CHECK_ON_STARTUP` | `1` to run integration health checks at startup |

### Verified model IDs (confirmed on-platform 2026-09-13)

- `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` (nano tier)
- `nvidia/nemotron-3-super-120b-a12b` (super tier)
- `nvidia/Nemotron-3-Ultra-550b-a55b` (ultra tier)

---

## Endpoints

| Method | Path | Behavior |
|---|---|---|
| GET | `/` | Service identity (`{name, phase, version}`) |
| GET | `/health` | Liveness (`{"status":"ok"}`) |
| GET | `/api/v1/infra/status` | Fused provider health: inference (models verified) + sandbox (probe image `python:3.11-slim`) |
| POST | `/api/v1/infra/proof` | Full proof path — real Nemotron inference returning `INFRA_OK` **and** real sandbox execution returning `INFRA_OK`; `machine_verifiable` only true when both pieces of evidence exist |

Error envelope (503 configuration / 502 infrastructure): `{category, message, detail, remediation}`.

---

## Quality gates

| Gate | Command | Status |
|---|---|---|
| Unit tests | `pytest tests` (from `apps/api`) | 109 passed (2026-09-13) |
| Lint | `ruff check app tests` | All checks passed |
| Types | `mypy --strict --explicit-package-bases app tests` | Success (33 files) |
| Runtime | Live uvicorn `:8099` | `/health` 200, `/api/v1/infra/status` clean, proof path exercised |

The test suite is fully offline (no network). A fixture (`tests/conftest.py`) **isolates credentials**: it clears `Settings` cache, disables `.env` file loading, and removes `NEBIUS_*`/`CONTREE_*` env vars so real credentials in `apps/api/.env` never leak into tests.

### Proof-path logic (evidence binding)

`ProofPathService` executes in order:

1. **Model step** — Nemotron nano-tier chat completion; `machine_verifiable` requires the model to return exactly `INFRA_OK`.
2. **Sandbox step** — create sandbox from `python:3.11-slim`, run a command; `execution_authoritative` requires `exit_code == 0` and `ExecutionStatus.SUCCEEDED`.
3. **Fusion** — `machine_verifiable` is the conjunction of both predicates. No assertion is accepted without its corresponding execution evidence.

---

## Live verification evidence (2026-09-13)

### Inference — PROVEN (two live passes)

Live `GET /api/v1/infra/status` against the running server returned:

```json
{"inference": {"configured": true, "provider": "nebius_token_factory",
  "status": "healthy", "latency_ms": 15672, "models_verified": [<23 models>]}}
```

All three configured Nemotron tiers were confirmed present on-platform, alongside 20 additional supported models.

Direct inference through the proof-path client (`TokenFactoryClient.chat_completion` on `NEMOTRON_MODEL_NANO`), 2026-09-13:

```
MODEL_EXIT  '\nINFRA_OK'          → model_participated = True (exact token after strip().upper())
FINISH      stop
USAGE       prompt=27 completion=42 total=69
DURATION_MS 4858
```

### Sandbox — credential authenticated, permission blocked

- `configured: true` — the API key and project id resolve and the ConTree API authenticates the IAM pair.
- `get_token_info()` returned all sandbox permissions `false`: `import`, `spawn`, `spawn_disposable`, `list`, `cancel`, `set_image_tag`.
- `POST /api/v1/infra/proof` sandbox stage failed with `502 sandbox_execution_failure` / `ForbiddenError: You do not have permission to perform this action` — the token authenticates but the service account lacks the ConTree sandbox role on the configured project.

**Required user action:** grant the ConTree sandbox permission for the API key (its service account) on project `tenantuseraccount-e00kh2mwenymgpmm2v`, then re-run the sandbox stage. The system cannot escalate its own grants.

Verified again with a **second key** (service account `serviceaccount-e00jsbrfza9s5jr4dn`, token `ed70870e-…`, 2026-09-13 11:03Z expiration): inference healthy (24 models served, all Nemotron tiers present) but `get_token_info()` still returns all six sandbox permissions `false`. The grant must be attached to the service account / project in the console — none of the issued keys so far carries it.

---

## Known limitations & remaining work

1. **Sandbox execution permission (blocked on console grant)** — inference is fully verified; sandbox execution needs the ConTree sandbox role on the project.
2. **Token lifetime** — both API keys used during verification were short-lived (~15–30 min; expired 10:52Z and 11:03Z, 2026-09-13). A longer-lived key is recommended for continued development/demo.
3. **PostgreSQL** — the behavioral data model (Phase 2) has PG-targeted DDL in migration `4be282d73a12`, but real-PostgreSQL verification still needs a Supabase `DATABASE_URL` (SQLite was the user-confirmed test-first approach).
4. **Base image import** — `python:3.11-slim` availability is only decidable once sandbox permissions grant image probing; the health probe reports `DEGRADED` (not `UNHEALTHY`) if the image is reachable but not yet imported.

---

## Related documents

- `IMPLEMENTATION_PLAN.md` — Phase 1 scope and exit gate
- `docs/adr/ADR-README.md` — engineering decision record index
- `docs/README.md` — documentation index
- Root `README.md` — repository overview