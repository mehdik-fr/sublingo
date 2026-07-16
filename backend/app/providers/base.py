from typing import Protocol

from app.domain.analysis import AnalysisBatch, AnalyzedCue, ProviderMetadata


class ProviderError(RuntimeError):
    """Raised when an analysis provider cannot satisfy a request."""


class AnalysisProvider(Protocol):
    @property
    def metadata(self) -> ProviderMetadata:
        """Describe the concrete provider implementation."""

    def analyze_batch(self, batch: AnalysisBatch) -> tuple[AnalyzedCue, ...]:
        """Analyze a batch while preserving cue order and identifiers."""

    def check_readiness(self) -> None:
        """Raise ProviderError when the configured runtime or model is unavailable."""
