import importlib.util
import unittest
from pathlib import Path


EVALUATION_SCRIPT = (
    Path(__file__).resolve().parents[1] / "evaluation" / "run_model_evaluation.py"
)
SPEC = importlib.util.spec_from_file_location("run_model_evaluation", EVALUATION_SCRIPT)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load the model evaluation module")

EVALUATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVALUATION)


class EvaluationDatasetTests(unittest.TestCase):
    def test_multilingual_fixture_is_bidirectional_and_has_non_latin_cases(self) -> None:
        dataset = EVALUATION_SCRIPT.parent / "fixtures" / "multilingual.json"
        cases = EVALUATION.load_cases(dataset)
        language_pairs = {
            (case["sourceLanguage"], case["targetLanguage"]) for case in cases
        }

        self.assertIn(("fr", "en"), language_pairs)
        self.assertIn(("en", "fr"), language_pairs)
        self.assertIn(("ko", "en"), language_pairs)
        self.assertIn(("en", "ko"), language_pairs)
        self.assertTrue(
            any(
                segment.get("romanizationRequired") is True
                for case in cases
                for segment in case.get("expectedSegments", [])
            )
        )

    def test_groups_cases_without_mixing_language_directions(self) -> None:
        cases = [
            {"id": "one", "sourceLanguage": "fr", "targetLanguage": "en"},
            {"id": "two", "sourceLanguage": "en", "targetLanguage": "fr"},
            {"id": "three", "sourceLanguage": "fr", "targetLanguage": "en"},
        ]

        groups = list(EVALUATION.group_by_language_pair(cases))

        self.assertEqual([key for key, _cases in groups], [("fr", "en"), ("en", "fr")])
        self.assertEqual([case["id"] for case in groups[0][1]], ["one", "three"])


if __name__ == "__main__":
    unittest.main()
