from __future__ import annotations

from app.settings import Settings


def test_base_urls_have_trailing_slashes_stripped() -> None:
    s = Settings(
        nebius_inference_base_url="https://api.example.com/v1/",
        contree_base_url="https://api.example.com/sandboxes/",
    )
    assert s.nebius_inference_base_url == "https://api.example.com/v1"
    assert s.contree_base_url == "https://api.example.com/sandboxes"


def test_api_key_is_stripped() -> None:
    s = Settings(nebius_api_key="  sk-1234  ")
    assert s.nebius_api_key == "sk-1234"


def test_empty_api_key_stays_empty() -> None:
    s = Settings(nebius_api_key="   ")
    assert s.nebius_api_key == ""


def test_nebius_project_prefers_ai_project() -> None:
    s = Settings(nebius_ai_project="proj-a", nebius_project_id="proj-b")
    assert s.nebius_project == "proj-a"


def test_nebius_project_falls_back_to_project_id() -> None:
    s = Settings(nebius_project_id="proj-b")
    assert s.nebius_project == "proj-b"


def test_nebius_project_empty_without_any_value() -> None:
    assert Settings().nebius_project == ""


def test_has_inference_credentials() -> None:
    assert Settings(nebius_api_key="k").has_inference_credentials is True
    assert Settings().has_inference_credentials is False


def test_has_sandbox_credentials() -> None:
    assert (
        Settings(nebius_api_key="k", nebius_ai_project="p").has_sandbox_credentials
        is True
    )
    assert Settings(nebius_api_key="k").has_sandbox_credentials is False
    assert Settings(nebius_project_id="p").has_sandbox_credentials is False


def test_inference_credentials_error() -> None:
    assert Settings().inference_credentials_error() == "NEBIUS_API_KEY is not configured"
    assert Settings(nebius_api_key="k").inference_credentials_error() == ""


def test_sandbox_credentials_error() -> None:
    assert Settings().sandbox_credentials_error() == "NEBIUS_API_KEY is not configured"
    assert (
        Settings(nebius_api_key="k").sandbox_credentials_error()
        == "NEBIUS_AI_PROJECT (or NEBIUS_PROJECT_ID) is not configured"
    )
    assert Settings(nebius_api_key="k", nebius_ai_project="p").sandbox_credentials_error() == ""


def test_defaults_are_applied(settings: Settings) -> None:
    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.nebius_inference_base_url == "https://api.tokenfactory.nebius.com/v1"
    assert settings.contree_base_url == "https://api.tokenfactory.nebius.com/sandboxes"
    assert settings.nemotron_model_nano
    assert settings.nemotron_model_super
    assert settings.nemotron_model_ultra
    assert settings.model_timeout_seconds == 60.0
    assert settings.model_max_retries == 2
    assert settings.command_timeout_seconds == 120.0
    assert settings.infra_check_on_startup is False


def test_field_overrides(settings: Settings) -> None:
    s = Settings(
        app_env="test",
        log_level="ERROR",
        model_timeout_seconds=5.5,
        model_max_retries=1,
        sandbox_timeout_seconds=10.0,
        output_truncate_at=1024,
    )
    assert s.app_env == "test"
    assert s.log_level == "ERROR"
    assert s.model_timeout_seconds == 5.5
    assert s.model_max_retries == 1
    assert s.sandbox_timeout_seconds == 10.0
    assert s.output_truncate_at == 1024
