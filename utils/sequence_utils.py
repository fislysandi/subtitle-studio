"""
Sequence Utilities

Helper functions for working with Blender sequencer
"""

import bpy
from typing import Optional, List, Any


def get_selected_strip(context) -> Optional[Any]:
    """Get the currently selected strip in the sequencer"""
    if not context.scene.sequence_editor:
        return None

    selected = [s for s in context.scene.sequence_editor.sequences if s.select]
    if selected:
        return selected[0]
    return None


def get_selected_strips(context) -> List[Any]:
    """Get all selected strips in the sequencer"""
    if not context.scene.sequence_editor:
        return []

    return [s for s in context.scene.sequence_editor.sequences if s.select]


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
    scene, name: str, text: str, frame_start: int, frame_end: int, channel: int = 3
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

    # Create text strip
    strip = scene.sequence_editor.sequences.new_effect(
        name=name,
        type="TEXT",
        channel=channel,
        frame_start=frame_start,
        length=length,
    )

    # Set text properties
    strip.text = text
    strip.font_size = 24
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

    if not context.scene.sequence_editor:
        return

    # Get the designated subtitle channel from settings
    subtitle_channel = props.subtitle_channel
    speaker_count = max(1, int(getattr(props, "speaker_count", 1)))
    channels = {subtitle_channel + offset for offset in range(speaker_count)}

    # Add only text strips that are on the subtitle channel
    for strip in context.scene.sequence_editor.sequences:
        if strip.type == "TEXT" and strip.channel in channels:
            item = context.scene.text_strip_items.add()
            item.name = strip.name
            item.text = strip.text
            item.frame_start = strip.frame_final_start
            item.frame_end = strip.frame_final_end
            item.channel = strip.channel
            if not item.speaker:
                prefix = None
                if ":" in strip.name:
                    head = strip.name.split(":", 1)[0].strip()
                    if head in [
                        props.speaker_name_1,
                        props.speaker_name_2,
                        props.speaker_name_3,
                    ]:
                        prefix = head

                if prefix:
                    item.speaker = prefix
                else:
                    item.speaker = props._speaker_label()
            item.is_selected = strip.select


def get_text_strips(scene) -> List[Any]:
    """Get all text strips in the scene"""
    if not scene.sequence_editor:
        return []

    return [s for s in scene.sequence_editor.sequences if s.type == "TEXT"]


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
        if context.scene.sequence_editor:
            # Deselect all
            for s in context.scene.sequence_editor.sequences:
                s.select = False

            # Select the matching strip
            for s in context.scene.sequence_editor.sequences:
                if s.name == item.name:
                    s.select = True
                    context.scene.sequence_editor.active_strip = s
                    break
