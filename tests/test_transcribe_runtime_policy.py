"""Tests for transcribe runtime queue-terminal policy."""

import unittest

from core.transcribe_runtime_policy import resolve_terminal_message_type


class TestTranscribeRuntimePolicy(unittest.TestCase):
    def test_ignores_non_terminal_messages(self):
        self.assertIsNone(resolve_terminal_message_type(None, "progress", False))

    def test_accepts_first_terminal_message(self):
        result = resolve_terminal_message_type(None, "error", False)
        self.assertEqual(result, "error")

    def test_keeps_existing_terminal_message(self):
        result = resolve_terminal_message_type("cancelled", "complete", False)
        self.assertEqual(result, "cancelled")

    def test_converts_complete_to_cancelled_when_cancel_requested(self):
        result = resolve_terminal_message_type(None, "complete", True)
        self.assertEqual(result, "cancelled")

    def test_keeps_complete_when_cancel_not_requested(self):
        result = resolve_terminal_message_type(None, "complete", False)
        self.assertEqual(result, "complete")


if __name__ == "__main__":
    unittest.main()
