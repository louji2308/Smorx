"""smorx_verification — Phase 9 Independent Verification.

Six independent verification modules (static analysis, differential
execution, historical ghost replay, metamorphic checks, adversarial
scenarios, mutation testing), evidence collection, claim evidence fusion, a
trust boundary that prevents the verifier from inheriting Coding Agent
authority, and the verification runner that emits the Phase 9 -> Phase 10
``VERIFICATION_RESULT`` contract.

The management of the module registry lives in :mod:`smorx_verification.runner`;
lazy submodule resolution keeps import cost low and avoids heavyweight imports.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType as _PythonModuleType
from typing import TYPE_CHECKING

__all__ = [
    "adversarial",
    "boundary",
    "context",
    "contracts",
    "control_center",
    "differential",
    "evidence",
    "fusion",
    "ghost_replay",
    "metamorphic",
    "mutation",
    "runner",
    "static_analysis",
]

_LazyModules = tuple(__all__)

if TYPE_CHECKING:
    from smorx_verification import (
        adversarial as adversarial,
    )
    from smorx_verification import (
        boundary as boundary,
    )
    from smorx_verification import (
        context as context,
    )
    from smorx_verification import (
        contracts as contracts,
    )
    from smorx_verification import (
        control_center as control_center,
    )
    from smorx_verification import (
        differential as differential,
    )
    from smorx_verification import (
        evidence as evidence,
    )
    from smorx_verification import (
        fusion as fusion,
    )
    from smorx_verification import (
        ghost_replay as ghost_replay,
    )
    from smorx_verification import (
        metamorphic as metamorphic,
    )
    from smorx_verification import (
        mutation as mutation,
    )
    from smorx_verification import (
        runner as runner,
    )
    from smorx_verification import (
        static_analysis as static_analysis,
    )


def __getattr__(name: str) -> _PythonModuleType:
    if name in _LazyModules:
        module = importlib.import_module(f"smorx_verification.{name}")
        setattr(sys.modules[__name__], name, module)
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
