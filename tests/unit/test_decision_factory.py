from __future__ import annotations

import pytest

from cited_rag.adapters.decision import TypeSafeEvidenceDecisioner, create_decisioner
from cited_rag.config import Settings


def test_decision_factory_returns_none_when_shadow_is_disabled() -> None:
    assert create_decisioner(Settings(_env_file=None)) is None


def test_decision_factory_builds_typesafe_adapter_when_enabled() -> None:
    decisioner = create_decisioner(
        Settings(_env_file=None, jev_shadow_enabled=True, jev_api_key="test-key")
    )
    assert isinstance(decisioner, TypeSafeEvidenceDecisioner)


def test_decision_factory_rejects_missing_key() -> None:
    with pytest.raises(ValueError, match="JEV_API_KEY"):
        Settings(_env_file=None, jev_shadow_enabled=True)
