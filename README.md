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

Then load the `extension/` folder from `chrome://extensions`.

The popup exposes a minimal active/inactive toggle backed by extension storage.

When the local backend is running, the extension can request a full-line French-to-English translation from Argos Translate. The tooltip also displays a first token-level translation when the backend can provide one.

This local backend is an integration experiment. It proves the extension can call an external translation layer, but it is not the final turnkey architecture because it requires a Python process and local model setup.

## Planned MVP

- Chrome extension using Manifest V3
- Subtitle detection on a local test page, then YouTube watch pages
- Interactive words and expressions
- Minimal tooltip with translation details
- Small local French/English dictionary for the first version
- Python API later for context-aware language help

## Tech Direction

- TypeScript for the browser extension
- Python and FastAPI for the translation backend
- Argos Translate as the first local integration experiment
- Hosted open-weight model inference as the target product direction
- Lightweight tests as soon as core parsing logic appears

## Status

Local subtitle prototype complete. YouTube caption detection and local backend integration are in progress.

## Roadmap

See [docs/roadmap.md](docs/roadmap.md).

## License

No open-source license has been selected yet while the product direction is being explored.
