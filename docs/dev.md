# Subtitle Studio - Development Workflow

## Overview

This guide captures the local iteration, testing, and packaging workflow for Subtitle Studio while keeping Blender's threading and auto-loading patterns intact.

## Requirements

- Blender 4.5 LTS or 5.0+ (depending on the release target)
- Python 3.11 (Blender's bundled interpreter)
- UV package manager with `uv.lock` synced to `pyproject.toml`

## Local Workflow

1. Clone this repository, then install the ZIP for quick verification or drop the `subtitle_studio/` package into Blender's `scripts/addons` path for live iteration.
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

## Blender Smoke Script

Use the smoke script to quickly validate core strip workflows and MetaStrip copy-style behavior.

Script:

- `tests/blender_smoke_strip_workflows.py`

What it validates:

- strip add/update/remove workflow
- apply style to selected strips
- copy style inside a MetaStrip

How to run (UI session recommended):

1. Enable the `subtitle_studio` add-on.
2. Open a Sequencer area in the current workspace.
3. Run in Blender's Python console or Text Editor:

```python
exec(compile(open("/absolute/path/to/addons/subtitle_studio/tests/blender_smoke_strip_workflows.py", "rb").read(), "blender_smoke_strip_workflows.py", "exec"))
```

Expected output: explicit `[PASS]`/`[FAIL]` lines and an `[overall]` line.

## Evaluation Logging Standard

Use a single structured format for all addon evaluation logs written to the Blender system console.

Format:

```text
[Subtitle Studio][EVAL] action=<action> phase=<phase> outcome=<outcome> reason=<reason> context=<json>
```

Required fields:

- `action`: logical operation id (example: `transcribe.invoke`, `transcribe.worker`, `deps.check`, `model.load`)
- `phase`: `start|checkpoint|decision|success|warning|fail|cancel`
- `outcome`: `ok|warn|error|cancelled|noop`
- `reason`: short machine-readable reason code (example: `missing_strip`, `low_recall_retry`, `model_not_found`)
- `context`: sanitized JSON payload with only useful debug data

Required event phases:

- `start`: operation begins
- `checkpoint`: important intermediate state
- `decision`: branch selection based on evaluated conditions
- `success`: operation completed successfully
- `warning`: non-fatal issue or fallback
- `fail`: operation failed
- `cancel`: user or system cancellation

Context sanitization rules:

- Avoid secrets/tokens and private credentials.
- Avoid dumping full large payloads.
- Prefer short, stable keys (`scene`, `model`, `device`, `segment_count`, `coverage`).
- Include enough data to explain why a branch was taken.

Examples:

```text
[Subtitle Studio][EVAL] action=transcribe.invoke phase=start outcome=ok reason=begin context={"scene":"Scene","strip":"Voice_01","model":"base","device":"auto"}
[Subtitle Studio][EVAL] action=transcribe.worker phase=decision outcome=warn reason=low_recall_retry context={"audio_duration":92.4,"segments":3,"word_count":14,"coverage":0.018}
[Subtitle Studio][EVAL] action=model.load phase=fail outcome=error reason=model_not_found context={"model":"large-v3","cache":"configured"}
[Subtitle Studio][EVAL] action=deps.check phase=success outcome=ok reason=dependency_scan_complete context={"missing":["onnxruntime"],"gpu_detected":false}
```
