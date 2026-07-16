import type {
  AnalyzeSubtitlesRequest,
  AnalyzeSubtitlesResponse,
  SubtitleAnalysisErrorCode
} from "./backend-client";

export type AnalyzeSubtitlesMessage = {
  type: "SUBLINGO_ANALYZE_SUBTITLES";
  requestId: string;
  request: AnalyzeSubtitlesRequest;
};

export type CancelSubtitleAnalysisMessage = {
  type: "SUBLINGO_CANCEL_SUBTITLE_ANALYSIS";
  requestId: string;
};

export type AnalyzeSubtitlesMessageResponse =
  | { ok: true; analysis: AnalyzeSubtitlesResponse }
  | { ok: false; error: string; errorCode: SubtitleAnalysisErrorCode };

export function isAnalyzeSubtitlesMessage(value: unknown): value is AnalyzeSubtitlesMessage {
  if (!isRecord(value) || value.type !== "SUBLINGO_ANALYZE_SUBTITLES") {
    return false;
  }

  const request = value.request;

  return (
    typeof value.requestId === "string" &&
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

export function isCancelSubtitleAnalysisMessage(
  value: unknown
): value is CancelSubtitleAnalysisMessage {
  return (
    isRecord(value) &&
    value.type === "SUBLINGO_CANCEL_SUBTITLE_ANALYSIS" &&
    typeof value.requestId === "string"
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
