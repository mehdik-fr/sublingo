import {
  requestSubtitleAnalysis,
  SubtitleAnalysisRequestError
} from "./api/backend-client";
import {
  isCancelSubtitleAnalysisMessage,
  isAnalyzeSubtitlesMessage,
  type AnalyzeSubtitlesMessageResponse
} from "./api/messages";

const activeRequests = new Map<string, AbortController>();

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (isCancelSubtitleAnalysisMessage(message)) {
    activeRequests.get(message.requestId)?.abort();
    return false;
  }

  if (!isAnalyzeSubtitlesMessage(message)) {
    return false;
  }

  const controller = new AbortController();
  activeRequests.get(message.requestId)?.abort();
  activeRequests.set(message.requestId, controller);

  void requestSubtitleAnalysis(message.request, { signal: controller.signal })
    .then((analysis) => {
      const response: AnalyzeSubtitlesMessageResponse = {
        ok: true,
        analysis
      };
      sendResponse(response);
    })
    .catch((error: unknown) => {
      const response: AnalyzeSubtitlesMessageResponse = {
        ok: false,
        error: error instanceof Error ? error.message : "Subtitle analysis backend unavailable",
        errorCode:
          error instanceof SubtitleAnalysisRequestError ? error.code : "unavailable"
      };
      sendResponse(response);
    })
    .finally(() => {
      if (activeRequests.get(message.requestId) === controller) {
        activeRequests.delete(message.requestId);
      }
    });

  return true;
});
