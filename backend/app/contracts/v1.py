from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

LANGUAGE_TAG_PATTERN = r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$"


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
    )


class SubtitleCueRequest(ApiModel):
    cue_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=2_000)
    context_before: str | None = Field(default=None, max_length=2_000)
    context_after: str | None = Field(default=None, max_length=2_000)


class AnalyzeSubtitlesRequest(ApiModel):
    schema_version: Literal["1.0"]
    source_language: str = Field(pattern=LANGUAGE_TAG_PATTERN)
    target_language: str = Field(pattern=LANGUAGE_TAG_PATTERN)
    cues: list[SubtitleCueRequest] = Field(min_length=1, max_length=20)

    @field_validator("cues")
    @classmethod
    def cue_ids_must_be_unique(
        cls,
        cues: list[SubtitleCueRequest],
    ) -> list[SubtitleCueRequest]:
        cue_ids = [cue.cue_id for cue in cues]

        if len(cue_ids) != len(set(cue_ids)):
            raise ValueError("cueId values must be unique within a batch")

        return cues


class TranslationCandidateResponse(ApiModel):
    text: str
    kind: Literal["contextual", "literal"]
    is_primary: bool
    confidence: float | None = Field(default=None, ge=0, le=1)


class ScriptVariantResponse(ApiModel):
    script: str
    text: str


class GrammaticalFeatureResponse(ApiModel):
    name: str
    value: str


class SegmentAnalysisResponse(ApiModel):
    segment_id: str
    surface: str
    kind: Literal["word", "expression", "punctuation", "whitespace"]
    normalized_form: str | None = None
    romanization: str | None = None
    script_variants: list[ScriptVariantResponse] = Field(default_factory=list)
    translations: list[TranslationCandidateResponse] = Field(default_factory=list)
    grammar: list[GrammaticalFeatureResponse] = Field(default_factory=list)


class CueAnalysisResponse(ApiModel):
    cue_id: str
    source_text: str
    translations: list[TranslationCandidateResponse]
    segments: list[SegmentAnalysisResponse] = Field(default_factory=list)


class ProviderResponse(ApiModel):
    name: str
    model: str | None = None
    revision: str | None = None


class AnalyzeSubtitlesResponse(ApiModel):
    schema_version: Literal["1.0"]
    analysis_id: str
    source_language: str = Field(pattern=LANGUAGE_TAG_PATTERN)
    target_language: str = Field(pattern=LANGUAGE_TAG_PATTERN)
    provider: ProviderResponse
    cues: list[CueAnalysisResponse]
