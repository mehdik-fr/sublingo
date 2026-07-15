# Sublingo Backend

FastAPI backend for versioned subtitle analysis.

The backend exists so the browser extension can stay lightweight while translation and language analysis run outside the content script.

The current Argos runtime remains a local development provider. The versioned API,
service layer, and provider boundary are designed to migrate to hosted inference
without changing the extension contract.

## Current Scope

- Health check endpoint
- Versioned batch endpoint at `POST /v1/subtitles/analyze`
- Provider-independent response contract with multilingual optional fields
- Deprecated French-to-English endpoint at `POST /translate-line`
- No paid API usage
- Argos Translate model installed outside the repository

## Known Limitations

- The service must still be started manually during development.
- Translation models are installed locally and are not packaged with the extension.
- The Argos v1 provider returns whole-line translations and no segment analysis.
- On the current Windows development environment, a real Argos smoke request can
  exceed 60 seconds; deterministic tests validate the boundary but do not claim
  production inference latency.
- The target product architecture is a hosted backend using an open-weight model provider.
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

## Install The Translation Model

Argos Translate keeps models outside the repository. Install the French-to-English model once on your machine:

```powershell
python -c "import argostranslate.package; argostranslate.package.update_package_index(); packages = argostranslate.package.get_available_packages(); package = next(item for item in packages if item.from_code == 'fr' and item.to_code == 'en'); argostranslate.package.install_from_path(package.download())"
```

## Run

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8765
```

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

The Argos development provider currently fills the whole-line `translations`
array. Segment and expression analysis are reserved for the hosted provider.

## Legacy Line Translation

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8765/translate-line `
  -ContentType "application/json" `
  -Body '{"sourceLanguage":"fr","targetLanguage":"en","text":"Regardez la fleur de plus pres."}'
```

The response uses the local Argos Translate model when it is installed on the machine.
This endpoint is deprecated and remains available only while the extension migrates.

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
