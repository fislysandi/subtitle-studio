"""
Property Groups for Subtitle Studio
"""

import bpy
from bpy.props import (
    StringProperty,
    FloatProperty,
    IntProperty,
    BoolProperty,
    EnumProperty,
    CollectionProperty,
)
from bpy.types import PropertyGroup

# Import language items directly
from .constants import LANGUAGE_ITEMS
from .core.style_plan import build_style_patch_from_props
from .utils import file_utils, sequence_utils


class TextStripItem(PropertyGroup):
    """Property group representing a text strip in the sequencer"""

    name: StringProperty(name="Name", description="Strip name", default="Subtitle")

    text: StringProperty(name="Text", description="Subtitle text content", default="")

    frame_start: IntProperty(
        name="Start Frame",
        description="Frame where subtitle starts",
        default=1,
        update=lambda self, context: self._update_frames(context, source="start"),
    )

    frame_end: IntProperty(
        name="End Frame",
        description="Frame where subtitle ends",
        default=25,
        update=lambda self, context: self._update_frames(context, source="end"),
    )

    channel: IntProperty(
        name="Channel", description="Sequencer channel", default=3, min=1, max=128
    )

    speaker: StringProperty(
        name="Speaker",
        description="Speaker label for this subtitle",
        default="Speaker 1",
    )

    is_selected: BoolProperty(
        name="Selected", description="Whether this strip is selected", default=False
    )

    strip_type: StringProperty(
        name="Strip Type",
        description="Type of strip (TEXT, SCENE, etc.)",
        default="TEXT",
    )

    strip_ref: StringProperty(
        name="Strip Reference",
        description="Internal reference to the strip",
        default="",
    )

    def _resolve_scene(self, context):
        scene = getattr(context, "scene", None) if context else None
        if scene:
            return scene

        owner = getattr(self, "id_data", None)
        if isinstance(owner, bpy.types.Scene):
            return owner
        return None

    def _update_frames(self, context, source: str):
        scene = self._resolve_scene(context)
        if not scene or not scene.sequence_editor:
            return

        target_strip = None
        for strip in scene.sequence_editor.strips:
            if strip.name == self.name and strip.type == "TEXT":
                target_strip = strip
                break

        if not target_strip:
            return

        channel = target_strip.channel
        prev_end = None
        next_start = None

        for strip in scene.sequence_editor.strips:
            if strip.type != "TEXT" or strip == target_strip:
                continue
            if strip.channel != channel:
                continue
            if strip.frame_final_end <= target_strip.frame_final_start:
                if prev_end is None or strip.frame_final_end > prev_end:
                    prev_end = strip.frame_final_end
            elif strip.frame_final_start >= target_strip.frame_final_end:
                if next_start is None or strip.frame_final_start < next_start:
                    next_start = strip.frame_final_start

        start = target_strip.frame_final_start
        end = target_strip.frame_final_end

        def _try_set_duration(strip, duration: int) -> bool:
            """Best-effort duration update via writable RNA properties only."""
            for attr in ("frame_final_duration", "frame_duration"):
                if hasattr(strip, attr):
                    try:
                        setattr(strip, attr, duration)
                        return True
                    except Exception:
                        continue
            return False

        if source == "start":
            new_start = int(self.frame_start)
            new_start = min(new_start, end - 1)
            if prev_end is not None:
                new_start = max(new_start, prev_end)
            if new_start != start:
                new_duration = max(1, end - new_start)
                try:
                    target_strip.frame_start = new_start
                except Exception:
                    pass
                _try_set_duration(target_strip, new_duration)
        elif source == "end":
            new_end = int(self.frame_end)
            new_end = max(new_end, start + 1)
            if next_start is not None:
                new_end = min(new_end, next_start)
            if new_end != end:
                new_duration = max(1, new_end - start)
                _try_set_duration(target_strip, new_duration)
        else:
            return

        # sync property values with actual strip after Blender adjustments
        self["frame_start"] = target_strip.frame_final_start
        self["frame_end"] = target_strip.frame_final_end


class SubtitleEditorProperties(PropertyGroup):
    """Main properties for the Subtitle Studio"""

    # Transcription settings
    language: EnumProperty(
        name="Language",
        description="Language for transcription",
        items=LANGUAGE_ITEMS,
        default="auto",
    )

    model: EnumProperty(
        name="Model",
        description="Whisper model size",
        items=[
            # Multilingual Models
            ("tiny", "Tiny", "Fastest, lowest accuracy (~39 MB)"),
            ("base", "Base", "Fast, good accuracy (~74 MB)"),
            ("small", "Small", "Balanced speed/accuracy (~244 MB)"),
            ("medium", "Medium", "Better accuracy (~769 MB)"),
            ("large-v3", "Large-v3", "Best accuracy, slowest (~1550 MB)"),
            ("large-v2", "Large-v2", "Second generation large (~1550 MB)"),
            ("large-v1", "Large-v1", "First generation large (~1550 MB)"),
            ("large", "Large", "Alias for large-v3 (~1550 MB)"),
            # English-Only Models
            ("tiny.en", "Tiny.EN", "Fastest English (~39 MB)"),
            ("base.en", "Base.EN", "Fast English (~74 MB)"),
            ("small.en", "Small.EN", "Balanced English (~244 MB)"),
            ("medium.en", "Medium.EN", "High quality English (~769 MB)"),
            # Distilled Models (Faster, English-Only)
            ("distil-small.en", "Distil-Small.EN", "Distilled, very fast (~111 MB)"),
            ("distil-medium.en", "Distil-Medium.EN", "Distilled, fast (~394 MB)"),
            ("distil-large-v2", "Distil-Large-v2", "Distilled large-v2 (~756 MB)"),
            ("distil-large-v3", "Distil-Large-v3", "Distilled large-v3 (~756 MB)"),
            (
                "distil-large-v3.5",
                "Distil-Large-v3.5",
                "Distilled v3.5",
            ),
            # Turbo Models (Fast & Accurate)
            (
                "large-v3-turbo",
                "Large-v3-Turbo",
                "Fast with great accuracy",
            ),
            ("turbo", "Turbo", "Alias for large-v3-turbo"),
        ],
        default="base",
    )

    device: EnumProperty(
        name="Device",
        description="Computation device for transcription",
        items=[
            ("auto", "Auto", "Automatically select best device"),
            ("cpu", "CPU", "CPU only - works on all systems"),
            (
                "cuda",
                "GPU",
                "Use GPU (CUDA, ROCm, or Metal depending on PyTorch install)",
            ),
        ],
        default="auto",
    )

    compute_type: EnumProperty(
        name="Compute Type",
        description="Computation precision (affects speed/quality)",
        items=[
            ("default", "Default", "Use default precision"),
            ("int8", "int8", "Fastest, lowest precision"),
            ("float16", "float16", "Good balance"),
            ("float32", "float32", "Best precision, slowest"),
        ],
        default="default",
    )

    beam_size: IntProperty(
        name="Beam Size",
        description="Beam size for transcription (higher = better accuracy, slower)",
        default=5,
        min=1,
        max=10,
    )

    max_words_per_strip: IntProperty(
        name="Max Words",
        description="Maximum number of words per subtitle strip before creating a new one (0 = unlimited)",
        default=7,
        min=0,
        max=20,
        subtype="NONE",
    )

    # Subtitle strip settings
    subtitle_channel: IntProperty(
        name="Channel",
        description="Default channel for new subtitle strips",
        default=2,
        min=1,
        max=128,
    )

    subtitle_font_size: IntProperty(
        name="Font Size",
        description="Default font size for subtitle strips",
        default=50,
        min=8,
        max=200,
    )

    v_align: EnumProperty(
        name="V Alignment",
        description="Vertical alignment of subtitles",
        items=[
            ("TOP", "Top", "Align to top"),
            ("CENTER", "Center", "Align to center"),
            ("BOTTOM", "Bottom", "Align to bottom"),
            ("CUSTOM", "Custom", "Do not force alignment; keep manual positioning"),
        ],
        default="BOTTOM",
        update=lambda self, context: self._apply_live_style(context),
    )

    wrap_width: FloatProperty(
        name="Wrap Width",
        description="Text wrap width (0 = no wrapping, 1 = full width)",
        default=0.70,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
        update=lambda self, context: self._apply_live_style(context),
    )

    max_chars_per_line: IntProperty(
        name="Max Chars",
        description="Maximum characters per line when inserting line breaks",
        default=40,
        min=10,
        max=200,
    )

    # Transcription options
    translate: BoolProperty(
        name="Translate to English",
        description="Translate non-English audio to English",
        default=False,
    )

    word_timestamps: BoolProperty(
        name="Word Timestamps",
        description="Generate timestamps for each word",
        default=False,
    )

    vad_filter: BoolProperty(
        name="Voice Activity Filter",
        description="Filter out non-speech segments",
        default=True,
    )

    # VAD Parameters (Advanced)
    vad_threshold: FloatProperty(
        name="Threshold",
        description="Speech probability threshold (lower = more sensitive and captures quieter speech)",
        default=0.35,
        min=0.0,
        max=1.0,
    )

    min_speech_duration_ms: IntProperty(
        name="Min Speech (ms)",
        description="Minimum duration of speech segments. Lower values keep short spoken words.",
        default=120,
        min=0,
        max=5000,
    )

    min_silence_duration_ms: IntProperty(
        name="Min Silence (ms)",
        description="Minimum silence needed to split speech segments. Lower values preserve conversational flow.",
        default=700,
        min=0,
        max=10000,
    )

    max_speech_duration_s: FloatProperty(
        name="Max Speech (s)",
        description="Maximum speech segment duration before forced split (helps separate music-heavy spans)",
        default=15.0,
        min=1.0,
        max=60.0,
    )

    speech_pad_ms: IntProperty(
        name="Speech Padding (ms)",
        description="Padding added around speech boundaries to avoid clipped words",
        default=500,
        min=0,
        max=2000,
    )

    vad_retry_on_low_recall: BoolProperty(
        name="Auto Retry VAD",
        description="Automatically retry transcription with relaxed VAD when too much speech is missed",
        default=True,
    )

    vocal_separation_prepass: BoolProperty(
        name="Vocal Separation Prepass",
        description="Run vocal/source separation before transcription for better speech recall in music-heavy audio",
        default=False,
    )

    # UI State
    show_advanced: BoolProperty(
        name="Show Advanced Options",
        description="Show advanced transcription settings",
        default=False,
    )

    # Progress tracking
    is_transcribing: BoolProperty(
        name="Is Transcribing", description="Transcription in progress", default=False
    )

    progress: FloatProperty(
        name="Progress",
        description="Transcription progress (0-1)",
        min=0.0,
        max=1.0,
        default=0.0,
        subtype="PERCENTAGE",
    )

    progress_text: StringProperty(
        name="Progress Text",
        description="Current transcription status",
        default="Ready",
    )

    # Text editing
    current_text: StringProperty(
        name="Current Text",
        description="Currently edited subtitle text",
        default="",
        update=lambda self, context: self.update_text(context),
    )

    def update_text(self, context):
        """Update the selected text strip when text changes."""
        if getattr(self, "_updating_text", False) or getattr(
            self, "_updating_name", False
        ):
            return

        scene = getattr(context, "scene", None) if context else None
        if scene is None:
            scene = getattr(self, "id_data", None)
        if scene is None:
            return

        resolution = sequence_utils.resolve_edit_target_for_scene(
            scene, allow_index_fallback=False
        )
        target_strip = resolution.strip
        if not target_strip:
            if resolution.warning:
                print(f"[Subtitle Studio] Edit target unresolved: {resolution.warning}")
            return

        target_strip.text = self.current_text

        target_item = resolution.item
        if target_item is None:
            items = getattr(scene, "text_strip_items", [])
            for item in items:
                if item.name == target_strip.name:
                    target_item = item
                    break

        if target_item is not None:
            target_item.text = self.current_text

        screen = getattr(context, "screen", None)
        if screen:
            for area in screen.areas:
                if area.type == "SEQUENCE_EDITOR":
                    area.tag_redraw()

    # Import/Export settings
    import_format: EnumProperty(
        name="Import Format",
        description="Subtitle format for import",
        items=[
            ("AUTO", "Auto-detect", "Automatically detect format"),
            ("SRT", "SubRip (.srt)", "SRT format"),
            ("VTT", "WebVTT (.vtt)", "VTT format"),
            ("ASS", "Advanced SSA (.ass)", "ASS format"),
        ],
        default="AUTO",
    )

    export_format: EnumProperty(
        name="Export Format",
        description="Subtitle format for export",
        items=[
            ("SRT", "SubRip (.srt)", "SRT format"),
            ("VTT", "WebVTT (.vtt)", "VTT format"),
            ("ASS", "Advanced SSA (.ass)", "ASS format"),
        ],
        default="SRT",
    )

    # Dependencies status
    deps_faster_whisper: BoolProperty(
        name="Faster Whisper",
        description="Faster Whisper is installed",
        default=False,
    )

    deps_torch: BoolProperty(
        name="PyTorch",
        description="PyTorch is installed",
        default=False,
    )

    deps_pysubs2: BoolProperty(
        name="PySubs2",
        description="PySubs2 is installed",
        default=False,
    )

    deps_onnxruntime: BoolProperty(
        name="ONNX Runtime",
        description="ONNX Runtime is installed",
        default=False,
    )

    is_installing_deps: BoolProperty(
        name="Installing",
        description="Dependencies are being installed",
        default=False,
    )

    deps_install_status: StringProperty(
        name="Install Status",
        description="Current installation status",
        default="",
    )

    # PyTorch settings
    pytorch_version: EnumProperty(
        name="PyTorch Version",
        description="PyTorch backend for your GPU (platform-specific)",
        items=[
            # CPU (Universal fallback)
            ("cpu", "CPU Only", "No GPU - CPU computation only (works on all systems)"),
            # NVIDIA GPUs (All platforms)
            (
                "cu118",
                "CUDA 11.8 — GTX/RTX 10/20/30 series",
                "GTX 10 series, RTX 20/30 series, older GPUs",
            ),
            (
                "cu121",
                "CUDA 12.1 — RTX 30/40 series (Recommended)",
                "RTX 3060/3070/3080/3090/4060/4070/4080/4090 - Best compatibility",
            ),
            (
                "cu124",
                "CUDA 12.4 — RTX 40 series only",
                "RTX 4060/4070/4080/4090 - Latest, may not work with older cards",
            ),
            # AMD GPUs (Platform-specific)
            ("rocm57", "ROCm 5.7 — AMD (Linux)", "AMD RX 7900 series - Linux ONLY"),
            # Apple / Intel
            ("mps", "Metal (MPS) — Apple Silicon", "Apple M1/M2/M3 Macs"),
        ],
        default="cpu",
    )

    gpu_detected: BoolProperty(
        name="GPU Detected",
        description="Whether a compatible GPU was detected",
        default=False,
    )

    is_installing_pytorch: BoolProperty(
        name="Installing PyTorch",
        description="PyTorch is being installed",
        default=False,
    )

    pytorch_install_status: StringProperty(
        name="PyTorch Install Status",
        description="Current PyTorch installation status",
        default="",
    )

    # PyTorch backend detection
    pytorch_backend_detected: StringProperty(
        name="PyTorch Backend Detected",
        description="The actual PyTorch backend detected (cpu, cuda, mps, etc.)",
        default="",
    )

    pytorch_backend_mismatch: BoolProperty(
        name="PyTorch Backend Mismatch",
        description="Whether installed PyTorch doesn't match selected version",
        default=False,
    )

    # Model download status
    is_downloading_model: BoolProperty(
        name="Downloading Model",
        description="Whisper model is being downloaded",
        default=False,
    )

    model_download_status: StringProperty(
        name="Model Download Status",
        description="Current model download status",
        default="",
    )

    model_download_progress: FloatProperty(
        name="Download Progress",
        description="Model download progress (0-100)",
        min=0.0,
        max=100.0,
        default=0.0,
        subtype="PERCENTAGE",
    )

    def _get_is_cached(self):
        """Check if current model is cached"""
        # Be careful not to cause IO lag, file_utils.is_model_cached is fast
        return file_utils.is_model_cached(self.model)

    is_cached: BoolProperty(
        name="Model Cached",
        description="Whether the selected model is already downloaded",
        get=_get_is_cached,
    )

    # Text strip appearance
    font_size: IntProperty(
        name="Font Size",
        description="Default font size for text strips",
        default=24,
        min=8,
        max=200,
        update=lambda self, context: self._apply_live_style(context),
    )

    nudge_step: IntProperty(
        name="Nudge Step",
        description="Frames to nudge subtitle in/out",
        default=1,
        min=1,
        max=100,
    )

    edit_frame_start: IntProperty(
        name="Start",
        description="Edit start frame of the currently targeted text strip",
        default=1,
        update=lambda self, context: self._apply_live_timing(context, source="start"),
    )

    edit_frame_end: IntProperty(
        name="End",
        description="Edit end frame of the currently targeted text strip",
        default=2,
        update=lambda self, context: self._apply_live_timing(context, source="end"),
    )

    text_color: bpy.props.FloatVectorProperty(
        name="Text Color",
        description="Default text color",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=lambda self, context: self._apply_live_style(context),
    )

    use_text_color: BoolProperty(
        name="Use Text Color",
        description="Apply text color to the active text strip",
        default=True,
        update=lambda self, context: self._apply_live_style(context),
    )

    outline_color: bpy.props.FloatVectorProperty(
        name="Outline Color",
        description="Default outline color",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0),
        update=lambda self, context: self._apply_live_style(context),
    )

    use_outline_color: BoolProperty(
        name="Use Outline",
        description="Toggle outline color on the active text strip",
        default=True,
        update=lambda self, context: self._apply_live_style(context),
    )

    shadow_color: bpy.props.FloatVectorProperty(
        name="Shadow Color",
        description="Default shadow color",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0),
        update=lambda self, context: self._apply_live_style(context),
    )

    preset_1_name: StringProperty(
        name="Preset 1",
        description="Preset slot name",
        default="Default",
    )

    preset_1_font_size: IntProperty(
        name="Preset 1 Font Size",
        description="Preset font size",
        default=24,
        min=8,
        max=200,
    )

    preset_1_text_color: bpy.props.FloatVectorProperty(
        name="Preset 1 Text Color",
        description="Preset text color",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
    )

    preset_1_shadow_color: bpy.props.FloatVectorProperty(
        name="Preset 1 Shadow Color",
        description="Preset shadow color",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0),
    )

    preset_1_v_align: EnumProperty(
        name="Preset 1 V Align",
        description="Preset vertical alignment",
        items=[
            ("TOP", "Top", "Align to top"),
            ("CENTER", "Center", "Align to center"),
            ("BOTTOM", "Bottom", "Align to bottom"),
            ("CUSTOM", "Custom", "Do not force alignment"),
        ],
        default="BOTTOM",
    )

    preset_1_wrap_width: FloatProperty(
        name="Preset 1 Wrap Width",
        description="Preset wrap width",
        default=0.7,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )

    preset_2_name: StringProperty(
        name="Preset 2",
        description="Preset slot name",
        default="Lower Third",
    )

    preset_2_font_size: IntProperty(
        name="Preset 2 Font Size",
        description="Preset font size",
        default=28,
        min=8,
        max=200,
    )

    preset_2_text_color: bpy.props.FloatVectorProperty(
        name="Preset 2 Text Color",
        description="Preset text color",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
    )

    preset_2_shadow_color: bpy.props.FloatVectorProperty(
        name="Preset 2 Shadow Color",
        description="Preset shadow color",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0),
    )

    preset_2_v_align: EnumProperty(
        name="Preset 2 V Align",
        description="Preset vertical alignment",
        items=[
            ("TOP", "Top", "Align to top"),
            ("CENTER", "Center", "Align to center"),
            ("BOTTOM", "Bottom", "Align to bottom"),
            ("CUSTOM", "Custom", "Do not force alignment"),
        ],
        default="BOTTOM",
    )

    preset_2_wrap_width: FloatProperty(
        name="Preset 2 Wrap Width",
        description="Preset wrap width",
        default=0.7,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )

    preset_3_name: StringProperty(
        name="Preset 3",
        description="Preset slot name",
        default="Large",
    )

    preset_3_font_size: IntProperty(
        name="Preset 3 Font Size",
        description="Preset font size",
        default=40,
        min=8,
        max=200,
    )

    preset_3_text_color: bpy.props.FloatVectorProperty(
        name="Preset 3 Text Color",
        description="Preset text color",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
    )

    preset_3_shadow_color: bpy.props.FloatVectorProperty(
        name="Preset 3 Shadow Color",
        description="Preset shadow color",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0),
    )

    preset_3_v_align: EnumProperty(
        name="Preset 3 V Align",
        description="Preset vertical alignment",
        items=[
            ("TOP", "Top", "Align to top"),
            ("CENTER", "Center", "Align to center"),
            ("BOTTOM", "Bottom", "Align to bottom"),
            ("CUSTOM", "Custom", "Do not force alignment"),
        ],
        default="BOTTOM",
    )

    preset_3_wrap_width: FloatProperty(
        name="Preset 3 Wrap Width",
        description="Preset wrap width",
        default=0.7,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )

    def _resolve_scene(self, context):
        scene = getattr(context, "scene", None) if context else None
        if scene:
            return scene

        owner = getattr(self, "id_data", None)
        if isinstance(owner, bpy.types.Scene):
            return owner

        return None

    def _tag_sequence_editor_redraw(self, context):
        screen = getattr(context, "screen", None) if context else None
        if screen:
            for area in screen.areas:
                if area.type == "SEQUENCE_EDITOR":
                    area.tag_redraw()
            return

        wm = getattr(bpy.context, "window_manager", None)
        if not wm:
            return
        for window in wm.windows:
            window_screen = getattr(window, "screen", None)
            if not window_screen:
                continue
            for area in window_screen.areas:
                if area.type == "SEQUENCE_EDITOR":
                    area.tag_redraw()

    def _apply_live_style(self, context):
        if getattr(self, "_updating_style", False):
            return

        scene = self._resolve_scene(context)
        if scene is None:
            return

        resolution = sequence_utils.resolve_edit_target_for_scene(
            scene,
            allow_index_fallback=False,
        )
        strip = resolution.strip
        if not strip:
            return

        style_patch = build_style_patch_from_props(self)

        self._updating_style = True
        try:
            try:
                strip.font_size = style_patch.font_size
            except AttributeError:
                pass

            try:
                strip.color = style_patch.text_color_rgba
            except AttributeError:
                pass

            try:
                if style_patch.use_outline:
                    strip.use_outline = True
                    strip.outline_color = style_patch.outline_color_rgba
                else:
                    strip.use_outline = False
            except AttributeError:
                pass

            if style_patch.v_align != "CUSTOM":
                try:
                    strip.align_y = style_patch.v_align
                except AttributeError:
                    pass
            else:
                try:
                    strip.location = (0.5, 0.5)
                except AttributeError:
                    pass

            try:
                strip.wrap_width = style_patch.wrap_width
            except AttributeError:
                pass
        finally:
            self._updating_style = False

        self._tag_sequence_editor_redraw(context)

    def _set_strip_end(self, strip, new_end: int) -> bool:
        for attr in ("frame_final_end", "frame_end"):
            if hasattr(strip, attr):
                try:
                    setattr(strip, attr, new_end)
                    return True
                except Exception:
                    continue
        return False

    def _set_strip_duration(self, strip, duration: int) -> bool:
        for attr in ("frame_final_duration", "frame_duration"):
            if hasattr(strip, attr):
                try:
                    setattr(strip, attr, duration)
                    return True
                except Exception:
                    continue
        return False

    def _apply_live_timing(self, context, source: str):
        if getattr(self, "_updating_timing", False):
            return

        scene = self._resolve_scene(context)
        if scene is None:
            return

        resolution = sequence_utils.resolve_edit_target_for_scene(
            scene,
            allow_index_fallback=False,
        )
        strip = resolution.strip
        if not strip:
            return

        start = int(strip.frame_final_start)
        end = int(strip.frame_final_end)

        if source == "start":
            new_start = max(scene.frame_start, int(self.edit_frame_start))
            new_start = min(new_start, end - 1)
            if new_start != start:
                strip.frame_start = new_start
                if not self._set_strip_end(strip, end):
                    self._set_strip_duration(strip, max(1, end - new_start))
        elif source == "end":
            new_end = max(start + 1, int(self.edit_frame_end))
            if new_end != end:
                if not self._set_strip_end(strip, new_end):
                    self._set_strip_duration(strip, max(1, new_end - start))

        self._updating_timing = True
        try:
            self["edit_frame_start"] = int(strip.frame_final_start)
            self["edit_frame_end"] = int(strip.frame_final_end)
        finally:
            self._updating_timing = False

        self._tag_sequence_editor_redraw(context)
