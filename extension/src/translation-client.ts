import type {
  AnalyzeSubtitlesRequest,
  AnalyzeSubtitlesResponse,
  CueAnalysis
} from "./api/backend-client";
import type { AnalyzeSubtitlesMessageResponse } from "./api/messages";
import {
  SubtitleAnalysisQueue,
  type SubtitleAnalysisResult,
  type SubtitleLanguagePair
} from "./api/subtitle-analysis-queue";

export type SubtitleTranslation = {
  sourceText: string;
  translatedText: string;
  sourceLanguage: string;
  targetLanguage: string;
  provider: string;
  isMock: boolean;
  tokenTranslations: Record<string, string>;
};

const analysisQueue = new SubtitleAnalysisQueue(sendBatchRequest);

export async function translateSubtitleLine(
  text: string,
  languages: SubtitleLanguagePair = { sourceLanguage: "fr", targetLanguage: "en" },
  context: { contextBefore?: string; contextAfter?: string } = {}
): Promise<SubtitleTranslation> {
  const result = await analysisQueue.request({ text, ...context }, languages);
  return toSubtitleTranslation(result);
}

export function prefetchSubtitleLine(
  text: string,
  languages: SubtitleLanguagePair,
  context: { contextBefore?: string; contextAfter?: string } = {}
): void {
  void analysisQueue.request({ text, ...context }, languages).catch(() => {
    // Prefetch failures are intentionally silent; the visible cue retries and
    // reports an error through the normal translation path.
  });
}

export function clearSubtitleTranslationCache(): void {
  analysisQueue.clear();
}

async function sendBatchRequest(request: AnalyzeSubtitlesRequest) {
  const response = (await chrome.runtime.sendMessage({
    type: "SUBLINGO_ANALYZE_SUBTITLES",
    request
  })) as unknown;

  if (!isMessageResponse(response)) {
    throw new Error("Subtitle analysis bridge returned an invalid payload");
  }

  if (!response.ok) {
    throw new Error(response.error);
  }

  return response.analysis;
}

function isMessageResponse(value: unknown): value is AnalyzeSubtitlesMessageResponse {
  if (!isRecord(value)) {
    return false;
  }

  if (value.ok === true) {
    return isAnalyzeSubtitlesResponse(value.analysis);
  }

  return value.ok === false && typeof value.error === "string";
}

function isAnalyzeSubtitlesResponse(value: unknown): value is AnalyzeSubtitlesResponse {
  return (
    isRecord(value) &&
    value.schemaVersion === "1.0" &&
    typeof value.analysisId === "string" &&
    typeof value.sourceLanguage === "string" &&
    typeof value.targetLanguage === "string" &&
    isRecord(value.provider) &&
    typeof value.provider.name === "string" &&
    Array.isArray(value.cues) &&
    value.cues.every(isCueAnalysis)
  );
}

function isCueAnalysis(value: unknown): value is CueAnalysis {
  return (
    isRecord(value) &&
    typeof value.cueId === "string" &&
    typeof value.sourceText === "string" &&
    Array.isArray(value.translations) &&
    value.translations.every(isTranslation) &&
    Array.isArray(value.segments) &&
    value.segments.every(
      (segment) =>
        isRecord(segment) &&
        typeof segment.segmentId === "string" &&
        typeof segment.surface === "string" &&
        Array.isArray(segment.translations) &&
        segment.translations.every(isTranslation)
    )
  );
}

function isTranslation(value: unknown): boolean {
  return (
    isRecord(value) &&
    typeof value.text === "string" &&
    (value.kind === "contextual" || value.kind === "literal") &&
    typeof value.isPrimary === "boolean"
  );
}

function toSubtitleTranslation(result: SubtitleAnalysisResult): SubtitleTranslation {
  const primaryTranslation =
    result.cue.translations.find((translation) => translation.isPrimary) ??
    result.cue.translations[0];
  const tokenTranslations: Record<string, string> = {};

  for (const segment of result.cue.segments ?? []) {
    const segmentTranslations = segment.translations ?? [];
    const translation =
      segmentTranslations.find((candidate) => candidate.isPrimary) ?? segmentTranslations[0];

    if (translation) {
      tokenTranslations[normalizeToken(segment.surface)] = translation.text;
    }
  }

  return {
    sourceText: result.cue.sourceText,
    translatedText: primaryTranslation?.text ?? "Translation unavailable",
    sourceLanguage: result.sourceLanguage,
    targetLanguage: result.targetLanguage,
    provider: result.provider.model
      ? `${result.provider.name}:${result.provider.model}`
      : result.provider.name,
    isMock: result.provider.name === "development",
    tokenTranslations
  };
}

function normalizeToken(value: string): string {
  return value
    .toLocaleLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/['’]/g, "")
    .trim();
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
