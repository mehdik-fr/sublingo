from asyncio import Semaphore

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.domain.analysis import AnalysisBatch, AnalyzedCue, ProviderMetadata
from app.providers.base import InvalidProviderOutputError, ProviderError
from app.providers.structured import (
    GeneratedBatch,
    build_chat_messages,
    to_analyzed_cues,
)


class VllmMessage(BaseModel):
    content: str


class VllmChoice(BaseModel):
    message: VllmMessage


class VllmChatResponse(BaseModel):
    choices: list[VllmChoice] = Field(min_length=1)


class VllmModel(BaseModel):
    id: str


class VllmModelsResponse(BaseModel):
    data: list[VllmModel]


class VllmAnalysisProvider:
    """Use a self-hosted vLLM OpenAI-compatible protocol endpoint."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        revision: str | None,
        timeout_seconds: float,
        max_tokens: int,
        max_concurrency: int,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._revision = revision
        self._timeout_seconds = timeout_seconds
        self._max_tokens = max_tokens
        self._transport = transport
        self._semaphore = Semaphore(max_concurrency)

    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            name="vllm",
            model=self._model,
            revision=self._revision,
        )

    async def analyze_batch(self, batch: AnalysisBatch) -> tuple[AnalyzedCue, ...]:
        # The semaphore waits instead of rejecting concurrent cues. Cancellation while
        # waiting or during httpx I/O propagates to vLLM and frees capacity.
        async with self._semaphore:
            request_body = {
                "model": self._model,
                "messages": build_chat_messages(batch),
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 20,
                "min_p": 0,
                "presence_penalty": 1.5,
                "max_tokens": self._max_tokens,
                "seed": 0,
                "stream": False,
                "chat_template_kwargs": {"enable_thinking": False},
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "sublingo_analysis",
                        "strict": True,
                        "schema": GeneratedBatch.model_json_schema(),
                    },
                },
            }

            try:
                async with self._client() as client:
                    response = await client.post("/v1/chat/completions", json=request_body)
                    response.raise_for_status()
            except httpx.HTTPError as error:
                raise ProviderError("vLLM analysis request failed") from error

            try:
                chat_response = VllmChatResponse.model_validate(response.json())
                generated = GeneratedBatch.model_validate_json(
                    chat_response.choices[0].message.content
                )
            except (ValidationError, ValueError) as error:
                raise InvalidProviderOutputError(
                    "vLLM returned an invalid analysis response"
                ) from error

            return to_analyzed_cues(generated, batch)

    async def check_readiness(self) -> None:
        try:
            async with self._client() as client:
                response = await client.get("/v1/models")
                response.raise_for_status()
            available = VllmModelsResponse.model_validate(response.json())
        except (httpx.HTTPError, ValidationError, ValueError) as error:
            raise ProviderError("Cannot read models from vLLM") from error

        model_ids = {item.id for item in available.data}

        if self._model not in model_ids:
            raise ProviderError(f"vLLM model '{self._model}' is not loaded")

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout_seconds,
            transport=self._transport,
        )
