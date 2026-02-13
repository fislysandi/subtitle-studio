"""
Sequence Utilities

Helper functions for working with Blender sequencer
"""

import bpy
from bpy.app.handlers import persistent
from typing import Optional, List, Any, NamedTuple


_selection_signature_by_scene = {}


class EditTargetResolution(NamedTuple):
    strip: Optional[Any]
    item: Optional[Any]
    item_index: int
    warning: str


def _get_sequence_collection(scene):
    if not scene.sequence_editor:
        return None

    return scene.sequence_editor.strips


def _find_text_strip_by_name(scene, strip_name: str) -> Optional[Any]:
    if not strip_name:
        return None

    sequences = _get_sequence_collection(scene)
    if not sequences:
        return None

    for strip in sequences:
        if strip.type == "TEXT" and strip.name == strip_name:
            return strip

    return None


def _find_list_item_for_strip(scene, strip_name: str):
    items = getattr(scene, "text_strip_items", None)
    if items is None:
        return None, -1

    for idx, item in enumerate(items):
        if item.name == strip_name:
            return item, idx

    return None, -1


def _sync_current_text_from_strip(scene, strip) -> None:
    props = getattr(scene, "subtitle_editor", None)
    if not props:
        return

    if props.current_text == strip.text:
        return

    props._updating_text = True
    try:
        props.current_text = strip.text
    finally:
        props._updating_text = False


def _set_single_strip_selected(scene, target_strip) -> None:
    sequences = _get_sequence_collection(scene)
    if not sequences:
        return

    for strip in sequences:
        strip.select = strip == target_strip

    if scene.sequence_editor:
        scene.sequence_editor.active_strip = target_strip


def get_selected_strip(context) -> Optional[Any]:
    """Get selected TEXT strip, preferring active strip for determinism."""
    sequences = _get_sequence_collection(context.scene)
    if not sequences:
        return None

    active = None
    if context.scene.sequence_editor:
        active = getattr(context.scene.sequence_editor, "active_strip", None)

    if active and getattr(active, "type", "") == "TEXT":
        return active

    selected_text = [s for s in sequences if s.select and s.type == "TEXT"]
    if len(selected_text) == 1:
        return selected_text[0]

    if selected_text and active and getattr(active, "type", "") == "TEXT":
        return active

    return None


def resolve_edit_target(
    context, allow_index_fallback: bool = True
) -> EditTargetResolution:
    """Resolve a single authoritative target for edit UI and tools."""
    scene = getattr(context, "scene", None)
    return resolve_edit_target_for_scene(scene, allow_index_fallback)


def resolve_edit_target_for_scene(
    scene, allow_index_fallback: bool = True
) -> EditTargetResolution:
    """Scene-based target resolver shared by handlers and property callbacks."""
    if not scene:
        return EditTargetResolution(None, None, -1, "No active scene")

    sequences = _get_sequence_collection(scene)
    if not sequences:
        return EditTargetResolution(None, None, -1, "No sequence editor")

    active_strip = None
    if scene.sequence_editor:
        active_strip = getattr(scene.sequence_editor, "active_strip", None)

    selected_text = [s for s in sequences if s.type == "TEXT" and s.select]

    if active_strip and getattr(active_strip, "type", "") == "TEXT":
        item, idx = _find_list_item_for_strip(scene, active_strip.name)
        return EditTargetResolution(active_strip, item, idx, "")

    if len(selected_text) == 1:
        strip = selected_text[0]
        item, idx = _find_list_item_for_strip(scene, strip.name)
        return EditTargetResolution(strip, item, idx, "")

    if len(selected_text) > 1:
        return EditTargetResolution(
            None,
            None,
            -1,
            "Multiple TEXT strips selected; set one active strip to edit.",
        )

    if not allow_index_fallback:
        return EditTargetResolution(None, None, -1, "Select a TEXT strip in Sequencer")

    items = getattr(scene, "text_strip_items", [])
    index = getattr(scene, "text_strip_items_index", -1)
    if 0 <= index < len(items):
        item = items[index]
        strip = _find_text_strip_by_name(scene, item.name)
        if strip:
            return EditTargetResolution(strip, item, index, "")

    return EditTargetResolution(None, None, -1, "Select a TEXT strip in Sequencer")


def get_selected_strips(context) -> List[Any]:
    """Get selected TEXT strips; fallback to active TEXT strip."""
    sequences = _get_sequence_collection(context.scene)
    if not sequences:
        return []

    selected_text = [s for s in sequences if s.select and s.type == "TEXT"]
    if selected_text:
        return selected_text

    active = None
    if context.scene.sequence_editor:
        active = getattr(context.scene.sequence_editor, "active_strip", None)
    if active and getattr(active, "type", "") == "TEXT":
        return [active]

    return []


def get_strip_filepath(strip) -> Optional[str]:
    """Get file path from a movie or sound strip"""
    filepath = None
    if strip.type == "MOVIE":
        filepath = strip.filepath
    elif strip.type == "SOUND":
        filepath = strip.sound.filepath if strip.sound else None

    if filepath:
        # Convert to absolute path (handles // prefix)
        abs_path = bpy.path.abspath(filepath)
        # Normalize path (handles .. and redundant separators)
        import os

        return os.path.abspath(abs_path)
    return None


def create_text_strip(
    scene,
    name: str,
    text: str,
    frame_start: int,
    frame_end: int,
    channel: int = 3,
    font_size: int = 24,
) -> Optional[Any]:
    """Create a text strip in the sequencer

    Args:
        scene: Blender scene
        name: Strip name
        text: Text content
        frame_start: Start frame
        frame_end: End frame
        channel: Sequencer channel

    Returns:
        Created strip or None
    """
    if not scene.sequence_editor:
        scene.sequence_editor_create()

    # Calculate length from frame_start and frame_end
    # Blender 5.0 API: new_effect() uses 'length' instead of 'frame_end'
    length = max(1, frame_end - frame_start)

    sequences = _get_sequence_collection(scene)
    if sequences is None:
        return None

    # Create text strip
    strip = sequences.new_effect(
        name=name,
        type="TEXT",
        channel=channel,
        frame_start=frame_start,
        length=length,
    )

    # Set text properties
    strip.text = text
    strip.font_size = font_size
    strip.location = (0.5, 0.1)  # Center bottom
    strip.use_shadow = True
    strip.shadow_color = (0, 0, 0, 1)  # RGBA - Blender 5.0 requires 4 values

    return strip


def refresh_list(context):
    """Refresh the UI list of text strips on the subtitle channel"""
    if not context.scene:
        return

    props = getattr(context.scene, "subtitle_editor", None)
    if not props:
        return

    # Clear current list
    context.scene.text_strip_items.clear()

    sequences = _get_sequence_collection(context.scene)
    if not sequences:
        return

    # Get the designated subtitle channel from settings
    subtitle_channel = props.subtitle_channel

    # Add only text strips that are on the subtitle channel
    for strip in sequences:
        if strip.type == "TEXT" and strip.channel == subtitle_channel:
            item = context.scene.text_strip_items.add()
            item.name = strip.name
            item.text = strip.text
            item.frame_start = strip.frame_final_start
            item.frame_end = strip.frame_final_end
            item.channel = strip.channel
            item.is_selected = strip.select


def get_text_strips(scene) -> List[Any]:
    """Get all text strips in the scene"""
    sequences = _get_sequence_collection(scene)
    if not sequences:
        return []

    return [s for s in sequences if s.type == "TEXT"]


def on_text_strip_index_update(self, context):
    """Callback when text strip list index changes"""
    if not context.scene:
        return

    scene = context.scene
    props = getattr(scene, "subtitle_editor", None)
    if not props:
        return

    if getattr(props, "_syncing_target", False):
        return

    index = scene.text_strip_items_index
    items = scene.text_strip_items

    if 0 <= index < len(items):
        item = items[index]
        strip = _find_text_strip_by_name(scene, item.name)

        props._syncing_target = True
        try:
            if strip:
                _set_single_strip_selected(scene, strip)
                scene.frame_current = strip.frame_final_start
                if item.text != strip.text:
                    item.text = strip.text
                _sync_current_text_from_strip(scene, strip)
            else:
                scene.frame_current = item.frame_start
                props._updating_text = True
                try:
                    props.current_text = item.text
                finally:
                    props._updating_text = False
        finally:
            props._syncing_target = False


def sync_list_selection_from_sequencer(context) -> bool:
    """Sync panel list selection from currently selected TEXT strip."""
    scene = getattr(context, "scene", None)
    if not scene:
        return False

    resolution = resolve_edit_target(context, allow_index_fallback=False)
    selected = resolution.strip
    if not selected:
        return False

    items = scene.text_strip_items

    def _find_index() -> int:
        for i, item in enumerate(items):
            if item.name == selected.name:
                return i
        return -1

    match_index = _find_index()
    if match_index < 0:
        refresh_list(context)
        items = scene.text_strip_items
        match_index = _find_index()

    if match_index < 0:
        return False

    if scene.text_strip_items_index != match_index:
        scene.text_strip_items_index = match_index

    _sync_current_text_from_strip(scene, selected)

    return True


def _selection_signature(scene):
    sequences = _get_sequence_collection(scene)
    if not sequences:
        return None

    active_name = ""
    if scene.sequence_editor and scene.sequence_editor.active_strip:
        active_name = scene.sequence_editor.active_strip.name

    selected_names = tuple(
        sorted(s.name for s in sequences if s.type == "TEXT" and s.select)
    )

    resolution = resolve_edit_target_for_scene(scene, allow_index_fallback=False)
    strip = resolution.strip
    if strip is None:
        return active_name, selected_names, "", "", -1, -1

    return (
        active_name,
        selected_names,
        strip.name,
        strip.text,
        int(strip.frame_final_start),
        int(strip.frame_final_end),
    )


def _sync_edit_state_from_scene(scene) -> None:
    props = getattr(scene, "subtitle_editor", None)
    if not props:
        return

    resolution = resolve_edit_target_for_scene(scene, allow_index_fallback=False)
    strip = resolution.strip
    if not strip:
        return

    item, idx = _find_list_item_for_strip(scene, strip.name)
    props._syncing_target = True
    try:
        if idx >= 0 and scene.text_strip_items_index != idx:
            scene.text_strip_items_index = idx
        if item and item.text != strip.text:
            item.text = strip.text

        props._updating_timing = True
        try:
            props["edit_frame_start"] = int(strip.frame_final_start)
            props["edit_frame_end"] = int(strip.frame_final_end)
        finally:
            props._updating_timing = False

        props._updating_style = True
        try:
            if hasattr(strip, "font_size"):
                props["font_size"] = int(strip.font_size)
            if hasattr(strip, "color"):
                props["text_color"] = (
                    float(strip.color[0]),
                    float(strip.color[1]),
                    float(strip.color[2]),
                )
            if hasattr(strip, "shadow_color"):
                props["shadow_color"] = (
                    float(strip.shadow_color[0]),
                    float(strip.shadow_color[1]),
                    float(strip.shadow_color[2]),
                )
            if hasattr(strip, "align_y"):
                align_value = str(strip.align_y)
                if props.get("v_align", "") != "CUSTOM":
                    if align_value in {"TOP", "CENTER", "BOTTOM", "CUSTOM"}:
                        props["v_align"] = align_value
            if hasattr(strip, "wrap_width"):
                props["wrap_width"] = float(strip.wrap_width)
        finally:
            props._updating_style = False

        _sync_current_text_from_strip(scene, strip)
    finally:
        props._syncing_target = False


def _poll_selection_sync() -> float:
    """Timer fallback: selection changes don't always emit depsgraph updates."""
    for scene in bpy.data.scenes:
        if not getattr(scene, "subtitle_editor", None):
            continue

        signature = _selection_signature(scene)
        if signature is None:
            continue

        previous = _selection_signature_by_scene.get(scene.name)
        if previous == signature:
            continue

        _selection_signature_by_scene[scene.name] = signature
        _sync_edit_state_from_scene(scene)

    return 0.2


@persistent
def on_depsgraph_update(scene, depsgraph):
    del depsgraph

    if not scene:
        return

    if not getattr(scene, "subtitle_editor", None):
        return

    signature = _selection_signature(scene)
    if signature is None:
        return

    previous = _selection_signature_by_scene.get(scene.name)
    if previous == signature:
        return

    _selection_signature_by_scene[scene.name] = signature
    _sync_edit_state_from_scene(scene)


def register_handlers() -> None:
    handlers = bpy.app.handlers.depsgraph_update_post
    if on_depsgraph_update not in handlers:
        handlers.append(on_depsgraph_update)

    if not bpy.app.timers.is_registered(_poll_selection_sync):
        bpy.app.timers.register(
            _poll_selection_sync, first_interval=0.2, persistent=True
        )


def unregister_handlers() -> None:
    handlers = bpy.app.handlers.depsgraph_update_post
    if on_depsgraph_update in handlers:
        handlers.remove(on_depsgraph_update)

    if bpy.app.timers.is_registered(_poll_selection_sync):
        bpy.app.timers.unregister(_poll_selection_sync)

    _selection_signature_by_scene.clear()
