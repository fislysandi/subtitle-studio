"""Style and formatting operators for subtitle strips."""

import bpy
from bpy.types import Operator

from ..core.style_plan import build_style_patch_from_props
from ..utils import sequence_utils
from .ops_strip_edit_helpers import (
    apply_style_patch_to_strip,
    get_preset_data,
    set_preset_data,
)


class SUBTITLE_OT_apply_style_preset(Operator):
    """Apply a style preset to the current editor values."""

    bl_idname = "subtitle.apply_style_preset"
    bl_label = "Apply Style Preset"
    bl_description = "Load a style preset into the current editor controls"
    bl_options = {"REGISTER", "UNDO"}

    preset_id: bpy.props.EnumProperty(
        items=[
            ("PRESET_1", "Preset 1", "Use preset 1"),
            ("PRESET_2", "Preset 2", "Use preset 2"),
            ("PRESET_3", "Preset 3", "Use preset 3"),
        ]
    )

    def execute(self, context):
        props = context.scene.subtitle_editor
        preset = get_preset_data(props, self.preset_id)

        props.font_size = preset["font_size"]
        props.text_color = preset["text_color"]
        props.outline_color = preset["outline_color"]
        props.v_align = preset["v_align"]
        props.wrap_width = preset["wrap_width"]

        return {"FINISHED"}


class SUBTITLE_OT_save_style_preset(Operator):
    """Save the current style into a preset slot."""

    bl_idname = "subtitle.save_style_preset"
    bl_label = "Save Style Preset"
    bl_description = "Save current style values into a preset slot"
    bl_options = {"REGISTER", "UNDO"}

    preset_id: bpy.props.EnumProperty(
        items=[
            ("PRESET_1", "Preset 1", "Save to preset 1"),
            ("PRESET_2", "Preset 2", "Save to preset 2"),
            ("PRESET_3", "Preset 3", "Save to preset 3"),
        ]
    )

    def execute(self, context):
        props = context.scene.subtitle_editor
        set_preset_data(props, self.preset_id)
        return {"FINISHED"}


class SUBTITLE_OT_apply_style(Operator):
    """Apply current style settings to selected subtitle strips."""

    bl_idname = "subtitle.apply_style"
    bl_label = "Apply Style to Selected"
    bl_description = "Apply current font size, text color, and outline settings to selected subtitle strips"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        props = scene.subtitle_editor
        style_patch = build_style_patch_from_props(props)

        selected = sequence_utils.get_selected_strips(context)
        if not selected:
            resolution = sequence_utils.resolve_edit_target(
                context,
                allow_index_fallback=False,
            )
            if not resolution.strip:
                self.report(
                    {"WARNING"},
                    resolution.warning or "No text strip selected",
                )
                return {"CANCELLED"}
            selected = [resolution.strip]

        count = 0
        for strip in selected:
            if apply_style_patch_to_strip(strip, style_patch):
                count += 1

        self.report({"INFO"}, f"Applied style to {count} strips")
        return {"FINISHED"}


class SUBTITLE_OT_insert_line_breaks(Operator):
    """Insert line breaks into selected subtitles."""

    bl_idname = "subtitle.insert_line_breaks"
    bl_label = "Insert Line Breaks"
    bl_description = "Insert line breaks to fit text within character limit"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        import textwrap

        scene = context.scene
        props = scene.subtitle_editor
        max_chars = props.max_chars_per_line

        selected = sequence_utils.get_selected_strips(context)
        if not selected:
            resolution = sequence_utils.resolve_edit_target(
                context,
                allow_index_fallback=False,
            )
            if not resolution.strip:
                self.report(
                    {"WARNING"},
                    resolution.warning or "No text strip selected",
                )
                return {"CANCELLED"}
            selected = [resolution.strip]

        count = 0
        for strip in selected:
            if strip.type != "TEXT":
                continue

            current_text = strip.text
            wrapped_lines = textwrap.wrap(current_text, width=max_chars)
            new_text = "\n".join(wrapped_lines)

            if new_text != current_text:
                strip.text = new_text
                count += 1

        self.report({"INFO"}, f"Updated {count} strips")
        return {"FINISHED"}
