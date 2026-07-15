import assert from "node:assert/strict";
import test from "node:test";

import { buildSubtitleRenderParts } from "../src/segment-matcher.ts";
import type { SubtitleSegmentAnalysis } from "../src/subtitle-analysis-mapper.ts";

test("prefers an expression over overlapping word segments", () => {
  const segments = [
    createSegment("word-de", "de", "word", "of"),
    createSegment("word-plus", "plus", "word", "more"),
    createSegment("expression", "de plus près", "expression", "more closely")
  ];

  const parts = buildSubtitleRenderParts("Regardez de plus près.", segments);
  const interactiveParts = parts.filter((part) => part.segment !== null);

  assert.equal(interactiveParts.length, 1);
  assert.equal(interactiveParts[0].text, "de plus près");
  assert.equal(interactiveParts[0].segment?.segmentId, "expression");
  assert.equal(parts.map((part) => part.text).join(""), "Regardez de plus près.");
});

test("matches repeated surfaces to distinct source occurrences", () => {
  const parts = buildSubtitleRenderParts("oui, oui", [
    createSegment("first", "oui", "word", "yes"),
    createSegment("second", "oui", "word", "yes")
  ]);

  assert.deepEqual(
    parts.filter((part) => part.segment).map((part) => part.segment?.segmentId),
    ["first", "second"]
  );
  assert.equal(parts.map((part) => part.text).join(""), "oui, oui");
});

function createSegment(
  segmentId: string,
  surface: string,
  kind: "word" | "expression",
  translation: string
): SubtitleSegmentAnalysis {
  return {
    segmentId,
    surface,
    kind,
    normalizedForm: null,
    romanization: null,
    scriptVariants: [],
    translations: [
      {
        text: translation,
        kind: "contextual",
        isPrimary: true,
        confidence: null
      }
    ],
    grammar: []
  };
}
