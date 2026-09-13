# Bootstrap the Software Evolution Intelligence System development environment.
# Creates a root .venv on Windows, installs the QA toolchain, and performs
# editable installs of the local Python packages when they are implemented.
#
# Usage:  powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1

param(
    [switch]$SkipPackages
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[bootstrap] creating root .venv (requires python 3.11)" -ForegroundColor Cyan
    python -m venv .venv
    if (-not $?) { throw "failed to create .venv" }
}

Write-Host "[bootstrap] upgrading pip" -ForegroundColor Cyan
& $VenvPython -m pip install --upgrade pip
if (-not $?) { throw "pip upgrade failed" }

Write-Host "[bootstrap] installing QA toolchain" -ForegroundColor Cyan
& $VenvPython -m pip install ruff mypy pytest pytest-asyncio pydantic pydantic-settings
if (-not $?) { throw "QA toolchain install failed" }

if (-not $SkipPackages) {
    foreach ($Package in @("packages/contracts", "packages/agent-runtime")) {
        $PyProject = Join-Path $Root "$Package\pyproject.toml"
        if (Test-Path $PyProject) {
            Write-Host "[bootstrap] editable install: $Package" -ForegroundColor Cyan
            & $VenvPython -m pip install -e $Package
            if (-not $?) { throw "editable install failed: $Package" }
        }
        else {
            Write-Host "[bootstrap] skip editable install: $Package (not implemented yet)"
        }
    }
}

Write-Host "[bootstrap] done. venv: $VenvPython" -ForegroundColor Green
Write-Host "[bootstrap] next: .venv\Scripts\python.exe scripts/quality_gate.py --skip-web"