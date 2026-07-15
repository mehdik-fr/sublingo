const BACKEND_TRANSLATE_URL = "http://127.0.0.1:8765/translate-line";

type TranslateLineMessage = {
  type: "SUBLINGO_TRANSLATE_LINE";
  text: string;
};

type SubtitleTranslation = {
  sourceText: string;
  translatedText: string;
  sourceLanguage: string;
  targetLanguage: string;
  provider: string;
  isMock: boolean;
  tokenTranslations: Record<string, string>;
};

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!isTranslateLineMessage(message)) {
    return false;
  }

  void fetchSubtitleTranslation(message.text)
    .then((translation) => {
      sendResponse({
        ok: true,
        translation
      });
    })
    .catch((error: unknown) => {
      sendResponse({
        ok: false,
        error: error instanceof Error ? error.message : "Translation backend unavailable"
      });
    });

  return true;
});

async function fetchSubtitleTranslation(text: string): Promise<SubtitleTranslation> {
  const response = await fetch(BACKEND_TRANSLATE_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      sourceLanguage: "fr",
      targetLanguage: "en",
      text
    })
  });

  if (!response.ok) {
    throw new Error(`Translation backend returned ${response.status}`);
  }

  const data = (await response.json()) as unknown;

  if (!isSubtitleTranslation(data)) {
    throw new Error("Translation backend returned an invalid payload");
  }

  return data;
}

function isTranslateLineMessage(value: unknown): value is TranslateLineMessage {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const record = value as Record<string, unknown>;

  return record.type === "SUBLINGO_TRANSLATE_LINE" && typeof record.text === "string";
}

function isSubtitleTranslation(value: unknown): value is SubtitleTranslation {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const record = value as Record<string, unknown>;

  return (
    typeof record.sourceText === "string" &&
    typeof record.translatedText === "string" &&
    typeof record.sourceLanguage === "string" &&
    typeof record.targetLanguage === "string" &&
    typeof record.provider === "string" &&
    typeof record.isMock === "boolean" &&
    isStringRecord(record.tokenTranslations)
  );
}

function isStringRecord(value: unknown): value is Record<string, string> {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  return Object.values(value).every((item) => typeof item === "string");
}
