# Subtitle Editor - Blender VSE Addon

Automatic subtitle transcription and editing addon for Blender's Video Sequence Editor.

## Features

- **AI-Powered Transcription**: Uses Faster Whisper for offline speech-to-text
- **Multi-Language Support**: 99+ languages supported
- **Visual Subtitle Editing**: Edit subtitles directly in Blender VSE
- **Import/Export**: Support for SRT, VTT, ASS, SSA formats
- **Offline Capable**: Bundled dependencies for air-gapped workflows
- **Blender 5.0+ Compatible**: Works with latest Blender versions

## Installation

1. Download the release zip
2. In Blender: Edit → Preferences → Add-ons → Install
3. Enable "Subtitle Editor"
4. Download dependencies (or use bundled libs/)

## Usage

1. Open Video Sequence Editor
2. Load your video/audio strip
3. Select strip → Subtitle Editor panel → "Transcribe"
4. Edit subtitles in the list view
5. Export when done

## Requirements

- Blender 5.0+ (or 4.5 LTS)
- Python 3.11 (bundled with Blender)
- ~500MB disk space for AI models

## Architecture

- `core/`: Pure Python business logic (no Blender deps)
- `operators/`: Blender operators
- `ui/`: Interface panels and lists
- `utils/`: Helper utilities

## License

MIT License
