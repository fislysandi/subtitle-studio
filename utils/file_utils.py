"""
File Utilities
"""

import os
import shutil
import tempfile
from pathlib import Path


def get_addon_directory() -> str:
    """Get the addon directory"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_addon_models_dir() -> str:
    """Get the models cache directory"""
    models_dir = os.path.join(get_addon_directory(), "models")
    os.makedirs(models_dir, exist_ok=True)
    return models_dir


def get_temp_dir() -> str:
    """Get temporary directory for the addon"""
    temp_dir = os.path.join(tempfile.gettempdir(), "subtitle_editor")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


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
    models_dir = os.path.join(get_addon_directory(), "models")
    if os.path.isdir(models_dir):
        shutil.rmtree(models_dir)
    os.makedirs(models_dir, exist_ok=True)
