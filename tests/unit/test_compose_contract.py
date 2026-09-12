from __future__ import annotations

from pathlib import Path


def test_compose_defines_required_services() -> None:
    text = Path("docker-compose.yml").read_text(encoding="utf-8")
    for name in ("postgres", "redis", "qdrant", "migrate", "api", "worker"):
        assert f"{name}:" in text


def test_ci_runs_unit_and_integration() -> None:
    text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "pytest tests/unit" in text
    assert "pytest tests/integration" in text
    assert "python -m cited_rag.evaluation" in text
    assert "docker compose up" in text
