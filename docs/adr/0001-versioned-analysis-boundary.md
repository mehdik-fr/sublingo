# ADR 0001: Versioned subtitle analysis boundary

- Status: accepted
- Date: 2026-07-15

## Context

The prototype couples the extension to a local French-to-English Argos endpoint.
Its response is a string map keyed by normalized words, which cannot reliably
represent duplicate tokens, expressions, non-Latin scripts, or multiple meanings.

## Decision

Sublingo exposes a versioned batch endpoint at `POST /v1/subtitles/analyze`.
Pydantic models generate the canonical OpenAPI contract and TypeScript types are
generated from that artifact. The service depends on an `AnalysisProvider`
protocol rather than a concrete model runtime.

Responses preserve cue and segment order and allow optional romanization, script
variants, grammatical features, and multiple contextual or literal translations.
The first Argos adapter supplies whole-line translations only; it is a development
provider rather than the target product engine.

The legacy `/translate-line` endpoint remains temporarily available and is marked
as deprecated while the extension migrates.

## Consequences

- Provider and hosting decisions no longer leak into the public API.
- Contract changes are reviewable and can be checked by both Python and TypeScript.
- Batching becomes possible before hosted inference is introduced.
- A migration period is required while both endpoints coexist.
- Cache, authentication, rate limiting, and production CORS remain later milestones.
