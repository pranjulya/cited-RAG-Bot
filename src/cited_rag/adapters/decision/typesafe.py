from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from urllib.request import Request, urlopen

from cited_rag.domain.exceptions import DecisionProviderError
from cited_rag.domain.models.decision import EvidenceDecision
from cited_rag.domain.models.evidence import EvidencePackage


class TypeSafeEvidenceDecisioner:
    """Stdlib adapter for TypeSafe's System One Noul decision."""

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
            raise ValueError("CITED_RAG_JEV_API_KEY is required for shadow mode")

    async def decide(self, question: str, evidence: EvidencePackage) -> EvidenceDecision:
        try:
            payload = await asyncio.to_thread(self._request, question, evidence)
            return self._parse(payload)
        except DecisionProviderError:
            raise
        except Exception as exc:
            raise DecisionProviderError("typesafe decision provider failed") from exc

    def _request(self, question: str, evidence: EvidencePackage) -> Mapping[str, object]:
        body = json.dumps(
            {
                "state": {
                    "question": question,
                    "evidence": [
                        {"id": item.evidence_id, "text": item.text} for item in evidence.records
                    ],
                },
                "model": self.model,
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
            status = getattr(response, "status", 200)
            if status >= 400:
                raise DecisionProviderError("typesafe decision provider failed")
            parsed = json.loads(response.read())
        if not isinstance(parsed, dict):
            raise DecisionProviderError("typesafe decision response was malformed")
        return parsed

    def _endpoint(self) -> str:
        if self.base_url.endswith("/v1/systemone"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/systemone"
        return f"{self.base_url}/v1/systemone"

    def _parse(self, payload: Mapping[str, object]) -> EvidenceDecision:
        try:
            answers = payload["answers"]
            if not isinstance(answers, dict):
                raise TypeError("answers is not an object")
            answer = answers["answerable"]
            if not isinstance(answer, dict) or answer.get("type") != "noul":
                raise TypeError("answerable is not a Noul answer")
            probability = answer["noul"]
            if isinstance(probability, bool) or not isinstance(probability, (float, int)):
                raise TypeError("noul probability is not numeric")
            model = payload.get("model", self.model)
            if not isinstance(model, str):
                raise TypeError("model is not text")
            return EvidenceDecision(answerable_probability=float(probability), model=model)
        except (KeyError, TypeError, ValueError) as exc:
            raise DecisionProviderError("typesafe decision response was malformed") from exc
