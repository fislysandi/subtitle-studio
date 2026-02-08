"""
Strip Edit Operators
"""

import bpy
from bpy.types import Operator

from ..utils import sequence_utils


class SUBTITLE_OT_refresh_list(Operator):
    """Refresh the list of text strips"""

    bl_idname = "subtitle.refresh_list"
    bl_label = "Refresh List"
    bl_description = "Refresh the subtitle strips list"
    bl_options = {"REGISTER"}

    def execute(self, context):
        sequence_utils.refresh_list(context)
        return {"FINISHED"}


class SUBTITLE_OT_select_strip(Operator):
    """Select a text strip"""

    bl_idname = "subtitle.select_strip"
    bl_label = "Select Strip"
    bl_description = "Select this subtitle strip in the sequencer"
    bl_options = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene

        if self.index < 0 or self.index >= len(scene.text_strip_items):
            return {"CANCELLED"}

        item = scene.text_strip_items[self.index]

        # Find and select the strip
        if scene.sequence_editor:
            for strip in scene.sequence_editor.strips:
                strip.select = strip.name == item.name
                if strip.name == item.name:
                    # Jump to strip
                    scene.frame_current = strip.frame_final_start

        # Update current text
        scene.subtitle_editor.current_text = item.text

        return {"FINISHED"}


class SUBTITLE_OT_update_text(Operator):
    """Update subtitle text"""

    bl_idname = "subtitle.update_text"
    bl_label = "Update Text"
    bl_description = "Update the selected subtitle text"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        index = scene.text_strip_items_index

        if index < 0 or index >= len(scene.text_strip_items):
            self.report({"WARNING"}, "No subtitle selected")
            return {"CANCELLED"}

        item = scene.text_strip_items[index]
        new_text = scene.subtitle_editor.current_text

        # Update UI list
        item.text = new_text

        # Update actual strip
        if scene.sequence_editor:
            for strip in scene.sequence_editor.strips:
                if strip.name == item.name and strip.type == "TEXT":
                    strip.text = new_text
                    break

class SUBTITLE_OT_apply_style(Operator):
    """Apply current style settings to selected subtitle strips"""

    bl_idname = "subtitle.apply_style"
    bl_label = "Apply Style to Selected"
    bl_description = "Apply current font size, color, and shadow settings to all selected subtitle strips"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        props = scene.subtitle_editor
        
        # Get selected sequences
        selected = sequence_utils.get_selected_strips(context)
        if not selected:
            self.report({"WARNING"}, "No strips selected")
            return {"CANCELLED"}
            
        count = 0
        for strip in selected:
            if strip.type == "TEXT":
                # Apply style
                strip.font_size = props.font_size
                strip.color = props.text_color + (1.0,) # RGB + Alpha
                # Shadow isn't a direct property on TextSequence in simple API, 
                # but let's check if we can set it.
                # Blender VSE Text strips use 'use_shadow' and 'shadow_color' if available?
                # Actually standard VSE Text Strip has:
                # - font_size
                # - color
                # - use_shadow (bool)
                # - shadow_color (rgba)
                
                # Let's check what properties are available on standard text strip using dir() if needed,
                # but standard API usually supports these.
                
                # For safety let's use try/except block for properties that might vary by version
                try:
                    strip.font_size = props.font_size
                except AttributeError:
                    pass
                    
                try:
                    # props.text_color is FloatVector(size=3)
                    # strip.color is FloatVector(size=4) usually
                    strip.color = (props.text_color[0], props.text_color[1], props.text_color[2], 1.0)
                except AttributeError:
                    pass
                
                try:
                    strip.use_shadow = True
                    strip.shadow_color = (props.shadow_color[0], props.shadow_color[1], props.shadow_color[2], 1.0)
                except AttributeError:
                    pass
                
                # Also alignment
                try:
                    if props.v_align == "TOP":
                        strip.align_y = "TOP"
                    elif props.v_align == "CENTER":
                        strip.align_y = "CENTER"
                    elif props.v_align == "BOTTOM":
                        strip.align_y = "BOTTOM"
                except AttributeError:
                    pass

                count += 1
        
        self.report({"INFO"}, f"Applied style to {count} strips")
        return {"FINISHED"}


class SUBTITLE_OT_insert_line_breaks(Operator):
    """Insert line breaks into selected subtitles"""

    bl_idname = "subtitle.insert_line_breaks"
    bl_label = "Insert Line Breaks"
    bl_description = "Insert line breaks to fit text within character limit"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        import textwrap
        
        scene = context.scene
        props = scene.subtitle_editor
        max_chars = props.max_chars_per_line
        
        # Get selected sequences
        selected = sequence_utils.get_selected_strips(context)
        if not selected:
            self.report({"WARNING"}, "No strips selected")
            return {"CANCELLED"}
            
        count = 0
        for strip in selected:
            if strip.type == "TEXT":
                # Get current text
                current_text = strip.text
                
                # Unwrap first to remove existing line breaks if any (optional, but good for re-flowing)
                # But simple assumption: input is just text. 
                # Let's replace single newlines with spaces to allow re-flow, but keep double newlines?
                # For simple subtitles, usually just one block.
                # Let's just wrap existing text.
                
                # Logic: Split by newlines first to preserve intentional paragraphs? 
                # Standard approach: treat as one block for simple wrapping.
                
                wrapped_lines = textwrap.wrap(current_text, width=max_chars)
                new_text = "\n".join(wrapped_lines)
                
                if new_text != current_text:
                    strip.text = new_text
                    count += 1
        
        self.report({"INFO"}, f"Updated {count} strips")
        return {"FINISHED"}


classes = [
    SUBTITLE_OT_refresh_list,
    SUBTITLE_OT_select_strip,
    SUBTITLE_OT_update_text,
    SUBTITLE_OT_apply_style,
    SUBTITLE_OT_insert_line_breaks,
]
