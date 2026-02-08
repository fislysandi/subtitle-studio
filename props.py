"""
Property Groups for Subtitle Editor
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


class TextStripItem(PropertyGroup):
    """Property group representing a text strip in the sequencer"""

    name: StringProperty(name="Name", description="Strip name", default="Subtitle")

    text: StringProperty(name="Text", description="Subtitle text content", default="")

    frame_start: IntProperty(
        name="Start Frame", description="Frame where subtitle starts", default=1
    )

    frame_end: IntProperty(
        name="End Frame", description="Frame where subtitle ends", default=25
    )

    channel: IntProperty(
        name="Channel", description="Sequencer channel", default=3, min=1, max=128
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


class SubtitleEditorProperties(PropertyGroup):
    """Main properties for the Subtitle Editor"""

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
        """Update the selected text strip when text changes"""
        if not context.scene:
            return

        items = getattr(context.scene, "text_strip_items", [])
        index = getattr(context.scene, "text_strip_items_index", -1)

        if 0 <= index < len(items):
            items[index].text = self.current_text

            # Also update the actual strip in the sequencer
            try:
                import bpy

                for strip in context.scene.sequence_editor.sequences:
                    if strip.name == items[index].name:
                        if hasattr(strip, "text"):
                            strip.text = self.current_text
                        break
            except Exception:
                pass

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

    # Text strip appearance
    font_size: IntProperty(
        name="Font Size",
        description="Default font size for text strips",
        default=24,
        min=8,
        max=200,
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
