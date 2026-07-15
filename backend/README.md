# Sublingo Backend

Local FastAPI backend for subtitle translation experiments.

The backend exists so the browser extension can stay lightweight while translation and language analysis run outside the content script.

This backend is currently a local development experiment. It validates the extension/backend boundary, but it is not intended to be the final turnkey runtime because users should not have to start a Python process manually.

## Current Scope

- Health check endpoint
- French-to-English line translation endpoint
- No paid API usage
- Argos Translate model installed outside the repository

## Known Limitations

- The service must be started manually during development.
- Translation models are installed locally and are not packaged with the extension.
- Token translations are still basic and should be replaced by contextual structured analysis.
- The target product architecture is a hosted backend using an open-weight model provider.

## Setup

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
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

## Translate A Line

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8765/translate-line `
  -ContentType "application/json" `
  -Body '{"sourceLanguage":"fr","targetLanguage":"en","text":"Regardez la fleur de plus pres."}'
```

The response uses the local Argos Translate model when it is installed on the machine.
