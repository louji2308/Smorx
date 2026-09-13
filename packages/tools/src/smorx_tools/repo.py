"""Path-safe repository toolkit with attributable mutations.

Phase 4 ``smorx_tools.repo``: real read/write/create/delete confined to an
approved root, with an append-only, attributable mutation ledger so every
consequential mutation carries ``Task -> Decision -> Tool -> Result`` trace
fields (path, operation, writer, reason, timestamp).

Safety model: :class:`PathSafety` refuses any path whose ``resolve()`` lands
outside every approved root; :class:`RepositoryToolkit` routes every operation
through it, so traversal attempts raise :class:`PathSafetyError` before a single
mutation record is appended.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import KW_ONLY, dataclass, field
from datetime import UTC, datetime
from pathlib import Path


class PathSafetyError(Exception):
    """Raised when a path resolves outside the approved roots (or is otherwise rejected)."""


class PathSafety:
    """Ensures every resolved path stays inside an approved root."""

    def __init__(self, *, roots: Sequence[Path]) -> None:
        self._roots: tuple[Path, ...] = tuple(root.resolve() for root in roots)

    def resolve(self, relative_or_absolute: str) -> Path:
        """Resolve a path and refuse any result outside the approved roots.

        Relative paths are anchored to the first approved root; absolute paths
        must already fall inside one of the roots.
        """
        resolved = self._resolve_candidate(relative_or_absolute)
        if not self._contained(resolved):
            raise PathSafetyError(
                f"path escapes approved roots: {relative_or_absolute!r} -> {resolved}"
            )
        return resolved

    def is_safe(self, candidate: str | Path) -> bool:
        """``True`` when the candidate resolves inside an approved root."""
        return self._contained(self._resolve_candidate(candidate))

    def _resolve_candidate(self, candidate: str | Path) -> Path:
        path = Path(candidate)
        if not path.is_absolute():
            base = self._roots[0] if self._roots else Path.cwd()
            path = base / path
        return path.resolve()

    def _contained(self, candidate: Path) -> bool:
        return any(candidate.is_relative_to(root) for root in self._roots)


@dataclass
class RepositoryToolkit:
    """Real read/write/create/delete with explicit attribution.

    Every consequential mutation is recorded in an append-only ledger with
    ``path`` / ``operation`` / ``writer`` / ``reason`` / ``at`` so the mutation
    is traceable (Task -> Decision -> Tool -> Result). When ``safety`` is
    omitted, a :class:`PathSafety` over the ``root`` alone is created.
    """

    root: Path
    safety: PathSafety | None = None
    _: KW_ONLY
    writer: str = ""
    reason: str = ""

    _safety: PathSafety = field(init=False, repr=False, compare=False)
    _mutations: list[dict[str, object]] = field(
        default_factory=list, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        self.root = self.root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        if self.safety is None:
            self._safety = PathSafety(roots=(self.root,))
        else:
            self._safety = self.safety

    def _record(self, *, path: str, operation: str, reason: str) -> None:
        self._mutations.append(
            {
                "path": path,
                "operation": operation,
                "writer": self.writer,
                "reason": reason if reason else self.reason,
                "at": datetime.now(UTC).isoformat(),
            }
        )

    def read(self, path: str) -> str:
        """Resolve safely and return the file contents as text."""
        resolved = self._safety.resolve(path)
        return resolved.read_text(encoding="utf-8")

    def exists(self, path: str) -> bool:
        """``True`` when the (safely resolved) path exists."""
        resolved = self._safety.resolve(path)
        return resolved.exists()

    def write(self, path: str, content: str, *, reason: str = "") -> str:
        """Create parents as needed, write, and record a ``write`` mutation."""
        resolved = self._safety.resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        self._record(path=str(resolved), operation="write", reason=reason)
        return str(resolved)

    def create(self, path: str, content: str = "", *, reason: str = "") -> str:
        """Create a file only if it does not already exist (else ``PathSafetyError``)."""
        resolved = self._safety.resolve(path)
        if resolved.exists():
            raise PathSafetyError(f"cannot create: file already exists: {resolved}")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        self._record(path=str(resolved), operation="create", reason=reason)
        return str(resolved)

    def delete(self, path: str, *, reason: str = "") -> str:
        """Delete a file, recording the mutation FIRST so attribution survives.

        Missing files raise ``PathSafetyError`` (idempotent-safe). A failed
        delete still appends a ``delete_error`` record before re-raising.
        """
        resolved = self._safety.resolve(path)
        if not resolved.exists():
            raise PathSafetyError(f"cannot delete missing path: {resolved}")
        try:
            self._record(path=str(resolved), operation="delete", reason=reason)
            resolved.unlink()
        except OSError:
            self._record(path=str(resolved), operation="delete_error", reason=reason)
            raise
        return str(resolved)

    def mutations(self) -> tuple[dict[str, object], ...]:
        """Append-only attributable mutation records in insertion order."""
        return tuple(self._mutations)

    def list_files(self, relative_base: str = "") -> tuple[str, ...]:
        """Files under ``relative_base`` (root when omitted), as posix-relative paths."""
        base = self.root if relative_base == "" else self._safety.resolve(relative_base)
        files = sorted(path for path in base.rglob("*") if path.is_file())
        return tuple(path.relative_to(base).as_posix() for path in files)
