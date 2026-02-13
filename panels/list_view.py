"""
UI List for Text Strips
Based on upstream: https://github.com/tin2tin/Subtitle_Editor
"""

import bpy
from bpy.types import UIList


class SEQUENCER_UL_List(UIList):
    """UI List showing text strips"""

    bl_idname = "SEQUENCER_UL_List"

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname
    ):
        scene = getattr(context, "scene", None)
        fps = 24.0
        if scene and scene.render:
            fps = scene.render.fps / (scene.render.fps_base or 1.0)

        frame = max(0, int(getattr(item, "frame_start", 0)))
        fps_int = max(1, int(round(fps)))

        total_seconds = frame // fps_int
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        frame_part = frame % fps_int
        prefix = f"{minutes:02d}:{seconds:02d}:{frame_part:02d}"

        text = getattr(item, "text", "")
        layout.label(text=f"{prefix}  {text}")

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        if not items:
            return [], []

        query = (self.filter_name or "").strip().lower()
        flags = []

        for item in items:
            haystack = (
                f"{getattr(item, 'text', '')} {getattr(item, 'name', '')}".lower()
            )
            if not query or query in haystack:
                flags.append(self.bitflag_filter_item)
            else:
                flags.append(0)

        neworder = []
        if self.use_filter_sort_alpha:
            neworder = bpy.types.UI_UL_list.sort_items_by_name(items, "text")

        return flags, neworder
