"""Semver versioning and immutability helpers (ADR-0005).

Contract schemas and locked objects are versioned with semantic versions.
This module provides the standalone, side-effect-free helpers used by the
``smorx_contracts`` package: validation, bumping, compatibility, and the
new-identity semantics expressed by ``immutable_key``.

stdlib only — no third-party imports.
"""

from __future__ import annotations

import re

__all__ = [
    "bump_major",
    "bump_minor",
    "bump_patch",
    "immutable_key",
    "is_compatible",
    "validate_version",
]

_SEMVER_RE = re.compile(
    r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def validate_version(value: str) -> bool:
    """Return ``True`` when ``value`` is a valid semantic version string."""
    return isinstance(value, str) and _SEMVER_RE.match(value) is not None


def _release_parts(value: str) -> tuple[int, int, int]:
    if not validate_version(value):
        raise ValueError(f"invalid semantic version: {value!r}")
    core = value.split("+", 1)[0].split("-", 1)[0]
    major, minor, patch = (int(part) for part in core.split("."))
    return major, minor, patch


def bump_major(value: str) -> str:
    """Return ``value`` with the major version incremented (2.3.4 -> 3.0.0)."""
    major, _, _ = _release_parts(value)
    return f"{major + 1}.0.0"


def bump_minor(value: str) -> str:
    """Return ``value`` with the minor version incremented (1.2.4 -> 1.3.0)."""
    major, minor, _ = _release_parts(value)
    return f"{major}.{minor + 1}.0"


def bump_patch(value: str) -> str:
    """Return ``value`` with the patch version incremented (1.2.3 -> 1.2.4)."""
    major, minor, patch = _release_parts(value)
    return f"{major}.{minor}.{patch + 1}"


def is_compatible(original: str, candidate: str) -> bool:
    """Return ``True`` when ``candidate`` is backward-compatible with ``original``.

    Per ADR-0005, a schema change that removes or renames a field is a
    breaking change and must bump the major version. Compatibility is
    therefore major-version equality.
    """
    if not validate_version(original) or not validate_version(candidate):
        return False
    return _release_parts(original)[0] == _release_parts(candidate)[0]


def immutable_key(identity: str, version: str) -> str:
    """Express new-identity semantics (ADR-0005): a new version implies a new identity.

    Locked objects cannot silently mutate; a different state is only reachable
    through a new version, which yields a distinct immutable key. The key binds
    the base identity to its exact version so downstream references pin the
    version they were created against.
    """
    if not identity:
        raise ValueError("identity must be a non-empty string")
    if not validate_version(version):
        raise ValueError(f"invalid semantic version: {version!r}")
    return f"{identity}@{version}"
