from collections.abc import Mapping
from dataclasses import dataclass
from os import environ
from re import compile as compile_regex
from re import error as RegexError

SUPPORTED_PROVIDERS = {"ollama"}


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = "development"
    analysis_provider: str = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout_seconds: float = 180.0
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    )
    allowed_origin_regex: str | None = r"^chrome-extension://[a-p]{32}$"
    max_request_body_bytes: int = 256 * 1024

    @classmethod
    def from_environment(cls, values: Mapping[str, str] | None = None) -> "Settings":
        source = values if values is not None else environ
        environment = source.get("SUBLINGO_ENVIRONMENT", "development").strip().lower()

        if environment not in {"development", "staging", "production", "test"}:
            raise ValueError(
                "SUBLINGO_ENVIRONMENT must be development, staging, production, or test"
            )

        provider = source.get("SUBLINGO_ANALYSIS_PROVIDER", "ollama").strip().lower()

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

        max_body_value = source.get("SUBLINGO_MAX_REQUEST_BODY_BYTES", str(256 * 1024))

        try:
            max_request_body_bytes = int(max_body_value)
        except ValueError as error:
            raise ValueError("SUBLINGO_MAX_REQUEST_BODY_BYTES must be an integer") from error

        if max_request_body_bytes < 1024:
            raise ValueError("SUBLINGO_MAX_REQUEST_BODY_BYTES must be at least 1024")

        default_origins = (
            "http://127.0.0.1:8000,http://localhost:8000"
            if environment in {"development", "test"}
            else ""
        )
        allowed_origins = tuple(
            origin.strip().rstrip("/")
            for origin in source.get("SUBLINGO_ALLOWED_ORIGINS", default_origins).split(",")
            if origin.strip()
        )
        default_origin_regex = (
            r"^chrome-extension://[a-p]{32}$"
            if environment in {"development", "test"}
            else ""
        )
        allowed_origin_regex = (
            source.get("SUBLINGO_ALLOWED_ORIGIN_REGEX", default_origin_regex).strip() or None
        )

        if allowed_origin_regex is not None:
            try:
                compile_regex(allowed_origin_regex)
            except RegexError as error:
                raise ValueError("SUBLINGO_ALLOWED_ORIGIN_REGEX must be valid") from error

        if environment in {"staging", "production"}:
            if not allowed_origins:
                raise ValueError(
                    "SUBLINGO_ALLOWED_ORIGINS must contain the deployed extension origin"
                )

            if "*" in allowed_origins or allowed_origin_regex == ".*":
                raise ValueError("Wildcard CORS origins are forbidden outside development")

        return cls(
            environment=environment,
            analysis_provider=provider,
            ollama_base_url=source.get(
                "SUBLINGO_OLLAMA_BASE_URL",
                "http://127.0.0.1:11434",
            ).rstrip("/"),
            ollama_model=source.get("SUBLINGO_OLLAMA_MODEL", "qwen2.5:7b").strip(),
            ollama_timeout_seconds=timeout_seconds,
            allowed_origins=allowed_origins,
            allowed_origin_regex=allowed_origin_regex,
            max_request_body_bytes=max_request_body_bytes,
        )
