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
            "vad_parameters": {
                "threshold": props.vad_threshold,
                "min_speech_duration_ms": props.min_speech_duration_ms,
                "min_silence_duration_ms": props.min_silence_duration_ms,
                "speech_pad_ms": props.speech_pad_ms,
            },
            "subtitle_channel": props.subtitle_channel,
            "render_fps": scene.render.fps,
            "compute_type": props.compute_type,
            # Extract filepath on main thread for safety
            "filepath": sequence_utils.get_strip_filepath(strip),
        }

        if not config["filepath"]:
            self.report({"ERROR"}, "Could not get file path from selected strip")
            return {"CANCELLED"}

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
        print(f"[Subtitle Editor] Starting transcription thread for {config['filepath']}")
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
            # Get filepath from config (extracted on main thread)
            filepath = config["filepath"]
            
            # NOTE: We do NOT check filepath here again, assuming it was checked in execute
            if not filepath:
                 # Should not happen if execute checks it
                update_props_on_main_thread(0.0, "Error: Invalid file path")
                return

            # Initialize transcriber
            tm = transcriber.TranscriptionManager(
                model_name=config["model"], 
                device=config["device"],
                compute_type=config["compute_type"]
            )

            cache_dir = file_utils.get_addon_models_dir()
            if not tm.load_model(cache_dir):
                update_props_on_main_thread(
                    0.0, 
                    f"Model '{config['model']}' not ready. Download it first or check console."
                )
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
                lambda: self._create_strips(context, segments, config), first_interval=0.0
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

    def _create_strips(self, context, segments, config):
        """Create text strips from transcription (called in main thread)"""
        scene = context.scene

        # Determine channel
        channel = config.get("subtitle_channel", 3)
        # If user wants a specific channel, we should respect it, or find next available if occupied?
        # User request says: "put it on a track defined by bpy.data.scenes["Scene"].subtitle_editor.subtitle_channel"
        # Implies strict adherence to that channel.
        # But commonly addons find *next available* from that point.
        # Let's check existing logic: it starts at 3 and finds empty.
        # New logic: Start at config["subtitle_channel"] and find next available if needed?
        # Or just use that channel? Usually subtitles shouldn't overlap.
        # If we just dump everything on one channel they might overlap if segments overlap (rare for whisper).
        # Let's respect the START channel, and if there are existing strips *on that channel* that overlap...
        # The existing logic finds a completely empty channel? No, it finding a channel number higher than any existing strip?
        # "if seq.channel >= channel: channel = seq.channel + 1" -> this finds the *highest* used channel + 1.
        # This completely ignores "3" if there's something on 4.
        
        # Correct logic for "use defined channel":
        # Just use the channel provided. If the user says channel 5, put it on channel 5.
        # If they want it on a new channel, they change the setting.
        # However, to avoid overwriting/mess, maybe we should just use it.
        
        # Let's trust the user's "defined by... subtitle_channel" request literally.
        # But we need render_fps too.
        
        render_fps = config["render_fps"]

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
            "vad_parameters": {
                "threshold": props.vad_threshold,
                "min_speech_duration_ms": props.min_speech_duration_ms,
                "min_silence_duration_ms": props.min_silence_duration_ms,
                "speech_pad_ms": props.speech_pad_ms,
            },
            "subtitle_channel": props.subtitle_channel,
            "render_fps": scene.render.fps,
            "compute_type": props.compute_type,
            # Extract filepath on main thread for safety
            "filepath": sequence_utils.get_strip_filepath(strip),
        }

        if not config["filepath"]:
            self.report({"ERROR"}, "Could not get file path from selected strip")
            return {"CANCELLED"}

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
        print(f"[Subtitle Editor] Starting translation thread for {config['filepath']}")
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
            # Get filepath from config (extracted on main thread)
            filepath = config["filepath"]
            
            # NOTE: We do NOT check filepath here again, assuming it was checked in execute
            if not filepath:
                 # Should not happen if execute checks it
                update_props_on_main_thread(0.0, "Error: Invalid file path")
                return

            # Initialize transcriber
            tm = transcriber.TranscriptionManager(
                model_name=config["model"], 
                device=config["device"],
                compute_type=config["compute_type"]
            )

            cache_dir = file_utils.get_addon_models_dir()
            if not tm.load_model(cache_dir):
                update_props_on_main_thread(
                    0.0, 
                    f"Model '{config['model']}' not ready. Download it first or check console."
                )
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
            import traceback
            traceback.print_exc()
            print(f"[Subtitle Editor] Error in translation thread: {e}")
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
