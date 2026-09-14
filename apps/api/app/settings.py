from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_INFERENCE_BASE_URL = "https://api.tokenfactory.nebius.com/v1"
DEFAULT_CONTREE_BASE_URL = "https://api.tokenfactory.nebius.com/sandboxes"

DEFAULT_NANO_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
DEFAULT_SUPER_MODEL = "nvidia/nemotron-3-super-120b-a12b"
DEFAULT_ULTRA_MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")

    nebius_api_key: str = Field(default="")
    nebius_inference_base_url: str = Field(default=DEFAULT_INFERENCE_BASE_URL)
    nebius_ai_project: str = Field(default="")
    nebius_project_id: str = Field(default="")
    contree_base_url: str = Field(default=DEFAULT_CONTREE_BASE_URL)

    nemotron_model_nano: str = Field(default=DEFAULT_NANO_MODEL)
    nemotron_model_super: str = Field(default=DEFAULT_SUPER_MODEL)
    nemotron_model_ultra: str = Field(default=DEFAULT_ULTRA_MODEL)

    model_timeout_seconds: float = Field(default=60.0)
    model_max_retries: int = Field(default=2)
    model_retry_backoff_factor: float = Field(default=1.5)

    sandbox_timeout_seconds: float = Field(default=300.0)
    command_timeout_seconds: float = Field(default=120.0)
    sandbox_poll_secs: float = Field(default=2.0)
    sandbox_base_image: str = Field(default="python:3.11-slim")
    output_truncate_at: int = Field(default=65535)

    infra_check_on_startup: bool = Field(default=False)

    behavior_database_url: str | None = Field(default=None)
    behavior_auto_seed: bool = Field(default=True)

    @field_validator("nebius_api_key")
    @classmethod
    def strip_key(cls, v: str) -> str:
        return v.strip() if v else ""

    @field_validator("nebius_inference_base_url", "contree_base_url")
    @classmethod
    def strip_base_url(cls, v: str) -> str:
        return v.rstrip("/")

    @property
    def nebius_project(self) -> str:
        return self.nebius_ai_project or self.nebius_project_id

    @property
    def has_inference_credentials(self) -> bool:
        return bool(self.nebius_api_key)

    @property
    def has_sandbox_credentials(self) -> bool:
        return bool(self.nebius_api_key) and bool(self.nebius_project)

    def inference_credentials_error(self) -> str:
        if not self.nebius_api_key:
            return "NEBIUS_API_KEY is not configured"
        return ""

    def sandbox_credentials_error(self) -> str:
        if not self.nebius_api_key:
            return "NEBIUS_API_KEY is not configured"
        if not self.nebius_project:
            return "NEBIUS_AI_PROJECT (or NEBIUS_PROJECT_ID) is not configured"
        return ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
