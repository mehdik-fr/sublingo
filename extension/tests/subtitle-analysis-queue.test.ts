import assert from "node:assert/strict";
import test from "node:test";

import type {
  AnalyzeSubtitlesRequest,
  AnalyzeSubtitlesResponse
} from "../src/api/backend-client.ts";
import { SubtitleAnalysisQueue } from "../src/api/subtitle-analysis-queue.ts";

function createAnalyzer(requests: AnalyzeSubtitlesRequest[]) {
  return async (request: AnalyzeSubtitlesRequest): Promise<AnalyzeSubtitlesResponse> => {
    requests.push(request);
    return {
      schemaVersion: "1.0",
      analysisId: `analysis-${requests.length}`,
      sourceLanguage: request.sourceLanguage,
      targetLanguage: request.targetLanguage,
      provider: { name: "development", model: "deterministic-fixture" },
      cues: request.cues.map((cue) => ({
        cueId: cue.cueId,
        sourceText: cue.text,
        translations: [
          {
            text: `Translated: ${cue.text}`,
            kind: "contextual",
            isPrimary: true
          }
        ],
        segments: []
      }))
    };
  };
}

test("batches subtitle lines before analysis", async () => {
  const requests: AnalyzeSubtitlesRequest[] = [];
  const queue = new SubtitleAnalysisQueue(createAnalyzer(requests), { batchDelayMs: 0 });
  const languages = { sourceLanguage: "fr", targetLanguage: "en" };

  const results = await Promise.all([
    queue.request({ text: "Première ligne." }, languages),
    queue.request({ text: "Deuxième ligne." }, languages)
  ]);

  assert.equal(requests.length, 1);
  assert.equal(requests[0].cues.length, 2);
  assert.equal(results[1].cue.translations[0].text, "Translated: Deuxième ligne.");
});

test("coalesces duplicate lines and serves later requests from cache", async () => {
  const requests: AnalyzeSubtitlesRequest[] = [];
  const queue = new SubtitleAnalysisQueue(createAnalyzer(requests), { batchDelayMs: 0 });
  const languages = { sourceLanguage: "fr", targetLanguage: "en" };

  const [first, duplicate] = await Promise.all([
    queue.request({ text: "Même ligne." }, languages),
    queue.request({ text: "Même ligne." }, languages)
  ]);
  const cached = await queue.request({ text: "Même ligne." }, languages);

  assert.equal(requests.length, 1);
  assert.equal(requests[0].cues.length, 1);
  assert.deepEqual(first, duplicate);
  assert.deepEqual(first, cached);
});

test("keeps language pairs in separate batches", async () => {
  const requests: AnalyzeSubtitlesRequest[] = [];
  const queue = new SubtitleAnalysisQueue(createAnalyzer(requests), { batchDelayMs: 0 });

  await Promise.all([
    queue.request(
      { text: "Bonjour." },
      { sourceLanguage: "fr", targetLanguage: "en" }
    ),
    queue.request(
      { text: "Hello." },
      { sourceLanguage: "en", targetLanguage: "fr" }
    )
  ]);

  assert.equal(requests.length, 2);
  assert.notEqual(requests[0].sourceLanguage, requests[1].sourceLanguage);
});

test("does not reuse cached analysis across different subtitle contexts", async () => {
  const requests: AnalyzeSubtitlesRequest[] = [];
  const queue = new SubtitleAnalysisQueue(createAnalyzer(requests), { batchDelayMs: 0 });
  const languages = { sourceLanguage: "fr", targetLanguage: "en" };

  await queue.request({ text: "Il est là.", contextBefore: "Jean arrive." }, languages);
  await queue.request({ text: "Il est là.", contextBefore: "Le livre tombe." }, languages);

  assert.equal(requests.length, 2);
});
