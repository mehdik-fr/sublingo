from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.contracts.v1 import (
    AnalyzeSubtitlesRequest,
    AnalyzeSubtitlesResponse,
    CueAnalysisResponse,
    GrammaticalFeatureResponse,
    ProviderResponse,
    ScriptVariantResponse,
    SegmentAnalysisResponse,
    TranslationCandidateResponse,
)
from app.domain.analysis import AnalysisBatch, AnalysisResult, SubtitleCue
from app.services.subtitle_analysis import (
    InvalidProviderResponseError,
    ProviderUnavailableError,
    SubtitleAnalysisService,
)

router = APIRouter(prefix="/v1", tags=["subtitle-analysis"])


def get_analysis_service(request: Request) -> SubtitleAnalysisService:
    return request.app.state.analysis_service


@router.post(
    "/subtitles/analyze",
    response_model=AnalyzeSubtitlesResponse,
    response_model_exclude_none=True,
)
def analyze_subtitles(
    payload: AnalyzeSubtitlesRequest,
    service: SubtitleAnalysisService = Depends(get_analysis_service),
) -> AnalyzeSubtitlesResponse:
    batch = AnalysisBatch(
        source_language=payload.source_language,
        target_language=payload.target_language,
        cues=tuple(
            SubtitleCue(
                cue_id=cue.cue_id,
                text=cue.text,
                context_before=cue.context_before,
                context_after=cue.context_after,
            )
            for cue in payload.cues
        ),
    )

    try:
        result = service.analyze(batch)
    except ProviderUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except InvalidProviderResponseError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    return to_response(result)


def to_response(result: AnalysisResult) -> AnalyzeSubtitlesResponse:
    return AnalyzeSubtitlesResponse(
        schema_version="1.0",
        analysis_id=result.analysis_id,
        source_language=result.source_language,
        target_language=result.target_language,
        provider=ProviderResponse(
            name=result.provider.name,
            model=result.provider.model,
            revision=result.provider.revision,
        ),
        cues=[
            CueAnalysisResponse(
                cue_id=cue.cue_id,
                source_text=cue.source_text,
                translations=[
                    TranslationCandidateResponse(
                        text=translation.text,
                        kind=translation.kind.value,
                        is_primary=translation.is_primary,
                        confidence=translation.confidence,
                    )
                    for translation in cue.translations
                ],
                segments=[
                    SegmentAnalysisResponse(
                        segment_id=segment.segment_id,
                        surface=segment.surface,
                        kind=segment.kind.value,
                        normalized_form=segment.normalized_form,
                        romanization=segment.romanization,
                        script_variants=[
                            ScriptVariantResponse(script=variant.script, text=variant.text)
                            for variant in segment.script_variants
                        ],
                        translations=[
                            TranslationCandidateResponse(
                                text=translation.text,
                                kind=translation.kind.value,
                                is_primary=translation.is_primary,
                                confidence=translation.confidence,
                            )
                            for translation in segment.translations
                        ],
                        grammar=[
                            GrammaticalFeatureResponse(name=feature.name, value=feature.value)
                            for feature in segment.grammar
                        ],
                    )
                    for segment in cue.segments
                ],
            )
            for cue in result.cues
        ],
    )
