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
        provider: { name: "fixture", model: "test-only" },
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
    {
      fetcher: fetcher as typeof fetch,
      endpoint: "http://backend.test/v1/subtitles/analyze",
      timeoutMs: 1_000
    }
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
      { fetcher: fetcher as typeof fetch, timeoutMs: 1_000 }
    ),
    /invalid payload/
  );
});

test("rejects malformed structured segment metadata", async () => {
  const fetcher = async (): Promise<Response> =>
    new Response(
      JSON.stringify({
        schemaVersion: "1.0",
        analysisId: "analysis-1",
        sourceLanguage: "ko",
        targetLanguage: "en",
        provider: { name: "fixture" },
        cues: [
          {
            cueId: "cue-1",
            sourceText: "안녕하세요",
            translations: [{ text: "Hello", kind: "contextual", isPrimary: true }],
            segments: [
              {
                segmentId: "cue-1:0",
                surface: "안녕하세요",
                kind: "expression",
                romanization: 123,
                translations: [{ text: "Hello", kind: "contextual", isPrimary: true }]
              }
            ]
          }
        ]
      }),
      { status: 200 }
    );

  await assert.rejects(
    requestSubtitleAnalysis(
      {
        schemaVersion: "1.0",
        sourceLanguage: "ko",
        targetLanguage: "en",
        cues: [{ cueId: "cue-1", text: "안녕하세요" }]
      },
      { fetcher: fetcher as typeof fetch, timeoutMs: 1_000 }
    ),
    /invalid payload/
  );
});

test("times out a backend request instead of leaving it pending", async () => {
  const fetcher = async (_input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    return await new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener("abort", () => reject(init.signal?.reason), { once: true });
    });
  };

  await assert.rejects(
    requestSubtitleAnalysis(
      {
        schemaVersion: "1.0",
        sourceLanguage: "fr",
        targetLanguage: "en",
        cues: [{ cueId: "cue-1", text: "Bonjour." }]
      },
      { fetcher: fetcher as typeof fetch, timeoutMs: 5 }
    ),
    (error: unknown) => {
      return error instanceof Error &&
        "code" in error &&
        error.code === "timeout";
    }
  );
});

test("retries a transient hosted failure only within the configured bound", async () => {
  let calls = 0;
  const fetcher = async (): Promise<Response> => {
    calls += 1;

    if (calls === 1) {
      return new Response(null, { status: 503 });
    }

    return new Response(
      JSON.stringify({
        schemaVersion: "1.0",
        analysisId: "analysis-retried",
        sourceLanguage: "fr",
        targetLanguage: "en",
        provider: { name: "fixture" },
        cues: [{
          cueId: "cue-1",
          sourceText: "Bonjour.",
          translations: [{ text: "Hello.", kind: "contextual", isPrimary: true }],
          segments: []
        }]
      }),
      { status: 200 }
    );
  };

  const response = await requestSubtitleAnalysis(
    {
      schemaVersion: "1.0",
      sourceLanguage: "fr",
      targetLanguage: "en",
      cues: [{ cueId: "cue-1", text: "Bonjour." }]
    },
    { fetcher: fetcher as typeof fetch, maxRetries: 1, timeoutMs: 1_000 }
  );

  assert.equal(calls, 2);
  assert.equal(response.analysisId, "analysis-retried");
});

test("classifies malformed JSON as an invalid analysis response", async () => {
  const fetcher = async (): Promise<Response> => {
    return new Response("{not-json", { status: 200 });
  };

  await assert.rejects(
    requestSubtitleAnalysis(
      {
        schemaVersion: "1.0",
        sourceLanguage: "fr",
        targetLanguage: "en",
        cues: [{ cueId: "cue-1", text: "Bonjour." }]
      },
      { fetcher: fetcher as typeof fetch, timeoutMs: 1_000 }
    ),
    (error: unknown) => {
      return error instanceof Error &&
        "code" in error &&
        error.code === "invalid-response";
    }
  );
});

test("honors a caller cancellation that happened before the request", async () => {
  const controller = new AbortController();
  controller.abort();
  const fetcher = async (_input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    assert.equal(init?.signal?.aborted, true);
    throw init?.signal?.reason;
  };

  await assert.rejects(
    requestSubtitleAnalysis(
      {
        schemaVersion: "1.0",
        sourceLanguage: "fr",
        targetLanguage: "en",
        cues: [{ cueId: "cue-1", text: "Bonjour." }]
      },
      { fetcher: fetcher as typeof fetch, signal: controller.signal, timeoutMs: 1_000 }
    ),
    (error: unknown) => {
      return error instanceof Error &&
        "code" in error &&
        error.code === "cancelled";
    }
  );
});
