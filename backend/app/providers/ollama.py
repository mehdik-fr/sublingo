from asyncio import Lock

import httpx
from pydantic import BaseModel, ValidationError

from app.domain.analysis import AnalysisBatch, AnalyzedCue, ProviderMetadata
from app.providers.base import InvalidProviderOutputError, ProviderError
from app.providers.structured import (
    GeneratedBatch,
    build_chat_messages,
    to_analyzed_cues,
)


class OllamaMessage(BaseModel):
    content: str


class OllamaChatResponse(BaseModel):
    message: OllamaMessage


class OllamaAnalysisProvider:
    """Analyze batches through an already-installed local Ollama model."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self._model_is_available = False
        self._inference_lock = Lock()

    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(name="ollama", model=self._model)

    async def analyze_batch(self, batch: AnalysisBatch) -> tuple[AnalyzedCue, ...]:
        # Waiting is cancellation-aware and avoids the previous immediate 503 on reactivation.
        async with self._inference_lock:
            return await self._analyze_batch(batch)

    async def check_readiness(self) -> None:
        await self._ensure_model_is_installed(force=True)

    async def _analyze_batch(self, batch: AnalysisBatch) -> tuple[AnalyzedCue, ...]:
        await self._ensure_model_is_installed()
        request_body = {
            "model": self._model,
            "stream": False,
            "keep_alive": "5m",
            "format": GeneratedBatch.model_json_schema(),
            "options": {"temperature": 0},
            "messages": build_chat_messages(batch),
        }

        try:
            async with self._client() as client:
                response = await client.post("/api/chat", json=request_body)
                response.raise_for_status()
        except httpx.HTTPError as error:
            raise ProviderError("Ollama analysis request failed") from error

        try:
            chat_response = OllamaChatResponse.model_validate(response.json())
            generated = GeneratedBatch.model_validate_json(chat_response.message.content)
        except (ValidationError, ValueError) as error:
            raise InvalidProviderOutputError(
                "Ollama returned an invalid analysis response"
            ) from error

        return to_analyzed_cues(generated, batch)

    async def _ensure_model_is_installed(self, *, force: bool = False) -> None:
        if self._model_is_available and not force:
            return

        try:
            async with self._client() as client:
                response = await client.get("/api/tags")
                response.raise_for_status()
            models = response.json().get("models", [])
            installed_names = {item.get("name") for item in models if isinstance(item, dict)}
        except (httpx.HTTPError, ValueError, AttributeError) as error:
            raise ProviderError("Cannot read locally installed Ollama models") from error

        if self._model not in installed_names:
            raise ProviderError(
                f"Ollama model '{self._model}' is not installed; "
                "Sublingo never downloads models automatically"
            )

        self._model_is_available = True

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout_seconds,
            transport=self._transport,
        )
