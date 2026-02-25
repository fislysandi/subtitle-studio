"""
Strip Edit Operators
"""

import bpy
from bpy.types import Operator

from ..utils import sequence_utils
from .ops_strip_navigation import (
    SUBTITLE_OT_jump_to_selected_end,
    SUBTITLE_OT_jump_to_selected_start,
    SUBTITLE_OT_nudge_strip,
    SUBTITLE_OT_select_next_strip,
    SUBTITLE_OT_select_previous_strip,
    SUBTITLE_OT_select_strip,
)
from .ops_strip_copy_style import SUBTITLE_OT_copy_style_from_active
from .ops_strip_style import (
    SUBTITLE_OT_apply_style,
    SUBTITLE_OT_apply_style_preset,
    SUBTITLE_OT_insert_line_breaks,
    SUBTITLE_OT_save_style_preset,
)
from .ops_strip_edit_helpers import (
    get_cursor_frame as _get_cursor_frame,
    get_default_duration as _get_default_duration,
    get_unique_strip_name as _get_unique_strip_name,
    resolve_edit_target_or_report as _resolve_edit_target_or_report,
)


class SUBTITLE_OT_refresh_list(Operator):
    """Refresh the list of text strips"""

    bl_idname = "subtitle.refresh_list"
    bl_label = "Refresh List"
    bl_description = "Refresh the subtitle strips list"
    bl_options = {"REGISTER"}

    def execute(self, context):
        sequence_utils.refresh_list(context)
        return {"FINISHED"}


class SUBTITLE_OT_add_strip_at_cursor(Operator):
    """Add a subtitle strip at the timeline cursor position"""

    bl_idname = "subtitle.add_strip_at_cursor"
    bl_label = "Add Subtitle at Cursor"
    bl_description = "Add a subtitle strip at the current timeline cursor"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        if not scene:
            self.report({"WARNING"}, "No active scene")
            return {"CANCELLED"}

        current_frame = scene.frame_current

        if not scene.sequence_editor:
            scene.sequence_editor_create()

        props = scene.subtitle_editor
        frame_start = _get_cursor_frame(context, scene)
        frame_start = max(scene.frame_start, frame_start)
        frame_end = frame_start + _get_default_duration(scene)

        name = _get_unique_strip_name(scene, f"Subtitle_{frame_start}")
        strip = sequence_utils.create_text_strip(
            scene,
            name=name,
            text="",
            frame_start=frame_start,
            frame_end=frame_end,
            channel=props.subtitle_channel,
        )

        if not strip:
            self.report({"ERROR"}, "Failed to create subtitle strip")
            return {"CANCELLED"}

        try:
            strip.font_size = props.font_size
        except AttributeError:
            pass

        try:
            strip.color = (
                props.text_color[0],
                props.text_color[1],
                props.text_color[2],
                1.0,
            )
        except AttributeError:
            pass

        try:
            if props.use_outline_color:
                strip.use_outline = True
                strip.outline_color = (
                    props.outline_color[0],
                    props.outline_color[1],
                    props.outline_color[2],
                    1.0,
                )
            else:
                strip.use_outline = False
        except AttributeError:
            pass

        try:
            strip.wrap_width = props.wrap_width
        except AttributeError:
            pass

        try:
            if props.v_align == "TOP":
                strip.align_y = "TOP"
            elif props.v_align == "CENTER":
                strip.align_y = "CENTER"
            elif props.v_align == "BOTTOM":
                strip.align_y = "BOTTOM"
            elif props.v_align == "CUSTOM":
                strip.location = (0.5, 0.5)
        except AttributeError:
            pass

        sequences = sequence_utils._get_sequence_collection(scene)
        if sequences:
            for s in sequences:
                s.select = False
        strip.select = True
        if scene.sequence_editor:
            scene.sequence_editor.active_strip = strip

        sequence_utils.refresh_list(context)
        for index, item in enumerate(scene.text_strip_items):
            if item.name == strip.name:
                scene.text_strip_items_index = index
                break

        scene.frame_current = current_frame
        return {"FINISHED"}


class SUBTITLE_OT_remove_selected_strip(Operator):
    """Remove the currently selected subtitle strip"""

    bl_idname = "subtitle.remove_selected_strip"
    bl_label = "Remove Subtitle"
    bl_description = "Remove the selected subtitle strip"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        if not scene:
            self.report({"WARNING"}, "No active scene")
            return {"CANCELLED"}

        index = scene.text_strip_items_index
        items = scene.text_strip_items

        if index < 0 or index >= len(items):
            self.report({"WARNING"}, "No subtitle selected")
            return {"CANCELLED"}

        item = items[index]

        sequences = sequence_utils._get_sequence_collection(scene)
        if not sequences:
            self.report({"WARNING"}, "No sequence editor to remove from")
            return {"CANCELLED"}

        removed = False
        for strip in list(sequences):
            if strip.name == item.name and strip.type == "TEXT":
                sequences.remove(strip)
                removed = True
                break

        if not removed:
            self.report({"WARNING"}, "Selected subtitle not found in sequencer")
            return {"CANCELLED"}

        sequence_utils.refresh_list(context)

        new_length = len(scene.text_strip_items)
        if new_length == 0:
            scene.text_strip_items_index = -1
            scene.subtitle_editor._updating_text = True
            try:
                scene.subtitle_editor.current_text = ""
            finally:
                scene.subtitle_editor._updating_text = False
        else:
            scene.text_strip_items_index = min(index, new_length - 1)

        return {"FINISHED"}


class SUBTITLE_OT_update_text(Operator):
    """Update subtitle text"""

    bl_idname = "subtitle.update_text"
    bl_label = "Update Text"
    bl_description = "Update the selected subtitle text"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        resolution = _resolve_edit_target_or_report(self, context)
        if not resolution or resolution.strip is None:
            return {"CANCELLED"}

        new_text = scene.subtitle_editor.current_text
        resolution.strip.text = new_text
        if resolution.item is not None:
            resolution.item.text = new_text
        return {"FINISHED"}


classes = [
    SUBTITLE_OT_refresh_list,
    SUBTITLE_OT_select_strip,
    SUBTITLE_OT_select_next_strip,
    SUBTITLE_OT_select_previous_strip,
    SUBTITLE_OT_add_strip_at_cursor,
    SUBTITLE_OT_remove_selected_strip,
    SUBTITLE_OT_update_text,
    SUBTITLE_OT_jump_to_selected_start,
    SUBTITLE_OT_jump_to_selected_end,
    SUBTITLE_OT_nudge_strip,
    SUBTITLE_OT_apply_style,
    SUBTITLE_OT_apply_style_preset,
    SUBTITLE_OT_save_style_preset,
    SUBTITLE_OT_copy_style_from_active,
    SUBTITLE_OT_insert_line_breaks,
]
