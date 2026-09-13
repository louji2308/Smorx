"""Unit tests for the ``env_check`` governance module.

These tests drive ``check_environment`` directly with injected environment
dicts and temporary repository roots; they never depend on the real process
environment, on the parallel packages, or on network access.
"""

from __future__ import annotations

from pathlib import Path

import env_check
import pytest


def _make_env_example(tmp_path: Path) -> None:
    config_dir = tmp_path / "apps" / "api"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / ".env.example").write_text("NEBIUS_API_KEY=\n", encoding="utf-8")


def test_development_missing_key_is_warning_only(tmp_path: Path) -> None:
    _make_env_example(tmp_path)
    report = env_check.check_environment(
        {"NEBIUS_API_KEY": ""}, app_env="development", repo_root=tmp_path
    )

    assert report.required_issues == []
    assert report.all_ok() is False
    key_issue = next(issue for issue in report.issues if issue.name == "NEBIUS_API_KEY")
    assert key_issue.ok is False
    assert key_issue.required is False
    assert report.environment == "development"


def test_production_missing_key_is_required(tmp_path: Path) -> None:
    _make_env_example(tmp_path)
    report = env_check.check_environment(
        {"APP_ENV": "production"}, app_env="production", repo_root=tmp_path
    )

    assert report.required_issues, (
        "production without credentials must produce required issues"
    )
    names = {issue.name for issue in report.required_issues}
    assert "NEBIUS_API_KEY" in names
    assert "NEBIUS_PROJECT" in names


def test_python_version_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _make_env_example(tmp_path)
    monkeypatch.setattr(env_check.sys, "version_info", (3, 10, 0, "final", 0))
    report = env_check.check_environment({}, app_env="development", repo_root=tmp_path)

    py_issue = next(issue for issue in report.issues if issue.name == "python")
    assert py_issue.ok is False
    assert py_issue.required is True


def test_python_version_ok_on_3_11(tmp_path: Path) -> None:
    _make_env_example(tmp_path)
    report = env_check.check_environment({}, app_env="development", repo_root=tmp_path)

    py_issue = next(issue for issue in report.issues if issue.name == "python")
    assert py_issue.ok is True
    assert py_issue.required is True


def test_check_tools_reports_git_and_python() -> None:
    report = env_check.check_tools()

    assert "git" in report.tools
    assert "python" in report.tools
    assert report.tools["git"].available is True
    assert report.tools["python"].available is True
    assert report.tools["python"].version


def test_extra_env_files_detection(tmp_path: Path) -> None:
    _make_env_example(tmp_path)
    deploy = tmp_path / "deploy.env.example"
    deploy.write_text("NEBIUS_API_KEY=\n", encoding="utf-8")

    report = env_check.check_environment(
        {}, app_env="development", repo_root=tmp_path, extra_env_files=(deploy,)
    )
    present = next(
        issue for issue in report.issues if issue.name == "env-file:deploy.env.example"
    )
    assert present.ok is True
    assert present.required is False

    deploy.unlink()
    report = env_check.check_environment(
        {}, app_env="development", repo_root=tmp_path, extra_env_files=(deploy,)
    )
    absent = next(
        issue for issue in report.issues if issue.name == "env-file:deploy.env.example"
    )
    assert absent.ok is False


def test_missing_config_surface_is_required(tmp_path: Path) -> None:
    report = env_check.check_environment({}, app_env="development", repo_root=tmp_path)

    surface = next(issue for issue in report.issues if issue.name == "config-surface")
    assert surface.ok is False
    assert surface.required is True
