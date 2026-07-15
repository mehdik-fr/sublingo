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
    ["word", "expression", "punctuation", "whitespace"].includes(String(value.kind)) &&
    isOptionalString(value.normalizedForm) &&
    isOptionalString(value.romanization) &&
    isOptionalArray(value.scriptVariants, isScriptVariant) &&
    Array.isArray(value.translations) &&
    value.translations.every(isTranslation) &&
    isOptionalArray(value.grammar, isGrammarFeature)
  );
}

function isScriptVariant(value: unknown): boolean {
  return isRecord(value) && typeof value.script === "string" && typeof value.text === "string";
}

function isGrammarFeature(value: unknown): boolean {
  return isRecord(value) && typeof value.name === "string" && typeof value.value === "string";
}

function isOptionalString(value: unknown): boolean {
  return value === undefined || value === null || typeof value === "string";
}

function isOptionalArray(value: unknown, validator: (item: unknown) => boolean): boolean {
  return value === undefined || (Array.isArray(value) && value.every(validator));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
