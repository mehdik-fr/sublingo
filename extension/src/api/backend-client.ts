import { BACKEND_ANALYZE_URL, BUILD_CONFIG } from "../build-config.ts";
import type { components } from "./generated";

export const DEFAULT_BACKEND_ANALYZE_URL = BACKEND_ANALYZE_URL;

export type AnalyzeSubtitlesRequest = components["schemas"]["AnalyzeSubtitlesRequest"];
export type AnalyzeSubtitlesResponse = components["schemas"]["AnalyzeSubtitlesResponse"];
export type CueAnalysis = components["schemas"]["CueAnalysisResponse"];

export type SubtitleAnalysisErrorCode =
  | "cancelled"
  | "invalid-response"
  | "rejected"
  | "timeout"
  | "unavailable";

export class SubtitleAnalysisRequestError extends Error {
  readonly code: SubtitleAnalysisErrorCode;
  readonly status: number | undefined;

  constructor(
    message: string,
    code: SubtitleAnalysisErrorCode,
    status?: number
  ) {
    super(message);
    this.name = "SubtitleAnalysisRequestError";
    this.code = code;
    this.status = status;
  }
}

type RequestSubtitleAnalysisOptions = {
  endpoint?: string;
  fetcher?: typeof fetch;
  maxRetries?: number;
  signal?: AbortSignal;
  timeoutMs?: number;
};

export async function requestSubtitleAnalysis(
  payload: AnalyzeSubtitlesRequest,
  options: RequestSubtitleAnalysisOptions = {}
): Promise<AnalyzeSubtitlesResponse> {
  const endpoint = options.endpoint ?? DEFAULT_BACKEND_ANALYZE_URL;
  const fetcher = options.fetcher ?? fetch;
  const maxRetries = options.maxRetries ?? BUILD_CONFIG.maxRetries;
  const timeoutMs = options.timeoutMs ?? BUILD_CONFIG.requestTimeoutMs;
  const controller = new AbortController();
  const abortFromCaller = () => controller.abort(options.signal?.reason);

  if (options.signal?.aborted) {
    controller.abort(options.signal.reason);
  } else {
    options.signal?.addEventListener("abort", abortFromCaller, { once: true });
  }
  const timeoutId = setTimeout(
    () => controller.abort(new DOMException("Request timed out", "TimeoutError")),
    timeoutMs
  );

  try {
    for (let attempt = 0; ; attempt += 1) {
      try {
        const response = await fetcher(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal: controller.signal
        });

        if (!response.ok) {
          if (attempt < maxRetries && isRetryableStatus(response.status)) {
            await waitBeforeRetry(response, controller.signal);
            continue;
          }

          throw new SubtitleAnalysisRequestError(
            `Subtitle analysis backend returned ${response.status}`,
            response.status >= 500 ? "unavailable" : "rejected",
            response.status
          );
        }

        let data: unknown;

        try {
          data = await response.json();
        } catch {
          throw new SubtitleAnalysisRequestError(
            "Subtitle analysis backend returned invalid JSON",
            "invalid-response"
          );
        }

        if (!isAnalyzeSubtitlesResponse(data)) {
          throw new SubtitleAnalysisRequestError(
            "Subtitle analysis backend returned an invalid payload",
            "invalid-response"
          );
        }

        return data;
      } catch (error) {
        if (error instanceof SubtitleAnalysisRequestError) {
          throw error;
        }

        if (controller.signal.aborted) {
          const isTimeout =
            controller.signal.reason instanceof DOMException &&
            controller.signal.reason.name === "TimeoutError";
          throw new SubtitleAnalysisRequestError(
            isTimeout
              ? "Subtitle analysis backend timed out"
              : "Subtitle analysis request cancelled",
            isTimeout ? "timeout" : "cancelled"
          );
        }

        if (attempt >= maxRetries) {
          throw new SubtitleAnalysisRequestError(
            "Subtitle analysis backend unavailable",
            "unavailable"
          );
        }

        await wait(250, controller.signal);
      }
    }
  } finally {
    clearTimeout(timeoutId);
    options.signal?.removeEventListener("abort", abortFromCaller);
  }
}

function isRetryableStatus(status: number): boolean {
  return status === 429 || status === 502 || status === 503 || status === 504;
}

async function waitBeforeRetry(response: Response, signal: AbortSignal): Promise<void> {
  const retryAfter = response.headers.get("Retry-After");
  const seconds = retryAfter === null ? Number.NaN : Number(retryAfter);
  const delayMs = Number.isFinite(seconds)
    ? Math.min(Math.max(seconds * 1000, 0), 1000)
    : 250;
  await wait(delayMs, signal);
}

function wait(delayMs: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const onAbort = () => {
      clearTimeout(timeoutId);
      reject(signal.reason);
    };
    const timeoutId = setTimeout(() => {
      signal.removeEventListener("abort", onAbort);
      resolve();
    }, delayMs);
    signal.addEventListener("abort", onAbort, { once: true });
  });
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
