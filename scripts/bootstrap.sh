#!/usr/bin/env bash
# Bootstrap the Software Evolution Intelligence System development environment.
# Creates a root .venv, installs the QA toolchain, and performs editable
# installs of the local Python packages when they are implemented.
#
# Usage:  bash scripts/bootstrap.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_PY="$ROOT/.venv/bin/python"

if [ ! -x "$VENV_PY" ]; then
  echo "[bootstrap] creating root .venv (requires python 3.11)"
  python3 -m venv .venv
fi

echo "[bootstrap] upgrading pip"
"$VENV_PY" -m pip install --upgrade pip

echo "[bootstrap] installing QA toolchain"
"$VENV_PY" -m pip install ruff mypy pytest pytest-asyncio pydantic pydantic-settings

if [ "${SKIP_PACKAGES:-0}" != "1" ]; then
  for pkg in packages/contracts packages/agent-runtime; do
    if [ -f "$ROOT/$pkg/pyproject.toml" ]; then
      echo "[bootstrap] editable install: $pkg"
      "$VENV_PY" -m pip install -e "$pkg"
    else
      echo "[bootstrap] skip editable install: $pkg (not implemented yet)"
    fi
  done
fi

echo "[bootstrap] done. venv: $VENV_PY"
echo "[bootstrap] next: python scripts/quality_gate.py --skip-web"