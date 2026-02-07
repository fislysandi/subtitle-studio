"""
File Utilities
"""

import os
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
