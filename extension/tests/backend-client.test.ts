import assert from "node:assert/strict";
import test from "node:test";

import {
  requestSubtitleAnalysis,
  type AnalyzeSubtitlesRequest
} from "../src/api/backend-client.ts";

test("posts the generated v1 contract and validates the response", async () => {
  const request: AnalyzeSubtitlesRequest = {
    schemaVersion: "1.0",
    sourceLanguage: "fr",
    targetLanguage: "en",
    cues: [{ cueId: "cue-1", text: "Bonjour." }]
  };
  let receivedBody: unknown;

  const fetcher = async (_input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    receivedBody = JSON.parse(String(init?.body));
    return new Response(
      JSON.stringify({
        schemaVersion: "1.0",
        analysisId: "analysis-1",
        sourceLanguage: "fr",
        targetLanguage: "en",
        provider: { name: "development", model: "deterministic-fixture" },
        cues: [
          {
            cueId: "cue-1",
            sourceText: "Bonjour.",
            translations: [{ text: "Hello.", kind: "contextual", isPrimary: true }],
            segments: []
          }
        ]
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  };

  const response = await requestSubtitleAnalysis(
    request,
    fetcher as typeof fetch,
    "http://backend.test/v1/subtitles/analyze"
  );

  assert.deepEqual(receivedBody, request);
  assert.equal(response.cues[0].translations[0].text, "Hello.");
});

test("rejects a malformed backend response", async () => {
  const fetcher = async (): Promise<Response> => {
    return new Response(JSON.stringify({ schemaVersion: "1.0", cues: [] }), { status: 200 });
  };

  await assert.rejects(
    requestSubtitleAnalysis(
      {
        schemaVersion: "1.0",
        sourceLanguage: "fr",
        targetLanguage: "en",
        cues: [{ cueId: "cue-1", text: "Bonjour." }]
      },
      fetcher as typeof fetch
    ),
    /invalid payload/
  );
});
