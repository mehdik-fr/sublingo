# RunPod GPU pilot report — 2026-07-16

## Decision

The pilot validated the self-hosted deployment path but failed the interactive product
acceptance criteria. `Qwen/Qwen3.5-9B` was the better of the two tested models, but it
is not acceptable as the current end-to-end Sublingo engine: real YouTube cards took
roughly 25 seconds, intermittent `Sublingo unavailable` states occurred, some lexical
words were absent, and completed word cards disappeared when YouTube appended text to
an existing caption.

The result is therefore a deployment checkpoint, not a production model selection.
No paid AI API was introduced and no provider secret was embedded in the extension.

## Pilot envelope and teardown

- RunPod Secure Cloud, EU-SE-1, one on-demand NVIDIA A40 with 48 GB VRAM.
- GPU price: USD 0.44/hour.
- Storage envelope: 50 GB container disk plus 100 GB Pod volume.
- vLLM was private on `127.0.0.1:18001`; only FastAPI port 8765 was proxied over HTTPS.
- The only downloaded weights were the two explicitly approved, revision-pinned Qwen
  models. Weights stayed on the temporary RunPod volume.
- Observed lifetime before deletion: approximately 1.76 hours.
- Estimated GPU cost before provider rounding: USD 0.77.
- Teardown verification: zero RunPod Pods, zero RunPod endpoints, and zero local pilot
  processes after deletion.

## Comparable model results

Both candidates used the same A40, multilingual fixtures, structured schema, warmup,
and three measured repeats.

| Metric | Qwen3.5-9B | Qwen3-14B |
| --- | ---: | ---: |
| Strict JSON validity | 100% | 100% |
| Exact cue identifiers | 100% | 100% |
| Expected translation signals | 72.2% | 55.6% |
| Expected segment recall | 50.0% | 60.0% |
| Part-of-speech accuracy | 71.4% | 71.4% |
| Romanization accuracy | 80.0% | 80.0% |
| Batch latency p50 | 40.136 s | 63.341 s |
| Batch latency p95 | 42.238 s | 74.063 s |
| Per-cue latency p50 | 20.068 s | 31.670 s |
| Per-cue latency p95 | 21.119 s | 37.032 s |
| Throughput | 0.071 cues/s | 0.037 cues/s |
| Measured evaluation inference cost | USD 0.0413 | USD 0.0793 |

The public Qwen3.5 staging endpoint returned a one-cue EN-to-FR smoke analysis in
23.0 seconds and a one-cue FR-to-EN smoke analysis in 25.2 seconds. This confirms the
hosted data path but also confirms that the latency problem is inference-bound, not a
local-PC or extension-only artifact.

Full machine-readable reports are retained in:

- `backend/evaluation/results/qwen3.5-9b-runpod-a40.json`
- `backend/evaluation/results/qwen3-14b-runpod-a40.json`

## Why the real YouTube experience failed

### 1. The timeout margin is too small

The deployed provider timeout was 45 seconds while Qwen3.5 already measured a
42.238-second batch p95 on controlled fixtures. Real captions, two-cue batches, output
variance, and queued work can cross that limit. The staging extension allowed one
retry, which can add more GPU work while newer caption revisions are already waiting.
This explains a credible path to intermittent `Sublingo unavailable` responses even
though health and readiness stayed green.

Increasing the timeout would hide errors but would make the interaction even slower;
it is not the right product fix.

### 2. Segment presence is requested but not guaranteed

The structured schema validates returned segment fields and verifies that each
surface exists in the cue. It does not prove that every lexical token in the source
is covered. The benchmark's 50% segment recall for Qwen3.5 matches the manual report
that some words had no card.

Prompt changes alone cannot provide a hard coverage guarantee. The backend must own
token or character spans and reject or repair incomplete coverage deterministically.
This is deterministic validation, not a production translation dictionary.

### 3. YouTube captions are incremental revisions, not independent sentences

YouTube often renders a caption prefix and appends one or more words to the same
visible line. The current extension keys analysis by the complete text and context.
When the text changes, it starts a new analysis and renders a new token tree. The old
response is stale, so previously translated words disappear while the longer revision
waits or fails.

Caption identity, caption revision, and already confirmed prefix segments must be
separate concepts. A growing cue should preserve completed cards and mark only the new
suffix as pending.

### 4. One generative request does every task on the critical path

Translation, segmentation, expressions, grammar, part of speech, romanization, and
strict JSON are currently generated together. The user cannot see any word card until
the largest combined operation finishes. This couples first-result latency to the
slowest enrichment task and produces much more output than the immediate interaction
needs.

## Recommended target design

The next design should be an incremental two-stage pipeline, measured against explicit
service-level objectives rather than another prompt-only iteration.

### Extension: preserve stable work

1. Assign a stable local caption identity and monotonically increasing revision.
2. Debounce rapid DOM mutations for a short, measured stability window.
3. Compute the longest common source prefix between revisions.
4. Keep translated prefix spans visible and request only missing or invalidated spans.
5. Merge responses by source offsets and revision; never replace a valid prefix just
   because a suffix was appended.
6. Show a pending state only on the new suffix and keep stale-response rejection.
7. Bound the queue and avoid automatic retries that compete with newer revisions.

Synthetic tests must cover `"Regardez les couleurs"` becoming
`"Regardez les couleurs de plus près"` while the first word cards remain interactive.

### Backend contract: make coverage verifiable

Keep `contracts/openapi.json` canonical, but evolve the analysis representation to
include stable character offsets, cue revision, and completeness. The backend should
tokenize or define candidate spans before inference, then require the provider to
annotate those spans. Expressions can overlay several word spans without removing the
underlying word coverage.

Minimum invariants should include:

- every required lexical span is covered exactly once by a word-level result;
- expression spans reference covered word spans;
- every response is tied to the requested cue revision;
- romanization is absent unless real text is supplied;
- one primary word translation is exposed once;
- cue-level translation remains separate from the word card.

### Inference: separate the fast path from enrichment

The first response should contain only the data needed to make visible words useful:
source spans, primary contextual word translations, and confidence. Part of speech can
join the fast path only if the selected implementation meets the latency target.

Grammar, alternative translations, expression overlays, script variants, and more
expensive disambiguation should be an asynchronous enrichment response. The UI can
upgrade an existing card without clearing or moving already usable results.

The next benchmark should compare, without paid AI APIs:

- a smaller commercial-compatible open-weight structured model;
- a dedicated translation model plus a lightweight linguistic annotator;
- a fine-tuned multi-task model with constrained, offset-based output;
- supported quantization and serving runtimes on the same GPU.

Every candidate license must be reverified from an official source before any weight
download. No new model should be downloaded without explicit approval.

### Proposed acceptance targets

- cached word card: p95 below 100 ms;
- uncached first useful word result: p50 below 1.5 s and p95 below 3 s;
- lexical-span coverage: at least 99.5% on the evaluation set;
- strict response and cue-revision validity: 100%;
- no loss of confirmed prefix cards across incremental cue updates;
- backend-unavailable rate below 1% in the controlled YouTube run;
- quality evaluation retained for expressions, POS, and conditional romanization.

These are checkpoint targets, not claims about the current implementation.

## Recommended next checkpoint

Implement incremental caption revision merging and strict span coverage first, using
test fixtures only. This can be validated without renting a GPU and prevents the UI
from discarding useful results regardless of the future model. Then shortlist and
license-check faster inference strategies, request approval for the exact weights, and
rent one bounded GPU only for the comparative benchmark and real YouTube acceptance
test.
