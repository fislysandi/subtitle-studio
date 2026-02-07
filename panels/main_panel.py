"""
UI Panels for Subtitle Editor
"""

import bpy
from bpy.types import Panel


class SUBTITLE_PT_main_panel(Panel):
    """Main Subtitle Editor Panel"""

    bl_label = "Subtitle Editor"
    bl_idname = "SUBTITLE_PT_main_panel"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Subtitle"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.subtitle_editor

        # Dependency status
        box = layout.box()
        box.label(text="Dependencies", icon="CHECKBOX_HLT")
        box.label(text="✓ Ready" if not props.is_transcribing else "⟳ Loading...")

        layout.separator()

        # Selected strip info
        box = layout.box()
        box.label(text="Selected Strip", icon="SEQUENCE")

        strip = None
        if scene.sequence_editor:
            for s in scene.sequence_editor.sequences_all:
                if s.select:
                    strip = s
                    break

        if strip:
            box.label(text=f"Name: {strip.name}")
            box.label(text=f"Type: {strip.type}")
        else:
            box.label(text="No strip selected", icon="ERROR")


class SUBTITLE_PT_transcription_panel(Panel):
    """Transcription settings panel"""

    bl_label = "Transcription"
    bl_idname = "SUBTITLE_PT_transcription_panel"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Subtitle"
    bl_parent_id = "SUBTITLE_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.subtitle_editor

        # Language
        layout.prop(props, "language")

        # Model
        layout.prop(props, "model")

        # Device
        layout.prop(props, "device")

        # Advanced options
        row = layout.row()
        row.prop(props, "show_advanced", toggle=True)

        if props.show_advanced:
            box = layout.box()
            box.prop(props, "translate")
            box.prop(props, "word_timestamps")
            box.prop(props, "vad_filter")

        layout.separator()

        # Progress
        if props.is_transcribing:
            box = layout.box()
            box.label(text="Transcribing...", icon="SORTTIME")
            box.prop(props, "progress", slider=True)
            box.label(text=props.progress_text)
        else:
            # Transcribe button
            row = layout.row()
            row.scale_y = 1.5
            row.operator("subtitle.transcribe", icon="PLAY")


class SUBTITLE_PT_edit_panel(Panel):
    """Subtitle editing panel"""

    bl_label = "Edit Subtitles"
    bl_idname = "SUBTITLE_PT_edit_panel"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Subtitle"
    bl_parent_id = "SUBTITLE_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # List of text strips
        layout.label(text="Subtitle Strips:")
        row = layout.row()
        row.template_list(
            "SUBTITLE_UL_text_strips",
            "",
            scene,
            "text_strip_items",
            scene,
            "text_strip_items_index",
        )

        # Edit selected
        if scene.text_strip_items_index >= 0 and scene.text_strip_items:
            item = scene.text_strip_items[scene.text_strip_items_index]
            box = layout.box()
            box.label(text=f"Editing: {item.name}")
            box.prop(scene.subtitle_editor, "current_text")

        layout.separator()

        # Import/Export
        row = layout.row(align=True)
        row.operator("subtitle.import_subtitles", icon="IMPORT")
        row.operator("subtitle.export_subtitles", icon="EXPORT")
