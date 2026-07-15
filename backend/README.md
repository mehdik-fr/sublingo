# Sublingo Backend

FastAPI backend for versioned subtitle analysis.

The backend exists so the browser extension can stay lightweight while translation and language analysis run outside the content script.

The runtime provider uses an already-installed Ollama model. Deterministic responses
and translations are confined to automated tests and are not a production fallback.

## Current Scope

- Health check endpoint
- Versioned batch endpoint at `POST /v1/subtitles/analyze`
- Provider-independent response contract with multilingual optional fields
- Configurable local or hosted Ollama endpoint
- No paid API usage
- No automatic model download
- API segments are required for word and expression cards

## Known Limitations

- The service must still be started manually during development.
- Model weights are installed outside the repository and are not packaged with the extension.
- Local Ollama evaluation on this CPU-only Windows computer is useful for contract
  and quality screening, not production latency estimates.
- A simple `Bonjour.` smoke analysis took 73.5 seconds on CPU. This is functionally
  valid but unusable for interactive subtitle latency.
- Word-level coverage and grammatical metadata remain inconsistent with the current
  model; model or pipeline strategy is not selected yet.
- The target product architecture is a self-hosted backend using a commercially
  compatible open-weight model on GPU infrastructure.
- Production authentication, rate limiting, caching, CORS, and observability are not implemented yet.

## Setup

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

For contract and API tests, install the development requirements instead:

```powershell
pip install -r requirements-dev.txt
```

## Run

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8765
```

The default configuration targets `qwen2.5:7b` through local Ollama. Override the
endpoint or model with:

```powershell
$env:SUBLINGO_OLLAMA_MODEL = "qwen2.5:7b"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8765
```

Optional variables are `SUBLINGO_OLLAMA_BASE_URL` and
`SUBLINGO_OLLAMA_TIMEOUT_SECONDS`. The provider checks `/api/tags` first and fails
with an explicit error if the requested model is absent. It never invokes a model
download.

Then open:

```txt
http://127.0.0.1:8765/health
```

## Analyze A Subtitle Batch

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8765/v1/subtitles/analyze `
  -ContentType "application/json" `
  -Body '{"schemaVersion":"1.0","sourceLanguage":"fr","targetLanguage":"en","cues":[{"cueId":"cue-1","text":"Regardez la fleur de plus près."}]}'
```

The response schema is provider-independent and can include primary translations,
word or expression segments, grammar metadata, script variants, and confidence.

## Tests And Contract Generation

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

From the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -B .\backend\scripts\export_openapi.py
npm run contract:generate
```

The local Ollama evaluation harness only accepts registered, commercially compatible
models that are already installed. See [evaluation/README.md](evaluation/README.md).
The hosted architecture questions and benchmark requirements are documented in
[../docs/hosted-inference-next-steps.md](../docs/hosted-inference-next-steps.md).
