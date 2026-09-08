from __future__ import annotations

from dataclasses import dataclass

LEXICAL_ENCODER_NAME = "lexical_tf_v1"
LEXICAL_ENCODER_VERSION = "v1"
BM42_ENCODER_NAME = "fastembed-bm42"
BM42_MODEL = "Qdrant/bm42-all-minilm-l6-v2-attentions"


@dataclass(frozen=True, slots=True)
class SparseEncoderConfig:
    name: str = LEXICAL_ENCODER_NAME
    version: str = LEXICAL_ENCODER_VERSION

    def as_record(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version}

    @classmethod
    def for_backend(cls, backend: str) -> SparseEncoderConfig:
        if backend == "lexical":
            return cls(name=LEXICAL_ENCODER_NAME, version=LEXICAL_ENCODER_VERSION)
        if backend == "bm42":
            return cls(name=BM42_ENCODER_NAME, version=BM42_MODEL)
        raise ValueError(f"unsupported sparse encoder backend: {backend}")
