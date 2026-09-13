# Infrastructure - Docker

Reproducible local and CI environment for the Software Evolution Intelligence
System via Docker and devcontainer tooling.

## Current state

* `compose.dev.yml` provides a single PostgreSQL 16 service that mirrors the
  Supabase Postgres setup referenced in `Tech-stack.md`. It is NOT wired to
  any application code yet: neither `apps/api` (FastAPI) nor `apps/web`
  (Next.js) reads the local Postgres service at this time.
* Dockerfiles for `apps/api` and `apps/web` are not yet authored.
* No devcontainer definition exists yet.

This directory exists now to satisfy the Phase-0 structure gate
(`scripts/phase_gate.py` `REQUIRED_PATHS`) and to host the Docker-powered
local environment as implementation progresses.

## Planned additions

* `Dockerfile` for `apps/api` (FastAPI).
* `Dockerfile` for `apps/web` (Next.js).
* A devcontainer definition matching `Tech-stack.md` (Node/Python toolchains,
  plus sandbox/client tooling for sandbox-driven workflows).
* CI usage of the same images in `.github/workflows/ci.yml`.

## Usage (development Postgres only)

```text
docker compose -f infrastructure/docker/compose.dev.yml up -d
docker compose -f infrastructure/docker/compose.dev.yml down
```

The compose file reads environment placeholders with documented local
defaults. No secrets are committed; override values in your shell or a local
`.env` next to the compose file.

## Notes

* The local Postgres service mirrors Supabase behavior (Postgres on port
  5432) so persistence integration can be exercised locally before a real
  Supabase instance is bound.
* Nothing in this directory is deployed or provisioned in any environment.