from collections.abc import Mapping
from dataclasses import dataclass
from os import environ

SUPPORTED_PROVIDERS = {"development", "argos", "ollama"}


@dataclass(frozen=True, slots=True)
class Settings:
    analysis_provider: str = "development"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout_seconds: float = 180.0

    @classmethod
    def from_environment(cls, values: Mapping[str, str] | None = None) -> "Settings":
        source = values if values is not None else environ
        provider = source.get("SUBLINGO_ANALYSIS_PROVIDER", "development").strip().lower()

        if provider not in SUPPORTED_PROVIDERS:
            supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
            raise ValueError(f"Unsupported analysis provider '{provider}'. Expected: {supported}")

        timeout_value = source.get("SUBLINGO_OLLAMA_TIMEOUT_SECONDS", "180")

        try:
            timeout_seconds = float(timeout_value)
        except ValueError as error:
            raise ValueError("SUBLINGO_OLLAMA_TIMEOUT_SECONDS must be numeric") from error

        if timeout_seconds <= 0:
            raise ValueError("SUBLINGO_OLLAMA_TIMEOUT_SECONDS must be greater than zero")

        return cls(
            analysis_provider=provider,
            ollama_base_url=source.get(
                "SUBLINGO_OLLAMA_BASE_URL",
                "http://127.0.0.1:11434",
            ).rstrip("/"),
            ollama_model=source.get("SUBLINGO_OLLAMA_MODEL", "qwen2.5:7b").strip(),
            ollama_timeout_seconds=timeout_seconds,
        )
