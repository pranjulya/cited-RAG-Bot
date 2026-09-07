from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SparseEncoderConfig:
    name: str = "lexical_tf_v1"
    version: str = "v1"

    def as_record(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version}
