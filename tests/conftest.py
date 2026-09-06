"""Test environment must not require production secrets."""

from __future__ import annotations

import os

os.environ.setdefault("CITED_RAG_ENVIRONMENT", "test")
os.environ.setdefault("CITED_RAG_API_KEY", "test-placeholder-key")
os.environ.setdefault("CITED_RAG_DEBUG", "false")
