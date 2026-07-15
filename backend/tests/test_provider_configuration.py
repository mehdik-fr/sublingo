import json
import unittest

import httpx

from app.core.config import Settings
from app.domain.analysis import AnalysisBatch, SubtitleCue
from app.providers.base import ProviderError
from app.providers.development import DevelopmentAnalysisProvider
from app.providers.factory import create_analysis_provider
from app.providers.ollama import OllamaAnalysisProvider


class ProviderConfigurationTests(unittest.TestCase):
    def test_defaults_to_fast_development_provider(self) -> None:
        settings = Settings.from_environment({})

        provider = create_analysis_provider(settings)

        self.assertIsInstance(provider, DevelopmentAnalysisProvider)

    def test_rejects_unknown_provider(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported analysis provider"):
            Settings.from_environment({"SUBLINGO_ANALYSIS_PROVIDER": "paid-api"})

    def test_development_provider_returns_deterministic_batch(self) -> None:
        batch = AnalysisBatch(
            source_language="fr",
            target_language="en",
            cues=(SubtitleCue(cue_id="cue-1", text="Regardez la fleur de plus près."),),
        )

        result = DevelopmentAnalysisProvider().analyze_batch(batch)

        self.assertEqual(result[0].translations[0].text, "Look at the flower more closely.")
        self.assertEqual(result[0].translations[0].confidence, 1.0)


class OllamaAnalysisProviderTests(unittest.TestCase):
    def test_uses_only_an_already_installed_model_and_validates_json(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)

            if request.url.path == "/api/tags":
                return httpx.Response(200, json={"models": [{"name": "qwen2.5:7b"}]})

            request_body = json.loads(request.content)
            self.assertEqual(request_body["model"], "qwen2.5:7b")
            self.assertFalse(request_body["stream"])
            self.assertIsInstance(request_body["format"], dict)
            cue_schema = request_body["format"]["$defs"]["GeneratedCue"]
            self.assertIn("cueId", cue_schema["properties"])
            self.assertNotIn("cue_id", cue_schema["properties"])
            return httpx.Response(
                200,
                json={
                    "message": {
                        "content": json.dumps(
                            {
                                "cues": [
                                    {
                                        "cue_id": "cue-1",
                                        "translations": [
                                            {
                                                "text": "Look at the flower.",
                                                "kind": "contextual",
                                                "is_primary": True,
                                                "confidence": 80,
                                            }
                                        ],
                                        "segments": [
                                            {
                                                "segment_id": "cue-1:0",
                                                "surface": "la fleur",
                                                "kind": "expression",
                                                "translations": [
                                                    {
                                                        "text": "the flower",
                                                        "kind": "literal",
                                                    }
                                                ],
                                            }
                                        ],
                                    }
                                ]
                            }
                        )
                    }
                },
            )

        provider = OllamaAnalysisProvider(
            base_url="http://ollama.test",
            model="qwen2.5:7b",
            timeout_seconds=30,
            transport=httpx.MockTransport(handler),
        )
        batch = AnalysisBatch(
            source_language="fr",
            target_language="en",
            cues=(SubtitleCue(cue_id="cue-1", text="Regardez la fleur."),),
        )

        result = provider.analyze_batch(batch)

        self.assertEqual(result[0].source_text, "Regardez la fleur.")
        self.assertEqual(result[0].translations[0].text, "Look at the flower.")
        self.assertEqual(result[0].translations[0].confidence, 0.8)
        self.assertEqual(result[0].segments[0].surface, "la fleur")
        self.assertEqual([request.url.path for request in requests], ["/api/tags", "/api/chat"])

    def test_refuses_missing_model_without_downloading_it(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"models": []})

        provider = OllamaAnalysisProvider(
            base_url="http://ollama.test",
            model="not-installed:latest",
            timeout_seconds=30,
            transport=httpx.MockTransport(handler),
        )
        batch = AnalysisBatch(
            source_language="fr",
            target_language="en",
            cues=(SubtitleCue(cue_id="cue-1", text="Bonjour."),),
        )

        with self.assertRaisesRegex(ProviderError, "never downloads models automatically"):
            provider.analyze_batch(batch)

        self.assertEqual([request.url.path for request in requests], ["/api/tags"])


if __name__ == "__main__":
    unittest.main()
