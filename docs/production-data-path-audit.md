# Production data-path audit

This audit records the remaining deterministic dependencies before Sublingo moves
to API-only word and expression analysis.

## Current production dependencies

- `extension/src/content.ts` imports dictionary entry types and calls
  `findEntryAt` while rendering subtitle tokens.
- `extension/src/tokenizer.ts` imports and prepares `extension/src/dictionary.ts`.
- Dictionary matches currently supply translation, grammar, definition, and
  pronunciation to word cards.
- `development` is the backend's default analysis provider and returns hard-coded
  fixture translations when the server starts without configuration.

The deterministic API provider and test fixtures are useful for automated tests,
but they must not be a runtime fallback in a production build.

## Migration boundary

The next checkpoint will:

1. map complete API segments to word and expression cards;
2. match UI selections against segment surfaces and source spans;
3. remove `dictionary.ts` and dictionary matching from the production bundle;
4. move deterministic analysis fixtures under test-only code;
5. require an explicit real provider for a non-test backend process;
6. preserve the model-free test suite through injected fake providers.

The full-line translation remains in the API response for future use, but it is not
displayed inside a word card.

## Validation gates

- no production import of `dictionary.ts`;
- no hard-coded translation fallback in the production bundle;
- French and expression fixtures covered through API response tests;
- a non-Latin fixture verifies conditional romanization;
- local YouTube smoke test with visible native captions;
- no model download and no paid AI API.
