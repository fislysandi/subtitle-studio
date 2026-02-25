"""Tests for file utility path resolution helpers."""

from pathlib import Path
import importlib.util
import sys
import tempfile
import unittest

try:
    from subtitle_studio.utils.file_utils import (
        ensure_dir,
        get_addon_models_dir,
        resolve_models_dir,
        resolve_temp_dir,
    )
except ImportError:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    module_path = PROJECT_ROOT / "utils" / "file_utils.py"
    spec = importlib.util.spec_from_file_location("subtitle_file_utils", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load file_utils module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ensure_dir = module.ensure_dir
    get_addon_models_dir = module.get_addon_models_dir
    resolve_models_dir = module.resolve_models_dir
    resolve_temp_dir = module.resolve_temp_dir


class TestFileUtilsPaths(unittest.TestCase):
    def test_resolve_models_dir_is_pure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            addon_dir = Path(temp_dir) / "addon"
            models_dir = Path(resolve_models_dir(str(addon_dir)))
            self.assertEqual(models_dir, addon_dir / "models")
            self.assertFalse(models_dir.exists())

    def test_resolve_temp_dir_is_pure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            resolved = Path(resolve_temp_dir(temp_dir))
            self.assertEqual(resolved, Path(temp_dir) / "subtitle_editor")
            self.assertFalse(resolved.exists())

    def test_ensure_dir_creates_resolved_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "nested" / "models"
            self.assertFalse(target.exists())
            ensure_dir(str(target))
            self.assertTrue(target.exists())

    def test_get_addon_models_dir_still_returns_existing_dir(self):
        models_dir = Path(get_addon_models_dir())
        self.assertTrue(models_dir.exists())
        self.assertEqual(models_dir.name, "models")


if __name__ == "__main__":
    unittest.main()
