# Subtitle Studio - Development Workflow

## Overview

This guide captures the local iteration, testing, and packaging workflow for Subtitle Studio while keeping Blender's threading and auto-loading patterns intact.

## Requirements

- Blender 4.5 LTS or 5.0+ (depending on the release target)
- Python 3.11 (Blender's bundled interpreter)
- UV package manager with `uv.lock` synced to `pyproject.toml`

## Local Workflow

1. Clone this repository, then install the ZIP for quick verification or drop the `subtitle_editor/` package into Blender's `scripts/addons` path for live iteration.
2. Enable `Subtitle Studio` under `Edit → Preferences → Add-ons` and confirm the VSE sidebar panel appears.
3. Run `uv run test subtitle_editor` to exercise modal operators, threading logic, and Faster Whisper pipelines (thread-safe UI updates are highlighted in `context/project-intelligence/technical-domain.md`).

## Run and Test

```bash
uv run test subtitle_editor
```

UV runs the Whisper inference tests, ensuring the modal operators post updates through timers instead of mutating props directly.

## Package Release

```bash
uv run release subtitle_editor
```

The release command builds the add-on ZIP without bundling dependencies. Runtime installs are handled through UV (see `docs/dependencies.md`).

## Dependency Management

- Keep `pyproject.toml` dependencies pinned to the ranges in `docs/dependencies.md` and update `uv.lock` via `uv lock` or `uv sync`.
- Use the add-on Preferences panel to install dependencies into Blender's Python (UV first, pip fallback).
- After dependency changes, rerun `uv run test subtitle_editor` and rebuild with `uv run release subtitle_editor`.

## Faster Whisper Configuration Reference

Consult `docs/whisper-config.md` before tweaking default beam sizes, VAD thresholds, or model choices (`tiny`, `base`, `medium`, `large-v3`). It captures memory/speed trade-offs, CPU-only knobs, and output expectations so Blender builds stay responsive.

## Blender Iteration Tips

- Reload the add-on via Blender's scripting console between edits if panels refuse to redraw; modal operators rely on `area.tag_redraw()` inside scheduled timers.
- Restart Blender when UI elements lag or hang, as event handlers are tied to `bpy.app.timers` for long-running downloads/transcriptions.
- Watch the console/logs for thread-safe updates and avoid touching props from background threads (the pattern is documented in `context/project-intelligence/technical-domain.md`).
