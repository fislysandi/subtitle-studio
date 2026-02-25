"""Tests for pure style patch planning helpers."""

from pathlib import Path
import sys
import unittest

try:
    from subtitle_studio.core.style_plan import (
        StylePatch,
        build_style_patch,
        build_style_patch_from_props,
    )
except ImportError:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from core.style_plan import (
        StylePatch,
        build_style_patch,
        build_style_patch_from_props,
    )


class _PropsStub:
    font_size = 42.0
    text_color = (0.9, 0.8, 0.7)
    use_outline_color = False
    outline_color = (0.2, 0.3, 0.4)
    v_align = "BOTTOM"
    wrap_width = 0.66


class TestStylePlan(unittest.TestCase):
    def test_build_style_patch_returns_immutable_patch(self):
        patch = build_style_patch(
            font_size=36,
            text_color=(0.1, 0.2, 0.3),
            use_outline_color=True,
            outline_color=(0.4, 0.5, 0.6),
            v_align="TOP",
            wrap_width=0.8,
        )
        self.assertIsInstance(patch, StylePatch)
        self.assertEqual(patch.text_color_rgba, (0.1, 0.2, 0.3, 1.0))
        self.assertEqual(patch.outline_color_rgba, (0.4, 0.5, 0.6, 1.0))
        self.assertTrue(patch.use_outline)

    def test_build_style_patch_from_props_maps_editor_values(self):
        patch = build_style_patch_from_props(_PropsStub())
        self.assertEqual(patch.font_size, 42.0)
        self.assertEqual(patch.text_color_rgba, (0.9, 0.8, 0.7, 1.0))
        self.assertFalse(patch.use_outline)
        self.assertEqual(patch.v_align, "BOTTOM")
        self.assertAlmostEqual(patch.wrap_width, 0.66)


if __name__ == "__main__":
    unittest.main()
