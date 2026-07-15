import { readFile } from "node:fs/promises";

const contentScriptPath = new URL("../extension/dist/content.js", import.meta.url);
const contentScript = await readFile(contentScriptPath, "utf8");

if (/^\s*import\s/m.test(contentScript)) {
  throw new Error(
    "extension/dist/content.js contains an ES module import, but Manifest V3 content scripts must be self-contained"
  );
}

console.log("Content script bundle is self-contained.");
