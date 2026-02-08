"""
Strip Edit Operators
"""

import bpy
from bpy.types import Operator

from ..utils import sequence_utils


def _is_vse_cursor_visible(space) -> bool:
    if not space or getattr(space, "type", None) != "SEQUENCE_EDITOR":
        return False

    overlay = getattr(space, "overlay", None)
    return bool(overlay and getattr(overlay, "show_cursor", False))


def _get_cursor_frame(context, scene) -> int:
    # Default to the playhead frame so we respect the user's visible cursor.
    frame_current = getattr(scene, "frame_current_final", scene.frame_current)
    space = context.space_data

    if _is_vse_cursor_visible(space):
        cursor_location = getattr(space, "cursor_location", None)
        if cursor_location is not None:
            return int(round(cursor_location[0]))

        if scene.sequence_editor:
            cursor2d = getattr(scene.sequence_editor, "cursor2d", None)
            if cursor2d is not None:
                return int(round(cursor2d[0]))

    return int(round(frame_current))


def _get_default_duration(scene) -> int:
    fps_base = scene.render.fps_base or 1.0
    duration = int(round(scene.render.fps / fps_base))
    return max(1, duration)


def _get_unique_strip_name(scene, base_name: str) -> str:
    if not scene.sequence_editor:
        return base_name

    existing_names = {strip.name for strip in scene.sequence_editor.strips}
    if base_name not in existing_names:
        return base_name

    index = 1
    while f"{base_name}_{index}" in existing_names:
        index += 1
    return f"{base_name}_{index}"


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
            for strip in scene.sequence_editor.strips:
                strip.select = strip.name == item.name
                if strip.name == item.name:
                    # Jump to strip
                    scene.frame_current = strip.frame_final_start

        # Update current text
        scene.subtitle_editor.current_text = item.text

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
            strip.use_shadow = True
            strip.shadow_color = (
                props.shadow_color[0],
                props.shadow_color[1],
                props.shadow_color[2],
                1.0,
            )
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
        except AttributeError:
            pass

        for s in scene.sequence_editor.strips:
            s.select = False
        strip.select = True
        if scene.sequence_editor:
            scene.sequence_editor.active_strip = strip

        sequence_utils.refresh_list(context)
        for index, item in enumerate(scene.text_strip_items):
            if item.name == strip.name:
                scene.text_strip_items_index = index
                break

        scene.subtitle_editor.current_text = strip.text
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

        if not scene.sequence_editor:
            self.report({"WARNING"}, "No sequence editor to remove from")
            return {"CANCELLED"}

        removed = False
        for strip in list(scene.sequence_editor.strips):
            if strip.name == item.name and strip.type == "TEXT":
                scene.sequence_editor.strips.remove(strip)
                removed = True
                break

        if not removed:
            self.report({"WARNING"}, "Selected subtitle not found in sequencer")
            return {"CANCELLED"}

        sequence_utils.refresh_list(context)

        new_length = len(scene.text_strip_items)
        if new_length == 0:
            scene.text_strip_items_index = -1
            scene.subtitle_editor.current_text = ""
        else:
            scene.text_strip_items_index = min(index, new_length - 1)
            scene.subtitle_editor.current_text = scene.text_strip_items[
                scene.text_strip_items_index
            ].text

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
            for strip in scene.sequence_editor.strips:
                if strip.name == item.name and strip.type == "TEXT":
                    strip.text = new_text
                    break


class SUBTITLE_OT_apply_style(Operator):
    """Apply current style settings to selected subtitle strips"""

    bl_idname = "subtitle.apply_style"
    bl_label = "Apply Style to Selected"
    bl_description = "Apply current font size, color, and shadow settings to all selected subtitle strips"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        props = scene.subtitle_editor

        # Get selected sequences
        selected = sequence_utils.get_selected_strips(context)
        if not selected:
            self.report({"WARNING"}, "No strips selected")
            return {"CANCELLED"}

        count = 0
        for strip in selected:
            if strip.type == "TEXT":
                # Apply style
                strip.font_size = props.font_size
                strip.color = props.text_color + (1.0,)  # RGB + Alpha
                # Shadow isn't a direct property on TextSequence in simple API,
                # but let's check if we can set it.
                # Blender VSE Text strips use 'use_shadow' and 'shadow_color' if available?
                # Actually standard VSE Text Strip has:
                # - font_size
                # - color
                # - use_shadow (bool)
                # - shadow_color (rgba)

                # Let's check what properties are available on standard text strip using dir() if needed,
                # but standard API usually supports these.

                # For safety let's use try/except block for properties that might vary by version
                try:
                    strip.font_size = props.font_size
                except AttributeError:
                    pass

                try:
                    # props.text_color is FloatVector(size=3)
                    # strip.color is FloatVector(size=4) usually
                    strip.color = (
                        props.text_color[0],
                        props.text_color[1],
                        props.text_color[2],
                        1.0,
                    )
                except AttributeError:
                    pass

                try:
                    strip.use_shadow = True
                    strip.shadow_color = (
                        props.shadow_color[0],
                        props.shadow_color[1],
                        props.shadow_color[2],
                        1.0,
                    )
                except AttributeError:
                    pass

                # Also alignment
                try:
                    if props.v_align == "TOP":
                        strip.align_y = "TOP"
                    elif props.v_align == "CENTER":
                        strip.align_y = "CENTER"
                    elif props.v_align == "BOTTOM":
                        strip.align_y = "BOTTOM"
                except AttributeError:
                    pass

                count += 1

        self.report({"INFO"}, f"Applied style to {count} strips")
        return {"FINISHED"}


class SUBTITLE_OT_copy_style_from_active(Operator):
    """Copy style from the active strip to other selected strips"""

    bl_idname = "subtitle.copy_style_from_active"
    bl_label = "Copy Style to Selected"
    bl_description = "Copy the active strip's styling to other selected text strips"
    bl_options = {"REGISTER", "UNDO"}

    _STYLE_ATTRS = (
        "font",
        "font_size",
        "color",
        "use_shadow",
        "shadow_color",
        "use_box",
        "box_color",
        "box_margin",
        "box_line_thickness",
        "wrap_width",
        "align_x",
        "align_y",
        "location",
    )

    def execute(self, context):
        scene = context.scene
        if not scene or not scene.sequence_editor:
            self.report({"WARNING"}, "Open the Sequencer to copy styles")
            return {"CANCELLED"}

        active_strip = scene.sequence_editor.active_strip
        if not active_strip or active_strip.type != "TEXT":
            self.report({"WARNING"}, "Select a text strip to copy from")
            return {"CANCELLED"}

        selected = sequence_utils.get_selected_strips(context)
        targets = [
            strip
            for strip in selected
            if strip.type == "TEXT" and strip != active_strip
        ]

        if not targets:
            self.report({"WARNING"}, "Select other text strips to receive the style")
            return {"CANCELLED"}

        copied = 0
        for strip in targets:
            for attr in self._STYLE_ATTRS:
                if hasattr(active_strip, attr) and hasattr(strip, attr):
                    try:
                        setattr(strip, attr, getattr(active_strip, attr))
                    except (AttributeError, TypeError):
                        continue
            copied += 1

        sequence_utils.refresh_list(context)
        self.report({"INFO"}, f"Copied style to {copied} strip(s)")
        return {"FINISHED"}


class SUBTITLE_OT_insert_line_breaks(Operator):
    """Insert line breaks into selected subtitles"""

    bl_idname = "subtitle.insert_line_breaks"
    bl_label = "Insert Line Breaks"
    bl_description = "Insert line breaks to fit text within character limit"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        import textwrap

        scene = context.scene
        props = scene.subtitle_editor
        max_chars = props.max_chars_per_line

        # Get selected sequences
        selected = sequence_utils.get_selected_strips(context)
        if not selected:
            self.report({"WARNING"}, "No strips selected")
            return {"CANCELLED"}

        count = 0
        for strip in selected:
            if strip.type == "TEXT":
                # Get current text
                current_text = strip.text

                # Unwrap first to remove existing line breaks if any (optional, but good for re-flowing)
                # But simple assumption: input is just text.
                # Let's replace single newlines with spaces to allow re-flow, but keep double newlines?
                # For simple subtitles, usually just one block.
                # Let's just wrap existing text.

                # Logic: Split by newlines first to preserve intentional paragraphs?
                # Standard approach: treat as one block for simple wrapping.

                wrapped_lines = textwrap.wrap(current_text, width=max_chars)
                new_text = "\n".join(wrapped_lines)

                if new_text != current_text:
                    strip.text = new_text
                    count += 1

        self.report({"INFO"}, f"Updated {count} strips")
        return {"FINISHED"}


classes = [
    SUBTITLE_OT_refresh_list,
    SUBTITLE_OT_select_strip,
    SUBTITLE_OT_add_strip_at_cursor,
    SUBTITLE_OT_remove_selected_strip,
    SUBTITLE_OT_update_text,
    SUBTITLE_OT_apply_style,
    SUBTITLE_OT_copy_style_from_active,
    SUBTITLE_OT_insert_line_breaks,
]
