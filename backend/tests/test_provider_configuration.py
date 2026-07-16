import json
import asyncio
import unittest

import httpx

from app.core.config import Settings
from app.domain.analysis import AnalysisBatch, SubtitleCue
from app.providers.base import ProviderError
from app.providers.factory import create_analysis_provider
from app.providers.ollama import OllamaAnalysisProvider
from app.providers.vllm import VllmAnalysisProvider


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

    def test_requires_restricted_cors_for_production(self) -> None:
        with self.assertRaisesRegex(ValueError, "extension origin or origin regex"):
            Settings.from_environment(
                {
                    "SUBLINGO_ENVIRONMENT": "production",
                    "SUBLINGO_ALLOWED_ORIGINS": "",
                }
            )

        settings = Settings.from_environment(
            {
                "SUBLINGO_ENVIRONMENT": "production",
                "SUBLINGO_ALLOWED_ORIGINS": "chrome-extension://abcdefghijklmnopabcdefghijklmnop",
            }
        )

        self.assertEqual(
            settings.allowed_origins,
            ("chrome-extension://abcdefghijklmnopabcdefghijklmnop",),
        )
        self.assertIsNone(settings.allowed_origin_regex)

    def test_validates_request_size_configuration(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 1024"):
            Settings.from_environment({"SUBLINGO_MAX_REQUEST_BODY_BYTES": "100"})

    def test_configures_self_hosted_vllm_without_a_paid_model_api(self) -> None:
        settings = Settings.from_environment(
            {
                "SUBLINGO_ANALYSIS_PROVIDER": "vllm",
                "SUBLINGO_VLLM_BASE_URL": "http://vllm.internal:8001",
                "SUBLINGO_VLLM_MODEL": "Qwen/Qwen3.5-9B",
                "SUBLINGO_VLLM_REVISION": "abc123",
                "SUBLINGO_VLLM_MAX_CONCURRENCY": "3",
            }
        )

        provider = create_analysis_provider(settings)

        self.assertIsInstance(provider, VllmAnalysisProvider)
        self.assertEqual(provider.metadata.name, "vllm")
        self.assertEqual(provider.metadata.model, "Qwen/Qwen3.5-9B")
        self.assertEqual(provider.metadata.revision, "abc123")


class OllamaAnalysisProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_waiting_inference_is_cancellation_aware(self) -> None:
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
        await provider._inference_lock.acquire()
        task = asyncio.create_task(provider.analyze_batch(batch))
        await asyncio.sleep(0)
        task.cancel()

        try:
            with self.assertRaises(asyncio.CancelledError):
                await task
        finally:
            provider._inference_lock.release()

    async def test_uses_only_an_already_installed_model_and_validates_json(self) -> None:
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
                                                "part_of_speech": "noun",
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

        result = await provider.analyze_batch(batch)

        self.assertEqual(result[0].source_text, "Regardez la fleur.")
        self.assertEqual(result[0].translations[0].text, "Look at the flower.")
        self.assertTrue(result[0].translations[0].is_primary)
        self.assertEqual(result[0].translations[0].confidence, 0.8)
        self.assertEqual(result[0].segments[0].surface, "la fleur")
        self.assertEqual([request.url.path for request in requests], ["/api/tags", "/api/chat"])

    async def test_refuses_missing_model_without_downloading_it(self) -> None:
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
            await provider.analyze_batch(batch)

        self.assertEqual([request.url.path for request in requests], ["/api/tags"])


if __name__ == "__main__":
    unittest.main()
