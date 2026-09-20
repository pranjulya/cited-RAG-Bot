from cited_rag.adapters.generation.heuristic import HeuristicGroundedGenerator
from cited_rag.adapters.generation.openai_compatible import OpenAICompatibleGroundedGenerator
from cited_rag.config import Settings
from cited_rag.ports.generation import GroundedGenerator


def create_generator(settings: Settings) -> GroundedGenerator:
    if settings.generation_backend == "heuristic":
        return HeuristicGroundedGenerator()
    if settings.generation_backend == "openai_compatible":
        if settings.generation_api_key is None:
            raise ValueError("CITED_RAG_GENERATION_API_KEY is required for hosted generation")
        return OpenAICompatibleGroundedGenerator(
            base_url=settings.generation_base_url,
            api_key=settings.generation_api_key.get_secret_value(),
            model=settings.generation_model,
            timeout_seconds=settings.generation_timeout_seconds,
        )
    raise ValueError(f"unsupported generation backend: {settings.generation_backend}")
