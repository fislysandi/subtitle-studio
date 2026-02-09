# Subtitle Studio - Project State (MVI)

**Last Updated:** 2026-02-09  
**Addon Location:** `addons/subtitle_editor/`

## Status

- ✅ Migrated to Blender Addon Framework (auto-load)
- ✅ UV dependency manager integrated

## About

Subtitle Studio is an AI-powered subtitle transcription and editing addon for Blender VSE.

## Critical Rules (for agents)

1. Read this file first.
2. Load project context from:
   - `~/.config/opencode/context/project/blender-subtitle-editor/context.md`
   - `~/.config/opencode/context/project/blender-subtitle-editor/agent-context.md`
3. Prefer local `.opencode/context/` if present (local-first).
4. Read `ROADMAP.md` after context to pick next tasks.

## Commands

```bash
uv run test subtitle_editor
uv run release subtitle_editor
uv run addon-deps list subtitle_editor
uv run addon-deps sync subtitle_editor
```

## Key Entry Points

- `__init__.py` - framework auto-load integration
- `config.py` - addon identifier
- `core/` - transcription + IO logic
- `operators/` - Blender operators (transcribe, import/export, deps, model download)
- `panels/` - UI panels and UIList
- `props.py` - property groups

## Known Priorities

- Verify thread safety on all background updates (use `bpy.app.timers`).
- Validate import/export formats (SRT/VTT/ASS) once per release.
- Keep Blender 5.0 API usage (`sequences`, not `sequences_all`).

## Quick Structure

```
subtitle_editor/
  core/
  operators/
  panels/
  utils/
  props.py
  constants.py
  config.py
  __init__.py
```
