import unittest

from fastapi.testclient import TestClient

from app.core.config import Settings
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

    def check_readiness(self) -> None:
        return None


class FailingAnalysisProvider(FakeAnalysisProvider):
    def analyze_batch(self, batch: AnalysisBatch) -> tuple[AnalyzedCue, ...]:
        raise ProviderError("provider failure")


class UnreadyAnalysisProvider(FakeAnalysisProvider):
    def check_readiness(self) -> None:
        raise ProviderError("runtime unavailable")


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


def create_client(
    provider: FakeAnalysisProvider,
    settings: Settings | None = None,
) -> TestClient:
    service = SubtitleAnalysisService(provider)
    return TestClient(create_app(service, settings=settings))


class SubtitleAnalysisApiTests(unittest.TestCase):
    def test_default_app_health_is_testable_without_model_inference(self) -> None:
        response = TestClient(create_app()).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_check_does_not_require_inference(self) -> None:
        response = create_client(FakeAnalysisProvider()).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_readiness_checks_the_configured_provider_without_inference(self) -> None:
        response = create_client(FakeAnalysisProvider()).get("/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ready", "provider": "fake"})

    def test_readiness_reports_an_unavailable_provider(self) -> None:
        response = create_client(UnreadyAnalysisProvider()).get("/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "not_ready", "provider": "fake"})

    def test_echoes_a_safe_request_identifier(self) -> None:
        response = create_client(FakeAnalysisProvider()).get(
            "/health",
            headers={"X-Request-ID": "test-request-42"},
        )

        self.assertEqual(response.headers["X-Request-ID"], "test-request-42")

    def test_replaces_an_unsafe_request_identifier(self) -> None:
        response = create_client(FakeAnalysisProvider()).get(
            "/health",
            headers={"X-Request-ID": "unsafe request id"},
        )

        self.assertNotEqual(response.headers["X-Request-ID"], "unsafe request id")
        self.assertEqual(len(response.headers["X-Request-ID"]), 36)

    def test_rejects_a_request_body_above_the_configured_limit(self) -> None:
        settings = Settings(max_request_body_bytes=1024)
        response = create_client(FakeAnalysisProvider(), settings=settings).post(
            "/v1/subtitles/analyze",
            content="x" * 1025,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json(), {"detail": "Request body too large"})

    def test_cors_allows_local_development_but_not_arbitrary_websites(self) -> None:
        client = create_client(FakeAnalysisProvider())
        allowed = client.options(
            "/v1/subtitles/analyze",
            headers={
                "Origin": "http://localhost:8000",
                "Access-Control-Request-Method": "POST",
            },
        )
        denied = client.options(
            "/v1/subtitles/analyze",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertEqual(allowed.headers["access-control-allow-origin"], "http://localhost:8000")
        self.assertNotIn("access-control-allow-origin", denied.headers)

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
