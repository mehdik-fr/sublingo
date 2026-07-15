# Translation Engine Decision

Sublingo needs full-language subtitle translation without paid API usage during the early development phase.

## Historical Experiment

The first local translation engine target was **Argos Translate**.

Why:

- It can run locally and offline.
- It has a Python package, which fits the planned backend.
- It avoids exposing API keys in the browser extension.
- It keeps early development free from external API costs.
- It can be replaced later if another open-source engine performs better.

## Decision Update

The Argos backend is useful for proving that the extension can call an external translation service, but it is not the target product architecture.

The main limitations are:

- It requires a Python process to be started manually on the user's machine.
- It requires translation models to be installed outside the browser extension.
- It does not make the extension turnkey.
- Word-by-word translation is not context-aware enough for reliable tooltips.
- Chrome extensions cannot directly bundle and run a Python backend.

These constraints make a hosted backend the better product direction. The next architecture should keep the browser extension lightweight, send subtitle lines to a backend, and use an open-weight language model to return structured translation data.

## Target Direction

The next translation architecture should use:

- A hosted Python backend.
- A provider interface so translation engines can be changed without rewriting the extension.
- An open-weight instruction model for contextual subtitle analysis.
- Structured JSON responses containing line translation and token-level translations.
- Request batching and caching to control inference cost.

The first locally available benchmark candidate is **Qwen2.5-7B-Instruct**, exposed
as `qwen2.5:7b` by Ollama. Its recorded Apache 2.0 license is compatible with the
potential commercial direction. The installed `qwen2.5:3b` is excluded by the
evaluation harness because its Qwen Research License is not suitable for that goal.

On the current CPU-only computer, an early four-cue run produced valid structured
output for every cue in about 61 seconds total, with an intentionally simple signal
recall of 0.89. Stricter segment requirements exposed inconsistent confidence,
source-copying, missing segment translations, and an invented cue identifier.
Single-cue attempts took between 85 and 102 seconds. This candidate is useful for
integration screening but is not validated for production quality or latency. GPU
benchmarking and human evaluation are required before model selection.

After serializing inference and normalizing a missing primary marker, a later
`Bonjour.` end-to-end smoke request succeeded with one translated word segment in
73.5 seconds. This confirms integration only; it does not resolve latency, segment
coverage, grammar, expression detection, or multilingual quality.

## Alternatives Considered

### LibreTranslate

LibreTranslate is a self-hosted translation API built around Argos Translate.

It remains a strong option if Sublingo later needs a standalone translation service, but using Argos directly keeps the first backend simpler.

### OPUS-MT / Helsinki-NLP

OPUS-MT models are useful candidates for quality comparisons, especially if Argos performs poorly for a specific language pair.

They are not the first implementation target because setup and inference code would add more complexity.

### NLLB

NLLB covers many languages and can be powerful, but the available Meta model license is not ideal for a product that may later become commercial.

It is not a first implementation target.

## Historical Implementation Sequence

1. Add a FastAPI backend with a mock translation endpoint.
2. Connect the extension to the local backend.
3. Replace the mock provider with Argos Translate.
4. Start with French-to-English because the local model is easier to validate.
5. Add extension batching, prefetching, and context-sensitive caching.
6. Use the local workflow to validate extension/backend integration.
7. Add an Ollama adapter that refuses absent models instead of downloading them.
8. Compare commercially compatible open-weight candidates using the same structured response contract.
9. Benchmark the shortlist on self-hosted GPU infrastructure before selecting a model.

Steps 1–7 established the architecture and the Argos path has since been removed.
The active work now starts with structured open-weight evaluation and hosted GPU
readiness.

## Accepted Limitations

- The first real translation target is French-to-English.
- Translation quality is only lightly evaluated for now.
- Models are not committed to the repository.
- The first workflow targets local development, not production hosting.
- The current backend is not intended to be the final turnkey extension architecture.
