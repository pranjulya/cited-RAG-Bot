from __future__ import annotations

import json
from collections.abc import Iterator

import pytest

from cited_rag.adapters.decision import typesafe
from cited_rag.adapters.decision.typesafe import TypeSafeEvidenceDecisioner
from cited_rag.domain.exceptions import DecisionProviderError
from cited_rag.domain.models.evidence import EvidencePackage, EvidenceRecord


class _FakeResponse:
    status = 200

    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


class _FakeTransport:
    response_body = json.dumps(
        {
            "model": "typesafe/jev-1.13",
            "answers": {"answerable": {"type": "noul", "noul": 0.8}},
            "usage": {"input_tokens": 12, "output_tokens": 4},
        }
    ).encode()
    status = 200
    seen_headers: dict[str, str] = {}
    seen_body: dict[str, object] = {}

    @classmethod
    def request(cls, request: object, timeout: float) -> _FakeResponse:
        del timeout
        cls.seen_headers = {
            key: value
            for key, value in request.header_items()  # type: ignore[attr-defined]
        }
        cls.seen_body = json.loads(request.data.decode())  # type: ignore[attr-defined]
        response = _FakeResponse(cls.response_body)
        response.status = cls.status
        return response


@pytest.fixture
def fake_transport(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    _FakeTransport.response_body = json.dumps(
        {
            "model": "typesafe/jev-1.13",
            "answers": {"answerable": {"type": "noul", "noul": 0.8}},
            "usage": {"input_tokens": 12, "output_tokens": 4},
        }
    ).encode()
    _FakeTransport.status = 200
    monkeypatch.setattr(typesafe, "urlopen", _FakeTransport.request)
    yield "http://fake"


def _package() -> EvidencePackage:
    from uuid import uuid4

    record = EvidenceRecord(
        evidence_id="E1",
        chunk_id=uuid4(),
        collection_id=uuid4(),
        document_id=uuid4(),
        document_version_id=uuid4(),
        document_name="handbook.pdf",
        page_start=2,
        page_end=2,
        text="Employees receive 20 days of leave.",
    )
    return EvidencePackage(records=(record,), model_context="", dropped_chunk_ids=())


@pytest.mark.asyncio
async def test_typesafe_decisioner_maps_noul_and_sends_only_model_evidence(
    fake_transport: str,
) -> None:
    decisioner = TypeSafeEvidenceDecisioner(
        base_url=fake_transport,
        api_key="test-key",
        model="typesafe/jev-1.13",
        timeout_seconds=1,
    )

    result = await decisioner.decide("How much leave?", _package())

    assert result.answerable is True
    assert result.answerable_probability == 0.8
    assert result.model == "typesafe/jev-1.13"
    assert _FakeTransport.seen_headers["Authorization"] == "Bearer test-key"
    assert _FakeTransport.seen_body == {
        "state": {
            "question": "How much leave?",
            "evidence": [{"id": "E1", "text": "Employees receive 20 days of leave."}],
        },
        "model": "typesafe/jev-1.13",
        "questions": {
            "answerable": {
                "type": "noul",
                "instructions": "Does the evidence answer the question?",
                "criteria": {
                    "true": "The evidence directly supports an answer.",
                    "false": "The evidence does not support an answer.",
                },
            }
        },
    }


@pytest.mark.asyncio
async def test_malformed_typesafe_response_is_provider_error(fake_transport: str) -> None:
    _FakeTransport.response_body = b'{"answers": {}}'
    with pytest.raises(DecisionProviderError, match="malformed"):
        await TypeSafeEvidenceDecisioner(
            base_url=fake_transport,
            api_key="test-key",
            model="typesafe/jev-1.13",
            timeout_seconds=1,
        ).decide("question", _package())


@pytest.mark.asyncio
async def test_non_2xx_typesafe_response_is_provider_error(fake_transport: str) -> None:
    _FakeTransport.status = 503
    with pytest.raises(DecisionProviderError, match="failed"):
        await TypeSafeEvidenceDecisioner(
            base_url=fake_transport,
            api_key="test-key",
            model="typesafe/jev-1.13",
            timeout_seconds=1,
        ).decide("question", _package())


@pytest.mark.asyncio
async def test_typesafe_timeout_is_provider_error(
    fake_transport: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    del fake_transport

    def timeout(request: object, timeout: float) -> _FakeResponse:
        del request, timeout
        raise TimeoutError("socket timed out")

    monkeypatch.setattr(typesafe, "urlopen", timeout)
    with pytest.raises(DecisionProviderError, match="failed"):
        await TypeSafeEvidenceDecisioner(
            base_url="http://fake",
            api_key="test-key",
            model="typesafe/jev-1.13",
            timeout_seconds=1,
        ).decide("question", _package())


def test_missing_typesafe_key_fails_creation() -> None:
    with pytest.raises(ValueError, match="JEV_API_KEY"):
        TypeSafeEvidenceDecisioner(
            base_url="http://fake",
            api_key="",
            model="typesafe/jev-1.13",
            timeout_seconds=1,
        )
