# Chrome Extension Prototype

This folder contains the first Chrome extension shell.

Build it from the repository root:

```bash
npm run build
```

Then load the complete local build in Chrome:

```txt
chrome://extensions
```

Enable Developer mode, choose `Load unpacked`, and select the `extension/dist/`
folder. The build emits JavaScript, popup assets, and an environment-specific
manifest into that directory.

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

## Backend environments

`npm run build` creates a local build targeting:

```txt
http://127.0.0.1:8765/v1/subtitles/analyze
```

Staging and production builds require an HTTPS origin supplied at build time. No
runtime secret is stored in the extension:

```powershell
$env:SUBLINGO_BACKEND_BASE_URL = "https://staging-api.example.com"
npm run build:staging

$env:SUBLINGO_BACKEND_BASE_URL = "https://api.example.com"
npm run build:production
```

The generated manifest grants access only to the configured backend origin. A
staging or production build fails if the URL is missing, is not HTTPS, or contains a
path. Optional `SUBLINGO_REQUEST_TIMEOUT_MS` and `SUBLINGO_MAX_RETRIES` values are
documented in the root `.env.example`.

Requests and responses use the TypeScript declarations generated from
`contracts/openapi.json`. A short queue batches nearby cues, coalesces duplicate
requests, serializes inference, drops stale captions, cancels obsolete fetches, and
caches analyses for 30 minutes.
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
before refreshing the demo page or YouTube. The source-level
`extension/manifest.json` remains the local manifest template; the
loadable/packageable artifact is `extension/dist/`.
