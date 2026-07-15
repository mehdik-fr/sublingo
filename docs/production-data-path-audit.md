# Production data-path audit

This audit records how the deterministic production dependencies were removed as
Sublingo moved to API-only word and expression analysis.

## Resolved production dependencies

- `extension/src/dictionary.ts` and its dictionary-aware tokenizer were removed.
- `extension/src/content.ts` now matches source spans against API word and expression
  segments and reads translation, grammar, and romanization from those segments.
- The deterministic backend provider was removed from application code.
- Ollama is the only configured runtime analysis provider.
- The deprecated `/translate-line` and its Argos-only data path were removed.

Deterministic fake-provider responses remain useful in automated tests, but no
runtime fallback is shipped in the application.

## Completed migration boundary

The completed migration:

1. maps complete API segments to word and expression cards;
2. matches UI selections against segment surfaces and source spans;
3. removed `dictionary.ts` and dictionary matching from the production bundle;
4. confined deterministic analysis responses to tests;
5. selects a real open-weight provider for a non-test backend process;
6. preserves the model-free test suite through injected fake providers.

The full-line translation remains in the API response for future use, but it is not
displayed inside a word card.

## Validation gates

- [x] no production import of `dictionary.ts`;
- [x] no hard-coded translation fallback in the production bundle;
- [x] French and expression fixtures covered through API response tests;
- [x] a non-Latin fixture verifies conditional romanization;
- [ ] local YouTube smoke test with visible native captions;
- no model download and no paid AI API.
