"""
Model Download Operator

Handles downloading Whisper models on demand using Modal Operator pattern
to prevent UI freezing during CPU-intensive model loading.
"""

import bpy
import threading
import queue
from bpy.types import Operator
from ..utils import file_utils


class SUBTITLE_OT_download_model(Operator):
    """Download the selected Whisper model"""

    bl_idname = "subtitle.download_model"
    bl_label = "Download Model"
    bl_description = (
        "Download the selected Whisper model (large models may take several minutes)"
    )
    bl_options = {"REGISTER"}

    _timer = None
    _thread = None
    _queue = None
    _is_complete = False
    _model_name = None

    def modal(self, context, event):
        """
        Called repeatedly by Blender's event loop.
        Processes queue updates and updates UI without blocking.
        """
        props = context.scene.subtitle_editor

        if event.type == "TIMER":
            # Process all pending messages from the worker thread
            while not self._queue.empty():
                try:
                    msg = self._queue.get_nowait()
                    msg_type = msg.get("type")

                    if msg_type == "status":
                        props.model_download_status = msg.get("text", "")
                    elif msg_type == "progress":
                        props.model_download_progress = msg.get("value", 0.0)
                    elif msg_type == "error":
                        props.model_download_status = f"Error: {msg.get('text', '')}"
                        self.report(
                            {"ERROR"},
                            f"Failed to download model: {msg.get('text', '')}",
                        )
                        self._is_complete = True
                    elif msg_type == "success":
                        props.model_download_status = msg.get("text", "")
                        self.report(
                            {"INFO"}, msg.get("text", "Model downloaded successfully!")
                        )
                        self._is_complete = True
                    elif msg_type == "complete":
                        self._is_complete = True

                except queue.Empty:
                    break

            # Force UI redraw to update progress bar
            for area in context.screen.areas:
                area.tag_redraw()

        if self._is_complete:
            self.cancel(context)
            props.is_downloading_model = False
            return {"FINISHED"}

        return {"PASS_THROUGH"}

    def execute(self, context):
        """
        Start the modal operator.
        Sets up timer, modal handler, and background thread.
        """
        props = context.scene.subtitle_editor
        self._model_name = props.model

        print(f"[Subtitle Editor] Starting model download for: {self._model_name}")

        # Check if faster-whisper is installed
        try:
            from faster_whisper import WhisperModel

            print("[Subtitle Editor] faster-whisper imported successfully")
        except ImportError as e:
            error_msg = f"faster-whisper not installed: {e}"
            print(f"[Subtitle Editor] ERROR: {error_msg}")
            self.report({"ERROR"}, error_msg)
            return {"CANCELLED"}

        # Initialize modal operator state
        self._queue = queue.Queue()
        self._is_complete = False
        props.is_downloading_model = True
        props.model_download_status = f"Preparing to download {self._model_name}..."
        props.model_download_progress = 0.0

        # Start background thread for the heavy work
        self._thread = threading.Thread(
            target=self._download_worker, args=(self._model_name,)
        )
        self._thread.daemon = True
        self._thread.start()

        # Add modal handler and timer (critical for non-blocking operation)
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        print(f"[Subtitle Editor] Modal operator started, download thread running")
        return {"RUNNING_MODAL"}

    def cancel(self, context):
        """
        Clean up when operator finishes or is cancelled.
        Always remove the timer to prevent memory leaks.
        """
        if self._timer:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            self._timer = None
            print("[Subtitle Editor] Modal operator timer removed")

    def _download_worker(self, model_name):
        """
        Download model in background thread.
        Uses queue to communicate with modal() method instead of bpy.app.timers.
        """
        try:
            from faster_whisper import WhisperModel
            import os

            cache_dir = file_utils.get_addon_models_dir()
            print(f"[Subtitle Editor] Download thread started for {model_name}")
            print(f"[Subtitle Editor] Cache directory: {cache_dir}")

            # Update status via queue
            self._queue.put(
                {"type": "status", "text": f"Checking if {model_name} exists..."}
            )
            self._queue.put({"type": "progress", "value": 0.1})

            # Check if model already exists
            model_path = os.path.join(
                cache_dir, f"models--Systran--faster-whisper-{model_name}"
            )
            if os.path.exists(model_path):
                print(
                    f"[Subtitle Editor] Model {model_name} already exists at {model_path}"
                )
                self._queue.put(
                    {
                        "type": "status",
                        "text": f"Model {model_name} already downloaded!",
                    }
                )
                self._queue.put({"type": "progress", "value": 1.0})
                self._queue.put(
                    {
                        "type": "success",
                        "text": f"Model {model_name} already downloaded!",
                    }
                )
                self._queue.put({"type": "complete"})
                return

            # Download model
            self._queue.put(
                {
                    "type": "status",
                    "text": f"Downloading {model_name}... This may take several minutes",
                }
            )
            self._queue.put({"type": "progress", "value": 0.2})
            print(
                f"[Subtitle Editor] Starting WhisperModel instantiation for {model_name}"
            )

            # This will download if not present
            # Use local_files_only=False to force download
            model = WhisperModel(
                model_name,
                device="cpu",
                compute_type="int8",
                download_root=cache_dir,
                local_files_only=False,
            )

            print(f"[Subtitle Editor] Model {model_name} loaded successfully")
            self._queue.put(
                {
                    "type": "status",
                    "text": f"Model {model_name} downloaded successfully!",
                }
            )
            self._queue.put({"type": "progress", "value": 1.0})
            self._queue.put(
                {
                    "type": "success",
                    "text": f"Model {model_name} downloaded successfully!",
                }
            )

        except Exception as e:
            error_msg = str(e)
            print(f"[Subtitle Editor] ERROR downloading model: {error_msg}")
            import traceback

            traceback.print_exc()

            self._queue.put({"type": "error", "text": error_msg})

        finally:
            # Signal completion
            self._queue.put({"type": "complete"})


classes = [
    SUBTITLE_OT_download_model,
]
