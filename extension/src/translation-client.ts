export type SubtitleTranslation = {
  sourceText: string;
  translatedText: string;
  sourceLanguage: string;
  targetLanguage: string;
  provider: string;
  isMock: boolean;
  tokenTranslations: Record<string, string>;
};

export async function translateSubtitleLine(text: string): Promise<SubtitleTranslation> {
  const response = await chrome.runtime.sendMessage({
    type: "SUBLINGO_TRANSLATE_LINE",
    text
  });

  if (!isTranslationMessageResponse(response)) {
    throw new Error("Translation bridge returned an invalid payload");
  }

  if (!response.ok) {
    throw new Error(response.error);
  }

  return response.translation;
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

function isTranslationMessageResponse(
  value: unknown
): value is
  | { ok: true; translation: SubtitleTranslation }
  | { ok: false; error: string } {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const record = value as Record<string, unknown>;

  if (record.ok === true) {
    return isSubtitleTranslation(record.translation);
  }

  return record.ok === false && typeof record.error === "string";
}
