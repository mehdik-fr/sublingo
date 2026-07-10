# Roadmap

This roadmap is intentionally small and will evolve as the project becomes clearer.

## Phase 1 - Foundation

- Set up a clean repository
- Document the project goal and first scope
- Create a minimal extension architecture

## Phase 2 - Local Subtitle Prototype

- Build a local test page with sample subtitles
- Detect subtitle lines from the page
- Split subtitles into interactive tokens

## Phase 3 - Tooltip and Dictionary

- Add a small, non-intrusive tooltip
- Use a local French/Korean dictionary
- Start testing tokenizer and lookup behavior

## Phase 4 - Expression Matching

- Detect common multi-word expressions
- Prefer full-expression matches over word-by-word translation

## Phase 5 - Python Backend

- Add a small FastAPI service
- Move richer language logic to Python
- Keep API keys and external services out of the extension
