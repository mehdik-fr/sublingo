# Open-weight model evaluation

This harness evaluates structured subtitle analysis through the local Ollama API.
It never downloads a model and refuses candidates that are absent from `ollama list`.

The model registry also blocks candidates whose recorded license is not compatible
with potential commercial use. `qwen2.5:3b` is therefore documented but excluded;
the locally installed `qwen2.5:7b` candidate is Apache 2.0.

From `backend/`, run a one-case CPU smoke evaluation with:

```powershell
.\.venv\Scripts\python.exe -B evaluation\run_model_evaluation.py --model qwen2.5:7b --limit 1
```

Run the complete small fixture set with:

```powershell
.\.venv\Scripts\python.exe -B evaluation\run_model_evaluation.py --model qwen2.5:7b
```

The default dataset is multilingual and bidirectional: French/English and
English/Korean in both directions. It records expected word or expression surfaces,
part of speech, and conditional romanization signals. The report includes per-batch
latency, structured-output validity, primary translations, segment recall,
part-of-speech accuracy, romanization accuracy, and a deliberately simple expected
translation-signal recall. Provider validation failures are emitted as structured
reports with a zero validity rate. Human review remains required before selecting a
product model.

On a CPU-only computer, latency is expected to be much higher than on the eventual
hosted GPU. The local run is useful for contract and quality screening, not for
estimating production response time.
