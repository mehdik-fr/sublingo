import type { components } from "./generated";

export const DEFAULT_BACKEND_ANALYZE_URL = "http://127.0.0.1:8765/v1/subtitles/analyze";

export type AnalyzeSubtitlesRequest = components["schemas"]["AnalyzeSubtitlesRequest"];
export type AnalyzeSubtitlesResponse = components["schemas"]["AnalyzeSubtitlesResponse"];
export type CueAnalysis = components["schemas"]["CueAnalysisResponse"];

export async function requestSubtitleAnalysis(
  payload: AnalyzeSubtitlesRequest,
  fetcher: typeof fetch = fetch,
  endpoint = DEFAULT_BACKEND_ANALYZE_URL
): Promise<AnalyzeSubtitlesResponse> {
  const response = await fetcher(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Subtitle analysis backend returned ${response.status}`);
  }

  const data = (await response.json()) as unknown;

  if (!isAnalyzeSubtitlesResponse(data)) {
    throw new Error("Subtitle analysis backend returned an invalid payload");
  }

  return data;
}

export function isAnalyzeSubtitlesResponse(value: unknown): value is AnalyzeSubtitlesResponse {
  if (!isRecord(value)) {
    return false;
  }

  return (
    value.schemaVersion === "1.0" &&
    typeof value.analysisId === "string" &&
    typeof value.sourceLanguage === "string" &&
    typeof value.targetLanguage === "string" &&
    isProvider(value.provider) &&
    Array.isArray(value.cues) &&
    value.cues.every(isCueAnalysis)
  );
}

function isProvider(value: unknown): boolean {
  return isRecord(value) && typeof value.name === "string";
}

function isCueAnalysis(value: unknown): value is CueAnalysis {
  return (
    isRecord(value) &&
    typeof value.cueId === "string" &&
    typeof value.sourceText === "string" &&
    Array.isArray(value.translations) &&
    value.translations.every(isTranslation) &&
    Array.isArray(value.segments) &&
    value.segments.every(isSegment)
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

function isSegment(value: unknown): boolean {
  return (
    isRecord(value) &&
    typeof value.segmentId === "string" &&
    typeof value.surface === "string" &&
    Array.isArray(value.translations) &&
    value.translations.every(isTranslation)
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
