from app.domain.analysis import (
    AnalysisBatch,
    AnalyzedCue,
    ProviderMetadata,
    TranslationCandidate,
    TranslationKind,
)

FIXTURE_TRANSLATIONS = {
    "Regardez la fleur de plus près.": "Look at the flower more closely.",
    "La fleur s'ouvre lentement.": "The flower opens slowly.",
    "Ses couleurs deviennent plus vives.": "Its colors become more vivid.",
}


class DevelopmentAnalysisProvider:
    """Fast deterministic provider for extension and contract development."""

    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(name="development", model="deterministic-fixture", revision="1")

    def analyze_batch(self, batch: AnalysisBatch) -> tuple[AnalyzedCue, ...]:
        return tuple(
            AnalyzedCue(
                cue_id=cue.cue_id,
                source_text=cue.text,
                translations=(
                    TranslationCandidate(
                        text=FIXTURE_TRANSLATIONS.get(
                            cue.text,
                            f"[{batch.target_language}] {cue.text}",
                        ),
                        kind=TranslationKind.CONTEXTUAL,
                        is_primary=True,
                        confidence=1.0 if cue.text in FIXTURE_TRANSLATIONS else None,
                    ),
                ),
            )
            for cue in batch.cues
        )
