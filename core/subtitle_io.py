"""
Subtitle Import/Export

Handles reading and writing subtitle files.
This module has NO Blender dependencies.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class SubtitleEntry:
    """Single subtitle entry"""

    index: int
    start: float  # Start time in seconds
    end: float  # End time in seconds
    text: str  # Subtitle text

    @property
    def duration(self) -> float:
        """Get duration in seconds"""
        return self.end - self.start


class SubtitleIO:
    """Import/Export handler for subtitle files"""

    SUPPORTED_FORMATS = [".srt", ".vtt", ".ass", ".ssa"]

    @classmethod
    def detect_format(cls, filepath: str) -> Optional[str]:
        """Detect subtitle format from file extension

        Args:
            filepath: Path to subtitle file

        Returns:
            Format string or None if unknown
        """
        ext = Path(filepath).suffix.lower()
        if ext in cls.SUPPORTED_FORMATS:
            return ext
        return None

    @classmethod
    def load(cls, filepath: str, format: Optional[str] = None) -> List[SubtitleEntry]:
        """Load subtitles from file

        Args:
            filepath: Path to subtitle file
            format: File format (auto-detect if None)

        Returns:
            List of SubtitleEntry objects
        """
        if format is None:
            format = cls.detect_format(filepath)

        if format is None:
            raise ValueError(f"Cannot detect subtitle format: {filepath}")

        # Use pysubs2 if available (best option)
        try:
            return cls._load_with_pysubs2(filepath)
        except ImportError:
            # Fallback to manual parsing
            if format == ".srt":
                return cls._load_srt(filepath)
            elif format == ".vtt":
                return cls._load_vtt(filepath)
            else:
                raise ValueError(f"Format {format} requires pysubs2 library")

    @classmethod
    def save(
        cls, filepath: str, entries: List[SubtitleEntry], format: Optional[str] = None
    ) -> None:
        """Save subtitles to file

        Args:
            filepath: Output file path
            entries: List of SubtitleEntry objects
            format: Output format (auto-detect if None)
        """
        if format is None:
            format = cls.detect_format(filepath)

        if format is None:
            raise ValueError(f"Cannot detect output format: {filepath}")

        # Use pysubs2 if available
        try:
            cls._save_with_pysubs2(filepath, entries, format)
        except ImportError:
            # Fallback to manual writing
            if format == ".srt":
                cls._save_srt(filepath, entries)
            elif format == ".vtt":
                cls._save_vtt(filepath, entries)
            else:
                raise ValueError(f"Format {format} requires pysubs2 library")

    @classmethod
    def _load_with_pysubs2(cls, filepath: str) -> List[SubtitleEntry]:
        """Load using pysubs2 library"""
        import pysubs2

        subs = pysubs2.load(filepath)
        entries = []

        for line in subs:
            entry = SubtitleEntry(
                index=line.index,
                start=line.start / 1000.0,  # Convert ms to seconds
                end=line.end / 1000.0,
                text=line.text.replace("\\N", "\n"),  # Convert newlines
            )
            entries.append(entry)

        return entries

    @classmethod
    def _save_with_pysubs2(cls, filepath: str, entries: List[SubtitleEntry], format: str) -> None:
        """Save using pysubs2 library"""
        import pysubs2

        subs = pysubs2.SSAFile()

        for entry in entries:
            line = pysubs2.SSAEvent()
            line.start = int(entry.start * 1000)  # Convert to ms
            line.end = int(entry.end * 1000)
            line.text = entry.text.replace("\n", "\\N")  # Convert newlines
            subs.append(line)

        # Map format to pysubs2 format
        fmt_map = {".srt": "srt", ".vtt": "vtt", ".ass": "ass", ".ssa": "ssa"}

        subs.save(filepath, format=fmt_map.get(format, "srt"))

    @classmethod
    def _load_srt(cls, filepath: str) -> List[SubtitleEntry]:
        """Parse SRT file manually"""
        entries = []

        with open(filepath, "r", encoding="utf-8-sig") as f:
            content = f.read()

        # Split by double newline (subtitle blocks)
        blocks = content.strip().split("\n\n")

        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) < 3:
                continue

            # First line is index
            try:
                index = int(lines[0].strip())
            except ValueError:
                continue

            # Second line is timecode
            time_line = lines[1].strip()
            if "-->" not in time_line:
                continue

            start_str, end_str = time_line.split("-->")
            start = cls._parse_timecode(start_str.strip())
            end = cls._parse_timecode(end_str.strip())

            # Remaining lines are text
            text = "\n".join(lines[2:]).strip()

            entries.append(SubtitleEntry(index, start, end, text))

        return entries

    @classmethod
    def _save_srt(cls, filepath: str, entries: List[SubtitleEntry]) -> None:
        """Write SRT file manually"""
        with open(filepath, "w", encoding="utf-8") as f:
            for i, entry in enumerate(entries, 1):
                f.write(f"{i}\n")
                f.write(
                    f"{cls._format_timecode(entry.start)} --> {cls._format_timecode(entry.end)}\n"
                )
                f.write(f"{entry.text}\n\n")

    @classmethod
    def _load_vtt(cls, filepath: str) -> List[SubtitleEntry]:
        """Parse WebVTT file manually"""
        entries = []

        with open(filepath, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()

        # Skip header
        i = 0
        while i < len(lines) and not lines[i].strip().startswith("00:"):
            i += 1

        index = 1
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Check for timecode line
            if "-->" in line:
                start_str, end_str = line.split("-->")
                start = cls._parse_timecode(start_str.strip())
                end = cls._parse_timecode(end_str.strip().split()[0])  # Remove positioning

                # Collect text lines
                text_lines = []
                i += 1
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1

                text = "\n".join(text_lines)
                entries.append(SubtitleEntry(index, start, end, text))
                index += 1
            else:
                i += 1

        return entries

    @classmethod
    def _save_vtt(cls, filepath: str, entries: List[SubtitleEntry]) -> None:
        """Write WebVTT file manually"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")

            for entry in entries:
                f.write(
                    f"{cls._format_timecode_vtt(entry.start)} --> {cls._format_timecode_vtt(entry.end)}\n"
                )
                f.write(f"{entry.text}\n\n")

    @staticmethod
    def _parse_timecode(timecode: str) -> float:
        """Parse timecode string to seconds"""
        # Handle both comma and dot as decimal separator
        timecode = timecode.replace(",", ".")

        parts = timecode.split(":")
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            return float(parts[0])

    @staticmethod
    def _format_timecode(seconds: float) -> str:
        """Format seconds to SRT timecode (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace(".", ",")

    @staticmethod
    def _format_timecode_vtt(seconds: float) -> str:
        """Format seconds to WebVTT timecode (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
