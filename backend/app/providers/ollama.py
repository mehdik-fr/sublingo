import json
from threading import Lock
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from pydantic.alias_generators import to_camel

from app.domain.analysis import (
    AnalysisBatch,
    AnalyzedCue,
    AnalyzedSegment,
    GrammaticalFeature,
    ProviderMetadata,
    ScriptVariant,
    SegmentKind,
    TranslationCandidate,
    TranslationKind,
)
from app.providers.base import ProviderError


class GeneratedModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
    )


class GeneratedTranslation(GeneratedModel):
    text: str = Field(min_length=1)
    kind: Literal["contextual", "literal"]
    is_primary: bool = False
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_percentage_confidence(cls, value: object) -> object:
        if isinstance(value, (int, float)) and 1 < value <= 100:
            return value / 100

        return value


class GeneratedScriptVariant(GeneratedModel):
    script: str = Field(min_length=1)
    text: str = Field(min_length=1)


class GeneratedGrammarFeature(GeneratedModel):
    name: str = Field(min_length=1)
    value: str = Field(min_length=1)


class GeneratedSegment(GeneratedModel):
    segment_id: str = Field(min_length=1)
    surface: str = Field(min_length=1)
    kind: Literal["word", "expression", "punctuation", "whitespace"]
    normalized_form: str | None = None
    romanization: str | None = None
    script_variants: list[GeneratedScriptVariant] = Field(default_factory=list)
    translations: list[GeneratedTranslation] = Field(min_length=1)
    grammar: list[GeneratedGrammarFeature] = Field(default_factory=list)


class GeneratedCue(GeneratedModel):
    cue_id: str = Field(min_length=1)
    translations: list[GeneratedTranslation] = Field(min_length=1)
    segments: list[GeneratedSegment] = Field(min_length=1)


class GeneratedBatch(GeneratedModel):
    cues: list[GeneratedCue] = Field(min_length=1)


class OllamaMessage(BaseModel):
    content: str


class OllamaChatResponse(BaseModel):
    message: OllamaMessage


class OllamaAnalysisProvider:
    """Analyze subtitle batches through an already-installed local Ollama model."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
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

    def analyze_batch(self, batch: AnalysisBatch) -> tuple[AnalyzedCue, ...]:
        if not self._inference_lock.acquire(blocking=False):
            raise ProviderError("Ollama analysis provider is already processing a batch")

        try:
            return self._analyze_batch(batch)
        finally:
            self._inference_lock.release()

    def _analyze_batch(self, batch: AnalysisBatch) -> tuple[AnalyzedCue, ...]:
        self._ensure_model_is_installed()
        request_body = {
            "model": self._model,
            "stream": False,
            "keep_alive": "5m",
            "format": GeneratedBatch.model_json_schema(),
            "options": {"temperature": 0},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Sublingo's subtitle language analyst. Return every cue exactly "
                        "once and preserve cue order. Provide one primary contextual translation. "
                        "Translate into the requested target language and never copy source text as "
                        "a translation when source and target languages differ. "
                        "Cover the source line with useful word or expression segments and include "
                        "a translation for each. Prefer one expression segment when words form one "
                        "contextual meaning. Preserve the exact source surface in each segment. "
                        "Confidence values must be decimals from 0 to 1, never percentages. Only "
                        "return the requested JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "sourceLanguage": batch.source_language,
                            "targetLanguage": batch.target_language,
                            "cues": [
                                {
                                    "cueId": cue.cue_id,
                                    "text": cue.text,
                                    "contextBefore": cue.context_before,
                                    "contextAfter": cue.context_after,
                                }
                                for cue in batch.cues
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }

        try:
            with self._client() as client:
                response = client.post("/api/chat", json=request_body)
                response.raise_for_status()
            chat_response = OllamaChatResponse.model_validate(response.json())
            generated = GeneratedBatch.model_validate_json(chat_response.message.content)
        except (httpx.HTTPError, ValidationError, ValueError) as error:
            raise ProviderError("Ollama returned an invalid analysis response") from error

        source_cues = {cue.cue_id: cue for cue in batch.cues}

        try:
            return tuple(
                AnalyzedCue(
                    cue_id=cue.cue_id,
                    source_text=source_cues[cue.cue_id].text,
                    translations=self._to_translations(cue.translations),
                    segments=tuple(self._to_segment(segment) for segment in cue.segments),
                )
                for cue in generated.cues
            )
        except KeyError as error:
            raise ProviderError("Ollama returned an unknown cue identifier") from error

    def _ensure_model_is_installed(self) -> None:
        if self._model_is_available:
            return

        try:
            with self._client() as client:
                response = client.get("/api/tags")
                response.raise_for_status()
            models = response.json().get("models", [])
            installed_names = {item.get("name") for item in models if isinstance(item, dict)}
        except (httpx.HTTPError, ValueError, AttributeError) as error:
            raise ProviderError("Cannot read locally installed Ollama models") from error

        if self._model not in installed_names:
            raise ProviderError(
                f"Ollama model '{self._model}' is not installed; Sublingo never downloads models automatically"
            )

        self._model_is_available = True

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._base_url,
            timeout=self._timeout_seconds,
            transport=self._transport,
        )

    @staticmethod
    def _to_segment(segment: GeneratedSegment) -> AnalyzedSegment:
        return AnalyzedSegment(
            segment_id=segment.segment_id,
            surface=segment.surface,
            kind=SegmentKind(segment.kind),
            normalized_form=segment.normalized_form,
            romanization=segment.romanization,
            script_variants=tuple(
                ScriptVariant(script=variant.script, text=variant.text)
                for variant in segment.script_variants
            ),
            translations=OllamaAnalysisProvider._to_translations(segment.translations),
            grammar=tuple(
                GrammaticalFeature(name=feature.name, value=feature.value)
                for feature in segment.grammar
            ),
        )

    @staticmethod
    def _to_translations(
        translations: list[GeneratedTranslation],
    ) -> tuple[TranslationCandidate, ...]:
        primary_index = next(
            (index for index, translation in enumerate(translations) if translation.is_primary),
            0,
        )

        return tuple(
            TranslationCandidate(
                text=translation.text,
                kind=TranslationKind(translation.kind),
                is_primary=index == primary_index,
                confidence=translation.confidence,
            )
            for index, translation in enumerate(translations)
        )
