# Documentation Index

This directory is the engineering documentation home for the **Software Evolution Intelligence System** (Nebius x NVIDIA Global AI Hackathon, Track 1).

## Purpose

Stable engineering decisions of the project are recorded as Architecture Decision Records (ADRs). ADRs capture *why* an architectural decision was made, the alternatives that were rejected, and how the decision is verified. They are authoritative for implementation behavior within the boundaries they describe.

The ADRs are the Phase 0 documentation deliverable referenced in `Project Spec/IMPLEMENTATION_PLAN.md` (Phase 0, "engineering ADRs").

## Governance and planning sources

- `Project Spec/` — the governing project documents (source of truth):
  - `Hackathon details.md`
  - `Final Demo Idea.md`
  - `Architecture Diagram.md`
  - `Requirements & Contract.md`
  - `Tech-stack.md`
  - `IMPLEMENTATION_PLAN.md`
- `AGENTS.md` — the agent operating constitution that applies to every engineering agent in this repository.
- `README.md` — repository-level readme at the repository root.
- `Progress.md` — the living engineering ledger at the repository root (created and maintained by the orchestrator; referenced here when present).

## Engineering documentation

- `ADR Index` — see `adr/README.md` for the table of accepted Architecture Decision Records.

## Reading order

1. `Project Spec/` governing documents and `AGENTS.md` for intent and operating rules.
2. `adr/README.md` for the record of accepted engineering decisions.
3. The individual ADRs for the reasoning, consequences, and verification approach of each decision.