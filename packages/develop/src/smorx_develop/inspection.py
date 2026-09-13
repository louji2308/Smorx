"""Phase 8.3 — Structured Repository Inspection.

The Coding Agent must inspect structure, dependencies, tests,
configuration, and entry points before planning (master prompt §8.3).
Inspection results are structured and traceable: every file entry and
summary key is recorded and can be attached to the run's evidence.

The inspection is performed against a real filesystem root (in production
the sandbox checkout; in tests deterministic fixtures). It never invents
files: what is not on disk does not exist in the result.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = ["InspectionError", "InspectionResult", "inspect_repository"]

_IGNORED_DIRECTORIES: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        "dist",
        "build",
    }
)
_MAX_FILE_BYTES = 1_000_000
_MAX_FILES = 5_000


class InspectionError(Exception):
    """Raised when inspection cannot run against the given root."""


@dataclass(frozen=True)
class InspectionResult:
    """Structured, traceable inspection output for one repository root."""

    root: str
    entry_points: tuple[str, ...]
    dependencies: tuple[str, ...]
    config_files: tuple[str, ...]
    test_files: tuple[str, ...]
    source_files: tuple[str, ...]
    file_count: int
    summary: dict[str, Any]
    trace: tuple[dict[str, str], ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "entry_points": list(self.entry_points),
            "dependencies": list(self.dependencies),
            "config_files": list(self.config_files),
            "test_files": list(self.test_files),
            "source_files": list(self.source_files),
            "file_count": self.file_count,
            "summary": dict(self.summary),
            "trace": [dict(item) for item in self.trace],
        }


def _walk(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _IGNORED_DIRECTORIES)
        for filename in sorted(filenames):
            files.append(Path(current) / filename)
            if len(files) >= _MAX_FILES:
                return files
    return files


def _looks_like_entry_point(relative: str) -> bool:
    return (
        relative in {"main.py", "app.py", "manage.py", "wsgi.py", "asgi.py"}
        or relative.endswith(("__main__.py", "cli.py"))
        or relative in {"package.json", "pyproject.toml"}
    )


def _looks_like_config(relative: str) -> bool:
    name = relative.rsplit("/", 1)[-1]
    return name.startswith(".") or (
        name.endswith((".toml", ".ini", ".cfg", ".yaml", ".yml", ".json", ".lock"))
        and name not in {"package-lock.json"}
    )


def _looks_like_test(relative: str) -> bool:
    name = relative.rsplit("/", 1)[-1]
    return name.startswith("test_") or name.endswith("_test.py") or "/tests/" in relative


_SOURCE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".rb"}


def _parse_dependency_names(root: Path, files: list[Path]) -> tuple[str, ...]:
    names: set[str] = set()
    for path in files:
        relative = path.relative_to(root).as_posix()
        if relative == "pyproject.toml":
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith(('"', "'")) and any(
                    marker in stripped for marker in (">", "<", "==", "~=")
                ):
                    token = stripped.strip("\"', ")
                    if token:
                        names.add(token.split(";")[0].strip())
    return tuple(sorted(names))


def inspect_repository(root: str | Path) -> InspectionResult:
    """Inspect the real filesystem tree under ``root``.

    Raises :class:`InspectionError` when the root is not an existing
    directory. The result classifies files deterministically (entry
    points, dependencies, config, tests, sources) and carries a trace of
    every classification step for attribution.
    """
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise InspectionError(f"inspection root is not an existing directory: {root_path}")

    files = _walk(root_path)
    trace: list[dict[str, str]] = [
        {"step": "walk", "detail": f"{len(files)} files under {root_path}"}
    ]

    entry_points: list[str] = []
    dependencies: list[str] = []
    config_files: list[str] = []
    test_files: list[str] = []
    source_files: list[str] = []
    skipped_binary: int = 0

    for path in files:
        try:
            relative = path.relative_to(root_path).as_posix()
        except ValueError:  # pragma: no cover - walk is rooted at root_path
            continue
        if path.is_symlink() or not path.is_file():
            trace.append({"step": "skip", "detail": f"not a regular file: {relative}"})
            continue
        try:
            if path.stat().st_size > _MAX_FILE_BYTES:
                skipped_binary += 1
                trace.append({"step": "skip", "detail": f"oversized file: {relative}"})
                continue
        except OSError as exc:
            trace.append({"step": "skip", "detail": f"stat failed for {relative}: {exc}"})
            continue

        if _looks_like_entry_point(relative):
            entry_points.append(relative)
        if _looks_like_config(relative):
            config_files.append(relative)
        if _looks_like_test(relative):
            test_files.append(relative)
        if path.suffix in _SOURCE_EXTENSIONS and not _looks_like_test(relative):
            source_files.append(relative)

    dependencies = list(_parse_dependency_names(root_path, files))
    trace.append(
        {
            "step": "classify",
            "detail": (
                f"entry_points={len(entry_points)} config={len(config_files)} "
                f"tests={len(test_files)} sources={len(source_files)} deps={len(dependencies)}"
            ),
        }
    )

    summary = {
        "total_files": len(files),
        "source_files": len(source_files),
        "test_files": len(test_files),
        "config_files": len(config_files),
        "entry_points": len(entry_points),
        "skipped_oversized": skipped_binary,
        "has_tests": len(test_files) > 0,
        "has_manifest": any(f in {"pyproject.toml", "package.json"} for f in config_files),
    }
    return InspectionResult(
        root=str(root_path),
        entry_points=tuple(sorted(entry_points)),
        dependencies=tuple(dependencies),
        config_files=tuple(sorted(config_files)),
        test_files=tuple(sorted(test_files)),
        source_files=tuple(sorted(source_files)),
        file_count=len(files),
        summary=summary,
        trace=tuple(trace),
    )
