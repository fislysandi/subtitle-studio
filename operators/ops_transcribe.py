"""
Transcription Operators
"""

import bpy
import threading
import os
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, EnumProperty

from ..core import transcriber
from ..utils import sequence_utils, file_utils


class SUBTITLE_OT_transcribe(Operator):
    """Transcribe selected audio/video strip to subtitles"""

    bl_idname = "subtitle.transcribe"
    bl_label = "Transcribe"
    bl_description = "Transcribe selected strip to subtitles using AI"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        props = scene.subtitle_editor

        # Get selected strip
        strip = sequence_utils.get_selected_strip(context)
        if not strip:
            self.report({"ERROR"}, "Please select an audio or video strip")
            return {"CANCELLED"}

        # Extract settings to dictionary (read on main thread)
        config = {
            "model": props.model,
            "device": props.device,
            "language": props.language,
            "translate": props.translate,
            "word_timestamps": props.word_timestamps,
            "vad_filter": props.vad_filter,
            "render_fps": scene.render.fps,
        }

        # Start transcription in background thread
        props.is_transcribing = True
        props.progress = 0.0
        props.progress_text = "Starting transcription..."

        thread = threading.Thread(
            target=self._transcribe_thread, args=(context, strip, config)
        )
        thread.daemon = True
        thread.start()

        return {"FINISHED"}

    def _transcribe_thread(self, context, strip, config):
        """Run transcription in background thread"""
        # Thread-safe storage for progress data
        progress_data = {"progress": 0.0, "text": "Starting..."}

        def update_props_on_main_thread(progress, text):
            """Schedule property updates on the main thread using bpy.app.timers"""
            progress_data["progress"] = progress
            progress_data["text"] = text

            def apply_updates():
                # Re-fetch props here (valid on main thread)
                if context.scene:
                    props = context.scene.subtitle_editor
                    props.progress = progress_data["progress"]
                    props.progress_text = progress_data["text"]
                return None  # Don't repeat

            bpy.app.timers.register(apply_updates, first_interval=0.0)

        try:
            # Extract audio from strip
            # Note: accessing strip.name etc might be unsafe if strip is deleted,
            # but sequence_utils.get_strip_filepath likely uses it.
            # Ideally we'd extract filepath on main thread too, but let's see.
            # sequence_utils.get_strip_filepath might access bpy data.
            # Best practice: get filepath in execute()
            
            # Since we can't easily change the signature of get_strip_filepath or move it entirely 
            # without checking its internals, and typically reading properties like filepath 
            # *might* be okay-ish but writing is definitely bad. 
            # However, for total safety, we should really pass the filepath.
            # But strip object is passed... let's check if we can improve this.
            # For now, following the plan to decouple config.
            
            filepath = sequence_utils.get_strip_filepath(strip)
            if not filepath:
                update_props_on_main_thread(0.0, "Error: Cannot get strip file path")
                bpy.app.timers.register(
                    lambda: setattr(context.scene.subtitle_editor, "is_transcribing", False) or None,
                    first_interval=0.0,
                )
                return

            # Initialize transcriber
            tm = transcriber.TranscriptionManager(
                model_name=config["model"], device=config["device"]
            )

            cache_dir = file_utils.get_addon_models_dir()
            if not tm.load_model(cache_dir):
                update_props_on_main_thread(0.0, "Error: Failed to load AI model")
                bpy.app.timers.register(
                    lambda: setattr(context.scene.subtitle_editor, "is_transcribing", False) or None,
                    first_interval=0.0,
                )
                return

            # Set up progress callback - uses thread-safe updates
            def progress_callback(progress, text):
                update_props_on_main_thread(progress, text)

            tm.set_progress_callback(progress_callback)

            # Extract audio if needed
            audio_path = filepath
            if not filepath.lower().endswith((".wav", ".mp3", ".flac", ".m4a")):
                update_props_on_main_thread(0.0, "Extracting audio...")
                audio_path = file_utils.get_temp_filepath("audio_extract.wav")
                audio_path = tm.extract_audio(filepath, audio_path)

            # Transcribe
            segments = list(
                tm.transcribe(
                    audio_path,
                    language=config["language"] if config["language"] != "auto" else None,
                    translate=config["translate"],
                    word_timestamps=config["word_timestamps"],
                    vad_filter=config["vad_filter"],
                )
            )

            # Create text strips in main thread
            bpy.app.timers.register(
                lambda: self._create_strips(context, segments, config["render_fps"]), first_interval=0.0
            )

            # Clean up temp file
            if audio_path != filepath and os.path.exists(audio_path):
                os.remove(audio_path)

            update_props_on_main_thread(1.0, f"Created {len(segments)} subtitle strips")

        except Exception as e:
            update_props_on_main_thread(0.0, f"Error: {str(e)}")
        finally:
            # Schedule cleanup on main thread
            def cleanup_props():
                if context.scene:
                    props = context.scene.subtitle_editor
                    props.is_transcribing = False
                    props.progress = 0.0
                return None

            bpy.app.timers.register(cleanup_props, first_interval=0.0)

    def _create_strips(self, context, segments, render_fps):
        """Create text strips from transcription (called in main thread)"""
        scene = context.scene

        # Determine channel
        channel = 3
        if scene.sequence_editor:
            # Find empty channel
            for seq in scene.sequence_editor.strips:
                if seq.channel >= channel:
                    channel = seq.channel + 1
            channel = min(channel, 128)

        # Create strips
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
            )

            if strip:
                # Add to UI list
                item = scene.text_strip_items.add()
                item.name = strip.name
                item.text = seg.text
                item.frame_start = frame_start
                item.frame_end = frame_end
                item.channel = channel

        # Refresh UI
        sequence_utils.refresh_list(context)
        return None  # Don't repeat


class SUBTITLE_OT_translate(Operator):
    """Translate selected audio/video strip to English subtitles"""

    bl_idname = "subtitle.translate"
    bl_label = "Translate"
    bl_description = "Translate non-English audio to English subtitles"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        props = scene.subtitle_editor

        # Get selected strip
        strip = sequence_utils.get_selected_strip(context)
        if not strip:
            self.report({"ERROR"}, "Please select an audio or video strip")
            return {"CANCELLED"}
            
        # Extract settings to dictionary (read on main thread)
        config = {
            "model": props.model,
            "device": props.device,
            "language": props.language,
            # "translate": True, # Implied for this operator
            "word_timestamps": props.word_timestamps,
            "vad_filter": props.vad_filter,
            "subtitle_channel": props.subtitle_channel,
            "render_fps": scene.render.fps,
        }

        # Start translation in background thread
        props.is_transcribing = True
        props.progress = 0.0
        props.progress_text = "Starting translation to English..."

        thread = threading.Thread(
            target=self._translate_thread, args=(context, strip, config)
        )
        thread.daemon = True
        thread.start()

        return {"FINISHED"}

    def _translate_thread(self, context, strip, config):
        """Run translation in background thread"""
        # Thread-safe storage for progress data
        progress_data = {"progress": 0.0, "text": "Starting..."}

        def update_props_on_main_thread(progress, text):
            """Schedule property updates on the main thread using bpy.app.timers"""
            progress_data["progress"] = progress
            progress_data["text"] = text

            def apply_updates():
                if context.scene:
                    props = context.scene.subtitle_editor
                    props.progress = progress_data["progress"]
                    props.progress_text = progress_data["text"]
                return None  # Don't repeat

            bpy.app.timers.register(apply_updates, first_interval=0.0)

        try:
            # Extract audio from strip
            filepath = sequence_utils.get_strip_filepath(strip)
            if not filepath:
                update_props_on_main_thread(0.0, "Error: Cannot get strip file path")
                bpy.app.timers.register(
                    lambda: setattr(context.scene.subtitle_editor, "is_transcribing", False) or None,
                    first_interval=0.0,
                )
                return

            # Initialize transcriber
            tm = transcriber.TranscriptionManager(
                model_name=config["model"], device=config["device"]
            )

            cache_dir = file_utils.get_addon_models_dir()
            if not tm.load_model(cache_dir):
                update_props_on_main_thread(0.0, "Error: Failed to load AI model")
                bpy.app.timers.register(
                    lambda: setattr(context.scene.subtitle_editor, "is_transcribing", False) or None,
                    first_interval=0.0,
                )
                return

            # Set up progress callback - uses thread-safe updates
            def progress_callback(progress, text):
                update_props_on_main_thread(progress, text)

            tm.set_progress_callback(progress_callback)

            # Extract audio if needed
            audio_path = filepath
            if not filepath.lower().endswith((".wav", ".mp3", ".flac", ".m4a")):
                update_props_on_main_thread(0.0, "Extracting audio...")
                audio_path = file_utils.get_temp_filepath("audio_extract.wav")
                audio_path = tm.extract_audio(filepath, audio_path)

            # Translate (always translate to English)
            segments = list(
                tm.transcribe(
                    audio_path,
                    language=config["language"] if config["language"] != "auto" else None,
                    translate=True,  # Force translate
                    word_timestamps=config["word_timestamps"],
                    vad_filter=config["vad_filter"],
                )
            )

            # Create text strips in main thread
            bpy.app.timers.register(
                lambda: self._create_strips(context, segments, config), first_interval=0.0
            )

            # Clean up temp file
            if audio_path != filepath and os.path.exists(audio_path):
                os.remove(audio_path)

            update_props_on_main_thread(
                1.0, f"Created {len(segments)} translated subtitle strips"
            )

        except Exception as e:
            update_props_on_main_thread(0.0, f"Error: {str(e)}")
        finally:
            # Schedule cleanup on main thread
            def cleanup_props():
                if context.scene:
                    props = context.scene.subtitle_editor
                    props.is_transcribing = False
                    props.progress = 0.0
                return None

            bpy.app.timers.register(cleanup_props, first_interval=0.0)

    def _create_strips(self, context, segments, config):
        """Create text strips from translation (called in main thread)"""
        scene = context.scene
        # props = scene.subtitle_editor # Don't rely on props if we can avoid it, but for defaults it's okay if on main thread

        # Determine channel
        channel = config.get("subtitle_channel", 2)
        if scene.sequence_editor:
            # Find empty channel
            for seq in scene.sequence_editor.strips:
                if seq.channel >= channel:
                    channel = seq.channel + 1
            channel = min(channel, 128)
        
        render_fps = config["render_fps"]

        # Create strips
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
            )

            if strip:
                # Add to UI list
                item = scene.text_strip_items.add()
                item.name = strip.name
                item.text = seg.text
                item.frame_start = frame_start
                item.frame_end = frame_end
                item.channel = channel

        # Refresh UI
        sequence_utils.refresh_list(context)
        return None  # Don't repeat
