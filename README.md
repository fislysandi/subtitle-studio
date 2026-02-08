# Subtitle Studio

Subtitle Studio is a Blender VSE add-on that packages Faster Whisper transcription, subtitle editing, and export tooling so you can keep the entire workflow inside Blender while staying compliant with Blender 5.0+ UI paradigms.

## Overview

- **Purpose**: Bring AI transcription, subtitle editing, and multi-format export to the Video Sequence Editor with Blender-native controls.
- **Why it matters**: Run Whisper models offline, edit captions visually, and ship polished subtitles without toggling between Blender and external tools.

## Requirements

- Blender 4.5 LTS / 5.0+ (whichever matches your release channel)
- Python 3.11 (bundled inside Blender)
- ~500 MB disk space for Faster Whisper/ONNX artifacts when bundling dependencies

## Installation

1. Download the latest release ZIP.
2. In Blender: `Edit → Preferences → Add-ons → Install`, then activate `Subtitle Studio` from the list.
3. Open the add-on Preferences and run **Install Dependencies** (uses UV when available, pip fallback). See `docs/dependencies.md` for the UV-first workflow and troubleshooting tips.

## Quick Start

1. Open Blender's Video Sequence Editor and add the strip you want to transcribe.
2. Open the Subtitle Studio sidebar panel (N-panel → Subtitle Studio).
3. Click **Transcribe** to run Faster Whisper on the active strip (status appears in the panel).
4. Fine-tune timing or text directly in the subtitle list view and use Blender tools to align strips.
5. Export to SRT/VTT/ASS/SSA when the sequence is ready.

## Usage

- Enable `Subtitle Studio` under `Edit → Preferences → Add-ons`.
- In the VSE sidebar panel, choose a model variant, configure VAD/beam settings, and trigger transcription.
- Use the list view to edit cues, pin strips, or push updated subtitles back into the pool.
- Export subtitles from the same panel or via the `Subtitle Studio → Export` operator when ready.

## Features

- **AI-Powered Transcription**: Offline Faster Whisper inference with beam/timer controls.
- **Multi-Language Support**: Dozens of languages plus auto-detect fallbacks.
- **VSE-Centric Editing**: Visual, frame-accurate subtitle edits inside Blender.
- **Flexible Imports/Exports**: Support for SRT, VTT, ASS, SSA.
- **Offline-Ready**: Bundle faster-whisper, pysubs2, onnxruntime, and friends for air-gapped installs.
- **Blender-Compatible Design**: Thread-safe modal operators, property groups, and iconography tuned for Blender 5.x.

## Dependency Management

Subtitle Studio no longer ships a `libs/` folder. Dependencies are resolved through UV and installed into Blender's Python at runtime (with pip as fallback). See `docs/dependencies.md` for the UV workflow, lockfile strategy, and how the add-on uses the built-in installer.

## Faster Whisper Configuration Reference

Use `docs/whisper-config.md` to compare models (`tiny` vs `large-v3`), tune beam/VAD settings, and read the expected output structure. The document also highlights memory/speed trade-offs and CPU-only knobs for Blender builds.

## Documentation

- `docs/dev.md` – local development workflow, UV commands, and Blender iteration tips.
- `docs/dependencies.md` – how to download, bundle, and ship offline dependencies.
- `docs/whisper-config.md` – Faster Whisper model and parameter guidance.
- `docs/changelog.md` – release history and notable changes.

## Troubleshooting

- Add-on not visible: Verify the ZIP is installed and enabled, then restart Blender. If you used a brand-new build, open the console to confirm the module path is correct.
- Model download fails: Use the Preferences UI to install dependencies and models; confirm Blender can reach the package index and model storage endpoints.
- No subtitles created: Confirm a strip is selected, the scene timeline is playing/active, and the operator log shows `segments` results.

## Changelog

See `docs/changelog.md` for the release log, including the current 0.5.1 snapshot and any upcoming updates.

## License

GPL-3.0-or-later. See `LICENSE` for full terms.
