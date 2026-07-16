from typing import Protocol

from app.domain.analysis import AnalysisBatch, AnalyzedCue, ProviderMetadata


class ProviderError(RuntimeError):
    """Raised when an analysis provider cannot satisfy a request."""


class InvalidProviderOutputError(ProviderError):
    """Raised when a reachable provider violates the structured output contract."""


class AnalysisProvider(Protocol):
    @property
    def metadata(self) -> ProviderMetadata:
        """Describe the concrete provider implementation."""

    async def analyze_batch(self, batch: AnalysisBatch) -> tuple[AnalyzedCue, ...]:
        """Analyze a batch while preserving cue order and identifiers."""

    async def check_readiness(self) -> None:
        """Raise ProviderError when the configured runtime or model is unavailable."""
