from collections.abc import Mapping
from dataclasses import dataclass
from os import environ
from re import compile as compile_regex
from re import error as RegexError

SUPPORTED_PROVIDERS = {"ollama", "vllm"}


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = "development"
    analysis_provider: str = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout_seconds: float = 180.0
    vllm_base_url: str = "http://127.0.0.1:8001"
    vllm_model: str = "Qwen/Qwen3.5-9B"
    vllm_revision: str | None = None
    vllm_timeout_seconds: float = 30.0
    vllm_max_tokens: int = 4_096
    vllm_max_concurrency: int = 2
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    )
    allowed_origin_regex: str | None = r"^chrome-extension://[a-p]{32}$"
    max_request_body_bytes: int = 256 * 1024
    rate_limit_requests_per_minute: int = 60

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

        vllm_timeout_seconds = _positive_float(
            source.get("SUBLINGO_VLLM_TIMEOUT_SECONDS", "30"),
            "SUBLINGO_VLLM_TIMEOUT_SECONDS",
        )
        vllm_max_tokens = _integer_in_range(
            source.get("SUBLINGO_VLLM_MAX_TOKENS", "4096"),
            "SUBLINGO_VLLM_MAX_TOKENS",
            minimum=128,
            maximum=32_768,
        )
        vllm_max_concurrency = _integer_in_range(
            source.get("SUBLINGO_VLLM_MAX_CONCURRENCY", "2"),
            "SUBLINGO_VLLM_MAX_CONCURRENCY",
            minimum=1,
            maximum=32,
        )
        rate_limit_requests_per_minute = _integer_in_range(
            source.get("SUBLINGO_RATE_LIMIT_REQUESTS_PER_MINUTE", "60"),
            "SUBLINGO_RATE_LIMIT_REQUESTS_PER_MINUTE",
            minimum=1,
            maximum=10_000,
        )

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
            if not allowed_origins and allowed_origin_regex is None:
                raise ValueError(
                    "A deployed extension origin or origin regex must be configured"
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
            vllm_base_url=source.get(
                "SUBLINGO_VLLM_BASE_URL",
                "http://127.0.0.1:8001",
            ).rstrip("/"),
            vllm_model=source.get("SUBLINGO_VLLM_MODEL", "Qwen/Qwen3.5-9B").strip(),
            vllm_revision=(source.get("SUBLINGO_VLLM_REVISION", "").strip() or None),
            vllm_timeout_seconds=vllm_timeout_seconds,
            vllm_max_tokens=vllm_max_tokens,
            vllm_max_concurrency=vllm_max_concurrency,
            allowed_origins=allowed_origins,
            allowed_origin_regex=allowed_origin_regex,
            max_request_body_bytes=max_request_body_bytes,
            rate_limit_requests_per_minute=rate_limit_requests_per_minute,
        )


def _positive_float(value: str, name: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValueError(f"{name} must be numeric") from error

    if parsed <= 0:
        raise ValueError(f"{name} must be greater than zero")

    return parsed


def _integer_in_range(value: str, name: str, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error

    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{name} must be from {minimum} to {maximum}")

    return parsed
