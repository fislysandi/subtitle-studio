"""
Subtitle Editor - Blender Addon Framework Edition

AI-powered subtitle transcription and editing for Blender Video Sequence Editor.
Now using Blender Addon Framework for auto-loading, hot-reload, and UV dependency management.
"""

import bpy
from bpy.props import PointerProperty, CollectionProperty, IntProperty

# Framework imports
from .config import __addon_name__
from ...common.class_loader import auto_load
from ...common.class_loader.auto_load import add_properties, remove_properties
from ...common.i18n.i18n import load_dictionary
from .i18n.dictionary import dictionary

# Property groups (must be imported for _addon_properties)
from .props import SubtitleEditorProperties, TextStripItem

# =============================================================================
# Blender Add-on Info
# =============================================================================

bl_info = {
    "name": "Subtitle Editor",
    "author": "Your Name",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "Video Sequence Editor > Sidebar > Subtitle Editor",
    "description": "AI-powered subtitle transcription and editing for Blender VSE",
    "warning": "",
    "doc_url": "",
    "category": "Sequencer",
}

# =============================================================================
# Addon Properties
# =============================================================================

# Properties are registered via this dict (framework convention)
# Don't define your own property group class in this file - import from props.py
_addon_properties = {
    bpy.types.Scene: {
        "subtitle_editor": PointerProperty(type=SubtitleEditorProperties),
        "text_strip_items": CollectionProperty(type=TextStripItem),
        "text_strip_items_index": IntProperty(default=-1),
    }
}

# =============================================================================
# Registration
# =============================================================================


def register():
    """Register the addon using framework's auto_load"""
    # Initialize and register auto-discovered classes
    auto_load.init()
    auto_load.register()

    # Register addon properties
    add_properties(_addon_properties)

    # Load translations
    load_dictionary(dictionary)
    bpy.app.translations.register(__addon_name__, dictionary)

    print(f"[Subtitle Editor] {__addon_name__} addon registered successfully")


def unregister():
    """Unregister the addon"""
    # Unload translations
    bpy.app.translations.unregister(__addon_name__)

    # Unregister classes
    auto_load.unregister()

    # Remove properties
    remove_properties(_addon_properties)

    print(f"[Subtitle Editor] {__addon_name__} addon unregistered")


if __name__ == "__main__":
    register()
