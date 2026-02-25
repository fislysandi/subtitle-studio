"""Helper utilities for strip edit operators."""

from ..utils import sequence_utils


def is_vse_cursor_visible(space) -> bool:
    if not space or getattr(space, "type", None) != "SEQUENCE_EDITOR":
        return False

    overlay = getattr(space, "overlay", None)
    return bool(overlay and getattr(overlay, "show_cursor", False))


def get_cursor_frame(context, scene) -> int:
    frame_current = getattr(scene, "frame_current_final", scene.frame_current)
    space = context.space_data

    if is_vse_cursor_visible(space):
        cursor_location = getattr(space, "cursor_location", None)
        if cursor_location is not None:
            return int(round(cursor_location[0]))

        if scene.sequence_editor:
            cursor2d = getattr(scene.sequence_editor, "cursor2d", None)
            if cursor2d is not None:
                return int(round(cursor2d[0]))

    return int(round(frame_current))


def get_default_duration(scene) -> int:
    fps_base = scene.render.fps_base or 1.0
    duration = int(round(scene.render.fps / fps_base))
    return max(1, duration)


def get_unique_strip_name(scene, base_name: str) -> str:
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


def select_strip_by_index(context, index: int) -> bool:
    scene = context.scene

    if index < 0 or index >= len(scene.text_strip_items):
        return False
    scene.text_strip_items_index = index
    return True


def resolve_edit_target_or_report(operator, context):
    resolution = sequence_utils.resolve_edit_target(context, allow_index_fallback=False)
    if resolution.strip:
        return resolution

    operator.report(
        {"WARNING"},
        resolution.warning or "No deterministic TEXT strip target",
    )
    return None


def get_preset_data(props, preset_id: str):
    if preset_id == "PRESET_1":
        return {
            "name": props.preset_1_name,
            "font_size": props.preset_1_font_size,
            "text_color": props.preset_1_text_color,
            "outline_color": props.preset_1_shadow_color,
            "v_align": props.preset_1_v_align,
            "wrap_width": props.preset_1_wrap_width,
        }
    if preset_id == "PRESET_2":
        return {
            "name": props.preset_2_name,
            "font_size": props.preset_2_font_size,
            "text_color": props.preset_2_text_color,
            "outline_color": props.preset_2_shadow_color,
            "v_align": props.preset_2_v_align,
            "wrap_width": props.preset_2_wrap_width,
        }
    return {
        "name": props.preset_3_name,
        "font_size": props.preset_3_font_size,
        "text_color": props.preset_3_text_color,
        "outline_color": props.preset_3_shadow_color,
        "v_align": props.preset_3_v_align,
        "wrap_width": props.preset_3_wrap_width,
    }


def set_preset_data(props, preset_id: str):
    if preset_id == "PRESET_1":
        props.preset_1_font_size = props.font_size
        props.preset_1_text_color = props.text_color
        props.preset_1_shadow_color = props.outline_color
        props.preset_1_v_align = props.v_align
        props.preset_1_wrap_width = props.wrap_width
        return
    if preset_id == "PRESET_2":
        props.preset_2_font_size = props.font_size
        props.preset_2_text_color = props.text_color
        props.preset_2_shadow_color = props.outline_color
        props.preset_2_v_align = props.v_align
        props.preset_2_wrap_width = props.wrap_width
        return
    props.preset_3_font_size = props.font_size
    props.preset_3_text_color = props.text_color
    props.preset_3_shadow_color = props.outline_color
    props.preset_3_v_align = props.v_align
    props.preset_3_wrap_width = props.wrap_width


def apply_style_patch_to_strip(strip, style_patch) -> bool:
    if getattr(strip, "type", "") != "TEXT":
        return False

    try:
        strip.font_size = style_patch.font_size
    except AttributeError:
        pass

    try:
        strip.color = style_patch.text_color_rgba
    except AttributeError:
        pass

    try:
        if style_patch.use_outline:
            strip.use_outline = True
            strip.outline_color = style_patch.outline_color_rgba
        else:
            strip.use_outline = False
    except AttributeError:
        pass

    try:
        if style_patch.v_align == "CUSTOM":
            strip.location = (0.5, 0.5)
        else:
            strip.align_y = style_patch.v_align
    except AttributeError:
        pass

    try:
        strip.wrap_width = style_patch.wrap_width
    except AttributeError:
        pass

    return True


def jump_to_selected(context, edge: str):
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
