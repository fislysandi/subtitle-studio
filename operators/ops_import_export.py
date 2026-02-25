"""
Import/Export Operators
"""

import logging

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper

from ..core.subtitle_io import SubtitleIO, SubtitleEntry
from ..hardening.error_boundary import (
    boundary_failure_from_exception,
    execute_with_boundary,
)
from ..utils import sequence_utils


logger = logging.getLogger(__name__)


class SUBTITLE_OT_import_subtitles(Operator, ImportHelper):
    """Import subtitles from file"""

    bl_idname = "subtitle.import_subtitles"
    bl_label = "Import Subtitles"
    bl_description = "Import subtitles from SRT, VTT, or ASS file"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".srt"
    filter_glob: StringProperty(default="*.srt;*.vtt;*.ass;*.ssa", options={"HIDDEN"})

    def execute(self, context):
        try:
            # Load subtitles
            load_result = execute_with_boundary(
                "subtitle.import.load",
                lambda: SubtitleIO.load(self.filepath),
                logger,
                context={"filepath": self.filepath},
                fallback_message="Import failed. Please verify subtitle format and file access.",
            )
            if not load_result.ok:
                self.report({"ERROR"}, load_result.user_message)
                return {"CANCELLED"}

            entries = load_result.value

            # Create text strips
            scene = context.scene
            channel = scene.subtitle_editor.subtitle_channel
            fps = scene.render.fps / (scene.render.fps_base or 1.0)

            for entry in entries:
                frame_start = int(entry.start * fps)
                frame_end = int(entry.end * fps)

                strip = sequence_utils.create_text_strip(
                    scene,
                    name=f"Subtitle_{entry.index:03d}",
                    text=entry.text,
                    frame_start=frame_start,
                    frame_end=frame_end,
                    channel=channel,
                )

                if strip:
                    # Add to UI list
                    item = scene.text_strip_items.add()
                    item.name = strip.name
                    item.text = entry.text
                    item.frame_start = frame_start
                    item.frame_end = frame_end
                    item.channel = channel

            self.report({"INFO"}, f"Imported {len(entries)} subtitles")
            return {"FINISHED"}

        except (AttributeError, TypeError, ValueError, RuntimeError, OSError) as e:
            fail_result = boundary_failure_from_exception(
                "subtitle.import.execute",
                e,
                logger,
                context={"filepath": self.filepath},
                fallback_message="Import failed. Please check the selected file and try again.",
            )
            self.report({"ERROR"}, fail_result.user_message)
            return {"CANCELLED"}


class SUBTITLE_OT_export_subtitles(Operator, ExportHelper):
    """Export subtitles to file"""

    bl_idname = "subtitle.export_subtitles"
    bl_label = "Export Subtitles"
    bl_description = "Export subtitles to SRT, VTT, or ASS file"
    bl_options = {"REGISTER"}

    filename_ext = ".srt"
    filter_glob: StringProperty(default="*.srt;*.vtt;*.ass;*.ssa", options={"HIDDEN"})

    format: EnumProperty(
        name="Format",
        items=[
            ("AUTO", "Auto-detect", "Detect from file extension"),
            (".srt", "SubRip (.srt)", "SRT format"),
            (".vtt", "WebVTT (.vtt)", "VTT format"),
            (".ass", "Advanced SSA (.ass)", "ASS format"),
        ],
        default="AUTO",
    )

    def execute(self, context):
        try:
            # Get text strips on configured subtitle channel
            scene = context.scene
            subtitle_channel = scene.subtitle_editor.subtitle_channel
            strips = [
                strip
                for strip in sequence_utils.get_text_strips(scene)
                if strip.channel == subtitle_channel
            ]

            if not strips:
                self.report(
                    {"WARNING"},
                    f"No subtitle text strips found on channel {subtitle_channel}",
                )
                return {"CANCELLED"}

            # Convert to entries
            entries = []
            fps = scene.render.fps / (scene.render.fps_base or 1.0)
            for i, strip in enumerate(strips, 1):
                entry = SubtitleEntry(
                    index=i,
                    start=strip.frame_final_start / fps,
                    end=strip.frame_final_end / fps,
                    text=strip.text,
                )
                entries.append(entry)

            # Determine format
            fmt = self.format
            if fmt == "AUTO":
                fmt = SubtitleIO.detect_format(self.filepath)
                if not fmt:
                    fmt = ".srt"  # Default

            # Save
            save_result = execute_with_boundary(
                "subtitle.export.save",
                lambda: SubtitleIO.save(self.filepath, entries, fmt),
                logger,
                context={
                    "filepath": self.filepath,
                    "format": fmt,
                    "entry_count": len(entries),
                },
                fallback_message="Export failed. Please verify destination path and format.",
            )
            if not save_result.ok:
                self.report({"ERROR"}, save_result.user_message)
                return {"CANCELLED"}

            self.report(
                {"INFO"}, f"Exported {len(entries)} subtitles to {self.filepath}"
            )
            return {"FINISHED"}

        except (AttributeError, TypeError, ValueError, RuntimeError, OSError) as e:
            fail_result = boundary_failure_from_exception(
                "subtitle.export.execute",
                e,
                logger,
                context={"filepath": self.filepath},
                fallback_message="Export failed. Please check settings and try again.",
            )
            self.report({"ERROR"}, fail_result.user_message)
            return {"CANCELLED"}
