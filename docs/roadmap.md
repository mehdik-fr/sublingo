# Roadmap

This roadmap is intentionally small and will evolve as the project becomes clearer.

## Phase 1 - Foundation

- Set up a clean repository
- Document the project goal and first scope
- Create a first local subtitle prototype

## Phase 2 - Local Subtitle Prototype

- Build a local test page with sample subtitles
- Detect subtitle lines from the page
- Split subtitles into interactive tokens

## Phase 3 - Chrome Extension Shell

- Add a Manifest V3 extension folder
- Build a TypeScript content script
- Detect the active subtitle cue on the local demo page

## Phase 4 - Tooltip and Dictionary

- Add a small, non-intrusive tooltip
- Use a local French/Korean dictionary
- Start testing tokenizer and lookup behavior

## Phase 5 - Expression Matching

- Detect common multi-word expressions
- Prefer full-expression matches over word-by-word translation

## Phase 6 - YouTube Adapter

- Detect standard YouTube watch pages
- Read the native visible captions from the player
- Reuse the tooltip and token logic on real pages

## Phase 7 - Translation Provider Layer

- Extract dictionary and lookup interfaces
- Add local caching for future translation calls
- Keep the extension usable without remote services

## Phase 8 - Python Backend

- Add a small FastAPI service
- Move richer language logic to Python
- Keep API keys and external services out of the extension
