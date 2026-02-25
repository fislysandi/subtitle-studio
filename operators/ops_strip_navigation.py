"""Navigation and timing operators for subtitle strips."""

import bpy
from bpy.types import Operator

from .ops_strip_edit_helpers import (
    jump_to_selected,
    resolve_edit_target_or_report,
    select_strip_by_index,
)


class SUBTITLE_OT_select_strip(Operator):
    """Select a text strip"""

    bl_idname = "subtitle.select_strip"
    bl_label = "Select Strip"
    bl_description = "Select this subtitle strip in the sequencer"
    bl_options = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty()

    def execute(self, context):
        if not select_strip_by_index(context, self.index):
            return {"CANCELLED"}
        return {"FINISHED"}


class SUBTITLE_OT_select_next_strip(Operator):
    """Select the next subtitle strip"""

    bl_idname = "subtitle.select_next_strip"
    bl_label = "Next Subtitle"
    bl_description = "Select the next subtitle strip in the list"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        total = len(scene.text_strip_items)
        if total == 0:
            return {"CANCELLED"}

        current = scene.text_strip_items_index
        next_index = min(total - 1, current + 1 if current >= 0 else 0)

        if not select_strip_by_index(context, next_index):
            return {"CANCELLED"}
        return {"FINISHED"}


class SUBTITLE_OT_select_previous_strip(Operator):
    """Select the previous subtitle strip"""

    bl_idname = "subtitle.select_previous_strip"
    bl_label = "Previous Subtitle"
    bl_description = "Select the previous subtitle strip in the list"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        total = len(scene.text_strip_items)
        if total == 0:
            return {"CANCELLED"}

        current = scene.text_strip_items_index
        if current == -1:
            prev_index = max(0, total - 1)
        else:
            prev_index = max(0, current - 1)

        if not select_strip_by_index(context, prev_index):
            return {"CANCELLED"}
        return {"FINISHED"}


class SUBTITLE_OT_jump_to_selected_start(Operator):
    """Jump timeline to the selected subtitle start"""

    bl_idname = "subtitle.jump_to_selected_start"
    bl_label = "Jump to Start"
    bl_description = "Jump the timeline to the selected subtitle start"
    bl_options = {"REGISTER"}

    def execute(self, context):
        ok, message = jump_to_selected(context, "START")
        if not ok:
            self.report({"WARNING"}, message)
            return {"CANCELLED"}
        return {"FINISHED"}


class SUBTITLE_OT_jump_to_selected_end(Operator):
    """Jump timeline to the selected subtitle end"""

    bl_idname = "subtitle.jump_to_selected_end"
    bl_label = "Jump to End"
    bl_description = "Jump the timeline to the selected subtitle end"
    bl_options = {"REGISTER"}

    def execute(self, context):
        ok, message = jump_to_selected(context, "END")
        if not ok:
            self.report({"WARNING"}, message)
            return {"CANCELLED"}
        return {"FINISHED"}


class SUBTITLE_OT_nudge_strip(Operator):
    """Nudge selected subtitle timing"""

    bl_idname = "subtitle.nudge_strip"
    bl_label = "Nudge Subtitle"
    bl_description = "Nudge subtitle start/end by the step size"
    bl_options = {"REGISTER", "UNDO"}

    edge: bpy.props.EnumProperty(
        items=[
            ("START", "Start", "Nudge start"),
            ("END", "End", "Nudge end"),
        ]
    )

    direction: bpy.props.IntProperty(default=1)

    def execute(self, context):
        scene = context.scene
        props = scene.subtitle_editor
        resolution = resolve_edit_target_or_report(self, context)
        if not resolution:
            return {"CANCELLED"}

        strip = resolution.strip
        if strip is None:
            self.report({"WARNING"}, "No deterministic TEXT strip target")
            return {"CANCELLED"}
        item = resolution.item

        delta = max(1, props.nudge_step) * (1 if self.direction >= 0 else -1)
        strip_start = int(strip.frame_final_start)
        strip_end = int(strip.frame_final_end)

        def _set_end(target_strip, new_end: int) -> bool:
            for attr in ("frame_final_end", "frame_end"):
                if hasattr(target_strip, attr):
                    try:
                        setattr(target_strip, attr, new_end)
                        return True
                    except (AttributeError, TypeError, ValueError, RuntimeError):
                        continue
            return False

        def _set_duration(target_strip, duration: int) -> bool:
            for attr in ("frame_final_duration", "frame_duration"):
                if hasattr(target_strip, attr):
                    try:
                        setattr(target_strip, attr, duration)
                        return True
                    except (AttributeError, TypeError, ValueError, RuntimeError):
                        continue
            return False

        if self.edge == "START":
            new_start = max(scene.frame_start, strip_start + delta)
            new_start = min(new_start, strip_end - 1)
            if new_start != strip_start:
                new_duration = max(1, strip_end - new_start)
                strip.frame_start = new_start
                if not _set_end(strip, strip_end):
                    _set_duration(strip, new_duration)
        else:
            new_end = max(strip_start + 1, strip_end + delta)
            new_duration = max(1, new_end - strip_start)
            if not _set_end(strip, new_end):
                _set_duration(strip, new_duration)

        if item is not None:
            item.frame_start = strip.frame_final_start
            item.frame_end = strip.frame_final_end

        scene.frame_current = strip.frame_final_start

        return {"FINISHED"}
