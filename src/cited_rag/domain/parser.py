from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ParsedPage:
    page_number: int
    raw_text: str
    normalized_text: str
    metadata: dict[str, Any]


def normalize_page_text(raw: str) -> str:
    """Collapse intra-line whitespace. Keep line breaks. Do not drop page identity."""
    lines = [" ".join(line.split()) for line in raw.replace("\r\n", "\n").split("\n")]
    return "\n".join(line for line in lines if line).strip()
