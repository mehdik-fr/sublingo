from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import HealthResponse, TranslateLineRequest, TranslateLineResponse
from app.translation_service import translate_line

app = FastAPI(
    title="Sublingo Backend",
    version="0.1.0",
    description="Local translation backend for the Sublingo browser extension.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/translate-line", response_model=TranslateLineResponse)
def translate_line_endpoint(request: TranslateLineRequest) -> TranslateLineResponse:
    return translate_line(request)
