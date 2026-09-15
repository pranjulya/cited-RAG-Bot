from __future__ import annotations

from pathlib import Path


def test_compose_defines_required_services() -> None:
    text = Path("docker-compose.yml").read_text(encoding="utf-8")
    for name in ("postgres", "redis", "qdrant", "migrate", "api", "worker", "web"):
        assert f"{name}:" in text
    assert '"8080:80"' in text
    assert '"5433:5432"' in text
    assert "127.0.0.1:8000/health" in text
    assert "b'arq'" in text


def test_ci_runs_unit_and_integration() -> None:
    text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "pytest tests/unit" in text
    assert "pytest tests/integration" in text
    assert "python -m cited_rag.evaluation" in text
    assert "docker compose up" in text
    assert "grep -i healthy" in text
    assert "working-directory: web" in text
    assert "localhost:8080" in text


def test_qdrant_client_is_pinned_to_server_minor() -> None:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "qdrant-client>=1.13.0,<1.14.0" in text
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "qdrant/qdrant:v1.13.6" in compose


def test_readme_documents_bearer_auth() -> None:
    text = Path("README.md").read_text(encoding="utf-8")
    assert "Authorization: Bearer replace-me" in text
    assert "localhost:5433" in text
