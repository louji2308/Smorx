"""smorx_delta — Phase 10 Behavioral Delta & Intent.

Owns the behavioral-delta computation (ADDED/REMOVED/ALTERED/UNCHANGED/
UNEXPLAINED), intent alignment against the LOCKED intent ledger, the
certification-readiness decision, structured repair packages, and the
evidence-bound repair loop that produces Candidate Patch #2 while preserving
Candidate Patch #1 and the historical failure (F-183 / Ghost) evidence.

Every entry point is gated by :mod:`smorx_delta.handoff`: no decision runs
until the Phase 9 ``VerificationResult`` is COMPLETED (AGENTS.md §10, §17).
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType as _PythonModuleType
from typing import TYPE_CHECKING

__all__ = [
    "decision",
    "deltas",
    "handoff",
    "intent",
    "repair",
    "repair_loop",
]

if TYPE_CHECKING:
    from smorx_delta import (
        decision as decision,
    )
    from smorx_delta import (
        deltas as deltas,
    )
    from smorx_delta import (
        handoff as handoff,
    )
    from smorx_delta import (
        intent as intent,
    )
    from smorx_delta import (
        repair as repair,
    )
    from smorx_delta import (
        repair_loop as repair_loop,
    )


def __getattr__(name: str) -> _PythonModuleType:
    if name in __all__:
        module = importlib.import_module(f"smorx_delta.{name}")
        setattr(sys.modules[__name__], name, module)
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
