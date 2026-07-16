# Sublingo

Browser extension project for learning languages through interactive subtitles.

> Early-stage project. Built incrementally, with small working steps and clear documentation.

## Goal

Sublingo aims to make video subtitles interactive: users can hover words or expressions to get useful language information without interrupting the video.

The first target is a controlled local test page, then Chrome, then streaming platforms when the core is stable.

## Local Demo

A first local prototype is available in [demo/index.html](demo/index.html).

The page itself only renders plain subtitles over a hosted CC0 sample video. The interactive behavior is now injected by the browser extension so it can be tested independently.

If you are in the folder that contains the project:

```bash
cd sublingo
python -m http.server 8000
```

Then open:

```txt
http://localhost:8000/demo/
```

Opening `demo/index.html` directly can display the video but skip the WebVTT subtitle loading in some browsers. Use the local server during development.

## Chrome Extension Prototype

The first extension shell is available in [extension/](extension/).

Build it before loading the unpacked extension in Chrome:

```bash
npm install
npm run build
```

Then load the generated `extension/dist/` folder from `chrome://extensions`.

The popup exposes a minimal active/inactive toggle backed by extension storage.

When the local backend is running, the extension batches subtitle cues through the
versioned analysis API. Repeated requests are cached and CPU inference is serialized
to prevent subtitle backlogs. Word and expression cards are built only from API
segments; no translation dictionary is embedded in the production extension.

An optional Ollama provider can evaluate an open-weight model that is already
installed on the machine. Sublingo never downloads a model automatically and does
not depend on paid AI APIs. The eventual operating cost is intended to be limited
to self-hosted infrastructure and GPU capacity.

## Planned MVP

- Chrome extension using Manifest V3
- Subtitle detection on a local test page, then YouTube watch pages
- Interactive words and expressions
- Minimal tooltip with translation details
- Contextual word and expression segments supplied by the backend API
- Versioned Python API for context-aware language help

## Tech Direction

- TypeScript for the browser extension
- Python and FastAPI for the translation backend
- Deterministic fixtures isolated to automated tests
- Self-hosted open-weight inference as the target product direction
- OpenAPI as the canonical extension/backend contract
- Lightweight tests as soon as core parsing logic appears

## Status

Local subtitle prototype complete. The extension now uses the versioned batch API
with client-side batching, serialized inference, stale-caption control, and caching.
The end-to-end Ollama path works, but a simple CPU request took 73.5 seconds and
segment granularity remains inconsistent. The API is now container-ready and the
extension has environment-specific local, staging, and production builds. Hosted
GPU and model/pipeline selection remain open. See
[docs/hosted-inference-next-steps.md](docs/hosted-inference-next-steps.md) and
[docs/production-hosting-architecture.md](docs/production-hosting-architecture.md).

## Roadmap

See [docs/roadmap.md](docs/roadmap.md).

## License

No open-source license has been selected yet while the product direction is being explored.
