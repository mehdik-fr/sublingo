import json
import unittest

import httpx

from app.core.config import Settings
from app.domain.analysis import AnalysisBatch, SubtitleCue
from app.providers.base import ProviderError
from app.providers.factory import create_analysis_provider
from app.providers.ollama import OllamaAnalysisProvider


class ProviderConfigurationTests(unittest.TestCase):
    def test_defaults_to_local_ollama_provider_without_contacting_runtime(self) -> None:
        settings = Settings.from_environment({})

        provider = create_analysis_provider(settings)

        self.assertIsInstance(provider, OllamaAnalysisProvider)
        self.assertEqual(provider.metadata.name, "ollama")
        self.assertEqual(provider.metadata.model, "qwen2.5:7b")

    def test_rejects_unknown_provider(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported analysis provider"):
            Settings.from_environment({"SUBLINGO_ANALYSIS_PROVIDER": "paid-api"})

        with self.assertRaisesRegex(ValueError, "Unsupported analysis provider"):
            Settings.from_environment({"SUBLINGO_ANALYSIS_PROVIDER": "development"})

class OllamaAnalysisProviderTests(unittest.TestCase):
    def test_rejects_concurrent_inference_instead_of_building_a_cpu_backlog(self) -> None:
        provider = OllamaAnalysisProvider(
            base_url="http://ollama.test",
            model="qwen2.5:7b",
            timeout_seconds=30,
            transport=httpx.MockTransport(lambda _request: httpx.Response(500)),
        )
        batch = AnalysisBatch(
            source_language="fr",
            target_language="en",
            cues=(SubtitleCue(cue_id="cue-1", text="Bonjour."),),
        )
        provider._inference_lock.acquire()

        try:
            with self.assertRaisesRegex(ProviderError, "already processing a batch"):
                provider.analyze_batch(batch)
        finally:
            provider._inference_lock.release()

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
        self.assertTrue(result[0].translations[0].is_primary)
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
