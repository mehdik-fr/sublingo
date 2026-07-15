from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as v1_router
from app.models import HealthResponse, TranslateLineRequest, TranslateLineResponse
from app.providers.argos import ArgosAnalysisProvider
from app.services.subtitle_analysis import SubtitleAnalysisService
from app.translation_service import translate_line


def create_app(
    analysis_service: SubtitleAnalysisService | None = None,
) -> FastAPI:
    application = FastAPI(
        title="Sublingo Backend",
        version="0.2.0",
        description="Versioned subtitle analysis API for the Sublingo browser extension.",
    )
    application.state.analysis_service = analysis_service or SubtitleAnalysisService(
        ArgosAnalysisProvider()
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    application.include_router(v1_router)

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @application.post("/translate-line", response_model=TranslateLineResponse, deprecated=True)
    def translate_line_endpoint(request: TranslateLineRequest) -> TranslateLineResponse:
        return translate_line(request)

    return application


app = create_app()
