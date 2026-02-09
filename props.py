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
from .utils import file_utils


def speaker_items(self, context):
    count = getattr(self, "speaker_count", 3) or 3
    names = [
        getattr(self, "speaker_name_1", "Speaker 1"),
        getattr(self, "speaker_name_2", "Speaker 2"),
        getattr(self, "speaker_name_3", "Speaker 3"),
    ]
    return [(idx + 1, names[idx], "") for idx in range(count)]


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

        if source == "start":
            new_start = int(self.frame_start)
            new_start = min(new_start, end - 1)
            if prev_end is not None:
                new_start = max(new_start, prev_end)
            if new_start != start:
                target_strip.frame_final_start = new_start
                # keep tail anchored by reapplying previous end
                target_strip.frame_final_end = end
        elif source == "end":
            new_end = int(self.frame_end)
            new_end = max(new_end, start + 1)
            if next_start is not None:
                new_end = min(new_end, next_start)
            if new_end != end:
                target_strip.frame_final_end = new_end
                target_strip.frame_final_start = start
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
            ("tiny", "Tiny — Multilingual (~39M)", "Fastest, lowest accuracy"),
            ("base", "Base — Multilingual (~74M)", "Fast, good accuracy"),
            ("small", "Small — Multilingual (~244M)", "Balanced speed/accuracy"),
            ("medium", "Medium — Multilingual (~769M)", "Better accuracy"),
            ("large-v3", "Large-v3 — Multilingual (~1550M)", "Best accuracy, slowest"),
            ("large-v2", "Large-v2 — Multilingual (~1550M)", "Second generation large"),
            ("large-v1", "Large-v1 — Multilingual (~1550M)", "First generation large"),
            ("large", "Large — Multilingual (~1550M)", "Alias for large-v3"),
            # English-Only Models
            (
                "tiny.en",
                "Tiny.EN — English Only (~39M)",
                "Fastest English transcription",
            ),
            ("base.en", "Base.EN — English Only (~74M)", "Fast English transcription"),
            (
                "small.en",
                "Small.EN — English Only (~244M)",
                "Balanced English transcription",
            ),
            ("medium.en", "Medium.EN — English Only (~769M)", "High quality English"),
            # Distilled Models (Faster, English-Only)
            (
                "distil-small.en",
                "Distil-Small.EN — English (~111M)",
                "Distilled, very fast",
            ),
            (
                "distil-medium.en",
                "Distil-Medium.EN — English (~394M)",
                "Distilled, fast",
            ),
            (
                "distil-large-v2",
                "Distil-Large-v2 — Multilingual (~756M)",
                "Distilled large-v2",
            ),
            (
                "distil-large-v3",
                "Distil-Large-v3 — Multilingual (~756M)",
                "Distilled large-v3",
            ),
            (
                "distil-large-v3.5",
                "Distil-Large-v3.5 — Multilingual (~756M)",
                "Distilled v3.5",
            ),
            # Turbo Models (Fast & Accurate)
            (
                "large-v3-turbo",
                "Large-v3-Turbo — Multilingual (~809M)",
                "Fast with great accuracy",
            ),
            ("turbo", "Turbo — Multilingual (~809M)", "Alias for large-v3-turbo"),
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
        update=lambda self, context: self.update_speaker_channels(context),
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
        ],
        default="BOTTOM",
    )

    wrap_width: FloatProperty(
        name="Wrap Width",
        description="Text wrap width (0 = no wrapping, 1 = full width)",
        default=0.70,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
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
        description="Speech probability threshold (lower = more sensitive). Tuning for music: try 0.3-0.4",
        default=0.5,
        min=0.0,
        max=1.0,
    )

    min_speech_duration_ms: IntProperty(
        name="Min Speech (ms)",
        description="Minimum duration of speech segments. Decrease for fast lyrics.",
        default=250,
        min=0,
        max=5000,
    )

    min_silence_duration_ms: IntProperty(
        name="Min Silence (ms)",
        description="Minimum duration of silence to split speech. Decrease to split lyrics better.",
        default=2000,
        min=0,
        max=10000,
    )

    speech_pad_ms: IntProperty(
        name="Speech Padding (ms)",
        description="Padding added to speech segments",
        default=400,
        min=0,
        max=2000,
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

    speaker_warning: StringProperty(
        name="Speaker Warning",
        description="Speaker channel warning text",
        default="",
    )

    def update_text(self, context):
        """Update the selected text strip when text changes"""
        if getattr(self, "_updating_text", False) or getattr(
            self, "_updating_name", False
        ):
            return
        if not context.scene:
            return

        items = getattr(context.scene, "text_strip_items", [])
        index = getattr(context.scene, "text_strip_items_index", -1)

        if 0 <= index < len(items):
            item = items[index]
            speaker = item.speaker or self._speaker_label()
            updated_text = self._apply_speaker_prefix(self.current_text, speaker)
            if updated_text != self.current_text:
                self._updating_text = True
                self.current_text = updated_text
                self._updating_text = False

            item.text = updated_text
            current_name = item.name
            self._update_strip_name(
                context.scene, item, updated_text, index + 1, current_name
            )

            # Also update the actual strip in the sequencer
            try:
                import bpy

                for strip in context.scene.sequence_editor.strips:
                    if strip.name == current_name:
                        if hasattr(strip, "text"):
                            strip.text = updated_text
                        strip.name = item.name
                        break
            except Exception:
                pass

        screen = getattr(context, "screen", None)
        if screen:
            for area in screen.areas:
                if area.type == "SEQUENCE_EDITOR":
                    area.tag_redraw()

    def _speaker_names(self):
        return [self.speaker_name_1, self.speaker_name_2, self.speaker_name_3]

    def _speaker_label(self) -> str:
        if self.speaker_index == 2:
            return self.speaker_name_2
        if self.speaker_index == 3:
            return self.speaker_name_3
        return self.speaker_name_1

    def update_speaker_choice(self, context):
        if getattr(self, "_updating_speaker_choice", False):
            return
        try:
            self.speaker_index = int(self.speaker_choice)
        except (TypeError, ValueError):
            self.speaker_index = 1

    def _apply_speaker_prefix(self, text: str, speaker: str) -> str:
        if not self.show_speaker_prefix_in_text:
            _, rest = self._strip_speaker_prefix(text.strip())
            return rest if rest is not None else text.strip()

        stripped = text.strip()
        if not stripped:
            return f"{speaker}:"

        prefix, rest = self._strip_speaker_prefix(stripped)
        if rest is None:
            return f"{speaker}: {stripped}"
        return f"{speaker}: {rest}"

    def _strip_speaker_prefix(self, text: str):
        if ":" not in text:
            return None, None
        prefix, rest = text.split(":", 1)
        prefix = prefix.strip()
        if prefix in self._speaker_names():
            return prefix, rest.strip()
        return None, None

    def _strip_text_body(self, text: str) -> str:
        prefix, rest = self._strip_speaker_prefix(text.strip())
        if rest is None:
            return text.strip()
        return rest

    def _unique_strip_name(self, scene, base: str, current_name: str) -> str:
        if not scene.sequence_editor:
            return base
        existing = {
            strip.name
            for strip in scene.sequence_editor.strips
            if strip.name != current_name
        }
        if base not in existing:
            return base
        index = 2
        while f"{base} {index}" in existing:
            index += 1
        return f"{base} {index}"

    def _update_strip_name(
        self, scene, item, text: str, fallback_index: int, current_name: str
    ) -> None:
        speaker = item.speaker or self._speaker_label()
        body = self._strip_text_body(text)
        if body:
            snippet = " ".join(body.split()[:4])
            base = f"{speaker}: {snippet}"
        else:
            base = f"{speaker}: {fallback_index}"

        new_name = self._unique_strip_name(scene, base, current_name)
        if new_name == current_name:
            return

        self._updating_name = True
        try:
            item.name = new_name

            if scene.sequence_editor:
                for strip in scene.sequence_editor.strips:
                    if strip.name == current_name and strip.type == "TEXT":
                        strip.name = new_name
                        break
        finally:
            self._updating_name = False

    def update_speaker_tab(self, context):
        if not context.scene:
            return

        if self.speaker_index > self.speaker_count:
            self.speaker_index = self.speaker_count

        self._updating_speaker_choice = True
        self.speaker_choice = self.speaker_index
        self._updating_speaker_choice = False

        label = self._speaker_label()
        selected = []

        if context.scene.sequence_editor:
            for strip in context.scene.sequence_editor.strips:
                if strip.select and strip.type == "TEXT":
                    selected.append(strip.name)

        if not selected:
            index = context.scene.text_strip_items_index
            items = context.scene.text_strip_items
            if 0 <= index < len(items):
                current_name = items[index].name
                items[index].speaker = label
                items[index].text = self._apply_speaker_prefix(items[index].text, label)
                self._update_strip_name(
                    context.scene,
                    items[index],
                    items[index].text,
                    index + 1,
                    current_name,
                )
                self._updating_text = True
                self.current_text = items[index].text
                self._updating_text = False
            self.update_speaker_channels(context)
            return

        for item in context.scene.text_strip_items:
            if item.name in selected:
                current_name = item.name
                item.speaker = label
                item.text = self._apply_speaker_prefix(item.text, label)
                idx = context.scene.text_strip_items.find(item.name)
                self._update_strip_name(
                    context.scene,
                    item,
                    item.text,
                    (idx + 1 if idx >= 0 else 1),
                    current_name,
                )

        active_index = context.scene.text_strip_items_index
        if 0 <= active_index < len(context.scene.text_strip_items):
            active_item = context.scene.text_strip_items[active_index]
            self._updating_text = True
            self.current_text = active_item.text
            self._updating_text = False

        self.update_speaker_channels(context)

    def _set_channel_name(self, scene, channel: int, name: str) -> None:
        if not scene.sequence_editor:
            return
        channels = scene.sequence_editor.channels
        if 0 <= channel - 1 < len(channels):
            channels[channel - 1].name = name

    def sync_speaker_names_from_scene(self, scene) -> None:
        if not scene or not scene.sequence_editor:
            return

        channels = scene.sequence_editor.channels
        base = self.subtitle_channel

        def _channel_name(channel_index: int):
            if 0 <= channel_index - 1 < len(channels):
                channel = channels[channel_index - 1]
                return getattr(channel, "name", None)
            return None

        def _maybe_update(channel_index: int, current: str, setter):
            channel_name = _channel_name(channel_index)
            if not channel_name:
                return
            default_name = f"Channel {channel_index}"
            if channel_name != default_name and channel_name != current:
                setter(channel_name)

        _maybe_update(
            base, self.speaker_name_1, lambda v: setattr(self, "speaker_name_1", v)
        )
        _maybe_update(
            base + 1, self.speaker_name_2, lambda v: setattr(self, "speaker_name_2", v)
        )
        _maybe_update(
            base + 2, self.speaker_name_3, lambda v: setattr(self, "speaker_name_3", v)
        )

    def sync_speaker_names_from_channels(self, context) -> None:
        scene = getattr(context, "scene", None)
        self.sync_speaker_names_from_scene(scene)

    def _reset_speaker_channel_names(self, scene, target_channels) -> None:
        if not scene.sequence_editor:
            return
        channels = scene.sequence_editor.channels
        speaker_names = set(self._speaker_names())
        for index, channel in enumerate(channels, start=1):
            if index in target_channels:
                continue
            if channel.name in speaker_names:
                channel.name = f"Channel {index}"

    def update_speaker_channels_for_scene(self, scene) -> None:
        if not scene or not scene.sequence_editor:
            return

        self.sync_speaker_names_from_scene(scene)

        mapping = {
            self.speaker_name_1: self.subtitle_channel,
            self.speaker_name_2: self.subtitle_channel + 1,
            self.speaker_name_3: self.subtitle_channel + 2,
        }

        channel_to_speaker = {
            self.subtitle_channel: self.speaker_name_1,
            self.subtitle_channel + 1: self.speaker_name_2,
            self.subtitle_channel + 2: self.speaker_name_3,
        }

        target_channels = set(mapping.values())

        subtitle_names = {item.name for item in scene.text_strip_items}
        warning = ""

        for strip in scene.sequence_editor.strips:
            if strip.channel in mapping.values():
                if strip.name not in subtitle_names or strip.type != "TEXT":
                    warning = (
                        "Speaker channel conflict: rename or move existing strips "
                        "before assigning speaker tracks."
                    )
                    break

        self.speaker_warning = warning

        strip_by_name = {
            strip.name: strip
            for strip in scene.sequence_editor.strips
            if strip.type == "TEXT"
        }

        for item in scene.text_strip_items:
            strip = strip_by_name.get(item.name)
            if strip and strip.channel in channel_to_speaker:
                new_speaker = channel_to_speaker[strip.channel]
                if item.speaker != new_speaker:
                    item.speaker = new_speaker
                    item.text = self._apply_speaker_prefix(strip.text, item.speaker)

                item.channel = strip.channel
            else:
                channel = mapping.get(item.speaker, self.subtitle_channel)
                item.channel = channel

            current_name = item.name
            strip = strip_by_name.get(item.name)
            if strip:
                if strip.channel != item.channel:
                    strip.channel = item.channel
                strip.text = self._apply_speaker_prefix(strip.text, item.speaker)
                item.text = strip.text
                idx = scene.text_strip_items.find(item.name)
                self._update_strip_name(
                    scene,
                    item,
                    strip.text,
                    (idx + 1 if idx >= 0 else 1),
                    current_name,
                )

        self._reset_speaker_channel_names(scene, target_channels)
        self._set_channel_name(scene, self.subtitle_channel, self.speaker_name_1)
        self._set_channel_name(scene, self.subtitle_channel + 1, self.speaker_name_2)
        self._set_channel_name(scene, self.subtitle_channel + 2, self.speaker_name_3)

    def update_speaker_channels(self, context):
        scene = getattr(context, "scene", None)
        if not scene:
            return
        self.update_speaker_channels_for_scene(scene)

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
        description="Model download progress (0-1)",
        min=0.0,
        max=1.0,
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
    )

    nudge_step: IntProperty(
        name="Nudge Step",
        description="Frames to nudge subtitle in/out",
        default=1,
        min=1,
        max=100,
    )

    text_color: bpy.props.FloatVectorProperty(
        name="Text Color",
        description="Default text color",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
    )

    shadow_color: bpy.props.FloatVectorProperty(
        name="Shadow Color",
        description="Default shadow color",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0),
    )

    speaker_count: IntProperty(
        name="Speaker Count",
        description="Number of active speaker slots",
        default=3,
        min=1,
        max=3,
    )

    speaker_index: IntProperty(
        name="Speaker",
        description="Active speaker slot (placeholder)",
        default=1,
        min=1,
        max=3,
        update=lambda self, context: self.update_speaker_tab(context),
    )

    speaker_choice: EnumProperty(
        name="Speaker",
        description="Active speaker selection",
        items=speaker_items,
        default=1,
        update=lambda self, context: self.update_speaker_choice(context),
    )

    speaker_name_1: StringProperty(
        name="Speaker 1 Name",
        description="Speaker tab label",
        default="Subtitle_Studio",
    )

    speaker_name_2: StringProperty(
        name="Speaker 2 Name",
        description="Speaker tab label",
        default="Speaker 2",
    )

    speaker_name_3: StringProperty(
        name="Speaker 3 Name",
        description="Speaker tab label",
        default="Speaker 3",
    )

    show_speaker_prefix_in_text: BoolProperty(
        name="Prefix in Text",
        description="Show speaker prefix in subtitle text",
        default=False,
        update=lambda self, context: self.update_text(context),
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
