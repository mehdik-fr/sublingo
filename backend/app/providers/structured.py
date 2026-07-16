import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.domain.analysis import (
    AnalysisBatch,
    AnalyzedCue,
    AnalyzedSegment,
    GrammaticalFeature,
    ScriptVariant,
    SegmentKind,
    TranslationCandidate,
    TranslationKind,
)
from app.providers.base import InvalidProviderOutputError


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


PartOfSpeech = Literal[
    "noun",
    "verb",
    "adjective",
    "adverb",
    "pronoun",
    "determiner",
    "preposition",
    "conjunction",
    "interjection",
    "particle",
    "numeral",
    "auxiliary",
    "proper_noun",
    "other",
]


class GeneratedSegment(GeneratedModel):
    segment_id: str = Field(min_length=1)
    surface: str = Field(min_length=1)
    kind: Literal["word", "expression", "punctuation", "whitespace"]
    part_of_speech: PartOfSpeech
    normalized_form: str | None = Field(default=None, min_length=1)
    romanization: str | None = Field(default=None, min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    script_variants: list[GeneratedScriptVariant] = Field(default_factory=list)
    translations: list[GeneratedTranslation] = Field(min_length=1)
    grammar: list[GeneratedGrammarFeature] = Field(default_factory=list)

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_percentage_confidence(cls, value: object) -> object:
        if isinstance(value, (int, float)) and 1 < value <= 100:
            return value / 100

        return value


class GeneratedCue(GeneratedModel):
    cue_id: str = Field(min_length=1)
    translations: list[GeneratedTranslation] = Field(min_length=1)
    segments: list[GeneratedSegment] = Field(min_length=1)


class GeneratedBatch(GeneratedModel):
    cues: list[GeneratedCue] = Field(min_length=1)


SYSTEM_PROMPT = """You are Sublingo's multilingual subtitle language analyst.
Return every cue exactly once, in input order, with the exact cueId.
Return exactly one primary contextual cue translation in the requested target language.

Segment the source for an interactive language-learning interface:
- create a word segment for every useful lexical word;
- combine words into one expression segment only for an idiom, phrasal verb, fixed phrase,
  or multi-word unit whose contextual meaning is better taught together;
- never collapse an ordinary full sentence into one expression segment;
- preserve the exact source substring, spelling, case, and spacing in each surface;
- provide at least one translation for every word or expression segment;
- use normalizedForm for the lemma or dictionary form;
- set the required partOfSpeech field to the segment's lexical category; for an
  expression, use the category of its head or function, and use other only when no
  listed category applies;
- use grammar only for additional features such as tense, mood, number, gender, or
  register; do not repeat partOfSpeech in grammar;
- provide romanization only when the source surface uses a script for which a real
  romanization is useful; otherwise omit it;
- use confidence decimals from 0 to 1, never percentages.

Do not add explanations and do not copy source text as a translation when the source and
target languages differ. Return only JSON matching the supplied schema."""


def build_chat_messages(batch: AnalysisBatch) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
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
    ]


def to_analyzed_cues(
    generated: GeneratedBatch,
    batch: AnalysisBatch,
) -> tuple[AnalyzedCue, ...]:
    source_cues = {cue.cue_id: cue for cue in batch.cues}
    expected_cue_ids = tuple(cue.cue_id for cue in batch.cues)
    generated_cue_ids = tuple(cue.cue_id for cue in generated.cues)

    if generated_cue_ids != expected_cue_ids:
        raise InvalidProviderOutputError(
            "Provider must return every cue exactly once and in input order"
        )

    try:
        analyzed_cues = []

        for cue in generated.cues:
            source_text = source_cues[cue.cue_id].text
            segment_ids = [segment.segment_id for segment in cue.segments]

            if len(segment_ids) != len(set(segment_ids)):
                raise InvalidProviderOutputError(
                    f"Provider returned duplicate segment identifiers for cue '{cue.cue_id}'"
                )

            invalid_surface = next(
                (segment.surface for segment in cue.segments if segment.surface not in source_text),
                None,
            )

            if invalid_surface is not None:
                raise InvalidProviderOutputError(
                    f"Provider returned a segment surface absent from cue '{cue.cue_id}'"
                )

            analyzed_cues.append(
                AnalyzedCue(
                    cue_id=cue.cue_id,
                    source_text=source_text,
                    translations=to_translations(cue.translations),
                    segments=tuple(to_segment(segment) for segment in cue.segments),
                )
            )

        return tuple(analyzed_cues)
    except KeyError as error:
        raise InvalidProviderOutputError(
            "Provider returned an unknown cue identifier"
        ) from error


def to_segment(segment: GeneratedSegment) -> AnalyzedSegment:
    extra_grammar = tuple(
        GrammaticalFeature(name=feature.name, value=feature.value)
        for feature in segment.grammar
        if "".join(character for character in feature.name.casefold() if character.isalpha())
        not in {"partofspeech", "type"}
    )

    return AnalyzedSegment(
        segment_id=segment.segment_id,
        surface=segment.surface,
        kind=SegmentKind(segment.kind),
        normalized_form=segment.normalized_form,
        romanization=segment.romanization,
        confidence=segment.confidence,
        script_variants=tuple(
            ScriptVariant(script=variant.script, text=variant.text)
            for variant in segment.script_variants
        ),
        translations=to_translations(segment.translations),
        grammar=(
            GrammaticalFeature(name="partOfSpeech", value=segment.part_of_speech),
            *extra_grammar,
        ),
    )


def to_translations(
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
