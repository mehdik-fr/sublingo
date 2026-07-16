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

Status: historical prototype. The embedded dictionary proved the interaction model
and is scheduled for removal from the production bundle.

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

Status: in progress. The versioned batch contract, provider protocol, generated
TypeScript declarations, extension migration, guarded Ollama adapter, and local
evaluation harness are now in place.

- [x] Make the extension backend target configurable for local, staging, and production builds
- [x] Package a non-root backend container without model weights or downloads
- [ ] Deploy a hosted backend target after explicit infrastructure approval
- [x] Add a provider interface for translation engines
- [x] Evaluate an already-installed open-weight instruction model for structured subtitle analysis
- [ ] Benchmark shortlisted models on hosted GPU hardware
- [x] Return structured JSON with line translation, token translations, and confidence metadata

## Phase 12 - API-Only Product Data Path

Status: API migration complete; real YouTube lifecycle validation remains. See
[production-data-path-audit.md](production-data-path-audit.md).

- [x] Remove the embedded dictionary from the production extension bundle
- [x] Make API segments the only source for word and expression cards
- [x] Keep deterministic fixtures only in automated tests
- [x] Require a non-fixture provider outside tests
- [ ] Validate the extension on real YouTube watch-page navigation
- [x] Scope caption observation to the YouTube player and reset on SPA navigation
- [x] Cancel obsolete backend requests on video, language, or activation changes
- [ ] Recover cleanly after reactivation while a cancelled client request is still
  executing in the inference runtime

## Phase 13 - Hosted Inference Strategy

Status: discovery required. The local end-to-end path works but is not fast or
reliable enough for product use. See
[hosted-inference-next-steps.md](hosted-inference-next-steps.md).

- [x] Define initial multilingual, bidirectional quality fixtures
- [ ] Compare a single structured model, specialized pipeline, and hybrid fast-path
- [ ] Measure word coverage, expressions, part of speech, and romanization
- [ ] Establish warm p50/p95 latency and throughput targets
- [ ] Estimate VRAM and hosting cost from measured GPU runs
- [ ] Select only commercially compatible open-weight components
- [ ] Host the backend independently from the developer computer

The proposed production boundary and hosting comparison are in
[production-hosting-architecture.md](production-hosting-architecture.md).

## Phase 11 - Cache and Language Analysis

- [x] Cache repeated translations locally
- Cache repeated translations on the backend
- [x] Batch subtitle lines to reduce inference overhead
- Add simple linguistic metadata after contextual translation is stable
- [x] Carry neighboring-cue context and support expression segments in the contract
