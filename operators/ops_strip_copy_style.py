"""Copy-style operator extracted from strip edit module."""

import os
import bpy
from bpy.types import Operator

from ..utils import sequence_utils


class SUBTITLE_OT_copy_style_from_active(Operator):
    """Copy style from the active strip to other selected strips."""

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
