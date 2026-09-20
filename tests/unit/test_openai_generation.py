from __future__ import annotations

import json
from collections.abc import Iterator
from uuid import uuid4

import pytest

from cited_rag.adapters.generation import create_generator, openai_compatible
from cited_rag.adapters.generation.openai_compatible import OpenAICompatibleGroundedGenerator
from cited_rag.application.citations import validate_citations
from cited_rag.application.context import serialize_model_evidence
from cited_rag.application.generation import generate_grounded_answer
from cited_rag.config import Settings
from cited_rag.domain.enums import AnswerStatus
from cited_rag.domain.exceptions import CitationValidationError, GenerationError
from cited_rag.domain.models.evidence import EvidencePackage, EvidenceRecord
from cited_rag.domain.models.generation import GenerationPrompt


class _FakeTransport:
    response_content = json.dumps(
        {
            "status": "ANSWERED",
            "answer": "Employees get 20 days of leave.",
            "claims": [{"text": "Employees get 20 days of leave.", "evidence_ids": ["E1"]}],
        }
    )
    delay_seconds = 0.0
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
        if cls.delay_seconds:
            import time

            time.sleep(cls.delay_seconds)
        body = json.dumps(
            {
                "choices": [{"message": {"content": cls.response_content}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 7},
            }
        ).encode()
        return _FakeResponse(body)


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


@pytest.fixture
def fake_transport(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    _FakeTransport.response_content = json.dumps(
        {
            "status": "ANSWERED",
            "answer": "Employees get 20 days of leave.",
            "claims": [{"text": "Employees get 20 days of leave.", "evidence_ids": ["E1"]}],
        }
    )
    _FakeTransport.delay_seconds = 0.0
    monkeypatch.setattr(openai_compatible, "urlopen", _FakeTransport.request)
    yield "http://fake/v1"


def _package() -> EvidencePackage:
    record = EvidenceRecord(
        evidence_id="E1",
        chunk_id=uuid4(),
        collection_id=uuid4(),
        document_id=uuid4(),
        document_version_id=uuid4(),
        document_name="handbook.pdf",
        page_start=3,
        page_end=3,
        text="Employees get 20 days of leave.",
    )
    return EvidencePackage(
        records=(record,),
        model_context=serialize_model_evidence((record,)),
        dropped_chunk_ids=(),
    )


@pytest.mark.asyncio
async def test_openai_compatible_generator_sends_grounded_json_request(fake_transport: str) -> None:
    generator = OpenAICompatibleGroundedGenerator(
        base_url=fake_transport,
        api_key="test-key",
        model="demo-model",
        timeout_seconds=1,
    )
    result = await generator.generate(
        GenerationPrompt(
            system="system",
            question="How much leave?",
            evidence_json='{"evidence":[]}',
        )
    )

    assert result.status is AnswerStatus.ANSWERED
    assert result.claims[0].evidence_ids == ("E1",)
    assert result.model == "demo-model"
    assert result.input_tokens == 12
    assert _FakeTransport.seen_headers["Authorization"] == "Bearer test-key"
    assert _FakeTransport.seen_body["model"] == "demo-model"


@pytest.mark.asyncio
async def test_missing_evidence_ids_still_fail_citation_validation(fake_transport: str) -> None:
    _FakeTransport.response_content = json.dumps(
        {"status": "ANSWERED", "answer": "unsupported", "claims": [{"text": "unsupported"}]}
    )
    try:
        result = await generate_grounded_answer(
            "question",
            _package(),
            generator=OpenAICompatibleGroundedGenerator(
                base_url=fake_transport,
                api_key="test-key",
                model="demo-model",
                timeout_seconds=1,
            ),
            timeout_seconds=1,
        )
        with pytest.raises(CitationValidationError):
            package = _package()
            validate_citations(result, package, collection_id=package.records[0].collection_id)
    finally:
        _FakeTransport.response_content = json.dumps(
            {
                "status": "ANSWERED",
                "answer": "Employees get 20 days of leave.",
                "claims": [{"text": "Employees get 20 days of leave.", "evidence_ids": ["E1"]}],
            }
        )


@pytest.mark.asyncio
async def test_invalid_hosted_json_is_generation_error(fake_transport: str) -> None:
    _FakeTransport.response_content = "not json"
    with pytest.raises(GenerationError, match="malformed"):
        await generate_grounded_answer(
            "question",
            _package(),
            generator=OpenAICompatibleGroundedGenerator(
                base_url=fake_transport,
                api_key="test-key",
                model="demo-model",
                timeout_seconds=1,
            ),
            timeout_seconds=1,
        )


def test_missing_hosted_key_fails_generator_creation() -> None:
    with pytest.raises(ValueError, match="GENERATION_API_KEY"):
        create_generator(Settings(_env_file=None, generation_backend="openai_compatible"))


@pytest.mark.asyncio
async def test_hosted_timeout_is_generation_error(fake_transport: str) -> None:
    _FakeTransport.delay_seconds = 0.2
    try:
        with pytest.raises(GenerationError):
            await generate_grounded_answer(
                "question",
                _package(),
                generator=OpenAICompatibleGroundedGenerator(
                    base_url=fake_transport,
                    api_key="test-key",
                    model="demo-model",
                    timeout_seconds=1,
                ),
                timeout_seconds=0.01,
            )
    finally:
        _FakeTransport.delay_seconds = 0.0
