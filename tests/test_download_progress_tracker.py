"""Tests for download progress tracker callback binding."""

from pathlib import Path
import sys
import threading
import unittest

try:
    from subtitle_studio.core.download_manager import create_progress_tracker_class
except ImportError:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from core.download_manager import create_progress_tracker_class


class TestDownloadProgressTracker(unittest.TestCase):
    def test_bound_tracker_uses_explicit_callback(self):
        events = []

        def callback(downloaded, total, desc, elapsed):
            events.append((downloaded, total, desc, elapsed > 0.0))

        tracker_class = create_progress_tracker_class(callback, threading.Event())
        tracker = tracker_class(desc="model.bin", total=100)
        tracker.update(25)

        self.assertEqual(len(events), 1)
        downloaded, total, desc, elapsed_flag = events[0]
        self.assertEqual(downloaded, 25)
        self.assertEqual(total, 100)
        self.assertEqual(desc, "model.bin")
        self.assertTrue(elapsed_flag)


if __name__ == "__main__":
    unittest.main()
