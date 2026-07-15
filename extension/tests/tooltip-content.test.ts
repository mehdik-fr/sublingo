import assert from "node:assert/strict";
import test from "node:test";

import { hasRomanization, isRedundantDefinition } from "../src/tooltip-content.ts";

test("hides absent romanization values", () => {
  assert.equal(hasRomanization("-"), false);
  assert.equal(hasRomanization("  "), false);
  assert.equal(hasRomanization("annyeong"), true);
});

test("hides definitions that only repeat the translation", () => {
  assert.equal(isRedundantDefinition("Colors.", "colors"), true);
  assert.equal(isRedundantDefinition("A flower.", "flower"), true);
  assert.equal(
    isRedundantDefinition("To open. For flowers, it can also mean to bloom.", "opens"),
    false
  );
});
