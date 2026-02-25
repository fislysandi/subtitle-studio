"""
Strip Edit Operators
"""

import bpy
import os
from bpy.types import Operator

from ..core.style_plan import build_style_patch_from_props
from ..utils import sequence_utils
from .ops_strip_navigation import (
    SUBTITLE_OT_jump_to_selected_end,
    SUBTITLE_OT_jump_to_selected_start,
    SUBTITLE_OT_nudge_strip,
    SUBTITLE_OT_select_next_strip,
    SUBTITLE_OT_select_previous_strip,
    SUBTITLE_OT_select_strip,
)
from .ops_strip_edit_helpers import (
    apply_style_patch_to_strip as _apply_style_patch_to_strip,
    get_cursor_frame as _get_cursor_frame,
    get_default_duration as _get_default_duration,
    get_preset_data as _get_preset_data,
    get_unique_strip_name as _get_unique_strip_name,
    resolve_edit_target_or_report as _resolve_edit_target_or_report,
    set_preset_data as _set_preset_data,
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
        props.outline_color = preset["outline_color"]
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
    bl_description = "Apply current font size, text color, and outline settings to selected subtitle strips"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        props = scene.subtitle_editor
        style_patch = build_style_patch_from_props(props)

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
            if _apply_style_patch_to_strip(strip, style_patch):
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
        "use_outline",
        "outline_color",
        "outline_width",
        "use_shadow",
        "shadow_color",
        "use_box",
        "box_color",
        "box_margin",
        "location",
        "box_line_thickness",
        "wrap_width",
        "align_x",
        "align_y",
    )
    _DEBUG_ENV = "SUBTITLE_STUDIO_COPY_STYLE_DEBUG"

    @classmethod
    def _is_debug_enabled(cls, context) -> bool:
        props = getattr(getattr(context, "scene", None), "subtitle_editor", None)
        if props:
            for attr_name in ("copy_style_debug", "debug_copy_style", "debug_mode"):
                if hasattr(props, attr_name):
                    return bool(getattr(props, attr_name))

        env_value = os.getenv(cls._DEBUG_ENV, "")
        return env_value.lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _debug(enabled: bool, message: str) -> None:
        if enabled:
            print(f"[Subtitle Studio][CopyStyle] {message}")

    @classmethod
    def _debug_strip_names(cls, enabled: bool, label: str, strips) -> None:
        if not enabled:
            return

        names = [getattr(strip, "name", "<unnamed>") for strip in strips[:10]]
        cls._debug(True, f"{label}: count={len(strips)} names={names}")

    @staticmethod
    def _read_style_value(strip, attr):
        if hasattr(strip, attr):
            return True, getattr(strip, attr)

        if attr == "align_x" and hasattr(strip, "location"):
            loc = getattr(strip, "location")
            if len(loc) >= 2:
                return True, float(loc[0])

        if attr == "align_y" and hasattr(strip, "location"):
            loc = getattr(strip, "location")
            if len(loc) >= 2:
                return True, float(loc[1])

        if attr == "box_line_thickness" and hasattr(strip, "box_margin"):
            return True, getattr(strip, "box_margin")

        return False, None

    def execute(self, context):
        scene = context.scene
        if not scene or not scene.sequence_editor:
            self.report({"WARNING"}, "Open the Sequencer to copy styles")
            return {"CANCELLED"}

        debug_enabled = self._is_debug_enabled(context)

        active_strip = scene.sequence_editor.active_strip
        if debug_enabled:
            self._debug(
                True,
                "Active strip: "
                f"name={getattr(active_strip, 'name', None)} "
                f"type={getattr(active_strip, 'type', None)}",
            )

        if not active_strip or getattr(active_strip, "type", "") != "TEXT":
            self.report({"WARNING"}, "Select a text strip to copy from")
            return {"CANCELLED"}

        selected = sequence_utils.get_selected_text_strips_in_current_scope(scene)
        selection_source = "scope.select"

        if not selected:
            scope_text_by_name = sequence_utils.get_scope_text_strip_map(scene)
            selected = sequence_utils.get_selected_text_strips_from_sequencer_context(
                scene,
                text_by_name=scope_text_by_name,
            )
            selection_source = "sequencer_context"

            if not selected:
                resolved = []
                seen_names = set()
                for strip in getattr(context, "selected_editable_sequences", []):
                    if getattr(strip, "type", "") != "TEXT":
                        continue

                    mapped = scope_text_by_name.get(getattr(strip, "name", ""))
                    if mapped is None:
                        continue

                    mapped_name = getattr(mapped, "name", "")
                    if mapped_name in seen_names:
                        continue

                    seen_names.add(mapped_name)
                    resolved.append(mapped)

                selected = resolved
                selection_source = "context.selected_editable_sequences"

                if not selected:
                    selected = (
                        sequence_utils.get_selected_text_strips_from_active_parent(
                            scene,
                            active_strip,
                        )
                    )
                    selection_source = "active_parent_collection"

        if debug_enabled:
            self._debug(True, f"Selection source: {selection_source}")
        self._debug_strip_names(debug_enabled, "Selected text strips", selected)

        targets = [
            strip
            for strip in selected
            if strip.type == "TEXT" and strip != active_strip
        ]

        if not targets:
            self.report({"WARNING"}, "Select at least one other text strip")
            return {"CANCELLED"}

        self._debug_strip_names(debug_enabled, "Target strips", targets)

        source_style_map = {}
        for attr in self._STYLE_ATTRS:
            has_source, source_value = self._read_style_value(active_strip, attr)
            if has_source:
                source_style_map[attr] = source_value

        if not source_style_map:
            self.report({"WARNING"}, "Active strip has no copyable style properties")
            return {"CANCELLED"}

        source_style_items = tuple(source_style_map.items())
        copied = 0
        total_attr_success = 0
        for strip in targets:
            attr_success = 0
            for attr, source_value in source_style_items:
                try:
                    if hasattr(strip, attr):
                        setattr(strip, attr, source_value)
                    elif attr in {"align_x", "align_y"} and hasattr(strip, "location"):
                        loc = strip.location
                        if len(loc) < 2:
                            continue
                        x_val = float(loc[0])
                        y_val = float(loc[1])
                        if attr == "align_x":
                            x_val = float(source_value)
                        else:
                            y_val = float(source_value)
                        strip.location = (x_val, y_val)
                    elif attr == "box_line_thickness" and hasattr(strip, "box_margin"):
                        strip.box_margin = source_value
                    else:
                        continue

                    attr_success += 1
                    total_attr_success += 1
                except (AttributeError, TypeError, ValueError):
                    continue

            if attr_success > 0:
                copied += 1
            if debug_enabled:
                self._debug(
                    True,
                    f"Target={strip.name} applied={attr_success}/{len(source_style_items)}",
                )

        if debug_enabled:
            self._debug(
                True,
                f"Copy complete: strips_with_changes={copied}, targets={len(targets)}, "
                f"total_attr_success={total_attr_success}",
            )
        self.report(
            {"INFO"},
            f"Copied style to {copied} strip(s) ({total_attr_success} attribute writes)",
        )
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
