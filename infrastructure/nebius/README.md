# Infrastructure - Nebius (Token Factory)

Reference and planning artifacts for the Nebius Token Factory integration
(sandboxes, serverless jobs, serverless endpoints) that will provide the real
execution and inference infrastructure for Track 1 of the Software Evolution
Intelligence System.

## Purpose

* Sandboxes (ConTree / Token Factory) are the intended code-execution
  environment for Track 1: the agent's tool actions run inside a disposable
  sandbox, and real execution results (exit codes, stdout/stderr, duration,
  artifacts) feed the evidence chain.
* Serverless jobs and serverless endpoints are the projected route for model
  routing across Nemotron tiers (smaller/faster against stronger) per
  `Tech-stack.md`.

## STATUS

NOT PROVISIONED. CREDENTIALS REQUIRED.

No Nebius credentials exist in this repository or in the local environment
yet. Until a credential set is provided and a provider adapter is bound:

* every operation on `smorx_tools.sandbox.SandboxControl` returns an explicit
  `UNAVAILABLE` result by design (see
  `packages/tools/src/smorx_tools/sandbox.py`) - the control never fabricates
  a fake sandbox success;
* the Token Factory inference provider reports its configured credentials
  error.

Nothing described in this directory is live, deployed, or authorized.

## Required credentials

Values must be supplied by the operator in the local `.env` (never committed).
Names only; the application reads them from the environment.

| Environment variable | Purpose | Required |
| -------------------- | ------- | -------- |
| `NEBIUS_API_KEY` | Token Factory API key (inference + sandboxes) | Yes |
| `NEBIUS_AI_PROJECT` | Project id scoping sandbox namespaces | Yes (or alias) |
| `NEBIUS_PROJECT_ID` | Alias accepted when `NEBIUS_AI_PROJECT` is empty | Alternative |
| `NEBIUS_INFERENCE_BASE_URL` | OpenAI-compatible inference base URL | For inference |
| `CONTREE_BASE_URL` | ConTree sandbox base URL | For sandboxes |

Current blocker: no real value supplied for `NEBIUS_API_KEY` and
`NEBIUS_AI_PROJECT`/`NEBIUS_PROJECT_ID`. See `apps/api/.env.example` for the
full configured set.

## Reference manifests

* `sandbox.example.json` - example sandbox lifecycle manifest (create,
  execute, checkpoint, rollback, destroy).
* `serverless-jobs.example.yaml` - example reference for a serverless job
  running a short Python payload.
* `serverless-endpoints.example.yaml` - example reference for a serverless
  endpoint routing to Nemotron via Token Factory.

All three are REFERENCE ONLY. They require credentials, and their API shapes
must be validated against the official Nebius Token Factory documentation
before any use.

## Binding plan

The future Nebius adapter will implement the structural
`smorx_tools.sandbox.SandboxPort` protocol (`create`, `inspect`, `execute`,
`checkpoint`, `rollback`, `destroy`, `health`) and will be attached through
`SandboxControl.bind(...)` at service startup, at which point sandbox
operations switch from `UNAVAILABLE` to provider-routed results. The same
plan applies to the Nemotron routing tiers configured by the `NEMOTRON_MODEL_*`
variables in `apps/api/.env.example`.