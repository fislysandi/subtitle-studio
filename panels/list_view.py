"""
UI List for Text Strips
"""

import bpy
from bpy.types import UIList


class SUBTITLE_UL_text_strips(UIList):
    """UI List showing text strips"""

    bl_idname = "SUBTITLE_UL_text_strips"

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname
    ):
        # Draw each item in the list
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row()
            row.label(text=item.name, icon="TEXT")
            row.label(text=f"{item.frame_start}-{item.frame_end}")
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text=item.name, icon="TEXT")
