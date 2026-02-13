"""
Model Download Operator - Non-Blocking Modal Pattern

Downloads Whisper models with:
- Real-time progress tracking via Blender's native progress bar
- Full UI responsiveness during download
- Cancellation support (Cancel button or ESC key)
"""

import bpy
import threading
from typing import Optional
from bpy.types import Operator
from ..core.download_manager import (
    DownloadManager,
    DownloadStatus,
    create_download_manager,
)
from ..config import __addon_name__
from ..utils import file_utils


class SUBTITLE_OT_download_model(Operator):
    """Download Whisper model with non-blocking progress"""

    bl_idname = "subtitle.download_model"
    bl_label = "Download Model"
    bl_description = "Download the selected Whisper model"
    bl_options = {"REGISTER"}

    # Instance variables (not class variables) for proper isolation
    _timer: Optional[bpy.types.Timer] = None
    _download_manager: Optional[DownloadManager] = None
    _thread: Optional[threading.Thread] = None
    _model_name: str = ""
    _finished: bool = False

    def invoke(self, context, event):
        """
        Start modal operator via invoke (not execute).
        invoke() is required for proper interactive modal behavior.
        """
        props = context.scene.subtitle_editor

        # Check if already downloading
        if props.is_downloading_model:
            self.report({"WARNING"}, "Download already in progress")
            return {"CANCELLED"}

        # Get model name
        self._model_name = props.model

        # Check dependencies
        try:
            from huggingface_hub import snapshot_download
        except ImportError:
            self.report(
                {"ERROR"}, "huggingface_hub not installed. Install dependencies first."
            )
            return {"CANCELLED"}

        # Create download manager
        cache_dir = file_utils.get_addon_models_dir()
        self._download_manager = create_download_manager(cache_dir)

        # Check if already cached
        if self._download_manager.is_cached(self._model_name):
            self.report({"INFO"}, f"Model '{self._model_name}' already downloaded")
            return {"FINISHED"}

        # Get HF token from preferences
        token = None
        prefs = context.preferences.addons.get(__addon_name__)
        if prefs and hasattr(prefs, "preferences"):
            token = getattr(prefs.preferences, "hf_token", None) or None

        # Initialize UI state
        props.is_downloading_model = True
        props.model_download_progress = 0.0
        props.model_download_status = f"Starting download of '{self._model_name}'..."
        self._finished = False

        # Start background download thread
        self._thread = threading.Thread(
            target=self._download_worker,
            args=(self._model_name, token),
            daemon=True,
        )
        self._thread.start()

        # Start Blender's native progress bar
        wm = context.window_manager
        wm.progress_begin(0, 100)

        # Add timer for polling (0.1 seconds = 10 updates/sec)
        self._timer = wm.event_timer_add(0.1, window=context.window)

        # Register modal handler
        wm.modal_handler_add(self)

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        """
        Called repeatedly by Blender's event loop.
        Must return quickly - heavy work is in background thread.
        """
        props = context.scene.subtitle_editor

        # Handle ESC key for cancellation
        if event.type == "ESC":
            self._cancel_download(context)
            self.report({"WARNING"}, "Download cancelled")
            return {"CANCELLED"}

        # Handle timer events
        if event.type == "TIMER":
            # Check for external cancellation (via cancel button)
            if not props.is_downloading_model and not self._finished:
                if self._download_manager:
                    self._download_manager.cancel()

            # Poll progress from download manager
            if self._download_manager:
                progress = self._download_manager.get_progress()

                # Update UI properties
                props.model_download_progress = progress.percentage
                props.model_download_status = progress.message

                # Update Blender's native status bar
                context.workspace.status_text_set(progress.message)

                # Update Blender's native progress bar (0-100)
                context.window_manager.progress_update(int(progress.percentage * 100))

                # Check if complete
                if progress.status in (
                    DownloadStatus.COMPLETE,
                    DownloadStatus.ERROR,
                    DownloadStatus.CANCELLED,
                ):
                    self._finished = True

                    # Report result
                    if progress.status == DownloadStatus.COMPLETE:
                        self.report({"INFO"}, progress.message)
                    elif progress.status == DownloadStatus.ERROR:
                        self.report({"ERROR"}, progress.message)
                    elif progress.status == DownloadStatus.CANCELLED:
                        self.report({"WARNING"}, "Download cancelled")

                    # Clean up and finish
                    self._cleanup(context)
                    return {"FINISHED"}

            # Force UI redraw to update progress
            for area in context.screen.areas:
                area.tag_redraw()

        # Return PASS_THROUGH to keep Blender responsive
        return {"PASS_THROUGH"}

    def _download_worker(self, model_name: str, token: Optional[str] = None):
        """Background thread that performs the download."""
        try:
            if self._download_manager:
                self._download_manager.download(model_name, token=token)
        except Exception as e:
            # Error is handled in download_manager
            print(f"[Subtitle Studio] Download error: {e}")

    def _cancel_download(self, context):
        """Cancel the download and clean up."""
        if self._download_manager:
            self._download_manager.cancel()
        self._cleanup(context)

    def _cleanup(self, context):
        """Clean up timer and state."""
        props = context.scene.subtitle_editor

        context.workspace.status_text_set(None)

        # Remove timer
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

        # End Blender's progress bar
        context.window_manager.progress_end()

        # Reset state
        props.is_downloading_model = False
        self._download_manager = None
        self._thread = None

    def cancel(self, context):
        """Called when operator is cancelled externally."""
        self._cancel_download(context)


class SUBTITLE_OT_cancel_download(Operator):
    """Cancel the current model download"""

    bl_idname = "subtitle.cancel_download"
    bl_label = "Cancel Download"
    bl_description = "Cancel the current model download"
    bl_options = {"REGISTER"}

    def execute(self, context):
        """Signal cancellation by setting is_downloading_model to False."""
        props = context.scene.subtitle_editor

        if props.is_downloading_model:
            props.is_downloading_model = False
            props.model_download_status = "Cancelling..."
            self.report({"INFO"}, "Cancelling download...")
        else:
            self.report({"WARNING"}, "No download in progress")

        return {"FINISHED"}


classes = [
    SUBTITLE_OT_download_model,
    SUBTITLE_OT_cancel_download,
]
