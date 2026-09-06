"""Typed environment settings. Later phases add fields as they need them."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvironmentName = Literal["development", "test", "production"]


class Settings(BaseSettings):
    """Runtime configuration loaded from `CITED_RAG_` environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="CITED_RAG_",
        extra="forbid",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
    )

    environment: EnvironmentName = "development"
    api_key: SecretStr | None = None
    log_level: str = "INFO"
    debug: bool = False
    correlation_id_header: str = Field(default="X-Correlation-ID")
    database_url: SecretStr | None = None

    @field_validator("debug")
    @classmethod
    def disable_debug_in_production(cls, value: bool, info: ValidationInfo) -> bool:
        environment = (info.data or {}).get("environment")
        if environment == "production":
            return False
        return value

    @model_validator(mode="after")
    def enforce_production_api_key(self) -> Self:
        if self.environment != "production":
            return self

        secret = self.api_key.get_secret_value() if self.api_key is not None else ""
        if not secret.strip() or secret.strip() == "replace-me":
            raise ValueError(
                "CITED_RAG_API_KEY must be set to a non-placeholder value when "
                "CITED_RAG_ENVIRONMENT=production"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
