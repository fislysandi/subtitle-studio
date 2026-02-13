"""
Transcription Operators
"""

import bpy
import threading
import queue
import os
import tempfile
from types import SimpleNamespace
from typing import Dict, Any, Optional, List
from bpy.types import Operator

from ..core import transcriber
from ..utils import sequence_utils, file_utils


class _BaseTranscribeOperator(Operator):
    """Shared modal operator logic for transcription/translation."""

    bl_idname = "subtitle._base_transcribe"
    bl_label = "Base Transcribe (Internal)"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    _timer: Optional[bpy.types.Timer] = None
    _thread: Optional[threading.Thread] = None
    _queue: Optional[queue.Queue] = None
    _config: Optional[Dict[str, Any]] = None
    _scene_name: str = ""
    _finished: bool = False
    _success: bool = False
    _segments: Optional[List[transcriber.TranscriptionSegment]] = None
    _error_message: str = ""
    _cancel_event: Optional[threading.Event] = None
    _cancel_requested: bool = False
    _was_cancelled: bool = False

    _active_operator: Optional["_BaseTranscribeOperator"] = None

    _translate_override: Optional[bool] = None
    _start_message: str = "Starting transcription..."

    def execute(self, context):
        return self.invoke(context, None)

    def invoke(self, context, event):
        scene = context.scene
        props = scene.subtitle_editor

        if props.is_transcribing:
            self.report({"WARNING"}, "Transcription already in progress")
            return {"CANCELLED"}

        strip = sequence_utils.get_selected_strip(context)
        if not strip:
            self.report({"ERROR"}, "Please select an audio or video strip")
            return {"CANCELLED"}

        filepath = sequence_utils.get_strip_filepath(strip)
        if not filepath:
            self.report({"ERROR"}, "Could not get file path from selected strip")
            return {"CANCELLED"}

        error = self._validate_filepath(filepath)
        if error:
            self.report({"ERROR"}, error)
            return {"CANCELLED"}

        config = self._build_config(scene, props, filepath)
        self._config = config
        self._scene_name = scene.name
        self._queue = queue.Queue()
        self._finished = False
        self._success = False
        self._segments = None
        self._error_message = ""
        self._cancel_event = threading.Event()
        self._cancel_requested = False
        self._was_cancelled = False

        props.is_transcribing = True
        props.progress = 0.0
        props.progress_text = self._start_message

        self._thread = threading.Thread(
            target=self._transcribe_worker,
            args=(config, self._queue, self._cancel_event),
            daemon=True,
        )
        self._thread.start()

        _BaseTranscribeOperator._active_operator = self

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == "ESC":
            self._request_cancel(context, "Cancelling...")
            return {"PASS_THROUGH"}

        if event.type == "TIMER":
            self._drain_queue(context)

            if self._finished:
                self._finalize(context)
                return {"FINISHED"}

            for area in context.screen.areas:
                area.tag_redraw()

        return {"PASS_THROUGH"}

    def _build_config(self, scene, props, filepath: str) -> Dict[str, Any]:
        translate = props.translate
        if self._translate_override is not None:
            translate = self._translate_override

        return {
            "model": props.model,
            "device": props.device,
            "language": props.language,
            "translate": translate,
            "beam_size": props.beam_size,
            "word_timestamps": props.word_timestamps,
            "vad_filter": props.vad_filter,
            "vad_parameters": {
                "threshold": props.vad_threshold,
                "min_speech_duration_ms": props.min_speech_duration_ms,
                "min_silence_duration_ms": props.min_silence_duration_ms,
                "speech_pad_ms": props.speech_pad_ms,
            },
            "subtitle_channel": props.subtitle_channel,
            "subtitle_font_size": props.subtitle_font_size,
            "max_words_per_strip": props.max_words_per_strip,
            "render_fps": scene.render.fps / (scene.render.fps_base or 1.0),
            "compute_type": props.compute_type,
            "filepath": filepath,
            "scene_name": scene.name,
        }

    def _validate_filepath(self, filepath: str) -> Optional[str]:
        if not os.path.exists(filepath):
            return f"File not found: {filepath}"
        if not os.path.isfile(filepath):
            return f"Path is not a file: {filepath}"
        if not os.access(filepath, os.R_OK):
            return f"File is not readable: {filepath}"
        return None

    def _get_scene(self, context):
        if self._scene_name:
            return bpy.data.scenes.get(self._scene_name) or context.scene
        return context.scene

    def _drain_queue(self, context):
        if not self._queue:
            return

        scene = self._get_scene(context)
        props = scene.subtitle_editor if scene else context.scene.subtitle_editor

        while True:
            try:
                msg = self._queue.get_nowait()
            except queue.Empty:
                break

            msg_type = msg.get("type")
            if msg_type == "progress":
                props.progress = msg.get("progress", 0.0)
                props.progress_text = msg.get("text", "")
            elif msg_type == "error":
                self._error_message = msg.get("error", "Unknown error")
                props.progress = 0.0
                props.progress_text = f"Error: {self._error_message}"
                self._finished = True
                self._success = False
            elif msg_type == "complete":
                self._segments = msg.get("segments", [])
                self._finished = True
                self._success = True
            elif msg_type == "cancelled":
                self._error_message = ""
                self._finished = True
                self._success = False
                self._was_cancelled = True
                props.progress = 0.0
                props.progress_text = msg.get("message", "Transcription cancelled")

    def _finalize(self, context):
        scene = self._get_scene(context)
        props = scene.subtitle_editor if scene else context.scene.subtitle_editor

        if self._was_cancelled:
            props.progress_text = "Transcription cancelled"
            self.report({"WARNING"}, "Transcription cancelled")
        elif self._success and scene and self._segments is not None:
            segments = self._split_segments_for_display(
                self._segments,
                self._config or {},
            )
            self._create_strips(scene, segments, self._config or {})
            count = len(segments)
            props.progress_text = self._success_message(count)
            self.report({"INFO"}, props.progress_text)
        else:
            error_msg = self._error_message or "Transcription failed"
            props.progress_text = f"Error: {error_msg}"
            self.report({"ERROR"}, error_msg)

        self._cleanup(context)

    def _cleanup(self, context):
        scene = self._get_scene(context)
        props = scene.subtitle_editor if scene else context.scene.subtitle_editor

        props.is_transcribing = False
        props.progress = 0.0

        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

        if _BaseTranscribeOperator._active_operator is self:
            _BaseTranscribeOperator._active_operator = None

    def _request_cancel(self, context, message: str):
        if self._cancel_requested:
            return

        self._cancel_requested = True
        if self._cancel_event:
            self._cancel_event.set()

        scene = self._get_scene(context)
        props = scene.subtitle_editor if scene else context.scene.subtitle_editor
        props.progress_text = message

    @classmethod
    def request_active_cancel(cls) -> bool:
        active = cls._active_operator
        if not active:
            return False

        active._cancel_requested = True
        if active._cancel_event:
            active._cancel_event.set()
        return True

    def _refresh_list(self, scene):
        sequence_utils.refresh_list(SimpleNamespace(scene=scene))

    def _split_segments_for_display(
        self,
        segments: List[transcriber.TranscriptionSegment],
        config: Dict[str, Any],
    ) -> List[transcriber.TranscriptionSegment]:
        max_words = int(config.get("max_words_per_strip", 0) or 0)
        if max_words <= 0:
            return segments

        output: List[transcriber.TranscriptionSegment] = []
        for seg in segments:
            words = seg.text.split()
            if len(words) <= max_words:
                output.append(seg)
                continue

            if seg.words:
                for i in range(0, len(seg.words), max_words):
                    chunk_words = seg.words[i : i + max_words]
                    if not chunk_words:
                        continue
                    text = " ".join(
                        w.get("word", "").strip() for w in chunk_words
                    ).strip()
                    if not text:
                        continue
                    output.append(
                        transcriber.TranscriptionSegment(
                            start=float(chunk_words[0].get("start", seg.start)),
                            end=float(chunk_words[-1].get("end", seg.end)),
                            text=text,
                            words=chunk_words,
                        )
                    )
                continue

            total_words = len(words)
            if total_words == 0:
                output.append(seg)
                continue

            duration = max(seg.end - seg.start, 0.001)
            sec_per_word = duration / total_words
            for i in range(0, total_words, max_words):
                chunk_words = words[i : i + max_words]
                chunk_start = seg.start + (i * sec_per_word)
                if i + len(chunk_words) >= total_words:
                    chunk_end = seg.end
                else:
                    chunk_end = seg.start + ((i + len(chunk_words)) * sec_per_word)
                output.append(
                    transcriber.TranscriptionSegment(
                        start=chunk_start,
                        end=chunk_end,
                        text=" ".join(chunk_words),
                        words=None,
                    )
                )

        return output

    def _transcribe_worker(
        self,
        config: Dict[str, Any],
        out_queue: queue.Queue,
        cancel_event: Optional[threading.Event],
    ):
        class _WorkerCancelled(Exception):
            pass

        def check_cancel(message: str = "Transcription cancelled"):
            if cancel_event and cancel_event.is_set():
                out_queue.put({"type": "cancelled", "message": message})
                raise _WorkerCancelled()

        try:
            check_cancel()

            tm = transcriber.TranscriptionManager(
                model_name=config["model"],
                device=config["device"],
                compute_type=config["compute_type"],
            )

            cache_dir = file_utils.get_addon_models_dir()
            if not tm.load_model(cache_dir):
                if cancel_event and cancel_event.is_set():
                    out_queue.put(
                        {"type": "cancelled", "message": "Transcription cancelled"}
                    )
                else:
                    out_queue.put(
                        {
                            "type": "error",
                            "error": (
                                f"Model '{config['model']}' not ready. "
                                "Download it first or check console."
                            ),
                        }
                    )
                return

            check_cancel()

            def progress_callback(progress, text):
                out_queue.put({"type": "progress", "progress": progress, "text": text})

            tm.set_progress_callback(progress_callback)

            filepath = config["filepath"]
            audio_path = filepath
            temp_audio_path = None

            try:
                if not filepath.lower().endswith((".wav", ".mp3", ".flac", ".m4a")):
                    progress_callback(0.0, "Extracting audio...")
                    fd, temp_audio_path = tempfile.mkstemp(
                        suffix=".wav",
                        prefix="subtitle_extract_",
                    )
                    os.close(fd)
                    audio_path = tm.extract_audio(filepath, temp_audio_path)

                check_cancel()

                segments = []
                for segment in tm.transcribe(
                    audio_path,
                    language=config["language"]
                    if config["language"] != "auto"
                    else None,
                    translate=config["translate"],
                    beam_size=config["beam_size"],
                    word_timestamps=config["word_timestamps"],
                    vad_filter=config["vad_filter"],
                    vad_parameters=config["vad_parameters"],
                ):
                    check_cancel()
                    segments.append(segment)

                check_cancel()
                out_queue.put({"type": "complete", "segments": segments})
            finally:
                if temp_audio_path and os.path.exists(temp_audio_path):
                    try:
                        os.remove(temp_audio_path)
                    except OSError:
                        pass
        except _WorkerCancelled:
            pass
        except Exception as e:
            if cancel_event and cancel_event.is_set():
                out_queue.put(
                    {"type": "cancelled", "message": "Transcription cancelled"}
                )
            else:
                out_queue.put({"type": "error", "error": str(e)})

    def _success_message(self, count: int) -> str:
        return f"Created {count} subtitle strips"

    def _create_strips(
        self,
        scene,
        segments: List[transcriber.TranscriptionSegment],
        config: Dict[str, Any],
    ) -> None:
        raise NotImplementedError


class SUBTITLE_OT_transcribe(_BaseTranscribeOperator):
    """Transcribe selected audio/video strip to subtitles"""

    bl_idname = "subtitle.transcribe"
    bl_label = "Transcribe"
    bl_description = "Transcribe selected strip to subtitles using AI"

    _translate_override = None
    _start_message = "Starting transcription..."

    def _create_strips(self, scene, segments, config) -> None:
        channel = config.get("subtitle_channel", 3)
        font_size = config.get("subtitle_font_size", 24)
        render_fps = config["render_fps"]

        for i, seg in enumerate(segments):
            frame_start = int(seg.start * render_fps)
            frame_end = int(seg.end * render_fps)

            strip = sequence_utils.create_text_strip(
                scene,
                name=f"Subtitle_{i + 1:03d}",
                text=seg.text,
                frame_start=frame_start,
                frame_end=frame_end,
                channel=channel,
                font_size=font_size,
            )

            if strip:
                item = scene.text_strip_items.add()
                item.name = strip.name
                item.text = seg.text
                item.frame_start = frame_start
                item.frame_end = frame_end
                item.channel = channel

        self._refresh_list(scene)


class SUBTITLE_OT_translate(_BaseTranscribeOperator):
    """Translate selected audio/video strip to English subtitles"""

    bl_idname = "subtitle.translate"
    bl_label = "Translate"
    bl_description = "Translate non-English audio to English subtitles"

    _translate_override = True
    _start_message = "Starting translation to English..."

    def _success_message(self, count: int) -> str:
        return f"Created {count} translated subtitle strips"

    def _create_strips(self, scene, segments, config) -> None:
        channel = config.get("subtitle_channel", 2)
        font_size = config.get("subtitle_font_size", 24)
        if scene.sequence_editor:
            for seq in scene.sequence_editor.sequences:
                if seq.channel >= channel:
                    channel = seq.channel + 1
            channel = min(channel, 128)

        render_fps = config["render_fps"]

        for i, seg in enumerate(segments):
            frame_start = int(seg.start * render_fps)
            frame_end = int(seg.end * render_fps)

            strip = sequence_utils.create_text_strip(
                scene,
                name=f"Subtitle_{i + 1:03d}_EN",
                text=seg.text,
                frame_start=frame_start,
                frame_end=frame_end,
                channel=channel,
                font_size=font_size,
            )

            if strip:
                item = scene.text_strip_items.add()
                item.name = strip.name
                item.text = seg.text
                item.frame_start = frame_start
                item.frame_end = frame_end
                item.channel = channel

        self._refresh_list(scene)


class SUBTITLE_OT_cancel_transcription(Operator):
    """Cancel the current transcription or translation operation"""

    bl_idname = "subtitle.cancel_transcription"
    bl_label = "Cancel Transcription"
    bl_description = "Cancel the current transcription/translation"
    bl_options = {"REGISTER"}

    def execute(self, context):
        """Signal cancellation request."""
        props = context.scene.subtitle_editor

        if props.is_transcribing:
            props.progress_text = "Cancelling..."
            if _BaseTranscribeOperator.request_active_cancel():
                self.report({"INFO"}, "Cancelling transcription...")
            else:
                self.report({"WARNING"}, "No active transcription operator found")
        else:
            self.report({"WARNING"}, "No transcription in progress")

        return {"FINISHED"}


classes = [
    SUBTITLE_OT_transcribe,
    SUBTITLE_OT_translate,
    SUBTITLE_OT_cancel_transcription,
]
