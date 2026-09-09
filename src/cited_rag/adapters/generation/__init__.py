from cited_rag.adapters.generation.heuristic import HeuristicGroundedGenerator
from cited_rag.config import Settings
from cited_rag.ports.generation import GroundedGenerator


def create_generator(settings: Settings) -> GroundedGenerator:
    if settings.generation_backend == "heuristic":
        return HeuristicGroundedGenerator()
    raise ValueError(f"unsupported generation backend: {settings.generation_backend}")
