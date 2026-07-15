import assert from "node:assert/strict";
import test from "node:test";

import { hasRomanization } from "../src/tooltip-content.ts";

test("hides absent romanization values", () => {
  assert.equal(hasRomanization("-"), false);
  assert.equal(hasRomanization("  "), false);
  assert.equal(hasRomanization("annyeong"), true);
});
