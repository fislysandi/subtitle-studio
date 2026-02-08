"""
UI Panels for Subtitle Studio
Simplified version matching upstream layout but using existing operators
"""

import bpy
from bpy.types import Panel


def _draw_trim_control(layout, item, handle: str):
    label = "Start" if handle == "START" else "End"
    prop_name = "frame_start" if handle == "START" else "frame_end"

    row = layout.row(align=True)
    row.prop(item, prop_name, text=label, slider=True)
    op = row.operator("subtitle.adjust_trim", text="", icon="DRIVER_DISTANCE")
    op.handle = handle


class SEQUENCER_PT_panel(Panel):
    """Main Subtitle Studio Panel"""

    bl_idname = "SEQUENCER_PT_panel"
    bl_label = "Subtitle Studio"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Subtitle Studio"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row()
        col = row.column()
        col.template_list(
            "SEQUENCER_UL_List",
            "",
            context.scene,
            "text_strip_items",
            context.scene,
            "text_strip_items_index",
            rows=10,
        )

        # Button column
        row = row.column(align=True)

        # Refresh
        row.operator("subtitle.refresh_list", text="", icon="FILE_REFRESH")
        row.separator()

        # Import/Export
        row.operator("subtitle.import_subtitles", text="", icon="IMPORT")
        row.operator("subtitle.export_subtitles", text="", icon="EXPORT")
        row.separator()

        # Add / Remove buttons
        row.operator("subtitle.add_strip_at_cursor", text="", icon="ADD")
        row.operator("subtitle.remove_selected_strip", text="", icon="REMOVE")
        row.separator()
        row.operator("subtitle.select_next_strip", text="", icon="TRIA_UP")
        row.operator("subtitle.select_previous_strip", text="", icon="TRIA_DOWN")

        # Update
        layout.separator()

        # Edit selected
        if scene.text_strip_items_index >= 0 and scene.text_strip_items:
            item = scene.text_strip_items[scene.text_strip_items_index]
            col = layout.column()

            # Text editing box
            box = col.box()
            box.label(text=f"Editing: {item.name}")
            box.prop(scene.subtitle_editor, "current_text")

            # Timing and position box
            box = col.box()
            _draw_trim_control(box, item, "START")
            _draw_trim_control(box, item, "END")
            box.prop(item, "channel")

            # Style box
            box = col.box()
            box.prop(scene.subtitle_editor, "font_size")
            row = box.row(align=True)
            row.prop(scene.subtitle_editor, "text_color")
            row.prop(scene.subtitle_editor, "shadow_color")

            # Line breaks box
            box = col.box()
            box.prop(scene.subtitle_editor, "max_chars_per_line")
            box.operator(
                "subtitle.insert_line_breaks", text="Insert Line Breaks", icon="TEXT"
            )
        else:
            box = layout.box()
            box.label(text="Select a subtitle from the list to edit")

        style_box = layout.box()
        style_box.label(text="Batch Styling")
        style_box.operator(
            "subtitle.copy_style_from_active",
            text="Copy Active Style to Selected",
            icon="BRUSH_DATA",
        )


class SEQUENCER_PT_whisper_panel(Panel):
    """Transcription & Translation Panel"""

    bl_label = "Transcription & Translation"
    bl_idname = "SEQUENCER_PT_whisper"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Subtitle Studio"

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.subtitle_editor

        # Dependencies Section
        col = layout.column()
        box = col.box()
        row = box.row(align=True)

        # Check if all dependencies are installed
        all_deps_installed = (
            props.deps_faster_whisper
            and props.deps_torch
            and props.deps_pysubs2
            and props.deps_onnxruntime
        )

        # Dependencies label with icon
        icon = "CHECKBOX_HLT" if all_deps_installed else "CHECKBOX_DEHLT"
        row.label(text="Dependencies:", icon=icon)

        # Install/Verify button
        row = box.row()
        row.operator(
            "subtitle.install_dependencies", text="Install/Verify Dependencies"
        )

        # Show install status if installing
        if props.is_installing_deps:
            row = box.row()
            row.prop(props, "deps_install_status", text="Status", emboss=False)
        elif not props.deps_faster_whisper or not props.deps_pysubs2:
            # Show message that PyTorch needs separate install
            row = box.row()
            row.label(text="Install base deps first, then PyTorch below", icon="INFO")

        # PyTorch Section
        box = col.box()

        # Check GPU and show warning if not detected
        if not props.gpu_detected and props.deps_torch:
            row = box.row()
            row.alert = True
            row.label(text="⚠ No GPU detected - CPU fallback", icon="ERROR")
            row = box.row()
            row.label(text="  Install PyTorch with CUDA for GPU acceleration")
        elif props.gpu_detected:
            row = box.row()
            row.label(text="✓ GPU detected", icon="CHECKMARK")

        # PyTorch Version selection (required)
        row = box.row()
        row.label(text="Select your GPU backend:", icon="PREFERENCES")

        # PyTorch Version dropdown and Install button
        row = box.row(align=True)
        row.prop(props, "pytorch_version", text="Backend")
        row.operator("subtitle.install_pytorch", text="Install PyTorch")

        # Show PyTorch install status if installing
        if props.is_installing_pytorch:
            row = box.row()
            row.prop(props, "pytorch_install_status", text="Status", emboss=False)
        elif not props.deps_torch:
            # Remind user to install PyTorch
            row = box.row()
            row.alert = True
            row.label(text="⚠ Select backend and click Install PyTorch", icon="ERROR")

        # Model sizes mapping for all 19 models
        model_sizes = {
            "tiny": "39 MB",
            "tiny.en": "39 MB",
            "base": "74 MB",
            "base.en": "74 MB",
            "small": "244 MB",
            "small.en": "244 MB",
            "medium": "769 MB",
            "medium.en": "769 MB",
            "large-v1": "1550 MB",
            "large-v2": "1550 MB",
            "large-v3": "1550 MB",
            "large": "1550 MB",
            "distil-small.en": "111 MB",
            "distil-medium.en": "394 MB",
            "distil-large-v2": "756 MB",
            "distil-large-v3": "756 MB",
            "distil-large-v3.5": "756 MB",
            "large-v3-turbo": "809 MB",
            "turbo": "809 MB",
        }

        # Model dropdown with download/cancel button
        box = col.box()
        row = box.row(align=True)
        row.prop(props, "model", text="")

        if props.is_downloading_model:
            # Show cancel button during download
            row.operator("subtitle.cancel_download", text="Cancel", icon="CANCEL")

            # Show progress bar
            box.prop(
                props, "model_download_progress", text="Download Progress", slider=True
            )

            # Show status message
            box.label(text=props.model_download_status, icon="FILE_REFRESH")
        else:
            if props.is_cached:
                # Model is ready
                col_dl = box.column(align=True)
                col_dl.label(text="Model Ready", icon="CHECKMARK")
                # Optional: Redownload button (smaller/different icon)
                col_dl.operator(
                    "subtitle.download_model",
                    text="Redownload Model",
                    icon="FILE_REFRESH",
                )
            else:
                # Show download button
                row.operator("subtitle.download_model", text="Download", icon="IMPORT")

            # Show model size info when not downloading
            if props.model in model_sizes:
                row = box.row()
                row.label(text=f"Size: {model_sizes[props.model]}", icon="INFO")

        # Device | Compute Type row
        row = box.row(align=True)
        row.prop(props, "device", text="")
        row.prop(props, "compute_type", text="")

        # Language dropdown
        box.prop(props, "language")

        # Beam Size | VAD Filter row
        row = box.row(align=True)
        row.prop(props, "beam_size", text="Beam Size")
        row.prop(props, "vad_filter", text="")

        # Show Advanced Options toggle
        box.prop(props, "show_advanced")

        if props.show_advanced:
            adv_box = box.box()
            adv_box.label(text="Advanced Settings", icon="PREFERENCES")

            # VAD Advanced Settings
            if props.vad_filter:
                vad_col = adv_box.column()
                vad_col.label(text="VAD Parameters (Music/Lyrics Tuning):")
                vad_col.prop(props, "vad_threshold")
                vad_col.prop(props, "min_silence_duration_ms")
                vad_col.prop(props, "min_speech_duration_ms")
                vad_col.prop(props, "speech_pad_ms")
                vad_col.separator()

            adv_box.prop(props, "beam_size")
            adv_box.prop(props, "max_words_per_strip", slider=True)
            adv_box.prop(props, "wrap_width", slider=True)
            adv_box.prop(props, "max_chars_per_line")
        else:
            # Simple view
            row = box.row()
            row.prop(props, "max_words_per_strip", slider=True)

        # Channel | Font Size row
        row = box.row(align=True)
        row.prop(props, "subtitle_channel", text="Channel")
        row.prop(props, "subtitle_font_size", text="Font Size")

        # V Alignment | Wrap Width row
        row = box.row(align=True)
        row.prop(props, "v_align", text="V Align")
        row.prop(props, "wrap_width", text="Wrap Width", toggle=True)

        # Actions Section
        box = col.box()
        action_col = box.column(align=True)

        # Transcribe to Text Strips button
        row = action_col.row(align=True)
        row.operator(
            "subtitle.transcribe", text="Transcribe to Text Strips", icon="RADIOBUT_OFF"
        )

        # Translate to Text Strips (EN) button
        row = action_col.row(align=True)
        row.operator(
            "subtitle.translate", text="Translate to Text Strips (EN)", icon="FONT_DATA"
        )
