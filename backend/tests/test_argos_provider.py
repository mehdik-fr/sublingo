import unittest
from unittest.mock import call, patch

from app.domain.analysis import AnalysisBatch, SubtitleCue, TranslationKind
from app.providers.argos import ArgosAnalysisProvider


class ArgosAnalysisProviderTests(unittest.TestCase):
    @patch("app.providers.argos.translate_text")
    def test_maps_each_batch_cue_to_a_whole_line_translation(self, translate_mock) -> None:
        translate_mock.side_effect = ["Look at the flower.", "It opens slowly."]
        batch = AnalysisBatch(
            source_language="fr",
            target_language="en",
            cues=(
                SubtitleCue(cue_id="cue-1", text="Regardez la fleur."),
                SubtitleCue(
                    cue_id="cue-2",
                    text="Elle s'ouvre lentement.",
                    context_before="Regardez la fleur.",
                ),
            ),
        )

        result = ArgosAnalysisProvider().analyze_batch(batch)

        self.assertEqual([cue.cue_id for cue in result], ["cue-1", "cue-2"])
        self.assertEqual(result[0].source_text, "Regardez la fleur.")
        self.assertEqual(result[0].translations[0].text, "Look at the flower.")
        self.assertEqual(result[0].translations[0].kind, TranslationKind.CONTEXTUAL)
        self.assertTrue(result[0].translations[0].is_primary)
        self.assertEqual(result[0].segments, ())
        self.assertEqual(
            translate_mock.call_args_list,
            [
                call("Regardez la fleur.", "fr", "en"),
                call("Elle s'ouvre lentement.", "fr", "en"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
