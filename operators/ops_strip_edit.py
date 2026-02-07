"""
Strip Edit Operators
"""

import bpy
from bpy.types import Operator

from ..utils import sequence_utils


class SUBTITLE_OT_refresh_list(Operator):
    """Refresh the list of text strips"""

    bl_idname = "subtitle.refresh_list"
    bl_label = "Refresh List"
    bl_description = "Refresh the subtitle strips list"
    bl_options = {"REGISTER"}

    def execute(self, context):
        sequence_utils.refresh_list(context)
        return {"FINISHED"}


class SUBTITLE_OT_select_strip(Operator):
    """Select a text strip"""

    bl_idname = "subtitle.select_strip"
    bl_label = "Select Strip"
    bl_description = "Select this subtitle strip in the sequencer"
    bl_options = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene

        if self.index < 0 or self.index >= len(scene.text_strip_items):
            return {"CANCELLED"}

        item = scene.text_strip_items[self.index]

        # Find and select the strip
        if scene.sequence_editor:
            for strip in scene.sequence_editor.sequences_all:
                strip.select = strip.name == item.name
                if strip.name == item.name:
                    # Jump to strip
                    scene.frame_current = strip.frame_final_start

        # Update current text
        scene.subtitle_editor.current_text = item.text

        return {"FINISHED"}


class SUBTITLE_OT_update_text(Operator):
    """Update subtitle text"""

    bl_idname = "subtitle.update_text"
    bl_label = "Update Text"
    bl_description = "Update the selected subtitle text"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        index = scene.text_strip_items_index

        if index < 0 or index >= len(scene.text_strip_items):
            self.report({"WARNING"}, "No subtitle selected")
            return {"CANCELLED"}

        item = scene.text_strip_items[index]
        new_text = scene.subtitle_editor.current_text

        # Update UI list
        item.text = new_text

        # Update actual strip
        if scene.sequence_editor:
            for strip in scene.sequence_editor.sequences_all:
                if strip.name == item.name and strip.type == "TEXT":
                    strip.text = new_text
                    break

        return {"FINISHED"}
