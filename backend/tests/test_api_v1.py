import unittest

from fastapi.testclient import TestClient

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
from app.main import create_app
from app.providers.base import ProviderError
from app.services.subtitle_analysis import SubtitleAnalysisService


class FakeAnalysisProvider:
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(name="fake", model="test-model", revision="1")

    def analyze_batch(self, batch: AnalysisBatch) -> tuple[AnalyzedCue, ...]:
        return tuple(
            AnalyzedCue(
                cue_id=cue.cue_id,
                source_text=cue.text,
                translations=(
                    TranslationCandidate(
                        text=f"Translated: {cue.text}",
                        kind=TranslationKind.CONTEXTUAL,
                        is_primary=True,
                        confidence=0.9,
                    ),
                ),
                segments=(
                    AnalyzedSegment(
                        segment_id=f"{cue.cue_id}:0",
                        surface=cue.text,
                        kind=SegmentKind.EXPRESSION,
                        normalized_form=cue.text.lower(),
                        romanization="sample",
                        script_variants=(ScriptVariant(script="Latn", text=cue.text),),
                        translations=(
                            TranslationCandidate(
                                text=f"Literal: {cue.text}",
                                kind=TranslationKind.LITERAL,
                            ),
                        ),
                        grammar=(GrammaticalFeature(name="type", value="fixture"),),
                    ),
                ),
            )
            for cue in batch.cues
        )


class FailingAnalysisProvider(FakeAnalysisProvider):
    def analyze_batch(self, batch: AnalysisBatch) -> tuple[AnalyzedCue, ...]:
        raise ProviderError("provider failure")


class IncompleteAnalysisProvider(FakeAnalysisProvider):
    def analyze_batch(self, batch: AnalysisBatch) -> tuple[AnalyzedCue, ...]:
        return ()


class MissingPrimaryTranslationProvider(FakeAnalysisProvider):
    def analyze_batch(self, batch: AnalysisBatch) -> tuple[AnalyzedCue, ...]:
        return tuple(
            AnalyzedCue(
                cue_id=cue.cue_id,
                source_text=cue.text,
                translations=(
                    TranslationCandidate(
                        text=f"Translated: {cue.text}",
                        kind=TranslationKind.CONTEXTUAL,
                    ),
                ),
            )
            for cue in batch.cues
        )


class MissingSegmentProvider(FakeAnalysisProvider):
    def analyze_batch(self, batch: AnalysisBatch) -> tuple[AnalyzedCue, ...]:
        return tuple(
            AnalyzedCue(
                cue_id=cue.cue_id,
                source_text=cue.text,
                translations=(
                    TranslationCandidate(
                        text=f"Translated: {cue.text}",
                        kind=TranslationKind.CONTEXTUAL,
                        is_primary=True,
                    ),
                ),
            )
            for cue in batch.cues
        )


def create_client(provider: FakeAnalysisProvider) -> TestClient:
    service = SubtitleAnalysisService(provider)
    return TestClient(create_app(service))


class SubtitleAnalysisApiTests(unittest.TestCase):
    def test_default_app_health_is_testable_without_model_inference(self) -> None:
        response = TestClient(create_app()).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_check_does_not_require_inference(self) -> None:
        response = create_client(FakeAnalysisProvider()).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_analyzes_a_batch_with_camel_case_contract(self) -> None:
        response = create_client(FakeAnalysisProvider()).post(
            "/v1/subtitles/analyze",
            json={
                "schemaVersion": "1.0",
                "sourceLanguage": "fr",
                "targetLanguage": "en",
                "cues": [
                    {"cueId": "cue-1", "text": "Bonjour le monde"},
                    {
                        "cueId": "cue-2",
                        "text": "Une autre ligne",
                        "contextBefore": "Bonjour le monde",
                    },
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["schemaVersion"], "1.0")
        self.assertEqual(payload["sourceLanguage"], "fr")
        self.assertEqual(payload["targetLanguage"], "en")
        self.assertEqual(
            payload["provider"],
            {"name": "fake", "model": "test-model", "revision": "1"},
        )
        self.assertEqual([cue["cueId"] for cue in payload["cues"]], ["cue-1", "cue-2"])
        self.assertEqual(
            payload["cues"][0]["translations"][0],
            {
                "text": "Translated: Bonjour le monde",
                "kind": "contextual",
                "isPrimary": True,
                "confidence": 0.9,
            },
        )
        self.assertEqual(payload["cues"][0]["segments"][0]["kind"], "expression")
        self.assertEqual(
            payload["cues"][0]["segments"][0]["scriptVariants"],
            [{"script": "Latn", "text": "Bonjour le monde"}],
        )

    def test_rejects_duplicate_cue_ids(self) -> None:
        response = create_client(FakeAnalysisProvider()).post(
            "/v1/subtitles/analyze",
            json={
                "schemaVersion": "1.0",
                "sourceLanguage": "fr",
                "targetLanguage": "en",
                "cues": [
                    {"cueId": "duplicate", "text": "Première ligne"},
                    {"cueId": "duplicate", "text": "Deuxième ligne"},
                ],
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_rejects_unknown_fields(self) -> None:
        response = create_client(FakeAnalysisProvider()).post(
            "/v1/subtitles/analyze",
            json={
                "schemaVersion": "1.0",
                "sourceLanguage": "fr",
                "targetLanguage": "en",
                "cues": [{"cueId": "cue-1", "text": "Bonjour", "unexpected": True}],
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_rejects_unknown_schema_version(self) -> None:
        response = create_client(FakeAnalysisProvider()).post(
            "/v1/subtitles/analyze",
            json={
                "schemaVersion": "2.0",
                "sourceLanguage": "fr",
                "targetLanguage": "en",
                "cues": [{"cueId": "cue-1", "text": "Bonjour"}],
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_maps_provider_failure_to_service_unavailable(self) -> None:
        response = create_client(FailingAnalysisProvider()).post(
            "/v1/subtitles/analyze",
            json={
                "schemaVersion": "1.0",
                "sourceLanguage": "fr",
                "targetLanguage": "en",
                "cues": [{"cueId": "cue-1", "text": "Bonjour"}],
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Analysis provider unavailable"})

    def test_rejects_incomplete_provider_output(self) -> None:
        response = create_client(IncompleteAnalysisProvider()).post(
            "/v1/subtitles/analyze",
            json={
                "schemaVersion": "1.0",
                "sourceLanguage": "fr",
                "targetLanguage": "en",
                "cues": [{"cueId": "cue-1", "text": "Bonjour"}],
            },
        )

        self.assertEqual(response.status_code, 502)

    def test_rejects_provider_output_without_one_primary_translation(self) -> None:
        response = create_client(MissingPrimaryTranslationProvider()).post(
            "/v1/subtitles/analyze",
            json={
                "schemaVersion": "1.0",
                "sourceLanguage": "fr",
                "targetLanguage": "en",
                "cues": [{"cueId": "cue-1", "text": "Bonjour"}],
            },
        )

        self.assertEqual(response.status_code, 502)

    def test_rejects_provider_output_without_interactive_segments(self) -> None:
        response = create_client(MissingSegmentProvider()).post(
            "/v1/subtitles/analyze",
            json={
                "schemaVersion": "1.0",
                "sourceLanguage": "fr",
                "targetLanguage": "en",
                "cues": [{"cueId": "cue-1", "text": "Bonjour"}],
            },
        )

        self.assertEqual(response.status_code, 502)

    def test_legacy_endpoint_is_removed(self) -> None:
        openapi = create_client(FakeAnalysisProvider()).get("/openapi.json").json()

        self.assertNotIn("/translate-line", openapi["paths"])


if __name__ == "__main__":
    unittest.main()
