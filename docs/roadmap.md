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

## Phase 7 - Local Translation Backend

- Select a free local translation engine
- Add a small FastAPI service
- Start with a mock translation endpoint, then validate real Argos translation

## Phase 8 - Offline Translation Engine Experiment

- Replace the mock backend provider with Argos Translate
- Start with French-to-English before expanding language pairs
- Keep model downloads outside the repository
- Use this phase to validate extension/backend communication, not as the final product architecture

## Phase 9 - Extension Backend Integration

- Send subtitle lines to the local backend
- Make every subtitle word interactive
- Display contextual word translations while keeping hover lightweight
- Keep the pinned tooltip focused on the selected token

## Phase 10 - Hosted Open-Weight Architecture

- Replace the manually started local backend with a hosted backend target
- Add a provider interface for translation engines
- Evaluate an open-weight instruction model for structured subtitle analysis
- Start with a small multilingual model before trying larger hosted models
- Return structured JSON with line translation, token translations, and confidence metadata

## Phase 11 - Cache and Language Analysis

- Cache repeated translations locally
- Cache repeated translations on the backend
- Batch subtitle lines to reduce inference overhead
- Add simple linguistic metadata after contextual translation is stable
- Add expression-level context after token-level translation works reliably
