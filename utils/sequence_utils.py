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

    selected = [s for s in context.scene.sequence_editor.sequences_all if s.select]
    if selected:
        return selected[0]
    return None


def get_strip_filepath(strip) -> Optional[str]:
    """Get file path from a movie or sound strip"""
    if strip.type == "MOVIE":
        return strip.filepath
    elif strip.type == "SOUND":
        return strip.sound.filepath if strip.sound else None
    elif strip.type == "SCENE":
        # Scene strips don't have files
        return None
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

    # Create text strip
    strip = scene.sequence_editor.sequences.new_effect(
        name=name, type="TEXT", channel=channel, frame_start=frame_start, frame_end=frame_end
    )

    # Set text properties
    strip.text = text
    strip.font_size = 24
    strip.location = (0.5, 0.1)  # Center bottom
    strip.use_shadow = True
    strip.shadow_color = (0, 0, 0)

    return strip


def refresh_list(context):
    """Refresh the UI list of text strips"""
    if not context.scene:
        return

    # Clear current list
    context.scene.text_strip_items.clear()

    if not context.scene.sequence_editor:
        return

    # Add all text strips
    for strip in context.scene.sequence_editor.sequences_all:
        if strip.type == "TEXT":
            item = context.scene.text_strip_items.add()
            item.name = strip.name
            item.text = strip.text
            item.frame_start = strip.frame_final_start
            item.frame_end = strip.frame_final_end
            item.channel = strip.channel
            item.is_selected = strip.select


def get_text_strips(scene) -> List[Any]:
    """Get all text strips in the scene"""
    if not scene.sequence_editor:
        return []

    return [s for s in scene.sequence_editor.sequences_all if s.type == "TEXT"]


def update_text_strip(strip, text: str):
    """Update text content of a strip"""
    if strip and strip.type == "TEXT":
        strip.text = text
