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
The first Argos adapter supplied whole-line translations only and was a migration
provider rather than the target product engine.

Implementation update: the extension migration is complete. The legacy
`/translate-line` endpoint, Argos adapter, embedded dictionary, and deterministic
runtime provider have been removed. Production word and expression cards now use
only structured API segments.

## Consequences

- Provider and hosting decisions no longer leak into the public API.
- Contract changes are reviewable and can be checked by both Python and TypeScript.
- Batching becomes possible before hosted inference is introduced.
- The completed migration leaves a single public analysis data path.
- Cache, authentication, rate limiting, and production CORS remain later milestones.
