import type {
  AnalyzeSubtitlesRequest,
  AnalyzeSubtitlesResponse,
  CueAnalysis,
  SubtitleAnalysisErrorCode
} from "./api/backend-client";
import type { AnalyzeSubtitlesMessageResponse } from "./api/messages";
import {
  SubtitleAnalysisQueue,
  type SubtitleLanguagePair
} from "./api/subtitle-analysis-queue";
import {
  mapSubtitleAnalysis,
  type SubtitleTranslation
} from "./subtitle-analysis-mapper";

export type { SubtitleTranslation } from "./subtitle-analysis-mapper";

export class SubtitleTranslationError extends Error {
  readonly code: SubtitleAnalysisErrorCode;

  constructor(message: string, code: SubtitleAnalysisErrorCode) {
    super(message);
    this.name = "SubtitleTranslationError";
    this.code = code;
  }
}

const analysisQueue = new SubtitleAnalysisQueue(sendBatchRequest);
const activeRequestIds = new Set<string>();

export async function translateSubtitleLine(
  text: string,
  languages: SubtitleLanguagePair = { sourceLanguage: "fr", targetLanguage: "en" },
  context: { contextBefore?: string; contextAfter?: string } = {}
): Promise<SubtitleTranslation> {
  const result = await analysisQueue.request({ text, ...context }, languages);
  return mapSubtitleAnalysis(result);
}

export function clearSubtitleTranslationCache(): void {
  analysisQueue.clear();
  activeRequestIds.forEach((requestId) => {
    void chrome.runtime.sendMessage({
      type: "SUBLINGO_CANCEL_SUBTITLE_ANALYSIS",
      requestId
    });
  });
  activeRequestIds.clear();
}

async function sendBatchRequest(request: AnalyzeSubtitlesRequest) {
  const requestId = crypto.randomUUID();
  activeRequestIds.add(requestId);
  let response: unknown;

  try {
    response = await chrome.runtime.sendMessage({
      type: "SUBLINGO_ANALYZE_SUBTITLES",
      requestId,
      request
    });
  } finally {
    activeRequestIds.delete(requestId);
  }

  if (!isMessageResponse(response)) {
    throw new Error("Subtitle analysis bridge returned an invalid payload");
  }

  if (!response.ok) {
    throw new SubtitleTranslationError(response.error, response.errorCode);
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

  return (
    value.ok === false &&
    typeof value.error === "string" &&
    ["cancelled", "invalid-response", "rejected", "timeout", "unavailable"].includes(
      String(value.errorCode)
    )
  );
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
