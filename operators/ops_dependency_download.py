"""
Non-blocking Dependency Download Operator

Downloads Python packages (PyTorch, faster-whisper, etc.) without freezing Blender UI.
Uses modal operator pattern with background threading.
"""

import bpy
import threading
import queue
import subprocess
import sys
from typing import Optional, Dict, Any
from bpy.types import Operator


class DependencyDownloadState:
    """
    Thread-safe shared state for download progress.
    Used to communicate between background thread and modal operator.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._progress = 0.0
        self._status = "Starting..."
        self._is_complete = False
        self._is_cancelled = False
        self._error_message = None
        self._success = False

    def update(self, progress: Optional[float] = None, status: Optional[str] = None):
        """Thread-safe update of progress and status"""
        with self._lock:
            if progress is not None:
                self._progress = progress
            if status is not None:
                self._status = status

    def get_progress(self) -> float:
        """Thread-safe read of progress"""
        with self._lock:
            return self._progress

    def get_status(self) -> str:
        """Thread-safe read of status"""
        with self._lock:
            return self._status

    def mark_complete(self, success: bool = True, error: Optional[str] = None):
        """Mark download as complete"""
        with self._lock:
            self._is_complete = True
            self._success = success
            if error:
                self._error_message = error

    def mark_cancelled(self):
        """Mark download as cancelled"""
        with self._lock:
            self._is_cancelled = True

    def is_complete(self) -> bool:
        """Check if download is complete"""
        with self._lock:
            return self._is_complete

    def is_cancelled(self) -> bool:
        """Check if download was cancelled"""
        with self._lock:
            return self._is_cancelled

    def get_result(self) -> Dict[str, Any]:
        """Get final result"""
        with self._lock:
            return {
                "success": self._success,
                "error": self._error_message,
                "cancelled": self._is_cancelled,
            }


class SUBTITLE_OT_download_dependencies(Operator):
    """
    Download Python dependencies in background without freezing UI.

    Uses modal operator pattern:
    - execute(): Starts the modal operator and background thread
    - modal(): Polls for progress updates (called by Blender's event loop)
    - cancel(): Cleans up when done
    """

    bl_idname = "subtitle.download_dependencies"
    bl_label = "Install Dependencies"
    bl_description = "Install required Python packages (non-blocking)"
    bl_options = {"REGISTER", "UNDO"}

    # Class variables to persist across modal calls
    _timer = None
    _thread = None
    _state = None
    _packages = None

    def modal(self, context, event) -> set:
        """
        Called repeatedly by Blender's event loop.
        Must return quickly - heavy work is done in background thread.

        Returns:
            {'PASS_THROUGH'} - Continue modal, let Blender process other events
            {'FINISHED'} - Complete the operator
            {'CANCELLED'} - Cancel the operator
        """
        if event.type == "ESC":
            self._request_cancel(context)
            self.report({"WARNING"}, "Download cancelled")
            return {"CANCELLED"}

        if not self._state:
            self.report({"ERROR"}, "Download state not initialized")
            self._cleanup(context)
            return {"CANCELLED"}

        # Only update on timer events (every 0.1 seconds)
        if event.type == "TIMER":
            # Get current progress from shared state (thread-safe)
            progress = self._state.get_progress()
            status = self._state.get_status()

            # Update Blender's built-in progress bar in status bar
            wm = context.window_manager
            wm.progress_update(int(progress * 100))
            context.workspace.status_text_set(status)

            # Check if complete
            if self._state.is_complete():
                result = self._state.get_result()

                if result["cancelled"]:
                    self.report({"INFO"}, "Download cancelled")
                elif result["success"]:
                    self.report({"INFO"}, "Dependencies installed successfully!")
                else:
                    error = result.get("error", "Unknown error")
                    self.report({"ERROR"}, f"Installation failed: {error}")

                # Clean up and finish
                self._cleanup(context)
                return {"FINISHED"}

            # Force UI redraw to show progress
            for area in context.screen.areas:
                area.tag_redraw()

        # PASS_THROUGH allows Blender to process other events (keeps UI responsive)
        return {"PASS_THROUGH"}

    def execute(self, context) -> set:
        """
        Start the modal operator.
        Sets up timer, modal handler, and background thread.
        """
        # Define packages to install
        self._packages = [
            "faster-whisper",
            "pysubs2>=1.8.0",
            "onnxruntime>=1.24.1",
        ]

        # Initialize shared state (thread-safe)
        self._state = DependencyDownloadState()

        # Start Blender's built-in progress bar
        wm = context.window_manager
        wm.progress_begin(0, 100)

        # Start background thread for actual download
        # This prevents blocking Blender's main thread
        self._thread = threading.Thread(
            target=self._download_worker,
            args=(self._packages, self._state),
            daemon=True,
        )
        self._thread.start()

        # Add modal handler and timer
        # Timer fires every 0.1 seconds to poll progress
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        self.report({"INFO"}, f"Installing {len(self._packages)} packages...")

        # RUNNING_MODAL keeps the operator alive and calls modal() repeatedly
        return {"RUNNING_MODAL"}

    def cancel(self, context):
        """
        Clean up when operator finishes or is cancelled.
        Always remove timer to prevent memory leaks.
        """
        self._request_cancel(context)

    def _request_cancel(self, context):
        """Signal cancellation and clean up UI."""
        if self._state:
            self._state.mark_cancelled()
        self._cleanup(context)

    def _cleanup(self, context):
        """Clean up timer and status/progress UI."""
        context.workspace.status_text_set(None)
        if self._timer:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            wm.progress_end()
            self._timer = None

    def _download_worker(self, packages: list, state: DependencyDownloadState):
        """
        Background thread - does the actual downloading.
        NEVER access Blender data (bpy.context, etc.) from here!
        Only uses the shared state object to report progress.
        """
        try:
            python_exe = sys.executable
            total_packages = len(packages)

            for i, package in enumerate(packages):
                if state.is_cancelled():
                    state.mark_complete(success=False)
                    return

                # Update progress before starting this package
                progress = i / total_packages
                state.update(progress=progress, status=f"Installing {package}...")

                # Run pip install for this package
                cmd = [python_exe, "-m", "pip", "install", "-q", package]

                result = subprocess.run(
                    cmd, capture_output=True, text=True, check=False
                )

                if result.returncode != 0:
                    error_msg = (
                        result.stderr[:200] if result.stderr else "Unknown error"
                    )
                    state.mark_complete(success=False, error=error_msg)
                    return

                # Update progress after completing this package
                progress = (i + 1) / total_packages
                state.update(progress=progress, status=f"Installed {package}")

            # All packages installed successfully
            state.update(progress=1.0, status="Complete!")
            state.mark_complete(success=True)

        except Exception as e:
            state.mark_complete(success=False, error=str(e))


class SUBTITLE_OT_cancel_download_deps(Operator):
    """
    Cancel the dependency download.
    Signals the background thread to stop gracefully.
    """

    bl_idname = "subtitle.cancel_download_deps"
    bl_label = "Cancel Installation"
    bl_description = "Cancel the dependency installation"
    bl_options = {"REGISTER"}

    def execute(self, context) -> set:
        # The modal operator will check the state and clean up
        # This operator just signals cancellation
        if SUBTITLE_OT_download_dependencies._state:
            SUBTITLE_OT_download_dependencies._state.mark_cancelled()
            self.report({"INFO"}, "Cancelling download...")
        return {"FINISHED"}


# Export classes for registration
classes = [
    SUBTITLE_OT_download_dependencies,
    SUBTITLE_OT_cancel_download_deps,
]
