from functools import lru_cache

from app.domain.analysis import (
    AnalysisBatch,
    AnalyzedCue,
    ProviderMetadata,
    TranslationCandidate,
    TranslationKind,
)
from app.providers.base import ProviderError


class ArgosAnalysisProvider:
    """Development provider that only supplies whole-line translations."""

    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(name="argos")

    def analyze_batch(self, batch: AnalysisBatch) -> tuple[AnalyzedCue, ...]:
        analyzed_cues: list[AnalyzedCue] = []

        for cue in batch.cues:
            translated_text = translate_text(
                cue.text,
                batch.source_language,
                batch.target_language,
            )
            analyzed_cues.append(
                AnalyzedCue(
                    cue_id=cue.cue_id,
                    source_text=cue.text,
                    translations=(
                        TranslationCandidate(
                            text=translated_text,
                            kind=TranslationKind.CONTEXTUAL,
                            is_primary=True,
                        ),
                    ),
                )
            )

        return tuple(analyzed_cues)


@lru_cache(maxsize=4_096)
def translate_text(text: str, source_language: str, target_language: str) -> str:
    try:
        # Argos is deliberately imported on first inference so health checks and
        # contract tooling do not pay the model initialization cost.
        from argostranslate import translate

        return translate.translate(text, source_language, target_language)
    except Exception as error:
        raise ProviderError("Argos translation failed") from error
