"""Deterministic demo seed package for the behavioral persistence layer.

Phase 2 (implementation plan, Integration Wave): a clearly-marked demo/scenario
fixture (Payments API / Change #184 / AUTH-017 / Ghost #221 / Failure F-183)
that proves the full lifecycle is representable and queryable without losing
ownership, version, provenance, or historical evidence. See
``smorx_behavior.seed.demo`` for the dataset documentation.
"""

from __future__ import annotations

from smorx_behavior.seed.demo import (
    EVIDENCE_BACKEND,
    SEED_NAMESPACE,
    DemoReport,
    build_seed,
    main,
)

__all__ = ["EVIDENCE_BACKEND", "SEED_NAMESPACE", "DemoReport", "build_seed", "main"]
