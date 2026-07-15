import type { AnalyzeSubtitlesRequest, AnalyzeSubtitlesResponse } from "./backend-client";

export type AnalyzeSubtitlesMessage = {
  type: "SUBLINGO_ANALYZE_SUBTITLES";
  request: AnalyzeSubtitlesRequest;
};

export type AnalyzeSubtitlesMessageResponse =
  | { ok: true; analysis: AnalyzeSubtitlesResponse }
  | { ok: false; error: string };

export function isAnalyzeSubtitlesMessage(value: unknown): value is AnalyzeSubtitlesMessage {
  if (!isRecord(value) || value.type !== "SUBLINGO_ANALYZE_SUBTITLES") {
    return false;
  }

  const request = value.request;

  return (
    isRecord(request) &&
    request.schemaVersion === "1.0" &&
    typeof request.sourceLanguage === "string" &&
    typeof request.targetLanguage === "string" &&
    Array.isArray(request.cues) &&
    request.cues.length > 0 &&
    request.cues.every(
      (cue) => isRecord(cue) && typeof cue.cueId === "string" && typeof cue.text === "string"
    )
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
