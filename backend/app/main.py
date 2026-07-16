import json
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as v1_router
from app.core.config import Settings
from app.middleware import RateLimitMiddleware, RequestBodyLimitMiddleware
from app.models import HealthResponse, ReadinessResponse
from app.providers.factory import create_analysis_provider
from app.services.subtitle_analysis import ProviderUnavailableError, SubtitleAnalysisService

logger = logging.getLogger("uvicorn.error")
REQUEST_ID_HEADER = "X-Request-ID"


def create_app(
    analysis_service: SubtitleAnalysisService | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    application = FastAPI(
        title="Sublingo Backend",
        version="0.3.0",
        description="Versioned subtitle analysis API for the Sublingo browser extension.",
    )
    resolved_settings = settings or Settings.from_environment()
    application.state.settings = resolved_settings
    application.state.analysis_service = analysis_service or SubtitleAnalysisService(
        create_analysis_provider(resolved_settings)
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.allowed_origins),
        allow_origin_regex=resolved_settings.allowed_origin_regex,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", REQUEST_ID_HEADER],
    )
    application.add_middleware(
        RequestBodyLimitMiddleware,
        max_body_bytes=resolved_settings.max_request_body_bytes,
    )
    application.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=resolved_settings.rate_limit_requests_per_minute,
    )
    application.include_router(v1_router)

    @application.middleware("http")
    async def observe_request(request: Request, call_next):
        request_id = _request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        started_at = perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            _log_request(
                request=request,
                request_id=request_id,
                status_code=500,
                duration_seconds=perf_counter() - started_at,
            )
            raise

        response.headers[REQUEST_ID_HEADER] = request_id
        _log_request(
            request=request,
            request_id=request_id,
            status_code=response.status_code,
            duration_seconds=perf_counter() - started_at,
        )
        return response

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @application.get(
        "/ready",
        response_model=ReadinessResponse,
        responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
    )
    async def readiness(request: Request):
        service: SubtitleAnalysisService = request.app.state.analysis_service

        try:
            await service.check_readiness()
        except ProviderUnavailableError:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "not_ready", "provider": service.provider_name},
            )

        return ReadinessResponse(status="ready", provider=service.provider_name)

    return application


def _request_id(candidate: str | None) -> str:
    if (
        candidate
        and 0 < len(candidate) <= 128
        and candidate.isascii()
        and candidate.isprintable()
        and all(character.isalnum() or character in "-_.:" for character in candidate)
    ):
        return candidate

    return str(uuid4())


def _log_request(
    *,
    request: Request,
    request_id: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "requestId": request_id,
                "method": request.method,
                "path": request.url.path,
                "statusCode": status_code,
                "durationMs": round(duration_seconds * 1000, 2),
            },
            separators=(",", ":"),
        )
    )


app = create_app()
