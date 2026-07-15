import { requestSubtitleAnalysis } from "./api/backend-client";
import {
  isAnalyzeSubtitlesMessage,
  type AnalyzeSubtitlesMessageResponse
} from "./api/messages";

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!isAnalyzeSubtitlesMessage(message)) {
    return false;
  }

  void requestSubtitleAnalysis(message.request)
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
        error: error instanceof Error ? error.message : "Subtitle analysis backend unavailable"
      };
      sendResponse(response);
    });

  return true;
});
