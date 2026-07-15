from uuid import uuid4

from app.domain.analysis import AnalysisBatch, AnalysisResult
from app.providers.base import AnalysisProvider, ProviderError


class ProviderUnavailableError(RuntimeError):
    """Raised when the configured provider cannot answer a valid request."""


class InvalidProviderResponseError(RuntimeError):
    """Raised when a provider breaks the internal analysis contract."""


class SubtitleAnalysisService:
    def __init__(self, provider: AnalysisProvider) -> None:
        self._provider = provider

    def analyze(self, batch: AnalysisBatch) -> AnalysisResult:
        try:
            cues = self._provider.analyze_batch(batch)
        except ProviderError as error:
            raise ProviderUnavailableError("Analysis provider unavailable") from error

        expected_cue_ids = tuple(cue.cue_id for cue in batch.cues)
        actual_cue_ids = tuple(cue.cue_id for cue in cues)

        if actual_cue_ids != expected_cue_ids:
            raise InvalidProviderResponseError(
                "Provider must return every cue exactly once and preserve batch order"
            )

        for input_cue, analyzed_cue in zip(batch.cues, cues, strict=True):
            if analyzed_cue.source_text != input_cue.text:
                raise InvalidProviderResponseError("Provider changed the source subtitle text")

            primary_count = sum(
                translation.is_primary for translation in analyzed_cue.translations
            )

            if primary_count != 1:
                raise InvalidProviderResponseError(
                    "Provider must return exactly one primary cue translation"
                )

        return AnalysisResult(
            analysis_id=str(uuid4()),
            source_language=batch.source_language,
            target_language=batch.target_language,
            provider=self._provider.metadata,
            cues=cues,
        )
