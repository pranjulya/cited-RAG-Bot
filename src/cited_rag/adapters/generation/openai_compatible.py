from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from urllib.request import Request, urlopen

from cited_rag.domain.enums import AnswerStatus
from cited_rag.domain.exceptions import GenerationError
from cited_rag.domain.models.generation import Claim, GenerationPrompt, GroundedGenerationResult


class OpenAICompatibleGroundedGenerator:
    """Small stdlib adapter for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        if not api_key.strip():
            raise ValueError("CITED_RAG_GENERATION_API_KEY is required for hosted generation")

    async def generate(self, prompt: GenerationPrompt) -> GroundedGenerationResult:
        try:
            payload = await asyncio.to_thread(self._request, prompt)
            return self._parse(payload)
        except GenerationError:
            raise
        except Exception as exc:
            raise GenerationError("hosted generation failed") from exc

    def _request(self, prompt: GenerationPrompt) -> Mapping[str, object]:
        body = json.dumps(
            {
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": prompt.system},
                    {
                        "role": "user",
                        "content": (
                            f"Question:\n{prompt.question}\n\n"
                            f"Evidence JSON:\n{prompt.evidence_json}"
                        ),
                    },
                ],
            }
        ).encode()
        request = Request(
            self._endpoint(),
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            parsed = json.loads(response.read())
        if not isinstance(parsed, dict):
            raise GenerationError("hosted response was not an object")
        return parsed

    def _endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def _parse(self, payload: Mapping[str, object]) -> GroundedGenerationResult:
        try:
            choices = payload["choices"]
            assert isinstance(choices, list)
            first = choices[0]
            assert isinstance(first, dict)
            message = first["message"]
            assert isinstance(message, dict)
            content = message["content"]
            if not isinstance(choices, list) or not choices:
                raise TypeError("choices is not a non-empty list")
            first = choices[0]
            if not isinstance(first, dict):
                raise TypeError("choice is not an object")
            message = first.get("message")
            if not isinstance(message, dict):
                raise TypeError("message is not an object")
            content = message.get("content")
            if not isinstance(content, str):
                raise TypeError("content is not text")
            result = json.loads(content)
            if not isinstance(result, dict):
                raise TypeError("content is not an object")
            status = AnswerStatus(str(result.get("status")))
            answer = result.get("answer")
            if not isinstance(answer, str):
                raise TypeError("answer is not text")
            raw_claims = result.get("claims", [])
            if not isinstance(raw_claims, list):
                raise TypeError("claims is not a list")
            claims = tuple(self._claim(item) for item in raw_claims)
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise GenerationError("hosted response was malformed") from exc

        usage = payload.get("usage")
        usage_map = usage if isinstance(usage, dict) else {}
        return GroundedGenerationResult(
            status=status,
            answer=answer,
            claims=claims,
            model=self.model,
            input_tokens=self._token_count(usage_map.get("prompt_tokens")),
            output_tokens=self._token_count(usage_map.get("completion_tokens")),
        )

    @staticmethod
    def _claim(raw: object) -> Claim:
        if not isinstance(raw, dict):
            raise TypeError("claim is not an object")
        text = raw.get("text")
        if not isinstance(text, str):
            raise TypeError("claim text is not text")
        raw_ids = raw.get("evidence_ids", ())
        if not isinstance(raw_ids, (list, tuple)):
            raise TypeError("claim evidence_ids is not a list")
        return Claim(text=text, evidence_ids=tuple(str(item) for item in raw_ids))

    @staticmethod
    def _token_count(value: object) -> int | None:
        return value if isinstance(value, int) else None
