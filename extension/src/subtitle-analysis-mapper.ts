import type { SubtitleAnalysisResult } from "./api/subtitle-analysis-queue";

export type SubtitleTranslationCandidate = {
  text: string;
  kind: "contextual" | "literal";
  isPrimary: boolean;
  confidence: number | null;
};

export type SubtitleGrammarFeature = {
  name: string;
  value: string;
};

export type SubtitleScriptVariant = {
  script: string;
  text: string;
};

export type SubtitleSegmentAnalysis = {
  segmentId: string;
  surface: string;
  kind: "word" | "expression" | "punctuation" | "whitespace";
  normalizedForm: string | null;
  romanization: string | null;
  scriptVariants: SubtitleScriptVariant[];
  translations: SubtitleTranslationCandidate[];
  grammar: SubtitleGrammarFeature[];
};

export type SubtitleTranslation = {
  sourceText: string;
  translatedText: string;
  sourceLanguage: string;
  targetLanguage: string;
  provider: string;
  segments: SubtitleSegmentAnalysis[];
};

export function mapSubtitleAnalysis(result: SubtitleAnalysisResult): SubtitleTranslation {
  const primaryTranslation = selectPrimaryTranslation(result.cue.translations);

  return {
    sourceText: result.cue.sourceText,
    translatedText: primaryTranslation?.text ?? "Translation unavailable",
    sourceLanguage: result.sourceLanguage,
    targetLanguage: result.targetLanguage,
    provider: result.provider.model
      ? `${result.provider.name}:${result.provider.model}`
      : result.provider.name,
    segments: (result.cue.segments ?? []).map((segment) => ({
      segmentId: segment.segmentId,
      surface: segment.surface,
      kind: segment.kind,
      normalizedForm: segment.normalizedForm ?? null,
      romanization: segment.romanization ?? null,
      scriptVariants: segment.scriptVariants ?? [],
      translations: (segment.translations ?? []).map((translation) => ({
        text: translation.text,
        kind: translation.kind,
        isPrimary: translation.isPrimary,
        confidence: translation.confidence ?? null
      })),
      grammar: segment.grammar ?? []
    }))
  };
}

export function selectPrimaryTranslation<T extends { isPrimary: boolean }>(
  translations: T[]
): T | null {
  return translations.find((translation) => translation.isPrimary) ?? translations[0] ?? null;
}
