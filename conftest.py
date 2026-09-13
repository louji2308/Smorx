"""Root pytest configuration for the Software Evolution Intelligence System.

Defensively places the parallel-package src trees and the governance scripts
on ``sys.path`` so root-level test runs can import ``smorx_contracts``,
``smorx_runtime``, ``smorx_behavior``, and the ``scripts`` modules
(``env_check``, ``phase_gate``) without a prior ``pip install``.

This module never imports any project package at collection time; it only
mutates ``sys.path``. Individual tests must import the packages lazily inside
functions when they are not required unconditionally.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent

_PYTHON_PATH_ENTRIES = (
    _ROOT / "packages" / "contracts" / "src",
    _ROOT / "packages" / "agent-runtime" / "src",
    _ROOT / "packages" / "behavior" / "src",
    _ROOT / "scripts",
)

for _entry in _PYTHON_PATH_ENTRIES:
    _encoded = str(_entry)
    if _encoded not in sys.path and _entry.exists():
        sys.path.insert(0, _encoded)
