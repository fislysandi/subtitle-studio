"""
Sequence Utilities

Helper functions for working with Blender sequencer
"""

import bpy
from typing import Optional, List, Any


def _get_sequence_collection(scene):
    if not scene.sequence_editor:
        return None

    return scene.sequence_editor.strips


def get_selected_strip(context) -> Optional[Any]:
    """Get the currently selected strip in the sequencer"""
    sequences = _get_sequence_collection(context.scene)
    if not sequences:
        return None

    selected = [s for s in sequences if s.select]
    if selected:
        return selected[0]
    return None


def get_selected_strips(context) -> List[Any]:
    """Get all selected strips in the sequencer"""
    sequences = _get_sequence_collection(context.scene)
    if not sequences:
        return []

    return [s for s in sequences if s.select]


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

    index = context.scene.text_strip_items_index
    items = context.scene.text_strip_items

    if 0 <= index < len(items):
        item = items[index]
        # Jump cursor to start of strip
        context.scene.frame_current = item.frame_start

        # Sync editing text
        context.scene.subtitle_editor.current_text = item.text

        # Optional: Select the actual strip in sequencer
        # This keeps the UI list and Sequencer selection in sync
        sequences = _get_sequence_collection(context.scene)
        if sequences:
            # Deselect all
            for s in sequences:
                s.select = False

            # Select the matching strip
            for s in sequences:
                if s.name == item.name:
                    s.select = True
                    if context.scene.sequence_editor:
                        context.scene.sequence_editor.active_strip = s
                    break


def sync_list_selection_from_sequencer(context) -> bool:
    """Sync panel list selection from currently selected TEXT strip."""
    scene = getattr(context, "scene", None)
    if not scene:
        return False

    props = getattr(scene, "subtitle_editor", None)
    if not props:
        return False

    selected = get_selected_strip(context)
    if not selected or getattr(selected, "type", "") != "TEXT":
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

    # Keep inline editor text in sync without triggering write-back loop.
    if props.current_text != selected.text:
        props._updating_text = True
        try:
            props.current_text = selected.text
        finally:
            props._updating_text = False

    return True
