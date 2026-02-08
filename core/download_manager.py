"""
Pure Python download manager - no Blender dependencies.
Implements real progress tracking using custom tqdm class.
"""

import os
import threading
from pathlib import Path
from typing import Optional, Dict, Callable
from dataclasses import dataclass
from enum import Enum

try:
    from huggingface_hub import snapshot_download, hf_hub_download
    from huggingface_hub.utils import are_progress_bars_disabled

    HAS_HF = True
except ImportError:
    HAS_HF = False
    snapshot_download = None
    hf_hub_download = None


class DownloadStatus(Enum):
    """Download status states."""

    PENDING = "pending"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class DownloadProgress:
    """Immutable progress state."""

    status: DownloadStatus
    bytes_downloaded: int
    bytes_total: int
    current_file: str
    message: str

    @property
    def percentage(self) -> float:
        """Progress as 0.0 to 1.0."""
        if self.bytes_total == 0:
            return 0.0
        return min(self.bytes_downloaded / self.bytes_total, 1.0)


class ProgressTracker:
    """
    Custom tqdm-compatible class that captures progress from huggingface_hub.
    
    huggingface_hub uses tqdm internally. By providing our own tqdm_class,
    we intercept all progress updates and forward them to our callback.
    """

    # Class variables for communication with DownloadManager
    _progress_callback: Optional[Callable[[int, int, str], None]] = None
    _cancel_event: Optional[threading.Event] = None
    _lock = threading.RLock()  # Class-level lock for tqdm compatibility

    def __init__(
        self,
        iterable=None,
        desc: str = "",
        total: Optional[int] = None,
        unit: str = "B",
        unit_scale: bool = True,
        unit_divisor: int = 1024,
        **kwargs,
    ):
        """Initialize the progress tracker."""
        self.iterable = iterable
        self.desc = desc or ""
        self.total = total or 0
        self.n = 0
        self.unit = unit
        
        # Get the callback from class variable (set by DownloadManager)
        self._callback = ProgressTracker._progress_callback
        self._cancel_event_ref = ProgressTracker._cancel_event

    @classmethod
    def get_lock(cls):
        """Return the class-level lock (required by huggingface_hub)."""
        return cls._lock

    @classmethod
    def set_lock(cls, lock):
        """Set the class-level lock (tqdm compatibility)."""
        cls._lock = lock

    @classmethod
    def external_write_mode(cls, file=None, nolock=False):
        """Context manager for external writes (tqdm compatibility)."""
        import contextlib
        return contextlib.nullcontext()

    @classmethod
    def write(cls, s, file=None, end="\n", nolock=False):
        """Write to output (tqdm compatibility)."""
        pass

    def __iter__(self):
        """Iterate with progress tracking."""
        if self.iterable is None:
            return self
        for item in self.iterable:
            yield item
            self.update(1)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.close()

    def update(self, n: int = 1):
        """Update progress by n units."""
        self.n += n
        if self._callback:
            self._callback(self.n, self.total, self.desc)

    def set_description(self, desc: str = "", refresh: bool = True):
        """Set the description."""
        self.desc = desc

    def set_postfix(self, **kwargs):
        """Set postfix (ignored)."""
        pass

    def close(self):
        """Close the progress bar."""
        pass

    def refresh(self):
        """Refresh display (no-op)."""
        pass

    @property
    def format_dict(self):
        """Return format dict for compatibility."""
        return {"n": self.n, "total": self.total}


class DownloadManager:
    """
    Manages model downloads with real progress tracking.
    Thread-safe with proper cancellation support.
    """

    # Model name to repo ID mapping
    REPO_MAP: Dict[str, str] = {
        "tiny": "Systran/faster-whisper-tiny",
        "tiny.en": "Systran/faster-whisper-tiny.en",
        "base": "Systran/faster-whisper-base",
        "base.en": "Systran/faster-whisper-base.en",
        "small": "Systran/faster-whisper-small",
        "small.en": "Systran/faster-whisper-small.en",
        "medium": "Systran/faster-whisper-medium",
        "medium.en": "Systran/faster-whisper-medium.en",
        "large-v1": "Systran/faster-whisper-large-v1",
        "large-v2": "Systran/faster-whisper-large-v2",
        "large-v3": "Systran/faster-whisper-large-v3",
        "large": "Systran/faster-whisper-large-v3",
        "distil-small.en": "Systran/faster-distil-whisper-small.en",
        "distil-medium.en": "Systran/faster-distil-whisper-medium.en",
        "distil-large-v2": "Systran/faster-distil-whisper-large-v2",
        "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
        "distil-large-v3.5": "distil-whisper/distil-large-v3.5-ct2",
        "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
        "turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    }

    def __init__(self, cache_dir: str):
        """Initialize download manager."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._cancel_event = threading.Event()
        self._lock = threading.Lock()
        self._progress = DownloadProgress(
            status=DownloadStatus.PENDING,
            bytes_downloaded=0,
            bytes_total=0,
            current_file="",
            message="Ready",
        )

    def get_progress(self) -> DownloadProgress:
        """Get current progress (thread-safe read)."""
        with self._lock:
            return self._progress

    def is_cancelled(self) -> bool:
        """Check if download was cancelled."""
        return self._cancel_event.is_set()

    def cancel(self) -> None:
        """Signal cancellation."""
        self._cancel_event.set()
        self._set_progress(
            status=DownloadStatus.CANCELLED,
            message="Download cancelled",
        )

    def _set_progress(self, **kwargs) -> None:
        """Update progress state (thread-safe)."""
        with self._lock:
            current = self._progress
            self._progress = DownloadProgress(
                status=kwargs.get("status", current.status),
                bytes_downloaded=kwargs.get("bytes_downloaded", current.bytes_downloaded),
                bytes_total=kwargs.get("bytes_total", current.bytes_total),
                current_file=kwargs.get("current_file", current.current_file),
                message=kwargs.get("message", current.message),
            )

    def _get_model_dir(self, model_name: str) -> Path:
        """Get the specific directory where this model should be stored."""
        # Use simple folder names: "tiny", "base.en", etc.
        # This creates a flat structure: .../models/tiny/model.bin
        return self.cache_dir / model_name

    def _get_repo_id(self, model_name: str) -> str:
        """Get the Hugging Face repo ID for a model."""
        if model_name not in self.REPO_MAP:
            raise ValueError(f"Unknown model: {model_name}")
        return self.REPO_MAP[model_name]

    def is_cached(self, model_name: str) -> bool:
        """Check if model is fully downloaded."""
        model_dir = self._get_model_dir(model_name)
        
        # Check if directory exists
        if not model_dir.exists():
            return False
            
        # Check for essential model files
        # faster-whisper needs at least model.bin and config.json
        has_bin = (model_dir / "model.bin").exists()
        has_config = (model_dir / "config.json").exists()
        
        return has_bin and has_config

    def _format_size(self, bytes_val: int) -> str:
        """Format bytes as human-readable string."""
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        elif bytes_val < 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"

    def _progress_callback(self, downloaded: int, total: int, filename: str) -> None:
        """Callback for progress updates from ProgressTracker."""
        if self._cancel_event.is_set():
            raise InterruptedError("Download cancelled")
        
        # Format nice progress message
        if total > 0:
            pct = (downloaded / total) * 100
            dl_str = self._format_size(downloaded)
            total_str = self._format_size(total)
            message = f"{dl_str} / {total_str} ({pct:.1f}%)"
        else:
            message = f"Downloading {filename}..."
            
        self._set_progress(
            status=DownloadStatus.DOWNLOADING,
            bytes_downloaded=downloaded,
            bytes_total=total,
            current_file=filename,
            message=message,
        )

    def download(self, model_name: str, token: Optional[str] = None) -> DownloadProgress:
        """
        Download a model with progress tracking.
        
        Args:
            model_name: Name of the Whisper model
            token: Optional Hugging Face token
            
        Returns:
            Final progress state
        """
        if not HAS_HF:
            self._set_progress(
                status=DownloadStatus.ERROR,
                message="huggingface_hub not installed",
            )
            return self.get_progress()

        # Check cache first
        if self.is_cached(model_name):
            self._set_progress(
                status=DownloadStatus.COMPLETE,
                bytes_downloaded=100,
                bytes_total=100,
                message=f"Model '{model_name}' already cached",
            )
            return self.get_progress()

        # Reset state
        self._cancel_event.clear()
        self._set_progress(
            status=DownloadStatus.CHECKING,
            bytes_downloaded=0,
            bytes_total=0,
            message=f"Preparing to download '{model_name}'...",
        )

        repo_id = self._get_repo_id(model_name)

        try:
            # Set up ProgressTracker class variables for callback
            ProgressTracker._progress_callback = self._progress_callback
            ProgressTracker._cancel_event = self._cancel_event

            # Use local_dir to download directly to our flat folder structure
            model_dir = self._get_model_dir(model_name)
            model_dir.mkdir(parents=True, exist_ok=True)
            
            snapshot_download(
                repo_id=repo_id,
                local_dir=str(model_dir),
                token=token,
                resume_download=None,  # Not needed with local_dir usually, but safe to omit
                tqdm_class=ProgressTracker,
            )

            if self._cancel_event.is_set():
                return self.get_progress()

            self._set_progress(
                status=DownloadStatus.COMPLETE,
                bytes_downloaded=100,
                bytes_total=100,
                message=f"Model '{model_name}' downloaded successfully!",
            )

        except InterruptedError:
            # Cancelled by user
            self._set_progress(
                status=DownloadStatus.CANCELLED,
                message="Download cancelled by user",
            )

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "not found" in error_msg.lower():
                error_msg = f"Model '{model_name}' not found on Hugging Face"
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                error_msg = "Authentication required. Add HF token in addon preferences."
            
            self._set_progress(
                status=DownloadStatus.ERROR,
                message=f"Error: {error_msg[:100]}",
            )

        finally:
            # Clean up class variables
            ProgressTracker._progress_callback = None
            ProgressTracker._cancel_event = None

        return self.get_progress()


def create_download_manager(cache_dir: str) -> DownloadManager:
    """Factory function to create DownloadManager."""
    return DownloadManager(cache_dir)
