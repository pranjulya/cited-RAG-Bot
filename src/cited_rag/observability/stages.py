QUERY_STAGES = (
    "query.request",
    "query.access_check",
    "query.dense_retrieval",
    "query.sparse_retrieval",
    "query.fusion",
    "query.rerank",
    "query.context_build",
    "query.generation",
    "query.citation_validate",
)

INGEST_STAGES = (
    "ingest.parse",
    "ingest.chunk",
    "ingest.embed",
    "ingest.sparse",
    "ingest.ready",
)
