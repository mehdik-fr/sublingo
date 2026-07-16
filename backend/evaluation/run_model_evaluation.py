import argparse
import asyncio
import json
import sys
from collections import OrderedDict
from pathlib import Path
from time import perf_counter

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
EVALUATION_DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.domain.analysis import AnalysisBatch, AnalyzedCue, SubtitleCue  # noqa: E402
from app.providers.ollama import OllamaAnalysisProvider  # noqa: E402
from app.providers.vllm import VllmAnalysisProvider  # noqa: E402
from app.services.subtitle_analysis import (  # noqa: E402
    InvalidProviderResponseError,
    ProviderUnavailableError,
    SubtitleAnalysisService,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate an explicitly provisioned open-weight model. "
            "The evaluator never downloads model weights."
        )
    )
    parser.add_argument("--provider", choices=("ollama", "vllm"), default="ollama")
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--revision", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--max-concurrency", type=int, default=2)
    parser.add_argument("--warmup-runs", type=int, default=1)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--environment", default="local-ollama-cpu-screening")
    parser.add_argument("--gpu-name", default=None)
    parser.add_argument("--gpu-vram-gb", type=float, default=None)
    parser.add_argument("--model-load-seconds", type=float, default=None)
    parser.add_argument("--hourly-cost-usd", type=float, default=0.0)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=EVALUATION_DIRECTORY / "fixtures" / "multilingual.json",
    )
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    validate_arguments(arguments)
    raise SystemExit(asyncio.run(run(arguments)))


async def run(arguments: argparse.Namespace) -> int:
    model_record = find_model_record(arguments.model)

    if not model_record["commercialUse"]:
        raise SystemExit(
            f"Model '{arguments.model}' is excluded because its recorded license "
            "is not compatible with potential commercial use."
        )

    if arguments.provider == "vllm":
        expected_revision = model_record.get("revision")

        if not expected_revision or arguments.revision != expected_revision:
            raise SystemExit(
                f"Hosted model '{arguments.model}' must use the reviewed revision "
                f"'{expected_revision}'."
            )

    cases = load_cases(arguments.dataset)

    if arguments.limit is not None:
        cases = cases[: arguments.limit]

    if not cases:
        raise SystemExit("Evaluation dataset is empty")

    provider = create_provider(arguments)
    service = SubtitleAnalysisService(provider)
    started_at = perf_counter()
    warmup_latencies: list[float] = []
    batch_latencies: list[float] = []
    per_cue_latencies: list[float] = []
    analyzed_cues: list[AnalyzedCue] = []

    try:
        await service.check_readiness()
        first_group = next(iter(group_by_language_pair(cases)))[1]

        for _ in range(arguments.warmup_runs):
            warmup_batch = make_batch(first_group)
            warmup_started = perf_counter()
            await service.analyze(warmup_batch)
            warmup_latencies.append(perf_counter() - warmup_started)

        for repeat_index in range(arguments.repeat):
            for _language_pair, pair_cases in group_by_language_pair(cases):
                batch = make_batch(pair_cases)
                batch_started = perf_counter()
                result = await service.analyze(batch)
                latency = perf_counter() - batch_started
                batch_latencies.append(latency)
                per_cue_latencies.append(latency / len(pair_cases))

                if repeat_index == 0:
                    analyzed_cues.extend(result.cues)
    except (ProviderUnavailableError, InvalidProviderResponseError) as error:
        elapsed_seconds = perf_counter() - started_at
        report = failed_report(
            arguments=arguments,
            model_record=model_record,
            case_count=len(cases),
            elapsed_seconds=elapsed_seconds,
            error=str(error),
        )
        emit_report(report, arguments.output)
        return 2

    elapsed_seconds = perf_counter() - started_at
    scoring = score_outputs(analyzed_cues, cases)
    inference_seconds = sum(batch_latencies)
    output_bytes = len(
        json.dumps(scoring["results"], ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    )
    report = {
        "schemaVersion": "1.0",
        "model": {**model_record, "revision": arguments.revision},
        "provider": arguments.provider,
        "environment": arguments.environment,
        "gpu": {
            "name": arguments.gpu_name,
            "vramGB": arguments.gpu_vram_gb,
        },
        "caseCount": len(cases),
        "repeatCount": arguments.repeat,
        "requestCount": len(batch_latencies),
        "elapsedSeconds": round(elapsed_seconds, 3),
        "modelLoadSeconds": arguments.model_load_seconds,
        "warmupLatencySeconds": [round(value, 3) for value in warmup_latencies],
        "timeToFirstResultSeconds": (
            round(batch_latencies[0], 3) if batch_latencies else None
        ),
        "batchLatencySeconds": [round(value, 3) for value in batch_latencies],
        "batchLatencyP50Seconds": percentile(batch_latencies, 0.5),
        "batchLatencyP95Seconds": percentile(batch_latencies, 0.95),
        "perCueLatencyP50Seconds": percentile(per_cue_latencies, 0.5),
        "perCueLatencyP95Seconds": percentile(per_cue_latencies, 0.95),
        "cuesPerSecond": (
            round((len(cases) * arguments.repeat) / inference_seconds, 3)
            if inference_seconds
            else None
        ),
        "outputBytes": output_bytes,
        "hourlyCostUSD": arguments.hourly_cost_usd,
        "estimatedInferenceCostUSD": round(
            inference_seconds / 3600 * arguments.hourly_cost_usd,
            6,
        ),
        **{key: value for key, value in scoring.items() if key != "results"},
        "results": scoring["results"],
    }
    emit_report(report, arguments.output)
    return 0


def create_provider(arguments: argparse.Namespace):
    if arguments.provider == "ollama":
        return OllamaAnalysisProvider(
            base_url=arguments.base_url or "http://127.0.0.1:11434",
            model=arguments.model,
            timeout_seconds=arguments.timeout,
        )

    return VllmAnalysisProvider(
        base_url=arguments.base_url or "http://127.0.0.1:8001",
        model=arguments.model,
        revision=arguments.revision,
        timeout_seconds=arguments.timeout,
        max_tokens=arguments.max_tokens,
        max_concurrency=arguments.max_concurrency,
    )


def make_batch(cases: list[dict]) -> AnalysisBatch:
    return AnalysisBatch(
        source_language=cases[0]["sourceLanguage"],
        target_language=cases[0]["targetLanguage"],
        cues=tuple(
            SubtitleCue(
                cue_id=case["id"],
                text=case["source"],
                context_before=cases[index - 1]["source"] if index > 0 else None,
                context_after=(
                    cases[index + 1]["source"] if index + 1 < len(cases) else None
                ),
            )
            for index, case in enumerate(cases)
        ),
    )


def score_outputs(analyzed_cues: list[AnalyzedCue], cases: list[dict]) -> dict:
    cases_by_id = {case["id"]: case for case in cases}
    results = []
    signal_hits = 0
    signal_count = 0
    segment_hits = 0
    segment_count = 0
    part_of_speech_hits = 0
    part_of_speech_count = 0
    romanization_hits = 0
    romanization_count = 0

    for cue in analyzed_cues:
        case = cases_by_id[cue.cue_id]
        primary = next(
            (translation for translation in cue.translations if translation.is_primary),
            cue.translations[0],
        )
        normalized_translation = primary.text.casefold()
        expected_signals = case["expectedSignals"]
        hits = [signal for signal in expected_signals if signal.casefold() in normalized_translation]
        signal_hits += len(hits)
        signal_count += len(expected_signals)

        for expected_segment in case.get("expectedSegments", []):
            matching_segment = next(
                (
                    segment
                    for segment in cue.segments
                    if segment.surface.casefold() == expected_segment["surface"].casefold()
                    and segment.kind.value == expected_segment["kind"]
                ),
                None,
            )
            segment_count += 1
            segment_hits += matching_segment is not None
            expected_part_of_speech = expected_segment.get("partOfSpeech")

            if expected_part_of_speech:
                part_of_speech_count += 1
                actual_values = {
                    feature.value.casefold()
                    for feature in (matching_segment.grammar if matching_segment else ())
                    if normalized_grammar_name(feature.name) in {"partofspeech", "type"}
                }
                part_of_speech_hits += expected_part_of_speech.casefold() in actual_values

            if expected_segment.get("romanizationRequired") is not None:
                romanization_count += 1
                has_romanization = bool(matching_segment and matching_segment.romanization)
                romanization_hits += (
                    has_romanization == expected_segment["romanizationRequired"]
                )

        results.append(
            {
                "id": cue.cue_id,
                "translation": primary.text,
                "matchedSignals": hits,
                "segments": [
                    {
                        "surface": segment.surface,
                        "kind": segment.kind.value,
                        "normalizedForm": segment.normalized_form,
                        "romanization": segment.romanization,
                        "confidence": segment.confidence,
                        "translations": [item.text for item in segment.translations],
                        "grammar": [
                            {"name": item.name, "value": item.value}
                            for item in segment.grammar
                        ],
                    }
                    for segment in cue.segments
                ],
            }
        )

    cue_ids = [cue.cue_id for cue in analyzed_cues]
    expected_ids = [case["id"] for case in cases]
    return {
        "structuredOutputRate": len(analyzed_cues) / len(cases),
        "exactCueIdRate": 1.0 if cue_ids == expected_ids else 0.0,
        "expectedSignalRecall": signal_hits / signal_count if signal_count else None,
        "segmentRecall": segment_hits / segment_count if segment_count else None,
        "partOfSpeechAccuracy": (
            part_of_speech_hits / part_of_speech_count if part_of_speech_count else None
        ),
        "romanizationAccuracy": (
            romanization_hits / romanization_count if romanization_count else None
        ),
        "results": results,
    }


def failed_report(
    *,
    arguments: argparse.Namespace,
    model_record: dict,
    case_count: int,
    elapsed_seconds: float,
    error: str,
) -> dict:
    return {
        "schemaVersion": "1.0",
        "model": {**model_record, "revision": arguments.revision},
        "provider": arguments.provider,
        "environment": arguments.environment,
        "caseCount": case_count,
        "elapsedSeconds": round(elapsed_seconds, 3),
        "structuredOutputRate": 0.0,
        "exactCueIdRate": 0.0,
        "expectedSignalRecall": None,
        "segmentRecall": None,
        "partOfSpeechAccuracy": None,
        "romanizationAccuracy": None,
        "error": error,
        "results": [],
    }


def emit_report(report: dict, output_path: Path | None) -> None:
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    summary = {key: value for key, value in report.items() if key not in {"results", "batchLatencySeconds"}}

    if output_path:
        summary["reportPath"] = str(output_path)

    print(json.dumps(summary, indent=2, ensure_ascii=False))


def load_cases(dataset_path: Path) -> list[dict]:
    document = json.loads(dataset_path.read_text(encoding="utf-8"))

    if isinstance(document, list):
        return [
            {**case, "sourceLanguage": "fr", "targetLanguage": "en"}
            for case in document
        ]

    if not isinstance(document, dict) or not isinstance(document.get("cases"), list):
        raise SystemExit("Evaluation dataset must be a case array or an object with cases")

    return document["cases"]


def group_by_language_pair(cases: list[dict]):
    grouped: OrderedDict[tuple[str, str], list[dict]] = OrderedDict()

    for case in cases:
        key = (case["sourceLanguage"], case["targetLanguage"])
        grouped.setdefault(key, []).append(case)

    return grouped.items()


def normalized_grammar_name(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalpha())


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None

    ordered = sorted(values)
    index = round((len(ordered) - 1) * quantile)
    return round(ordered[index], 3)


def find_model_record(model_name: str) -> dict:
    registry_path = EVALUATION_DIRECTORY / "models.json"
    records = json.loads(registry_path.read_text(encoding="utf-8"))

    for record in records:
        aliases = {record.get("id"), record.get("ollamaName"), record["upstreamModel"]}

        if model_name in aliases:
            return record

    raise SystemExit(
        f"Model '{model_name}' is not registered. Review its official license before "
        "adding it; the evaluator never downloads weights."
    )


def validate_arguments(arguments: argparse.Namespace) -> None:
    if arguments.repeat < 1:
        raise SystemExit("--repeat must be at least 1")

    if arguments.warmup_runs < 0:
        raise SystemExit("--warmup-runs cannot be negative")

    if arguments.hourly_cost_usd < 0:
        raise SystemExit("--hourly-cost-usd cannot be negative")


if __name__ == "__main__":
    main()
