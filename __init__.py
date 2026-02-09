"""
Subtitle Studio - Blender Addon Framework Edition

AI-powered subtitle transcription and editing for Blender Video Sequence Editor.
Now using Blender Addon Framework for auto-loading, hot-reload, and UV dependency management.
"""

import bpy
from bpy.props import (
    PointerProperty,
    CollectionProperty,
    IntProperty,
    StringProperty,
    BoolProperty,
)
from bpy.types import AddonPreferences

# Framework imports
from .config import __addon_name__
from ...common.class_loader import auto_load
from ...common.class_loader.auto_load import add_properties, remove_properties
from ...common.i18n.i18n import load_dictionary
from .i18n.dictionary import dictionary

# Property groups (must be imported for _addon_properties)
from .props import SubtitleEditorProperties, TextStripItem


# =============================================================================
# Addon Preferences
# =============================================================================


class SubtitleEditorAddonPreferences(AddonPreferences):
    """Addon preferences for Subtitle Studio"""

    bl_idname = __addon_name__

    hf_token: StringProperty(
        name="Hugging Face Token",
        description="Optional: Hugging Face authentication token for faster model downloads. Get yours at https://huggingface.co/settings/tokens",
        default="",
        subtype="PASSWORD",
    )

    use_uv: BoolProperty(
        name="Use UV for Downloads",
        description="Use 'uv' package manager for faster downloads (disable if you have connection issues)",
        default=True,
    )

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Dependency Management", icon="PACKAGE")
        box.prop(self, "use_uv")

        box = layout.box()
        box.label(text="Authentication", icon="LOCKED")
        box.prop(self, "hf_token")

        box.label(text="Set a Hugging Face token for faster downloads", icon="INFO")
        box.label(text="Get your token at: https://huggingface.co/settings/tokens")


# =============================================================================
# Blender Add-on Info
# =============================================================================

bl_info = {
    "name": "Subtitle Studio",
    "author": "Fislysandi (original by tin2tin)",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "Video Sequence Editor > Sidebar > Subtitle Studio",
    "description": "AI-powered subtitle transcription and editing for Blender VSE. Based on https://github.com/tin2tin/Subtitle_Editor",
    "warning": "",
    "doc_url": "",
    "category": "Sequencer",
}

# =============================================================================
# Addon Properties
# =============================================================================

from .utils import sequence_utils

# Properties are registered via this dict (framework convention)
# Don't define your own property group class in this file - import from props.py
_addon_properties = {
    bpy.types.Scene: {
        "subtitle_editor": PointerProperty(type=SubtitleEditorProperties),
        "text_strip_items": CollectionProperty(type=TextStripItem),
        "text_strip_items_index": IntProperty(
            default=-1, update=sequence_utils.on_text_strip_index_update
        ),
    }
}

# List of classes to register manually (not auto-discovered)
_manual_classes = [
    SubtitleEditorAddonPreferences,
]


def _sync_speaker_names_handler(depsgraph):
    for scene in bpy.data.scenes:
        props = getattr(scene, "subtitle_editor", None)
        if not props or not scene.sequence_editor:
            continue

        strips = [s for s in scene.sequence_editor.strips if s.type == "TEXT"]
        channel_state = {s.name: s.channel for s in strips}
        cache = scene.get("_subtitle_channel_cache", {})

        if channel_state != cache:
            scene["_subtitle_channel_cache"] = channel_state
            props.update_speaker_channels(bpy.context)


# =============================================================================
# Registration
# =============================================================================


def register():
    """Register the addon using framework's auto_load"""
    # Register manual classes (preferences, etc.)
    for cls in _manual_classes:
        bpy.utils.register_class(cls)

    # Initialize and register auto-discovered classes
    auto_load.init()
    auto_load.register()

    # Register addon properties
    add_properties(_addon_properties)

    # Load translations
    load_dictionary(dictionary)
    bpy.app.translations.register(__addon_name__, dictionary)

    if _sync_speaker_names_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_sync_speaker_names_handler)

    print(f"[Subtitle Studio] {__addon_name__} addon registered successfully")


def unregister():
    """Unregister the addon"""
    # Unload translations
    bpy.app.translations.unregister(__addon_name__)

    # Unregister classes
    auto_load.unregister()

    if _sync_speaker_names_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_sync_speaker_names_handler)

    # Unregister manual classes (in reverse order)
    for cls in reversed(_manual_classes):
        bpy.utils.unregister_class(cls)

    # Remove properties
    remove_properties(_addon_properties)

    print(f"[Subtitle Studio] {__addon_name__} addon unregistered")


if __name__ == "__main__":
    register()
