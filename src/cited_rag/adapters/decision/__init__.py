from cited_rag.adapters.decision.typesafe import TypeSafeEvidenceDecisioner
from cited_rag.config import Settings
from cited_rag.ports.decision import EvidenceDecisioner


def create_decisioner(settings: Settings) -> EvidenceDecisioner | None:
    if not settings.jev_shadow_enabled:
        return None
    if settings.jev_api_key is None:
        raise ValueError("CITED_RAG_JEV_API_KEY is required for shadow mode")
    return TypeSafeEvidenceDecisioner(
        base_url=settings.jev_base_url,
        api_key=settings.jev_api_key.get_secret_value(),
        model=settings.jev_model,
        timeout_seconds=settings.jev_timeout_seconds,
    )


__all__ = ["TypeSafeEvidenceDecisioner", "create_decisioner"]
