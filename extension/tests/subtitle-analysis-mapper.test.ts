import assert from "node:assert/strict";
import test from "node:test";

import type { SubtitleAnalysisResult } from "../src/api/subtitle-analysis-queue.ts";
import { mapSubtitleAnalysis } from "../src/subtitle-analysis-mapper.ts";

test("preserves complete API segment metadata for the word card", () => {
  const result: SubtitleAnalysisResult = {
    sourceLanguage: "ko",
    targetLanguage: "en",
    provider: { name: "ollama", model: "licensed-model" },
    cue: {
      cueId: "cue-1",
      sourceText: "안녕하세요",
      translations: [
        { text: "Hello", kind: "contextual", isPrimary: true, confidence: 0.96 }
      ],
      segments: [
        {
          segmentId: "cue-1:0",
          surface: "안녕하세요",
          kind: "expression",
          normalizedForm: "안녕하다",
          romanization: "annyeonghaseyo",
          scriptVariants: [{ script: "Hang", text: "안녕하세요" }],
          translations: [
            { text: "Hi", kind: "literal", isPrimary: false },
            { text: "Hello", kind: "contextual", isPrimary: true, confidence: 0.94 }
          ],
          grammar: [{ name: "speechLevel", value: "polite" }]
        }
      ]
    }
  };

  const translation = mapSubtitleAnalysis(result);

  assert.equal(translation.provider, "ollama:licensed-model");
  assert.equal(translation.segments[0].romanization, "annyeonghaseyo");
  assert.equal(translation.segments[0].translations.length, 2);
  assert.deepEqual(translation.segments[0].grammar, [
    { name: "speechLevel", value: "polite" }
  ]);
});
