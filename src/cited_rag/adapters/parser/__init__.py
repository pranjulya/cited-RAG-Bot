from __future__ import annotations

from cited_rag.ports.parser import DocumentParser


def create_document_parser(backend: str) -> DocumentParser:
    if backend == "pypdf":
        from cited_rag.adapters.parser.pypdf import PypdfDocumentParser

        return PypdfDocumentParser()
    if backend == "docling":
        from cited_rag.adapters.parser.docling import DoclingDocumentParser

        return DoclingDocumentParser()
    raise ValueError(f"unsupported parser backend: {backend}")
