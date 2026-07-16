import json
import unittest

import httpx

from app.domain.analysis import AnalysisBatch, SubtitleCue
from app.providers.base import InvalidProviderOutputError, ProviderError
from app.providers.vllm import VllmAnalysisProvider


class VllmAnalysisProviderTests(unittest.IsolatedAsyncioTestCase):
    def create_provider(self, handler) -> VllmAnalysisProvider:
        return VllmAnalysisProvider(
            base_url="http://vllm.test",
            model="Qwen/Qwen3.5-9B",
            revision="revision-123",
            timeout_seconds=30,
            max_tokens=2048,
            max_concurrency=2,
            transport=httpx.MockTransport(handler),
        )

    async def test_checks_that_the_configured_model_is_loaded(self) -> None:
        provider = self.create_provider(
            lambda request: httpx.Response(
                200,
                json={"data": [{"id": "Qwen/Qwen3.5-9B"}]},
                request=request,
            )
        )

        await provider.check_readiness()

        self.assertEqual(provider.metadata.name, "vllm")
        self.assertEqual(provider.metadata.revision, "revision-123")

    async def test_rejects_readiness_when_the_model_is_not_loaded(self) -> None:
        provider = self.create_provider(
            lambda request: httpx.Response(200, json={"data": []}, request=request)
        )

        with self.assertRaisesRegex(ProviderError, "is not loaded"):
            await provider.check_readiness()

    async def test_requests_strict_json_schema_and_maps_segments(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            body = json.loads(request.content)
            self.assertEqual(body["model"], "Qwen/Qwen3.5-9B")
            self.assertEqual(body["temperature"], 0.7)
            self.assertEqual(body["top_p"], 0.8)
            self.assertEqual(body["top_k"], 20)
            self.assertEqual(body["max_tokens"], 2048)
            self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
            self.assertEqual(body["response_format"]["type"], "json_schema")
            self.assertTrue(body["response_format"]["json_schema"]["strict"])

            content = {
                "cues": [
                    {
                        "cueId": "cue-1",
                        "translations": [
                            {
                                "text": "Look at the colors.",
                                "kind": "contextual",
                                "isPrimary": True,
                                "confidence": 0.95,
                            }
                        ],
                        "segments": [
                            {
                                "segmentId": "cue-1:0",
                                "surface": "Regardez",
                                "kind": "word",
                                "partOfSpeech": "verb",
                                "normalizedForm": "regarder",
                                "confidence": 0.9,
                                "translations": [
                                    {
                                        "text": "look",
                                        "kind": "contextual",
                                        "isPrimary": True,
                                    }
                                ],
                                "grammar": [
                                    {"name": "partOfSpeech", "value": "verb"}
                                ],
                            }
                        ],
                    }
                ]
            }
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": json.dumps(content)}}]},
                request=request,
            )

        provider = self.create_provider(handler)
        batch = AnalysisBatch(
            source_language="fr",
            target_language="en",
            cues=(SubtitleCue(cue_id="cue-1", text="Regardez les couleurs."),),
        )

        result = await provider.analyze_batch(batch)

        self.assertEqual(result[0].source_text, "Regardez les couleurs.")
        self.assertEqual(result[0].segments[0].normalized_form, "regarder")
        self.assertEqual(result[0].segments[0].confidence, 0.9)
        self.assertEqual(result[0].segments[0].grammar[0].value, "verb")
        self.assertEqual([request.url.path for request in requests], ["/v1/chat/completions"])

    async def test_classifies_malformed_json_as_invalid_provider_output(self) -> None:
        provider = self.create_provider(
            lambda request: httpx.Response(
                200,
                json={"choices": [{"message": {"content": "not-json"}}]},
                request=request,
            )
        )
        batch = AnalysisBatch(
            source_language="fr",
            target_language="en",
            cues=(SubtitleCue(cue_id="cue-1", text="Bonjour."),),
        )

        with self.assertRaises(InvalidProviderOutputError):
            await provider.analyze_batch(batch)

    async def test_rejects_missing_cues_and_invented_segment_surfaces(self) -> None:
        responses = [
            {
                "cues": [
                    {
                        "cueId": "cue-2",
                        "translations": [{"text": "Hi", "kind": "contextual"}],
                        "segments": [
                            {
                                "segmentId": "cue-2:0",
                                "surface": "Salut",
                                "kind": "word",
                                "partOfSpeech": "interjection",
                                "translations": [{"text": "Hi", "kind": "literal"}],
                            }
                        ],
                    }
                ]
            },
            {
                "cues": [
                    {
                        "cueId": "cue-1",
                        "translations": [{"text": "Hello", "kind": "contextual"}],
                        "segments": [
                            {
                                "segmentId": "cue-1:0",
                                "surface": "Bonsoir",
                                "kind": "word",
                                "partOfSpeech": "interjection",
                                "translations": [
                                    {"text": "Good evening", "kind": "literal"}
                                ],
                            }
                        ],
                    },
                    {
                        "cueId": "cue-2",
                        "translations": [{"text": "Hi", "kind": "contextual"}],
                        "segments": [
                            {
                                "segmentId": "cue-2:0",
                                "surface": "Salut",
                                "kind": "word",
                                "partOfSpeech": "interjection",
                                "translations": [{"text": "Hi", "kind": "literal"}],
                            }
                        ],
                    },
                ]
            },
        ]

        def handler(request: httpx.Request) -> httpx.Response:
            content = responses.pop(0)
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": json.dumps(content)}}]},
                request=request,
            )

        provider = self.create_provider(handler)
        batch = AnalysisBatch(
            source_language="fr",
            target_language="en",
            cues=(
                SubtitleCue(cue_id="cue-1", text="Bonjour"),
                SubtitleCue(cue_id="cue-2", text="Salut"),
            ),
        )

        with self.assertRaisesRegex(InvalidProviderOutputError, "every cue"):
            await provider.analyze_batch(batch)

        with self.assertRaisesRegex(InvalidProviderOutputError, "surface absent"):
            await provider.analyze_batch(batch)


if __name__ == "__main__":
    unittest.main()
