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
    sequences = sequence_utils._get_sequence_collection(scene)
    if not sequences:
        return base_name

    existing_names = {strip.name for strip in sequences}
    if base_name not in existing_names:
        return base_name

    index = 1
    while f"{base_name}_{index}" in existing_names:
        index += 1
    return f"{base_name}_{index}"


def _select_strip_by_index(context, index: int) -> bool:
    scene = context.scene

    if index < 0 or index >= len(scene.text_strip_items):
        return False
    scene.text_strip_items_index = index
    return True


def _resolve_edit_target_or_report(operator, context):
    resolution = sequence_utils.resolve_edit_target(context, allow_index_fallback=False)
    if resolution.strip:
        return resolution

    operator.report(
        {"WARNING"},
        resolution.warning or "No deterministic TEXT strip target",
    )
    return None


def _get_preset_data(props, preset_id: str):
    if preset_id == "PRESET_1":
        return {
            "name": props.preset_1_name,
            "font_size": props.preset_1_font_size,
            "text_color": props.preset_1_text_color,
            "shadow_color": props.preset_1_shadow_color,
            "v_align": props.preset_1_v_align,
            "wrap_width": props.preset_1_wrap_width,
        }
    if preset_id == "PRESET_2":
        return {
            "name": props.preset_2_name,
            "font_size": props.preset_2_font_size,
            "text_color": props.preset_2_text_color,
            "shadow_color": props.preset_2_shadow_color,
            "v_align": props.preset_2_v_align,
            "wrap_width": props.preset_2_wrap_width,
        }
    return {
        "name": props.preset_3_name,
        "font_size": props.preset_3_font_size,
        "text_color": props.preset_3_text_color,
        "shadow_color": props.preset_3_shadow_color,
        "v_align": props.preset_3_v_align,
        "wrap_width": props.preset_3_wrap_width,
    }


def _set_preset_data(props, preset_id: str):
    if preset_id == "PRESET_1":
        props.preset_1_font_size = props.font_size
        props.preset_1_text_color = props.text_color
        props.preset_1_shadow_color = props.shadow_color
        props.preset_1_v_align = props.v_align
        props.preset_1_wrap_width = props.wrap_width
        return
    if preset_id == "PRESET_2":
        props.preset_2_font_size = props.font_size
        props.preset_2_text_color = props.text_color
        props.preset_2_shadow_color = props.shadow_color
        props.preset_2_v_align = props.v_align
        props.preset_2_wrap_width = props.wrap_width
        return
    props.preset_3_font_size = props.font_size
    props.preset_3_text_color = props.text_color
    props.preset_3_shadow_color = props.shadow_color
    props.preset_3_v_align = props.v_align
    props.preset_3_wrap_width = props.wrap_width


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
        if not _select_strip_by_index(context, self.index):
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

        if not _select_strip_by_index(context, next_index):
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

        if not _select_strip_by_index(context, prev_index):
            return {"CANCELLED"}
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


def _jump_to_selected(context, edge: str):
    scene = context.scene
    resolution = sequence_utils.resolve_edit_target(context, allow_index_fallback=False)
    strip = resolution.strip
    if not strip:
        return False, resolution.warning or "No subtitle selected"

    if edge == "END":
        scene.frame_current = strip.frame_final_end
    else:
        scene.frame_current = strip.frame_final_start

    sequences = sequence_utils._get_sequence_collection(scene)
    if sequences:
        for seq in sequences:
            seq.select = seq == strip
    if scene.sequence_editor:
        scene.sequence_editor.active_strip = strip

    return True, ""


class SUBTITLE_OT_jump_to_selected_start(Operator):
    """Jump timeline to the selected subtitle start"""

    bl_idname = "subtitle.jump_to_selected_start"
    bl_label = "Jump to Start"
    bl_description = "Jump the timeline to the selected subtitle start"
    bl_options = {"REGISTER"}

    def execute(self, context):
        ok, message = _jump_to_selected(context, "START")
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
        ok, message = _jump_to_selected(context, "END")
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
        resolution = _resolve_edit_target_or_report(self, context)
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
                    except Exception:
                        continue
            return False

        def _set_duration(target_strip, duration: int) -> bool:
            for attr in ("frame_final_duration", "frame_duration"):
                if hasattr(target_strip, attr):
                    try:
                        setattr(target_strip, attr, duration)
                        return True
                    except Exception:
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


class SUBTITLE_OT_apply_style_preset(Operator):
    """Apply a style preset to the current editor values"""

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
        preset = _get_preset_data(props, self.preset_id)

        props.font_size = preset["font_size"]
        props.text_color = preset["text_color"]
        props.shadow_color = preset["shadow_color"]
        props.v_align = preset["v_align"]
        props.wrap_width = preset["wrap_width"]

        return {"FINISHED"}


class SUBTITLE_OT_save_style_preset(Operator):
    """Save the current style into a preset slot"""

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
        _set_preset_data(props, self.preset_id)
        return {"FINISHED"}


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
                    elif props.v_align == "CUSTOM":
                        strip.location = (0.5, 0.5)
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
