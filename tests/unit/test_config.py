from __future__ import annotations

import pytest
from pydantic import ValidationError

from cited_rag.config import Settings, get_settings


def test_default_settings_do_not_require_production_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CITED_RAG_DATABASE_URL", raising=False)
    monkeypatch.delenv("CITED_RAG_REDIS_URL", raising=False)
    get_settings.cache_clear()
    settings = Settings(_env_file=None)
    assert settings.environment in {"development", "test", "production"}
    assert settings.debug is False
    assert settings.database_url is None


def test_unknown_setting_fails_clearly() -> None:
    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Settings(_env_file=None, not_a_real_setting="oops")  # type: ignore[call-arg]


def test_invalid_environment_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CITED_RAG_ENVIRONMENT", "staging")
    get_settings.cache_clear()
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_production_rejects_placeholder_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CITED_RAG_ENVIRONMENT", "production")
    monkeypatch.setenv("CITED_RAG_API_KEY", "replace-me")
    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="CITED_RAG_API_KEY"):
        Settings(_env_file=None)


def test_production_disables_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CITED_RAG_ENVIRONMENT", "production")
    monkeypatch.setenv("CITED_RAG_API_KEY", "not-a-placeholder")
    monkeypatch.setenv("CITED_RAG_DEBUG", "true")
    monkeypatch.setenv(
        "CITED_RAG_DATABASE_URL",
        "postgresql+asyncpg://cited_rag:cited_rag@localhost:5432/cited_rag",
    )
    monkeypatch.setenv("CITED_RAG_REDIS_URL", "redis://localhost:6379/0")
    get_settings.cache_clear()
    settings = Settings(_env_file=None)
    assert settings.debug is False
    assert settings.api_key is not None
    assert "not-a-placeholder" not in repr(settings)


def test_production_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CITED_RAG_ENVIRONMENT", "production")
    monkeypatch.setenv("CITED_RAG_API_KEY", "not-a-placeholder")
    monkeypatch.delenv("CITED_RAG_DATABASE_URL", raising=False)
    monkeypatch.delenv("CITED_RAG_REDIS_URL", raising=False)
    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="CITED_RAG_DATABASE_URL"):
        Settings(_env_file=None)
