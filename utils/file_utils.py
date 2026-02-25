"""
File Utilities
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional


def get_addon_directory() -> str:
    """Get the addon directory"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_models_dir(addon_directory: Optional[str] = None) -> str:
    """Resolve models directory path without mutating filesystem."""
    base_dir = addon_directory or get_addon_directory()
    return os.path.join(base_dir, "models")


def resolve_temp_dir(base_temp_dir: Optional[str] = None) -> str:
    """Resolve addon temp directory path without mutating filesystem."""
    root = base_temp_dir or tempfile.gettempdir()
    return os.path.join(root, "subtitle_editor")


def get_addon_models_dir() -> str:
    """Get the models cache directory"""
    return ensure_dir(resolve_models_dir())


def get_temp_dir() -> str:
    """Get temporary directory for the addon"""
    return ensure_dir(resolve_temp_dir())


def get_temp_filepath(filename: str) -> str:
    """Get a temporary file path"""
    return os.path.join(get_temp_dir(), filename)


def ensure_dir(path: str) -> str:
    """Ensure directory exists"""
    os.makedirs(path, exist_ok=True)
    return path


def is_model_cached(model_name: str) -> bool:
    """Check if model is cached (fast check)"""
    models_dir = get_addon_models_dir()
    model_path = os.path.join(models_dir, model_name)

    # Check for essential files (same logic as DownloadManager)
    # faster-whisper needs model.bin and config.json
    bin_path = os.path.join(model_path, "model.bin")
    config_path = os.path.join(model_path, "config.json")
    has_bin = os.path.exists(bin_path) and os.path.getsize(bin_path) > 1024
    has_config = os.path.exists(config_path) and os.path.getsize(config_path) > 10

    return has_bin and has_config


def clear_models_cache() -> None:
    """Delete and recreate addon model cache directory."""
    models_dir = resolve_models_dir()
    if os.path.isdir(models_dir):
        shutil.rmtree(models_dir)
    os.makedirs(models_dir, exist_ok=True)
