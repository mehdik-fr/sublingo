# Hosted inference: limitations and next steps

## Validated locally

Sublingo now has one production analysis path: the extension sends subtitle cues to
`POST /v1/subtitles/analyze`, and word or expression cards are built from structured
API segments. The embedded dictionary, deterministic runtime provider, Argos path,
and legacy line endpoint have been removed.

The client serializes inference, limits batches, drops stale queued captions, and
caches repeated analyses. The backend also rejects concurrent Ollama inference so a
CPU cannot accumulate an unbounded model backlog.

A real local smoke request using the already-installed `qwen2.5:7b` produced:

- source: `Bonjour.`;
- cue translation: `Hello.`;
- word segment: `Bonjour` -> `Hello`;
- valid structured JSON;
- elapsed time: 73.5 seconds on CPU.

This proves the complete data path, but not product viability.

A later production-like manual checkpoint used the non-root Docker API against the
same host Ollama runtime and a real YouTube TED video with native French captions.
The extension successfully produced interactive analysis, but successful requests
took 81-89 seconds and the segmentation remained too coarse. Two other model
responses were rejected after 88 and 139 seconds with HTTP 502, confirming that
schema validity is still inconsistent.

## Current limitations

- Inference depends on the developer's local Ollama process and model installation.
- CPU latency is far too high for interactive subtitles.
- The current model can group a complete cue into one expression instead of returning
  useful word-level coverage.
- Structured-output reliability is inconsistent: earlier runs produced copied source
  text, missing segment translations, invalid confidence scales, and invented cue IDs.
- Part-of-speech and grammatical features are not reliably populated.
- Romanization behavior has contract and UI coverage but lacks representative model
  evaluation across non-Latin writing systems.
- Expression detection has deterministic matching tests but has not been validated
  against a multilingual human-reviewed dataset.
- The YouTube adapter is still an early visible-caption adapter and needs SPA,
  lifecycle, error-state, and multi-video validation.
- Disabling Sublingo cancels the browser fetch but cannot stop an Ollama inference
  already executing on the server. If the extension is re-enabled before that work
  finishes, new requests receive HTTP 503 from the occupied provider lock and the UI
  displays `Sublingo unavailable`. Recovery/backoff after reactivation remains a
  known bug; it is intentionally not fixed in this checkpoint.
- There is no independently hosted GPU backend, production authentication, rate
  limiting, backend cache, or full metrics/dashboard stack yet. The current
  metadata-only structured request logs are only an observability baseline.

## Required analysis output

Every textual cue must be covered by useful non-overlapping word or expression
segments. Each segment should support:

- exact source surface and normalized form;
- `word` or `expression` kind;
- one primary contextual translation and optional alternatives;
- controlled part of speech such as noun, verb, adjective, or adverb;
- additional grammatical features when useful;
- romanization only when the source writing system benefits from it;
- optional script variants;
- confidence calibrated from 0 to 1;
- exact cue and segment identity without source-text mutation.

The system must eventually support multiple language pairs in both directions. The
evaluation matrix must therefore test source and target direction independently
rather than assuming that a model good at French-to-English is equally good in the
reverse direction.

## Architecture strategies to compare

No strategy is selected yet. The benchmark must compare at least:

### One multilingual structured model

One instruction model performs contextual translation, segmentation, expression
detection, grammar, and romanization in one constrained response.

Potential benefit: the simplest serving and context flow.

Main risks: higher latency, unreliable fine-grained segmentation, and paying the
full generative-model cost for every metadata field.

### Specialized pipeline

A fast translation model handles the cue while language-specific tokenization,
morphology, part-of-speech tagging, and romanization components enrich the result.
Expression detection is handled by a smaller contextual model or dedicated stage.

Potential benefit: predictable segmentation and lower per-stage latency.

Main risks: more operational components, language-specific coverage gaps, and error
propagation between stages.

### Hybrid fast-path

A fast multilingual translation or analysis model handles common cues. A stronger
instruction model is called only for ambiguous wording, expressions, low confidence,
or unsupported metadata.

Potential benefit: better latency/cost balance while retaining contextual quality.

Main risks: routing complexity, confidence calibration, and inconsistent output
between the fast and fallback paths.

## Evaluation requirements

Before downloading or deploying another model, build a licensed-candidate shortlist
from official model sources and estimate weights, quantization, VRAM, context length,
throughput, and hosting cost.

The benchmark dataset must include:

- short and long subtitle cues;
- word-level coverage and overlapping expression candidates;
- idioms and context-dependent words;
- repeated words in one cue;
- French-to-English and English-to-French;
- at least one non-Latin language in both directions;
- part-of-speech and grammar expectations;
- conditional romanization expectations;
- strict JSON, cue-ID, source-preservation, and segment-coverage checks.

Measure at minimum:

- human-reviewed translation and expression quality;
- structured-output validity rate;
- word/expression coverage and part-of-speech accuracy;
- romanization accuracy where applicable;
- warm and cold latency at p50 and p95;
- cues and tokens per second;
- batch-size sensitivity;
- GPU memory and estimated cost per active user-hour;
- cache hit potential on repeated captions.

Provisional product targets should be defined before benchmarking. Interactive
subtitle analysis likely needs a warm response near one second and a low-single-digit
p95, but these thresholds remain product hypotheses until measured on hosted GPU
hardware.

## Recommended execution order

1. Harden and manually validate the YouTube caption lifecycle without changing the
   model.
2. Make backend URL and environment configuration production-ready.
3. Containerize the backend with readiness and no automatic model download.
4. Add backend cache, bounded traffic, safe logs, and latency/validity metrics.
5. Build the multilingual human-reviewed evaluation dataset and scoring tools.
6. Research official licenses and serving requirements for candidate models and
   pipeline components.
7. Compare the single-model, specialized, and hybrid strategies on hosted GPU.
8. Select the architecture from measured quality, latency, operational complexity,
   and real hosting cost.

No paid AI API is part of this plan. No new model weights or paid cloud resources
may be downloaded or created without explicit approval.

The proposed deployable service boundary, serving-engine direction, and current GPU
hosting trade-offs are documented in
[production-hosting-architecture.md](production-hosting-architecture.md).
