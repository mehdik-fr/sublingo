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
- local dictionary only, no remote translation provider yet

The extension popup now shows:

- whether Sublingo is enabled
- whether the current page is supported
- whether a subtitle layer has been detected on the current page
