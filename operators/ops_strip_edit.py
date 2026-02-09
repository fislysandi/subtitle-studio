"""
Strip Edit Operators
"""

import time

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


def _select_strip_by_index(context, index: int) -> bool:
    scene = context.scene

    if index < 0 or index >= len(scene.text_strip_items):
        return False

    item = scene.text_strip_items[index]

    if scene.sequence_editor:
        for strip in scene.sequence_editor.strips:
            strip.select = strip.name == item.name
            if strip.name == item.name:
                scene.frame_current = strip.frame_final_start

    scene.subtitle_editor.current_text = item.text
    scene.text_strip_items_index = index
    return True


def _get_active_item(scene):
    index = scene.text_strip_items_index
    if index < 0 or index >= len(scene.text_strip_items):
        return None
    return scene.text_strip_items[index]


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


def _get_speaker_name(props, index: int) -> str:
    if index == 2:
        return props.speaker_name_2
    if index == 3:
        return props.speaker_name_3
    return props.speaker_name_1


def _set_speaker_name(props, index: int, value: str) -> None:
    if index == 2:
        props.speaker_name_2 = value
    elif index == 3:
        props.speaker_name_3 = value
    else:
        props.speaker_name_1 = value


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
        scene.subtitle_editor.update_speaker_channels(context)
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


def _jump_to_selected(context, edge: str):
    scene = context.scene
    item = _get_active_item(scene)
    if not item:
        return False, "No subtitle selected"

    if not scene.sequence_editor:
        return False, "No sequence editor"

    for strip in scene.sequence_editor.strips:
        if strip.name == item.name and strip.type == "TEXT":
            if edge == "END":
                scene.frame_current = strip.frame_final_end
            else:
                scene.frame_current = strip.frame_final_start
            strip.select = True
            scene.sequence_editor.active_strip = strip
            return True, ""

    return False, "Selected subtitle not found"


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
        item = _get_active_item(scene)
        if not item:
            self.report({"WARNING"}, "No subtitle selected")
            return {"CANCELLED"}

        delta = max(1, props.nudge_step) * (1 if self.direction >= 0 else -1)

        if self.edge == "START":
            item.frame_start = max(scene.frame_start, item.frame_start + delta)
        else:
            item.frame_end = max(item.frame_start + 1, item.frame_end + delta)

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


class SUBTITLE_OT_adjust_speaker_count(Operator):
    """Adjust the number of speaker tabs"""

    bl_idname = "subtitle.adjust_speaker_count"
    bl_label = "Adjust Speaker Count"
    bl_description = "Increase or decrease the number of speaker slots"
    bl_options = {"REGISTER", "UNDO"}

    direction: bpy.props.IntProperty(default=1)
    name: bpy.props.StringProperty(name="Speaker Name", default="")

    def invoke(self, context, event):
        print(
            f"[Subtitle Studio] adjust_speaker_count invoke direction={self.direction}",
            flush=True,
        )
        if self.direction > 0:
            props = getattr(context.scene, "subtitle_editor", None)
            if not props:
                self.report({"WARNING"}, "Subtitle Studio is not registered")
                return {"CANCELLED"}
            next_index = max(1, min(3, props.speaker_count + 1))
            if next_index == 2:
                self.name = props.speaker_name_2
            elif next_index == 3:
                self.name = props.speaker_name_3
            return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name", text="Speaker Name")

    def execute(self, context):
        print(
            f"[Subtitle Studio] adjust_speaker_count execute direction={self.direction} name='{self.name}'",
            flush=True,
        )
        scene = context.scene
        props = getattr(scene, "subtitle_editor", None)
        if not props:
            self.report({"WARNING"}, "Subtitle Studio is not registered")
            return {"CANCELLED"}

        delta = 1 if self.direction >= 0 else -1
        new_count = max(1, min(3, props.speaker_count + delta))

        if new_count == props.speaker_count:
            return {"FINISHED"}

        print(
            f"[Subtitle Studio] speaker_count {props.speaker_count} -> {new_count}",
            flush=True,
        )
        props.speaker_count = new_count
        if props.speaker_index > new_count:
            props.speaker_index = new_count

        if self.direction > 0:
            value = (self.name or "").strip()
            if not value:
                self.report({"WARNING"}, "Speaker name cannot be empty")
                return {"CANCELLED"}
            if new_count == 2:
                props.speaker_name_2 = value
                props.speaker_index = 2
            elif new_count == 3:
                props.speaker_name_3 = value
                props.speaker_index = 3

        print(
            "[Subtitle Studio] update_speaker_tab/update_speaker_channels/refresh_list",
            flush=True,
        )
        props.update_speaker_tab(context)
        props.update_speaker_channels(context)
        sequence_utils.refresh_list(context)
        return {"FINISHED"}


class SUBTITLE_OT_select_speaker_tab(Operator):
    """Select or rename a speaker tab"""

    bl_idname = "subtitle.select_speaker_tab"
    bl_label = "Select Speaker"
    bl_description = "Select speaker tab (right click to rename)"
    bl_options = {"REGISTER"}

    index: bpy.props.IntProperty(default=1, min=1, max=3)

    def invoke(self, context, event):
        if event.type == "RIGHTMOUSE":
            bpy.ops.subtitle.rename_speaker("INVOKE_DEFAULT", index=self.index)
            return {"FINISHED"}
        if event.type == "LEFTMOUSE" and event.value == "DOUBLE_CLICK":
            bpy.ops.subtitle.rename_speaker("INVOKE_DEFAULT", index=self.index)
            return {"FINISHED"}
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            wm = context.window_manager
            key = f"_subtitle_speaker_click_{self.index}"
            now = time.monotonic()
            last_click = getattr(wm, key, 0.0)
            setattr(wm, key, now)
            if now - last_click <= 0.35:
                bpy.ops.subtitle.rename_speaker("INVOKE_DEFAULT", index=self.index)
                return {"FINISHED"}
        return self.execute(context)

    def execute(self, context):
        props = context.scene.subtitle_editor
        props.speaker_index = self.index
        return {"FINISHED"}


class SUBTITLE_OT_rename_speaker(Operator):
    """Rename a speaker tab"""

    bl_idname = "subtitle.rename_speaker"
    bl_label = "Rename Speaker"
    bl_description = "Rename speaker tab"
    bl_options = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(default=1, min=1, max=3)
    name: bpy.props.StringProperty(name="Speaker Name", default="")

    def invoke(self, context, event):
        props = context.scene.subtitle_editor
        self.name = _get_speaker_name(props, self.index)
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        props = context.scene.subtitle_editor
        value = (self.name or "").strip()
        if not value:
            self.report({"WARNING"}, "Speaker name cannot be empty")
            return {"CANCELLED"}

        if self.index == 2:
            old_name = props.speaker_name_2
        elif self.index == 3:
            old_name = props.speaker_name_3
        else:
            old_name = props.speaker_name_1

        _set_speaker_name(props, self.index, value)
        for item in context.scene.text_strip_items:
            if item.speaker == old_name:
                item.speaker = value
        props.update_speaker_channels(context)
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
    SUBTITLE_OT_adjust_speaker_count,
    SUBTITLE_OT_select_speaker_tab,
    SUBTITLE_OT_rename_speaker,
    SUBTITLE_OT_copy_style_from_active,
    SUBTITLE_OT_insert_line_breaks,
]
