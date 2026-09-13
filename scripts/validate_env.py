"""Thin CLI wrapper over ``env_check`` for shell/CI quality gates.

    python scripts/validate_env.py

Prints which environment is about to run (derived from ``APP_ENV`` /
``SMORX_APP_ENV``, defaulting to ``development``) and exits non-zero when any
*required* environment issue exists.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import env_check


def _declared_env() -> str:
    return os.environ.get("SMORX_APP_ENV") or os.environ.get("APP_ENV") or "development"


def main() -> int:
    app_env = _declared_env()
    report = env_check.check_environment(os.environ, app_env=app_env)
    print(f"[validate_env] validating repository for environment '{app_env}'")
    print(report.summary())
    if report.required_issues:
        print("[validate_env] REQUIRED issues present - environment invalid")
        return 1
    print("[validate_env] OK - no required issues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
