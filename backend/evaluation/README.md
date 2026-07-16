# Open-weight model evaluation

This harness evaluates structured subtitle analysis through local Ollama or a
self-hosted vLLM server. It never downloads weights itself. Ollama candidates must
already be installed; starting vLLM and provisioning an allow-listed model are
separate, explicit operator actions.

The registry blocks candidates whose recorded license is not compatible with
potential commercial use. Hosted candidates are also pinned to reviewed upstream
revisions in `models.json`.

## Local CPU screening

From `backend/`, run a one-case smoke evaluation with:

```powershell
.\.venv\Scripts\python.exe -B evaluation\run_model_evaluation.py `
  --provider ollama --model qwen2.5:7b --limit 1 --repeat 1
```

Local CPU results validate the contract and basic quality only; they are not useful
production latency estimates.

## Hosted vLLM comparison

After an approved model is already loaded on the RunPod pilot's
`127.0.0.1:18001`, run:

```bash
python -B evaluation/run_model_evaluation.py \
  --provider vllm \
  --model Qwen/Qwen3.5-9B \
  --revision c202236235762e1c871ad0ccb60c8ee5ba337b9a \
  --base-url http://127.0.0.1:18001 \
  --environment runpod-a40-pilot \
  --gpu-name "NVIDIA A40" \
  --gpu-vram-gb 48 \
  --hourly-cost-usd 0.44 \
  --warmup-runs 1 --repeat 3 \
  --output evaluation/results/qwen3.5-9b-runpod.json
```

Repeat with the exact `Qwen/Qwen3-14B` registry revision. Use the same GPU,
dataset, sampling configuration, warmup count, and repeat count for a fair comparison.

The default dataset is multilingual and bidirectional: French/English and
English/Korean in both directions. It covers literal translation, ambiguity, idioms,
phrasal expressions, part of speech, and conditional romanization. Reports include:

- strict structured-output validity and exact cue identifiers;
- translation signal, segment, part-of-speech, and romanization scores;
- first-result, p50, p95, per-cue, and throughput measurements;
- model revision, environment, GPU/VRAM, load duration, and estimated inference cost.

The fixture scores are regression signals, not a substitute for human review. The
selected model must also pass the extension test on real YouTube captions.
