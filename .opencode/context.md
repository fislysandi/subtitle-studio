# Subtitle Studio Addon - Development Context

## Project Overview
Blender addon for AI-powered subtitle transcription and editing using Faster Whisper.
- **Location**: `addons/subtitle_editor/`
- **Framework**: Blender Addon Framework with auto-loading
- **Python Version**: 3.11 (matching Blender 5.0)

## Blender Version
**Blender 5.0** - Must use Blender 5.0+ compatible API

## Critical API Change
**sequences_all REMOVED in Blender 5.0**
- ❌ OLD: `sequence_editor.sequences_all`
- ✅ NEW: `sequence_editor.sequences`

## Installed Dependencies (UV Environment)
- **faster-whisper** - Whisper transcription with CTranslate2
- **torch** - PyTorch with CUDA 11.8
- **torchaudio** - Audio processing
- **pysubs2** - Subtitle parsing (SRT, VTT, ASS)
- **onnxruntime** - ONNX model runtime

## Files Requiring sequences_all Fix
1. `utils/sequence_utils.py` - Lines 16, 80, 96
2. Any other files using sequences_all

## Code Standards
- Type annotations required for all bpy.props
- Use threading + bpy.app.timers for async operations
- No bpy imports in core/ modules
- Framework auto-loads - no manual registration
