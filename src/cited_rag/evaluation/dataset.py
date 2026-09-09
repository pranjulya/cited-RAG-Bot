from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class GoldenCase:
    id: str
    question: str
    answerable: bool
    relevant_texts: tuple[str, ...]
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GoldenDataset:
    version: str
    cases: tuple[GoldenCase, ...]


def load_golden_dataset(path: Path) -> GoldenDataset:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if "version" not in payload or "cases" not in payload:
        raise ValueError("golden dataset must include version and cases")
    cases: list[GoldenCase] = []
    for raw in payload["cases"]:
        if "id" not in raw or "question" not in raw:
            raise ValueError("golden case missing id or question")
        cases.append(
            GoldenCase(
                id=str(raw["id"]),
                question=str(raw["question"]),
                answerable=bool(raw.get("answerable", True)),
                relevant_texts=tuple(str(item) for item in raw.get("relevant_texts", ())),
                tags=tuple(str(item) for item in raw.get("tags", ())),
            )
        )
    return GoldenDataset(version=str(payload["version"]), cases=tuple(cases))
