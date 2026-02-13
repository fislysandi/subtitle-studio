"""
UI Panels for Subtitle Studio
Simplified version matching upstream layout but using existing operators
"""

import bpy
from bpy.types import Panel
from ..utils import sequence_utils


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
        sequence_utils.sync_list_selection_from_sequencer(context)
        if not getattr(scene, "subtitle_editor", None):
            box = layout.box()
            box.alert = True
            box.label(text="Subtitle Studio not registered", icon="ERROR")
            box.label(text="Reload the addon to restore UI")
            return
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

        row.operator("subtitle.add_strip_at_cursor", text="", icon="ADD")
        row.operator("subtitle.remove_selected_strip", text="", icon="REMOVE")
        row.separator()
        row.operator("subtitle.select_next_strip", text="", icon="TRIA_UP")
        row.operator("subtitle.select_previous_strip", text="", icon="TRIA_DOWN")
        row.separator()

        # Edit section (moved from separate panel)
        layout.separator()

        # Edit selected
        if scene.text_strip_items_index >= 0 and scene.text_strip_items:
            item = scene.text_strip_items[scene.text_strip_items_index]
            col = layout.column()

            # Text editing box
            box = col.box()
            box.label(text=f"Editing: {item.name}")
            box.prop(scene.subtitle_editor, "current_text")

            # Subtitle editing tools
            box = col.box()
            box.label(text="Subtitle Editing Tools")
            row = box.row(align=True)
            row.prop(scene.subtitle_editor, "nudge_step", text="Step")

            row = box.row(align=True)
            row.operator(
                "subtitle.jump_to_selected_start",
                text="Start",
                icon="TIME",
            )
            op = row.operator("subtitle.nudge_strip", text="-", icon="TRIA_LEFT")
            op.edge = "START"
            op.direction = -1
            op = row.operator("subtitle.nudge_strip", text="+", icon="TRIA_RIGHT")
            op.edge = "START"
            op.direction = 1

            row = box.row(align=True)
            row.operator(
                "subtitle.jump_to_selected_end",
                text="End",
                icon="TIME",
            )
            op = row.operator("subtitle.nudge_strip", text="-", icon="TRIA_LEFT")
            op.edge = "END"
            op.direction = -1
            op = row.operator("subtitle.nudge_strip", text="+", icon="TRIA_RIGHT")
            op.edge = "END"
            op.direction = 1

            # Timing and position
            row = box.row(align=True)
            row.prop(item, "frame_start", text="Start")
            row.prop(item, "frame_end", text="End")

            # Style
            box.prop(scene.subtitle_editor, "font_size")
            row = box.row(align=True)
            row.prop(scene.subtitle_editor, "text_color")
            row.prop(scene.subtitle_editor, "shadow_color")
            row = box.row(align=True)
            row.prop(scene.subtitle_editor, "v_align")
            row.prop(scene.subtitle_editor, "wrap_width")

            # Line breaks
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
        props = getattr(scene, "subtitle_editor", None)
        if not props:
            box = layout.box()
            box.alert = True
            box.label(text="Subtitle Studio not registered", icon="ERROR")
            box.label(text="Reload the addon to restore UI")
            return

        # Transcription Progress Section (Issue #1: Add transcription progress display)
        if props.is_transcribing:
            self._draw_transcription_progress(layout, props)

        # Dependencies Section
        col = layout.column()
        self._draw_dependencies_section(col, props)

        # PyTorch Section
        self._draw_pytorch_section(col, props)

        # Model Section
        self._draw_model_section(col, props)

        # Settings Section (Issue #3: Group settings logically)
        self._draw_hardware_settings(col, props)
        self._draw_input_settings(col, props)
        self._draw_output_settings(col, props)

        # Actions Section (Issue #5: Improve action button hierarchy)
        self._draw_actions_section(col, props)

    def _draw_transcription_progress(self, layout, props):
        """Draw transcription progress UI with progress bar and status."""
        progress_box = layout.box()
        progress_box.alert = True
        progress_box.label(text="Transcription in Progress", icon="RENDER_STILL")
        progress_box.prop(props, "progress", text="Progress", slider=True)
        progress_box.label(text=props.progress_text, icon="INFO")
        progress_box.operator(
            "subtitle.cancel_transcription", text="Cancel", icon="CANCEL"
        )
        layout.separator()

    def _draw_dependencies_section(self, col, props):
        """Draw dependencies section - compact when all installed."""
        # Check if all dependencies are installed
        all_deps_installed = (
            props.deps_faster_whisper
            and props.deps_torch
            and props.deps_pysubs2
            and props.deps_onnxruntime
        )

        box = col.box()

        if all_deps_installed:
            # Compact success state - just show checkmark and minimal info
            row = box.row()
            row.label(text="Dependencies", icon="CHECKMARK")
            # Only show install status if actively installing (verification)
            if props.is_installing_deps:
                status_row = box.row()
                status_row.label(text=props.deps_install_status, icon="INFO")
        else:
            # Full install UI when dependencies missing
            box.label(text="Dependencies", icon="CHECKMARK")

            row = box.row()
            row.alert = True
            row.label(text="Dependencies not installed", icon="ERROR")

            # Install/Verify button
            row = box.row()
            row.operator(
                "subtitle.download_dependencies", text="Install/Verify Dependencies"
            )

            # Show install status if installing
            if props.is_installing_deps:
                status_box = box.box()
                status_box.label(
                    text=f"Status: {props.deps_install_status}", icon="INFO"
                )
            elif not props.deps_faster_whisper or not props.deps_pysubs2:
                # Show message that PyTorch needs separate install
                info_row = box.row()
                info_row.label(
                    text="Install base deps first, then PyTorch below", icon="INFO"
                )

    def _draw_pytorch_section(self, col, props):
        """Draw PyTorch/GPU section with backend mismatch detection."""
        # Skip section entirely if PyTorch not installed (will be shown in deps section)
        if not props.deps_torch:
            box = col.box()
            box.label(text="PyTorch / GPU", icon="PREFERENCES")

            row = box.row()
            row.alert = True
            row.label(text="PyTorch not installed", icon="ERROR")

            # PyTorch Version selection
            row = box.row()
            row.label(text="Select GPU backend:", icon="PREFERENCES")

            # PyTorch Version dropdown and Install button
            row = box.row(align=True)
            row.prop(props, "pytorch_version", text="Backend")
            row.operator("subtitle.install_pytorch", text="Install PyTorch")

            # Show PyTorch install status if installing
            if props.is_installing_pytorch:
                status_box = box.box()
                status_box.label(
                    text=f"Status: {props.pytorch_install_status}", icon="INFO"
                )
            return

        # PyTorch is installed
        box = col.box()

        # Check for backend mismatch
        if props.pytorch_backend_mismatch:
            # Mismatch detected - show warning with fix options
            box.label(text="PyTorch / GPU", icon="ERROR")

            # Show mismatch details
            detected = props.pytorch_backend_detected or "CPU"
            selected = props.pytorch_version

            row = box.row()
            row.alert = True
            row.label(text=f"Backend mismatch detected!", icon="ERROR")

            row = box.row()
            row.label(text=f"Selected: {selected}", icon="PREFERENCES")

            row = box.row()
            row.label(text=f"Detected: {detected}", icon="CHECKMARK")

            # Show backend selection to choose different version
            row = box.row()
            row.label(text="Choose correct version:", icon="PREFERENCES")
            row = box.row(align=True)
            row.prop(props, "pytorch_version", text="")

            # Reinstall button
            row = box.row()
            row.operator(
                "subtitle.install_pytorch",
                text="Reinstall PyTorch",
                icon="FILE_REFRESH",
            )

            # Check button to re-detect
            row = box.row()
            row.operator(
                "subtitle.check_gpu", text="Check GPU Again", icon="FILE_REFRESH"
            )

            return

        # No mismatch - show normal status
        if props.gpu_detected:
            # Compact GPU ready state
            row = box.row()
            row.label(text="PyTorch / GPU", icon="CHECKMARK")
        else:
            # CPU-only state with warning
            box.label(text="PyTorch / GPU", icon="PREFERENCES")
            row = box.row()
            row.alert = True
            row.label(text="CPU only (no GPU detected)", icon="ERROR")

            # Show backend selection for potential GPU install
            row = box.row()
            row.label(text="Backend:", icon="PREFERENCES")
            row.prop(props, "pytorch_version", text="")

            row = box.row()
            row.operator("subtitle.install_pytorch", text="Reinstall for GPU")

    def _draw_model_section(self, col, props):
        """Draw model download section with improved progress layout."""
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

        box = col.box()
        box.label(text="Whisper Model", icon="MODIFIER")

        if props.is_downloading_model:
            # Issue #6: Consolidated download progress layout
            self._draw_download_progress(box, props)
        else:
            # Model selector - cleaner dropdown without sizes in text
            row = box.row()
            row.prop(props, "model", text="")

            # Size info right below model selector
            if props.model in model_sizes:
                size_row = box.row()
                size_row.label(text=f"Size: {model_sizes[props.model]}", icon="INFO")

            # Buttons at the bottom
            if props.is_cached:
                # Model is ready - show redownload button
                row = box.row()
                row.operator(
                    "subtitle.download_model",
                    text="Redownload Model",
                    icon="FILE_REFRESH",
                )
            else:
                # Show download button
                row = box.row()
                row.operator(
                    "subtitle.download_model", text="Download Model", icon="IMPORT"
                )

    def _draw_download_progress(self, box, props):
        """Draw consolidated download progress UI."""
        dl_box = box.box()
        dl_box.alert = True
        dl_box.label(text="Downloading Model...", icon="IMPORT")
        dl_box.prop(props, "model_download_progress", text="Progress", slider=True)
        dl_box.label(text=props.model_download_status, icon="FILE_REFRESH")
        dl_box.operator(
            "subtitle.cancel_download", text="Cancel Download", icon="CANCEL"
        )

    def _draw_hardware_settings(self, col, props):
        """Draw hardware configuration settings."""
        box = col.box()
        box.label(text="Hardware Settings", icon="PREFERENCES")

        # Device | Compute Type row
        row = box.row(align=True)
        row.prop(props, "device", text="Device")
        row.prop(props, "compute_type", text="Compute")

    def _draw_input_settings(self, col, props):
        """Draw input/processing settings."""
        box = col.box()
        box.label(text="Recognition Settings", icon="SOUND")

        # Language dropdown
        box.prop(props, "language")

        # Beam Size | VAD Filter row
        row = box.row(align=True)
        row.prop(props, "beam_size", text="Beam Size")
        row.prop(props, "vad_filter", text="VAD Filter")

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

    def _draw_output_settings(self, col, props):
        """Draw output/subtitle strip settings."""
        box = col.box()
        box.label(text="Output Settings", icon="OUTPUT")

        # Channel | Font Size row
        row = box.row(align=True)
        row.prop(props, "subtitle_channel", text="Channel")
        row.prop(props, "subtitle_font_size", text="Font Size")

        # V Alignment | Wrap Width row
        row = box.row(align=True)
        row.prop(props, "v_align", text="V Align")
        row.prop(props, "wrap_width", text="Wrap Width", toggle=True)

    def _draw_actions_section(self, col, props):
        """Draw action buttons with improved hierarchy."""
        box = col.box()
        box.label(text="Actions", icon="PLAY")
        action_col = box.column(align=True)

        # Transcribe to Text Strips button
        row = action_col.row(align=True)
        row.scale_y = 1.3  # Make button taller for prominence
        row.operator(
            "subtitle.transcribe",
            text="Transcribe Audio",
            icon="SOUND",  # More descriptive icon
        )

        # Translate to Text Strips button
        row = action_col.row(align=True)
        row.scale_y = 1.3
        row.operator(
            "subtitle.translate",
            text="Translate to English",
            icon="WORLD",  # More descriptive icon
        )
