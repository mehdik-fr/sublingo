from app.core.config import Settings
from app.providers.base import AnalysisProvider
from app.providers.ollama import OllamaAnalysisProvider
from app.providers.vllm import VllmAnalysisProvider


def create_analysis_provider(settings: Settings) -> AnalysisProvider:
    if settings.analysis_provider == "ollama":
        return OllamaAnalysisProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
        )

    if settings.analysis_provider == "vllm":
        return VllmAnalysisProvider(
            base_url=settings.vllm_base_url,
            model=settings.vllm_model,
            revision=settings.vllm_revision,
            timeout_seconds=settings.vllm_timeout_seconds,
            max_tokens=settings.vllm_max_tokens,
            max_concurrency=settings.vllm_max_concurrency,
        )

    raise ValueError(f"Unsupported analysis provider: {settings.analysis_provider}")
