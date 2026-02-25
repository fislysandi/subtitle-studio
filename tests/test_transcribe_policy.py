"""Tests for pure transcription policy helpers."""

from pathlib import Path
import sys
import unittest

try:
    from subtitle_studio.addons.subtitle_studio.core.transcribe_policy import (
        build_relaxed_vad_parameters,
        compute_recall_metrics,
        is_candidate_better,
        is_low_recall,
        should_retry_without_vad,
    )
    from subtitle_studio.addons.subtitle_studio.core.transcriber import (
        build_transcribe_options,
    )
except ImportError:
    try:
        from subtitle_studio.core.transcribe_policy import (
            build_relaxed_vad_parameters,
            compute_recall_metrics,
            is_candidate_better,
            is_low_recall,
            should_retry_without_vad,
        )
        from subtitle_studio.core.transcriber import build_transcribe_options
    except ImportError:
        PROJECT_ROOT = Path(__file__).resolve().parents[1]
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        from core.transcribe_policy import (
            build_relaxed_vad_parameters,
            compute_recall_metrics,
            is_candidate_better,
            is_low_recall,
            should_retry_without_vad,
        )
        from core.transcriber import build_transcribe_options


class _Segment:
    def __init__(self, start: float, end: float, text: str):
        self.start = start
        self.end = end
        self.text = text


class TestTranscribePolicy(unittest.TestCase):
    def test_compute_recall_metrics(self):
        segments = [
            _Segment(0.0, 1.0, "one two"),
            _Segment(1.0, 3.0, "three"),
        ]
        metrics = compute_recall_metrics(segments, audio_duration=10.0)
        self.assertEqual(metrics.segment_count, 2)
        self.assertEqual(metrics.word_count, 3)
        self.assertAlmostEqual(metrics.speech_duration, 3.0)
        self.assertAlmostEqual(metrics.coverage, 0.3)

    def test_low_recall_thresholds_and_retry_without_vad(self):
        low = compute_recall_metrics([_Segment(0.0, 0.4, "few")], audio_duration=120.0)
        self.assertTrue(is_low_recall(120.0, low))
        self.assertTrue(should_retry_without_vad(120.0, low))

    def test_candidate_comparison_prefers_more_words_or_duration(self):
        base = compute_recall_metrics([_Segment(0.0, 1.0, "one")], audio_duration=60.0)
        better = compute_recall_metrics(
            [_Segment(0.0, 2.0, "one two")],
            audio_duration=60.0,
        )
        self.assertTrue(is_candidate_better(base, better))

    def test_build_relaxed_vad_parameters(self):
        params = build_relaxed_vad_parameters(
            {
                "threshold": 0.5,
                "min_speech_duration_ms": 140,
                "min_silence_duration_ms": 900,
                "max_speech_duration_s": 18.0,
                "speech_pad_ms": 400,
            }
        )
        self.assertAlmostEqual(params["threshold"], 0.4)
        self.assertEqual(params["min_speech_duration_ms"], 80)
        self.assertEqual(params["min_silence_duration_ms"], 350)
        self.assertEqual(params["max_speech_duration_s"], 18.0)
        self.assertEqual(params["speech_pad_ms"], 600)

    def test_build_transcribe_options_is_deterministic(self):
        opts = build_transcribe_options(
            language="en",
            translate=True,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters={"threshold": 0.35},
        )
        self.assertEqual(opts["language"], "en")
        self.assertEqual(opts["task"], "translate")
        self.assertEqual(opts["beam_size"], 5)
        self.assertTrue(opts["word_timestamps"])
        self.assertTrue(opts["vad_filter"])
        self.assertEqual(opts["vad_parameters"], {"threshold": 0.35})


if __name__ == "__main__":
    unittest.main()
