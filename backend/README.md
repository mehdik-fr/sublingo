# Sublingo Backend

FastAPI backend for versioned subtitle analysis.

The backend exists so the browser extension can stay lightweight while translation and language analysis run outside the content script.

The runtime provider uses an explicitly provisioned Ollama or self-hosted vLLM model.
Deterministic responses and translations are confined to automated tests and are not
a production fallback. Neither provider invokes a model download endpoint.

## Current Scope

- Liveness endpoint at `GET /health`
- Provider/model readiness endpoint at `GET /ready`
- Versioned batch endpoint at `POST /v1/subtitles/analyze`
- Provider-independent response contract with multilingual optional fields
- Configurable local Ollama or hosted vLLM endpoint
- Strict JSON-schema output for the vLLM provider
- Cancellation-aware asynchronous inference with bounded concurrency
- Bounded request bodies and a small in-process pilot rate limit
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
- Earlier local CPU YouTube tests returned valid interactive results in 81-89 seconds,
  while two other generations were rejected after 88-139 seconds. This remains a
  historical CPU/Ollama limitation, not a production latency target.
- The target product architecture is a self-hosted backend using a commercially
  compatible open-weight model on GPU infrastructure.
- Production authentication, distributed rate limiting, backend caching, and full
  metrics are not implemented yet. CORS, a single-process pilot rate limiter,
  bounded request bodies, request IDs, and metadata-only request logs provide a
  minimum temporary deployment baseline.

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

The development default targets `qwen2.5:7b` through local Ollama. Override the
endpoint or model with:

```powershell
$env:SUBLINGO_OLLAMA_MODEL = "qwen2.5:7b"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8765
```

Optional variables are `SUBLINGO_OLLAMA_BASE_URL` and
`SUBLINGO_OLLAMA_TIMEOUT_SECONDS`. The provider checks `/api/tags` first and fails
with an explicit error if the requested model is absent. It never invokes a model
download.

For a self-hosted vLLM runtime that has already loaded an approved model:

```powershell
$env:SUBLINGO_ANALYSIS_PROVIDER = "vllm"
$env:SUBLINGO_VLLM_BASE_URL = "http://127.0.0.1:8001"
$env:SUBLINGO_VLLM_MODEL = "Qwen/Qwen3.5-9B"
$env:SUBLINGO_VLLM_REVISION = "c202236235762e1c871ad0ccb60c8ee5ba337b9a"
uvicorn app.main:app --host 127.0.0.1 --port 8765
```

This provider checks `/v1/models` and sends a strict JSON schema to the local vLLM
OpenAI-compatible protocol. It does not call OpenAI or another commercial API.

Deployment variables:

- `SUBLINGO_ENVIRONMENT`: `development`, `staging`, `production`, or `test`;
- `SUBLINGO_ALLOWED_ORIGINS`: comma-separated exact origins; required for staging
  and production;
- `SUBLINGO_ALLOWED_ORIGIN_REGEX`: optional only when a reviewed regex is needed;
- `SUBLINGO_MAX_REQUEST_BODY_BYTES`: defaults to 262144 bytes, large enough for the
  maximum current OpenAPI batch while remaining bounded;
- `SUBLINGO_RATE_LIMIT_REQUESTS_PER_MINUTE`: per-process pilot limit for analysis;
- `SUBLINGO_ANALYSIS_PROVIDER`: `ollama` or `vllm`; paid providers are rejected;
- `SUBLINGO_OLLAMA_BASE_URL`, `SUBLINGO_OLLAMA_MODEL`, and
  `SUBLINGO_OLLAMA_TIMEOUT_SECONDS`: transitional local inference settings;
- `SUBLINGO_VLLM_BASE_URL`, `SUBLINGO_VLLM_MODEL`, `SUBLINGO_VLLM_REVISION`,
  `SUBLINGO_VLLM_TIMEOUT_SECONDS`, `SUBLINGO_VLLM_MAX_TOKENS`, and
  `SUBLINGO_VLLM_MAX_CONCURRENCY`: self-hosted inference settings.

Request logs contain only request ID, method, path, status, and duration. Subtitle
text and YouTube history are not logged.

Then open:

```txt
http://127.0.0.1:8765/health
```

`/health` never contacts the inference runtime. `/ready` checks that the configured
runtime is reachable and that the configured model is already loaded; it still never
downloads a model.

## Container build

The root Dockerfile packages only the API. It runs as a non-root user and contains
no model weights:

```powershell
docker build --tag sublingo-backend:local .
```

Production configuration is illustrated in `backend.env.example`. Staging and
production require an exact extension origin or a reviewed origin regex. The vLLM
port should remain private; only the FastAPI port is exposed. The temporary RunPod
pilot and its teardown procedure are documented in
[`deployment/runpod/README.md`](deployment/runpod/README.md).

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

The evaluation harness only accepts registered, commercially compatible models. It
supports already-installed local Ollama models and explicitly provisioned hosted vLLM
models. See [evaluation/README.md](evaluation/README.md).
The hosted architecture questions and benchmark requirements are documented in
[../docs/hosted-inference-next-steps.md](../docs/hosted-inference-next-steps.md).
The proposed production service boundary and hosting options are documented in
[../docs/production-hosting-architecture.md](../docs/production-hosting-architecture.md).
