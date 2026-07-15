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

The extension popup keeps a minimal product surface:

- active/inactive state
- one toggle to enable or pause the subtitle overlay

## Local Backend

The content script can call the local backend at:

```txt
http://127.0.0.1:8765/translate-line
```

The backend currently uses Argos Translate for French-to-English translation when the local model is installed.
