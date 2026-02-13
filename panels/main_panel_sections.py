"""
Main panel draw helpers for Subtitle Studio.
"""

import bpy
from ..utils import sequence_utils


def _log_panel_error(panel: str, section: str, exc: Exception) -> None:
    message = f"{panel}::{section} failed: {exc}"
    print(f"[Subtitle Studio] {message}")


def _get_props(context, panel: str, section: str):
    scene = getattr(context, "scene", None)
    if not scene:
        _log_panel_error(panel, section, RuntimeError("No active scene"))
        return None
    props = getattr(scene, "subtitle_editor", None)
    if not props:
        _log_panel_error(
            panel, section, AttributeError("scene.subtitle_editor missing")
        )
        return None
    return props


def draw_list_section(layout, context):
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

    button_col = row.column(align=True)
    button_col.operator("subtitle.refresh_list", text="", icon="FILE_REFRESH")
    button_col.separator()
    button_col.operator("subtitle.import_subtitles", text="", icon="IMPORT")
    button_col.operator("subtitle.export_subtitles", text="", icon="EXPORT")
    button_col.separator()
    button_col.operator("subtitle.add_strip_at_cursor", text="", icon="ADD")
    button_col.operator("subtitle.remove_selected_strip", text="", icon="REMOVE")
    button_col.separator()
    button_col.operator("subtitle.select_next_strip", text="", icon="TRIA_UP")
    button_col.operator("subtitle.select_previous_strip", text="", icon="TRIA_DOWN")
    button_col.separator()


def draw_edit_section(layout, context):
    scene = context.scene
    sequence_utils.sync_list_selection_from_sequencer(context)
    props = _get_props(context, "SEQUENCER_PT_panel", "edit_section")
    if not props:
        return

    layout.separator()

    if scene.text_strip_items_index >= 0 and scene.text_strip_items:
        item = scene.text_strip_items[scene.text_strip_items_index]
        col = layout.column()

        box = col.box()
        box.label(text=f"Editing: {item.name}")
        box.prop(props, "current_text")

        box = col.box()
        box.label(text="Subtitle Editing Tools")
        row = box.row(align=True)
        row.prop(props, "nudge_step", text="Step")

        row = box.row(align=True)
        row.operator("subtitle.jump_to_selected_start", text="Start", icon="TIME")
        op = row.operator("subtitle.nudge_strip", text="-", icon="TRIA_LEFT")
        op.edge = "START"
        op.direction = -1
        op = row.operator("subtitle.nudge_strip", text="+", icon="TRIA_RIGHT")
        op.edge = "START"
        op.direction = 1

        row = box.row(align=True)
        row.operator("subtitle.jump_to_selected_end", text="End", icon="TIME")
        op = row.operator("subtitle.nudge_strip", text="-", icon="TRIA_LEFT")
        op.edge = "END"
        op.direction = -1
        op = row.operator("subtitle.nudge_strip", text="+", icon="TRIA_RIGHT")
        op.edge = "END"
        op.direction = 1

        row = box.row(align=True)
        row.prop(item, "frame_start", text="Start")
        row.prop(item, "frame_end", text="End")

        box.prop(props, "font_size")
        row = box.row(align=True)
        row.prop(props, "text_color")
        row.prop(props, "shadow_color")
        row = box.row(align=True)
        row.prop(props, "v_align")
        row.prop(props, "wrap_width")

        box.prop(props, "max_chars_per_line")
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
