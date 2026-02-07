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
            ("tiny", "Tiny", "Fastest, lowest accuracy"),
            ("base", "Base", "Fast, good accuracy"),
            ("small", "Small", "Balanced"),
            ("medium", "Medium", "Better accuracy"),
            ("large-v3", "Large v3", "Best accuracy, slowest"),
        ],
        default="base",
    )

    device: EnumProperty(
        name="Device",
        description="Computation device",
        items=[
            ("auto", "Auto", "Automatically select"),
            ("cpu", "CPU", "CPU only"),
            ("cuda", "CUDA", "NVIDIA GPU"),
        ],
        default="auto",
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

                for strip in context.scene.sequence_editor.sequences_all:
                    if strip.name == items[index].name:
                        if hasattr(strip, "text"):
                            strip.text = self.current_text
                        break
            except:
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
