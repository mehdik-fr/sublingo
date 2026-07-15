from app.core.config import Settings
from app.providers.base import AnalysisProvider
from app.providers.ollama import OllamaAnalysisProvider


def create_analysis_provider(settings: Settings) -> AnalysisProvider:
    if settings.analysis_provider == "ollama":
        return OllamaAnalysisProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
        )

    raise ValueError(f"Unsupported analysis provider: {settings.analysis_provider}")
