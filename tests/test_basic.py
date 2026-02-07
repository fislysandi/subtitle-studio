"""
Tests for Subtitle Editor
"""

import unittest


class TestSubtitleIO(unittest.TestCase):
    """Test subtitle import/export"""

    def test_srt_parsing(self):
        """Test SRT file parsing"""
        from ..core.subtitle_io import SubtitleIO, SubtitleEntry

        # This is a mock test - in real tests you'd use actual files
        entry = SubtitleEntry(index=1, start=0.0, end=5.0, text="Hello World")

        self.assertEqual(entry.index, 1)
        self.assertEqual(entry.text, "Hello World")
        self.assertEqual(entry.duration, 5.0)


class TestTranscription(unittest.TestCase):
    """Test transcription functionality"""

    def test_segment_creation(self):
        """Test transcription segment creation"""
        from ..core.transcriber import TranscriptionSegment

        seg = TranscriptionSegment(start=0.0, end=3.5, text="Test subtitle")

        self.assertEqual(seg.start, 0.0)
        self.assertEqual(seg.end, 3.5)
        self.assertEqual(seg.text, "Test subtitle")


if __name__ == "__main__":
    unittest.main()
