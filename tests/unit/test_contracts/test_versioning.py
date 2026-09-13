"""Versioning helpers (ADR-0005): validation, bumps, compatibility, immutable keys."""

from __future__ import annotations

import pytest
from smorx_contracts import (
    bump_major,
    bump_minor,
    bump_patch,
    immutable_key,
    is_compatible,
    validate_version,
)


@pytest.mark.parametrize(
    "value",
    [
        "0.0.0",
        "1.0.0",
        "1.2.3",
        "10.20.30",
        "1.2.3-alpha.1",
        "1.2.3+build.5",
        "1.2.3-rc.1+build.2",
    ],
)
def test_validate_version_accepts_valid(value: str) -> None:
    assert validate_version(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "",
        "1",
        "1.2",
        "1.2.3.4",
        "01.2.3",
        "1.02.3",
        "1.2.03",
        "v1.2.3",
        "a.b.c",
        "1.2.3-",
    ],
)
def test_validate_version_rejects_invalid(value: str) -> None:
    assert validate_version(value) is False


def test_bump_major() -> None:
    assert bump_major("1.2.3") == "2.0.0"
    assert bump_major("0.4.0") == "1.0.0"


def test_bump_minor() -> None:
    assert bump_minor("1.2.3") == "1.3.0"
    assert bump_minor("0.0.0") == "0.1.0"


def test_bump_patch() -> None:
    assert bump_patch("1.2.3") == "1.2.4"
    assert bump_patch("9.9.9") == "9.9.10"


def test_bump_rejects_invalid_input() -> None:
    with pytest.raises(ValueError):
        bump_patch("not-semver")


def test_is_compatible_same_major() -> None:
    assert is_compatible("1.0.0", "1.2.3") is True
    assert is_compatible("1.2.3", "1.0.0") is True


def test_is_compatible_different_major() -> None:
    assert is_compatible("1.2.3", "2.0.0") is False
    assert is_compatible("2.0.0", "1.2.3") is False


def test_is_compatible_invalid_input() -> None:
    assert is_compatible("nope", "1.0.0") is False
    assert is_compatible("1.0.0", "nope") is False


def test_immutable_key_new_identity_semantics() -> None:
    assert immutable_key("claim-auth-017", "1.0.0") == "claim-auth-017@1.0.0"
    new_version = immutable_key("claim-auth-017", bump_minor("1.0.0"))
    assert new_version != immutable_key("claim-auth-017", "1.0.0")


def test_immutable_key_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        immutable_key("", "1.0.0")
    with pytest.raises(ValueError):
        immutable_key("id", "x.y.z")
