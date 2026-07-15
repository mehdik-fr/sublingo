# Chrome Extension Prototype

This folder contains the first Chrome extension shell.

Build it from the repository root:

```bash
npm run build
```

Then load the `extension/` folder in Chrome:

```txt
chrome://extensions
```

Enable Developer mode, choose `Load unpacked`, and select the `extension/` folder.

The extension currently targets:

```txt
http://localhost:8000/demo/
https://www.youtube.com/watch?v=...
```

At this stage, YouTube support is intentionally narrow:

- standard watch pages only
- visible native captions required
- visible native captions are analyzed through the local backend when enabled

The extension popup keeps a minimal product surface:

- active/inactive state
- one toggle to enable or pause the subtitle overlay

## Local Backend

The content script calls the versioned batch endpoint at:

```txt
http://127.0.0.1:8765/v1/subtitles/analyze
```

Requests and responses use the TypeScript declarations generated from
`contracts/openapi.json`. A short queue batches nearby cues, coalesces duplicate
requests, serializes inference, drops stale captions, and caches analyses for 30 minutes.
The cache key includes the language pair and surrounding context.

The production bundle contains no translation dictionary. Word and expression cards
are created exclusively from API segments. The backend uses an already-installed
open-weight model and never invokes a paid AI API or downloads weights automatically.

Run extension tests, type checking, and the production build from the repository
root with:

```bash
npm run check
```

After every build, open `chrome://extensions` and click **Reload** on Sublingo
before refreshing the demo page. Load the `extension/` directory itself, not
`extension/dist/`, because the manifest and popup live at the extension root.
