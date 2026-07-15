import argparse
import json
import sys
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
        default=EVALUATION_DIRECTORY / "fixtures" / "fr_en.json",
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

    cases = json.loads(arguments.dataset.read_text(encoding="utf-8"))

    if arguments.limit is not None:
        cases = cases[: arguments.limit]

    if not cases:
        raise SystemExit("Evaluation dataset is empty")

    provider = OllamaAnalysisProvider(
        base_url="http://127.0.0.1:11434",
        model=arguments.model,
        timeout_seconds=arguments.timeout,
    )
    batch = AnalysisBatch(
        source_language="fr",
        target_language="en",
        cues=tuple(
            SubtitleCue(
                cue_id=case["id"],
                text=case["source"],
                context_before=cases[index - 1]["source"] if index > 0 else None,
                context_after=cases[index + 1]["source"] if index + 1 < len(cases) else None,
            )
            for index, case in enumerate(cases)
        ),
    )

    started_at = perf_counter()
    try:
        analyzed_cues = provider.analyze_batch(batch)
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
        results.append(
            {
                "id": cue.cue_id,
                "source": cue.source_text,
                "reference": case["reference"],
                "translation": primary.text,
                "expectedSignals": expected_signals,
                "matchedSignals": hits,
                "segments": [
                    {
                        "surface": segment.surface,
                        "kind": segment.kind.value,
                        "translations": [item.text for item in segment.translations],
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
        "results": results,
    }
    emit_report(report, arguments.output)


def emit_report(report: dict, output_path: Path | None) -> None:
    serialized_report = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    print(serialized_report, end="")

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized_report, encoding="utf-8")


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
