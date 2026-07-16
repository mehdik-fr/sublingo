import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from time import perf_counter

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
EVALUATION_DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.domain.analysis import AnalysisBatch, SubtitleCue  # noqa: E402
from app.providers.base import ProviderError  # noqa: E402
from app.providers.ollama import OllamaAnalysisProvider  # noqa: E402


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate an already-installed Ollama model without downloading weights."
    )
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=EVALUATION_DIRECTORY / "fixtures" / "multilingual.json",
    )
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    model_record = find_model_record(arguments.model)

    if not model_record["commercialUse"]:
        raise SystemExit(
            f"Model '{arguments.model}' is excluded because its recorded license "
            "is not compatible with potential commercial use."
        )

    cases = load_cases(arguments.dataset)

    if arguments.limit is not None:
        cases = cases[: arguments.limit]

    if not cases:
        raise SystemExit("Evaluation dataset is empty")

    provider = OllamaAnalysisProvider(
        base_url="http://127.0.0.1:11434",
        model=arguments.model,
        timeout_seconds=arguments.timeout,
    )
    started_at = perf_counter()
    analyzed_cues = []
    batch_latencies = []
    try:
        for (source_language, target_language), pair_cases in group_by_language_pair(cases):
            batch = AnalysisBatch(
                source_language=source_language,
                target_language=target_language,
                cues=tuple(
                    SubtitleCue(
                        cue_id=case["id"],
                        text=case["source"],
                        context_before=(
                            pair_cases[index - 1]["source"] if index > 0 else None
                        ),
                        context_after=(
                            pair_cases[index + 1]["source"]
                            if index + 1 < len(pair_cases)
                            else None
                        ),
                    )
                    for index, case in enumerate(pair_cases)
                ),
            )
            batch_started_at = perf_counter()
            analyzed_cues.extend(provider.analyze_batch(batch))
            batch_latencies.append(perf_counter() - batch_started_at)
    except ProviderError as error:
        elapsed_seconds = perf_counter() - started_at
        emit_report(
            {
                "model": model_record,
                "environment": "local-ollama-cpu-screening",
                "caseCount": len(cases),
                "elapsedSeconds": round(elapsed_seconds, 3),
                "secondsPerCue": round(elapsed_seconds / len(cases), 3),
                "structuredOutputRate": 0.0,
                "expectedSignalRecall": None,
                "segmentRecall": None,
                "partOfSpeechAccuracy": None,
                "romanizationAccuracy": None,
                "error": str(error),
                "results": [],
            },
            arguments.output,
        )
        raise SystemExit(2)

    elapsed_seconds = perf_counter() - started_at
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
        expected_segments = case.get("expectedSegments", [])

        for expected_segment in expected_segments:
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

            if matching_segment is not None:
                segment_hits += 1

            expected_part_of_speech = expected_segment.get("partOfSpeech")

            if expected_part_of_speech:
                part_of_speech_count += 1
                actual_values = {
                    feature.value.casefold()
                    for feature in (matching_segment.grammar if matching_segment else ())
                    if normalized_grammar_name(feature.name) in {"partofspeech", "type"}
                }

                if expected_part_of_speech.casefold() in actual_values:
                    part_of_speech_hits += 1

            if expected_segment.get("romanizationRequired") is not None:
                romanization_count += 1
                has_romanization = bool(
                    matching_segment and matching_segment.romanization
                )

                if has_romanization == expected_segment["romanizationRequired"]:
                    romanization_hits += 1

        results.append(
            {
                "id": cue.cue_id,
                "sourceLanguage": case["sourceLanguage"],
                "targetLanguage": case["targetLanguage"],
                "source": cue.source_text,
                "reference": case["reference"],
                "translation": primary.text,
                "expectedSignals": expected_signals,
                "matchedSignals": hits,
                "segments": [
                    {
                        "surface": segment.surface,
                        "kind": segment.kind.value,
                        "romanization": segment.romanization,
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

    report = {
        "model": model_record,
        "environment": "local-ollama-cpu-screening",
        "caseCount": len(cases),
        "elapsedSeconds": round(elapsed_seconds, 3),
        "secondsPerCue": round(elapsed_seconds / len(cases), 3),
        "structuredOutputRate": len(analyzed_cues) / len(cases),
        "expectedSignalRecall": signal_hits / signal_count if signal_count else None,
        "segmentRecall": segment_hits / segment_count if segment_count else None,
        "partOfSpeechAccuracy": (
            part_of_speech_hits / part_of_speech_count if part_of_speech_count else None
        ),
        "romanizationAccuracy": (
            romanization_hits / romanization_count if romanization_count else None
        ),
        "batchLatencySeconds": [round(value, 3) for value in batch_latencies],
        "batchLatencyP50Seconds": percentile(batch_latencies, 0.5),
        "batchLatencyP95Seconds": percentile(batch_latencies, 0.95),
        "results": results,
    }
    emit_report(report, arguments.output)


def emit_report(report: dict, output_path: Path | None) -> None:
    serialized_report = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    print(serialized_report, end="")

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized_report, encoding="utf-8")


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
        if record["ollamaName"] == model_name:
            return record

    raise SystemExit(
        f"Model '{model_name}' is not registered. Review its license before adding it; "
        "the evaluator will not download it."
    )


if __name__ == "__main__":
    main()
