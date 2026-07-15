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
      provider: { name: "fixture", model: "test-only" },
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

test("allows only one backend batch to be active", async () => {
  const releases: Array<() => void> = [];
  let activeRequests = 0;
  let maximumActiveRequests = 0;
  const analyzer = async (request: AnalyzeSubtitlesRequest): Promise<AnalyzeSubtitlesResponse> => {
    activeRequests += 1;
    maximumActiveRequests = Math.max(maximumActiveRequests, activeRequests);
    await new Promise<void>((resolve) => releases.push(resolve));
    activeRequests -= 1;
    return createResponse(request, `analysis-${releases.length}`);
  };
  const queue = new SubtitleAnalysisQueue(analyzer, {
    batchDelayMs: 0,
    maxBatchSize: 1
  });
  const languages = { sourceLanguage: "fr", targetLanguage: "en" };

  const first = queue.request({ text: "Première ligne." }, languages);
  await waitFor(() => releases.length === 1);
  const second = queue.request({ text: "Deuxième ligne." }, languages);
  await new Promise((resolve) => setTimeout(resolve, 10));

  assert.equal(releases.length, 1);
  releases.shift()?.();
  await first;
  await waitFor(() => releases.length === 1);
  releases.shift()?.();
  await second;
  assert.equal(maximumActiveRequests, 1);
});

test("drops stale queued captions when the backlog is full", async () => {
  let releaseFirst: (() => void) | null = null;
  let callCount = 0;
  const analyzer = async (request: AnalyzeSubtitlesRequest): Promise<AnalyzeSubtitlesResponse> => {
    callCount += 1;

    if (callCount === 1) {
      await new Promise<void>((resolve) => {
        releaseFirst = resolve;
      });
    }

    return createResponse(request, `analysis-${callCount}`);
  };
  const queue = new SubtitleAnalysisQueue(analyzer, {
    batchDelayMs: 0,
    maxBatchSize: 1,
    maxPendingEntries: 2
  });
  const languages = { sourceLanguage: "fr", targetLanguage: "en" };
  const first = queue.request({ text: "Active." }, languages);
  await waitFor(() => releaseFirst !== null);
  const stale = queue.request({ text: "Ancienne." }, languages);
  const staleRejection = assert.rejects(stale, /superseded by newer captions/);
  const recent = queue.request({ text: "Récente." }, languages);
  const newest = queue.request({ text: "Nouvelle." }, languages);

  await staleRejection;
  const releaseActiveRequest = releaseFirst as (() => void) | null;

  if (!releaseActiveRequest) {
    throw new Error("Expected the first analysis request to be active");
  }

  releaseActiveRequest();
  await Promise.all([first, recent, newest]);
});

function createResponse(
  request: AnalyzeSubtitlesRequest,
  analysisId: string
): AnalyzeSubtitlesResponse {
  return {
    schemaVersion: "1.0",
    analysisId,
    sourceLanguage: request.sourceLanguage,
    targetLanguage: request.targetLanguage,
    provider: { name: "fixture", model: "test-only" },
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
}

async function waitFor(predicate: () => boolean): Promise<void> {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (predicate()) {
      return;
    }

    await new Promise((resolve) => setTimeout(resolve, 1));
  }

  throw new Error("Timed out waiting for test condition");
}
