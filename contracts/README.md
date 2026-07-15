# API contracts

`openapi.json` is generated from the FastAPI application and is the canonical
boundary between the backend and browser extension.

From the repository root, export the schema with the backend virtual environment:

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\export_openapi.py
```

Then regenerate the TypeScript declarations:

```powershell
npm run contract:generate
```

Generated files are committed so contract changes remain visible in reviews.
