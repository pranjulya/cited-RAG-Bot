from __future__ import annotations

from cited_rag.main import create_app


def test_application_imports_and_factory_creates_app() -> None:
    app = create_app()
    assert app.title == "Cited RAG Bot"
    assert app.debug is False
