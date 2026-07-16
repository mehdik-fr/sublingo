from dataclasses import dataclass, field
from enum import StrEnum


class TranslationKind(StrEnum):
    CONTEXTUAL = "contextual"
    LITERAL = "literal"


class SegmentKind(StrEnum):
    WORD = "word"
    EXPRESSION = "expression"
    PUNCTUATION = "punctuation"
    WHITESPACE = "whitespace"


@dataclass(frozen=True, slots=True)
class SubtitleCue:
    cue_id: str
    text: str
    context_before: str | None = None
    context_after: str | None = None


@dataclass(frozen=True, slots=True)
class AnalysisBatch:
    source_language: str
    target_language: str
    cues: tuple[SubtitleCue, ...]


@dataclass(frozen=True, slots=True)
class TranslationCandidate:
    text: str
    kind: TranslationKind
    is_primary: bool = False
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class ScriptVariant:
    script: str
    text: str


@dataclass(frozen=True, slots=True)
class GrammaticalFeature:
    name: str
    value: str


@dataclass(frozen=True, slots=True)
class AnalyzedSegment:
    segment_id: str
    surface: str
    kind: SegmentKind
    translations: tuple[TranslationCandidate, ...] = field(default_factory=tuple)
    normalized_form: str | None = None
    romanization: str | None = None
    confidence: float | None = None
    script_variants: tuple[ScriptVariant, ...] = field(default_factory=tuple)
    grammar: tuple[GrammaticalFeature, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class AnalyzedCue:
    cue_id: str
    source_text: str
    translations: tuple[TranslationCandidate, ...]
    segments: tuple[AnalyzedSegment, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ProviderMetadata:
    name: str
    model: str | None = None
    revision: str | None = None


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    analysis_id: str
    source_language: str
    target_language: str
    provider: ProviderMetadata
    cues: tuple[AnalyzedCue, ...]
