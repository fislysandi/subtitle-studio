# Subtitle Studio - Project State

**Last Updated:** 2026-02-08 (NumPy Compatibility Fix)  
**Addon Location:** `addons/subtitle_editor/`

## 📍 Current Status

**Status:** ✅ Migrated to Blender Addon Framework  
**Git Branch:** master  
**Framework Version:** Using auto-loading + UV dependency management

## 🎬 About This Addon

**Subtitle Studio** - AI-powered subtitle transcription and editing for Blender Video Sequence Editor (VSE)

**Forked from:** https://github.com/tin2tin/Subtitle_Editor  
**Original Author:** tin2tin

### Features
- 🤖 **AI Transcription** using Faster Whisper (19 models available)
- 🌐 **Translation to English** with dedicated operator
- 📝 **Subtitle editing** with list-based UI (integrated into main panel)
- 🌍 **Multi-language support** (multilingual & English-only models)
- 📥 **Import/Export** (SRT, VTT, ASS formats)
- ⚙️ **Advanced settings**: beam size, max words per strip, font size, alignment
- 🔧 **Dependency management** with install/verify functionality
- 💾 **Model download** - Download Whisper models on demand
- 🔐 **Hugging Face authentication** - Optional HF_TOKEN for faster downloads
- 🔥 **Hot-reload** during development

## ✅ Completed Migration Tasks

### Phase 1: UV Setup ✓
- [x] Initialized UV for dependency management
- [x] Added `pyproject.toml` with dependencies:
  - faster-whisper>=1.0.0
  - pysubs2>=1.8.0
  - onnxruntime>=1.24.1
- [x] Generated `uv.lock` file

### Phase 2: Framework Integration ✓
- [x] Created `config.py` with `__addon_name__ = "subtitle_editor"`
- [x] Created `i18n/` folder for translations
- [x] Created `panels/` folder for UI (framework convention)
- [x] Removed manual registration from all modules
- [x] Framework auto-load discovers all classes

### Phase 3: Code Updates ✓
- [x] Updated `__init__.py` to use framework's auto_load
- [x] Removed `core/dependencies.py` (replaced by UV)
- [x] Updated imports in operators
- [x] Fixed EnumProperty with LANGUAGE_ITEMS from constants
- [x] Removed duplicate UI files

### Phase 4: UI Alignment ✓
- [x] Panels match upstream layout style:
  - SEQUENCER_PT_panel (main panel with UIList)
  - SEQUENCER_PT_whisper_panel (transcription settings)
  - SEQUENCER_PT_edit_panel (subtitle editing)
- [x] UIList displays subtitle text
- [x] Category: "Subtitle Studio"

## 🚀 Available Commands

```bash
# Test with hot reload (auto-updates in Blender on save)
uv run test subtitle_editor

# Package for distribution
uv run release subtitle_editor

# Manage dependencies
uv run addon-deps list subtitle_editor
uv run addon-deps sync subtitle_editor
uv run addon-deps add subtitle_editor <package>
```

## 📁 File Structure

```
subtitle_editor/
├── __init__.py              # Framework auto-load integration
├── config.py                # Addon name config
├── constants.py             # Language & model constants
├── blender_manifest.toml    # Blender extension manifest
├── props.py                 # Property groups (SubtitleEditorProperties, TextStripItem)
├── pyproject.toml           # UV dependencies
├── uv.lock                  # Locked dependencies
├── .venv/                   # Isolated Python environment
│
├── core/                    # Core functionality
│   ├── __init__.py
│   ├── subtitle_io.py       # Import/export logic
│   └── transcriber.py       # Whisper transcription
│
├── operators/               # Blender operators (auto-registered)
│   ├── __init__.py
│   ├── ops_dependencies.py  # Dependency management operators
│   ├── ops_dependency_download.py  # Non-blocking dependency download (modal)
│   ├── ops_import_export.py # Import/export operators
│   ├── ops_model_download.py       # Model download (modal operator + progress)
│   ├── ops_model_cancel.py         # Cancel model download
│   ├── ops_strip_edit.py    # List edit operators
│   └── ops_transcribe.py    # Transcription & translation operators
│
├── panels/                  # UI panels (framework convention)
│   ├── __init__.py
│   ├── main_panel.py        # Main panels
│   └── list_view.py         # UIList
│
├── ui/                      # Legacy folder (kept empty)
│   └── __init__.py
│
├── utils/                   # Utilities
│   ├── __init__.py
│   ├── file_utils.py        # File operations
│   └── sequence_utils.py    # VSE operations
│
├── i18n/                    # Translations
│   ├── __init__.py
│   └── dictionary.py
│
└── tests/                   # Test suite
    ├── __init__.py
    └── test_basic.py
```

## 🔧 Key Classes & Operators

### Property Groups
- `SubtitleEditorProperties` - Main addon properties (model, device, language, etc.)
- `TextStripItem` - Individual subtitle item in the list

### Operators
- `subtitle.transcribe` - Transcribe audio to subtitles
- `subtitle.translate` - Translate non-English audio to English subtitles
- `subtitle.import_subtitles` - Import subtitle files
- `subtitle.export_subtitles` - Export subtitle files
- `subtitle.refresh_list` - Refresh subtitle list
- `subtitle.select_strip` - Select strip from list
- `subtitle.update_text` - Update subtitle text
- `subtitle.check_dependencies` - Check if dependencies are installed
- `subtitle.install_dependencies` - Install missing dependencies (modal)
- `subtitle.check_gpu` - Check GPU availability for PyTorch
- `subtitle.install_pytorch` - Install PyTorch with selected CUDA/ROCm version (modal)
- `subtitle.download_model` - Download Whisper model with progress UI (modal)
- `subtitle.cancel_download` - Cancel model download
- `subtitle.check_dependencies` - Check if dependencies are installed
- `subtitle.install_dependencies` - Install missing dependencies
- `subtitle.check_gpu` - Check GPU availability for PyTorch
- `subtitle.install_pytorch` - Install PyTorch with selected CUDA/ROCm version
- `subtitle.download_model` - Download selected Whisper model on demand (subprocess, terminal output)
- `subtitle.download_dependencies` - Install Python packages with modal operator (non-blocking)
- `subtitle.cancel_download_deps` - Cancel dependency installation

### Panels
- `SEQUENCER_PT_panel` - Main panel with UIList and integrated editing
- `SEQUENCER_PT_whisper_panel` - Transcription & Translation settings (Dependencies, Model, Advanced options)

### UIList
- `SEQUENCER_UL_List` - Displays text strips

## 📝 Properties Available

**Scene Properties:**
- `scene.subtitle_editor` (SubtitleEditorProperties)
- `scene.text_strip_items` (Collection of TextStripItem)
- `scene.text_strip_items_index` (Int)

**SubtitleEditorProperties:**
- `language` - Transcription language
- `model` - Whisper model (19 options: tiny to turbo, multilingual & English-only)
- `device` - Compute device (auto, cpu, gpu)
- `compute_type` - Computation precision (default, int8, float16, float32)
- `beam_size` - Beam search size (1-10)
- `max_words_per_strip` - Max words before creating new strip (0-20, 0=unlimited)
- `translate` - Translate to English
- `word_timestamps` - Word-level timestamps
- `vad_filter` - Voice activity detection
- `show_advanced` - Show advanced options
- `subtitle_channel` - Default channel for new strips
- `subtitle_font_size` - Default font size (8-200)
- `v_align` - Vertical alignment (Top/Center/Bottom)
- `wrap_width` - Text wrap width factor (0-1)
- `is_transcribing` - Transcription in progress
- `progress` - Progress (0-1)
- `progress_text` - Status text
- `current_text` - Currently editing text
- **Dependencies:** `deps_faster_whisper`, `deps_torch`, `deps_pysubs2`, `deps_onnxruntime`, `is_installing_deps`, `deps_install_status`
- **PyTorch Settings:** `pytorch_version` (cpu/cu118/cu121/cu124/rocm57/mps), `gpu_detected`, `is_installing_pytorch`, `pytorch_install_status`
- **Model Download:** `is_downloading_model`, `model_download_status`, `model_download_progress`

## 🐛 Known Issues / TODO

### Critical (Fix Before Release)
- [x] **Thread Safety** - Property updates from background thread (ops_transcribe.py:69-70)
  - Properties updated directly from thread can cause crashes
  - Fix: Use `bpy.app.timers` for all property updates from threads
- [x] **Bare Except Clauses** - Replace with `except Exception:` (props.py:285, ops_dependencies.py:105)

### Medium Priority
- [x] **Implement batch styling** (copy style to selected)
  - Added `Apply Style to Selected` button in edit panel
  - Applies font size, color, shadow, and alignment to all selected text strips
- [x] **Model Persistence UI**: Fixed issue where users thought they had to redownload models. Added "Model Ready" indicator to UI.
- [x] **Blender 5.0 Compatibility**: Replaced deprecated `sequence_editor.sequences` with `sequence_editor.strips`.
- [x] **Transcribe Channel Fix**: `Transcribe` operator now correctly uses the channel specified in the UI (`subtitle_channel`).
- [x] **Thread Safety**: Fixed critical issue where accessing `strip` properties from background threads caused silent failures. Filepaths are now extracted on main thread.
- [x] **Relative Path Fix**: Added `bpy.path.abspath()` to ensure relative file paths (e.g. `//video.mp4`) work correctly with external tools like ffmpeg.
- [ ] Test all import/export formats
- [ ] Add file browser panels for import/export
- [ ] Optimize transcription performance
- [ ] Add temp file cleanup in finally blocks
- [ ] Validate empty transcription results

### Completed
- [x] Add progress callback during transcription
- [x] Implement dependency management UI
- [x] Add PyTorch version selection in dependency installer
- [x] Fix Blender 5.0 API compatibility (sequences_all → sequences)
- [x] Implement word count splitting in transcription
- [x] Test PyTorch installation on different GPU types
- [x] **Restored non-blocking model download with progress UI** (modal operator pattern)

## 🔄 To Resume Work

**In a new chat, say:**
> "Load from PROJECT_STATE.md in subtitle_editor addon and continue"

Or navigate to addon and:
```bash
cd addons/subtitle_editor
cat PROJECT_STATE.md
```

## 📝 Recent Changes (2026-02-08 Highlights)

### 🚀 Major Stability & Compatibility Fixes
- **NumPy 2.x Conflict Resolved**: Enforced `numpy<2.0` (1.26.4) in `pyproject.toml` and manually in `ops_dependencies.py`. This fixes crash-on-import issues with Blender's bundled `aud` module.
- **Blender 5.0 API Alignment**: 
  - Fixed `new_effect()` called with `frame_end` instead of `length`.
  - Fixed `shadow_color` requiring RGBA (4 values) instead of RGB (3 values).
  - Continuous migration from `sequences_all` to `sequences`.
- **Model Loading Fallbacks**: 
  - Implemented auto-fallback from `float16` to `int8/float32` on CPU to prevent crashes.
  - Added model file verification (`model.bin`/`config.json`) before loading to provide clear user guidance.

### ✨ UX & Workflow Improvements
- **Advanced VAD Tuning**: Exposed `threshold`, `min_speech_duration_ms`, `min_silence_duration_ms`, and `speech_pad_ms` in "Advanced Settings". Specifically tuned for better lyrics detection in music files.
- **UI & Timeline Sync**: 
  - Selecting a subtitle in the UI list now automatically jumps the playhead to its start frame.
  - Selecting in the list now selects the corresponding strip in the Sequencer and populates the `current_text` property for immediate editing.
- **Improved Installation Feedback**: Removed silent mode (`-q`) from dependency installers (General & PyTorch). Progress is now streamed to the **System Console** (Window > Toggle System Console) for better visibility.
- **Smart List Filtering**: The subtitle UI list now correctly filters text strips based on the selected `subtitle_channel`.

### 🛠️ Maintenance
- **Thread Safety**: Decoupled background threads from direct Blender property access using `bpy.app.timers`.
- **Error Handling**: Cleaned up bare `except:` clauses and added more descriptive status messages in operators.
- **Path Handling**: Improved relative path resolution for audio/video strips.

### 4. UV Dependency Manager Integration (2026-02-08)
- **Feature**: Embedded `uv` package manager logic to handle all dependency installations.
- **Benefits**:
  - 🚀 **Extremely Fast**: Multi-threaded downloads significantly fast than standard pip.
  - 🎯 **Accurate Pathing**: Explicitly targets Blender's Python executable using `--python` flag, solving "package not found" issues.
  - 🔄 **Auto-Bootstrap**: Automatically downloads `uv` if not present.
  - ⚙️ **Optional**: "Use UV" checkbox available in **Addon Preferences** (Edit > Preferences > Add-ons).
- **Files Changed**: Created `core/dependency_manager.py`, updated `operators/ops_dependencies.py`.

### 5. Robust Model Download (2026-02-08)
- **Fixes**:
  - 🛡️ **Crash Prevention**: Resolved `[Errno 39]` directory errors by handling filesystem locks gracefully.
  - 📊 **Better Progress**: Added real-time download speed (MB/s) and file-level tracking to the progress bar.
  - 🧠 **Smart Caching**: prevents redownloading by verifying file sizes (ignoring empty/corrupt files).
- **Files Changed**: `core/download_manager.py`, `core/transcriber.py`.

### 2. Restored Non-Blocking Model Download with Progress UI
**Git History Preserved:** This is a new implementation based on commit 8942594, not a revert

**Changes:**
- **Rewrote** `operators/ops_model_download.py` with proper Modal Operator pattern
- **Enhanced** UI in `panels/main_panel.py` with progress bar and cancel button
- **Utilizes** existing `core/download_manager.py` (already in codebase)
- **Integrates** `operators/ops_model_cancel.py` for cancellation support

**Features Restored:**
- ✅ Non-blocking UI - Use Blender while downloading
- ✅ Real-time progress bar (0-100%)
- ✅ Status messages ("Starting...", "Downloading...", "Complete!")
- ✅ Cancel button to stop download
- ✅ Blender's built-in progress indicator
- ✅ Thread-safe with proper cleanup
- ✅ Preserves all existing improvements (HF token support, model size display)

**Architecture:**
- Modal operator polls DownloadManager every 0.1 seconds
- Background thread handles actual download
- Thread-safe state sharing with locks
- Proper timer cleanup to prevent memory leaks

### 2. Dependency Download Operators
- Added `SUBTITLE_OT_download_dependencies` - Non-blocking modal operator for pip installs
- Added `SUBTITLE_OT_cancel_download_deps` - Cancel operator for dependency downloads
- Uses proper modal operator pattern with background threading
- Shows progress in Blender status bar
- Thread-safe shared state with locks
- File: `operators/ops_dependency_download.py`

### 2. Model Download Simplification
- Refactored model download to use subprocess approach
- Removed complex modal operator UI (was blocking)
- Downloads run in separate Python process (avoids GIL)
- Real-time output streamed to terminal
- Simplified UI: just Download button + model size
- Progress shown in terminal only
- File: `operators/ops_model_download.py`

### 3. Code Review & Agent Context
- Comprehensive code review by CodeReviewer agent
- Overall quality: **GOOD** ✅ Production-ready after thread safety fix
- Created `.opencode/context.md` - Core development standards
- Created `.opencode/agent-context.md` - Comprehensive agent guide
- Documented Blender 5.0 API compatibility requirements
- Listed all installed dependencies with versions
- Identified 5 warnings to fix (1 critical thread safety issue)
- All compliance checks passed (API, types, module separation, icons)

### 2. Blender 5.0 API Compatibility
- **CRITICAL FIX**: Replaced all `sequences_all` with `sequences`
- Fixed 8 occurrences across 4 files:
  - `utils/sequence_utils.py` (3x)
  - `props.py` (1x)
  - `operators/ops_transcribe.py` (2x)
  - `operators/ops_strip_edit.py` (2x)
- Addon now works with Blender 5.0+

### 3. PyTorch GPU Support
- GPU detection with visual warning if not detected (CPU fallback)
- Multi-backend support: NVIDIA CUDA, AMD ROCm, Apple Metal (MPS), Intel XPU
- PyTorch version dropdown with clear platform indicators:
  * CUDA 11.8/12.1/12.4 for NVIDIA GPUs (all platforms)
  * ROCm 5.7 for AMD RX 7900 series (Linux only)
  * Metal (MPS) for Apple Silicon Macs
- **Explicit selection required** - Removed "auto" option
- Install Dependencies button only installs base packages
- PyTorch installed separately via "Install PyTorch" button
- New operators: `check_gpu`, `install_pytorch`

### 4. Major UI Redesign
- Complete overhaul of Transcription & Translation panel
- Layout: Dependencies → PyTorch → Model → Device/Compute → Language → Settings → Actions
- 19 Whisper models with clear multilingual/English grouping
- New controls: Beam Size, Max Words, Channel, Font Size, V Align, Wrap Width
- Integrated edit section (removed separate panel)
- VAD Filter displays as checkbox

### 5. New Features
- `subtitle.translate` - Dedicated translation operator
- `subtitle.check_dependencies` / `subtitle.install_dependencies`
- `subtitle.check_gpu` / `subtitle.install_pytorch`
- Debug output for dependency checking
- Better NVIDIA GPU version guidance in dropdowns

### 6. Previous
- UI Update - Matched upstream tin2tin layout style
- Framework Migration - Auto-load system
- UV Integration - Dependency management

## 💡 For AI Assistant

**When working on this addon:**

1. **Check current state** - Read this file first
2. **Understand structure** - Files are in `panels/`, `operators/`, `core/`, etc.
3. **Framework rules** - Uses auto_load, no manual registration needed
4. **Test frequently** - Use `uv run test subtitle_editor` for hot-reload

**What can be modified:**
- ✅ Operators in `operators/`
- ✅ UI in `panels/`
- ✅ Core logic in `core/`
- ✅ Properties in `props.py`
- ✅ Constants in `constants.py`

**What needs care:**
- ⚠️ `__init__.py` - Framework integration point
- ⚠️ `config.py` - Addon identifier
- ⚠️ `blender_manifest.toml` - Blender metadata

## 📊 Quick Stats

- **Total Files:** 32
- **Operators:** 13
- **Panels:** 2
- **Property Groups:** 2
- **Dependencies:** 3 (faster-whisper, pysubs2, onnxruntime)
- **Whisper Models:** 19 (multilingual, English-only, distilled, turbo)
- **Lines of Code:** ~2700+

## 🔗 Important Links

- **Upstream Repo:** https://github.com/tin2tin/Subtitle_Editor
- **Faster Whisper:** https://github.com/SYSTRAN/faster-whisper
- **Framework Docs:** See main repo README.md

## 📖 Blender API Documentation

### Core API References
- **bpy.types.Operator** - https://docs.blender.org/api/current/bpy.types.Operator.html
  - Base class for all addon operators
  - `execute()`, `modal()`, `invoke()` methods
  - `bl_idname`, `bl_label`, `bl_options` properties
  
- **bpy.types.WindowManager** - https://docs.blender.org/api/current/bpy.types.WindowManager.html
  - Modal handler registration: `wm.modal_handler_add(operator)`
  - Event timer management: `wm.event_timer_add()` / `wm.event_timer_remove()`
  - Essential for non-blocking operations

### Threading & Concurrency
- **Threading Gotchas** - https://docs.blender.org/api/current/info_gotchas_threading.html
  - **Critical**: Never manipulate Blender data from background threads
  - Use `bpy.app.timers` for thread-safe UI updates
  - Use `queue.Queue` for thread-to-main communication
  - Always register timers on main thread only

### VSE (Video Sequence Editor) API
- **Sequences** - Use `sequences` (Blender 5.0+), not `sequences_all` (deprecated)
- **Text Strips** - `bpy.types.TextSequence` for subtitle strips
- **Scene Sequence Editor** - `context.scene.sequence_editor`

## 📦 Download System Architecture

The addon uses different approaches for different download types:

### Model Download (`subtitle.download_model`)
- **Approach**: Modal operator + background thread
- **Why**: Non-blocking UI with real progress tracking
- **Progress**: Progress bar + status messages + Blender progress indicator
- **Cancel**: Supported via `subtitle.cancel_download` operator
- **Resume**: Supported via huggingface_hub's resume_download
- **Core**: Uses `DownloadManager` from `core/download_manager.py`

### Dependency Download (`subtitle.download_dependencies`)
- **Approach**: Modal operator + background thread
- **Why**: Non-blocking UI with progress bar
- **Progress**: Blender status bar + thread-safe state
- **Cancel**: Supported via cancel operator

### PyTorch Installation (`subtitle.install_pytorch`)
- **Approach**: Modal operator + background thread
- **Why**: Complex installation with CUDA/ROCm selection
- **Progress**: Custom UI properties
- **Cancel**: Supported

## 🔐 Hugging Face Token Configuration (Optional)

To enable faster model downloads and avoid rate limits, you can set a Hugging Face authentication token:

### Getting Your Token:
1. Visit: https://huggingface.co/settings/tokens
2. Create a new token (read-only is sufficient)
3. Copy the token

### Setting the Token in Blender:
1. Open Blender
2. Go to **Edit > Preferences > Add-ons**
3. Find "Subtitle Studio" and expand it
4. Click on the addon preferences
5. Paste your token in the "Hugging Face Token" field
6. The token will be used automatically for all model downloads

### Benefits:
- **Faster downloads** - Higher rate limits from Hugging Face
- **No warnings** - Eliminates "unauthenticated requests" warnings
- **Better reliability** - Less likely to hit rate limits during peak times

**Note:** The token is optional. Downloads will work without it, but may be slower.

## 📚 Development Context Files

Located in `.opencode/` directory for AI assistants:

### `.opencode/context.md`
Critical development standards:
- Blender 5.0 API changes (sequences_all → sequences)
- Type annotations required for all bpy.props
- Module separation rules (no bpy in core/)
- Async operations pattern (threading + timers)
- Common pitfalls and testing procedures

### `.opencode/agent-context.md`
Comprehensive agent guide:
- All installed dependencies with versions
- Code architecture and patterns
- UI guidelines and available icons
- Property group examples
- Async operations pattern
- Thread safety requirements
- Complete file structure
- Testing with hot reload

## ⚠️ Code Review Findings

**Overall Quality: GOOD** ✅ Production-ready after thread safety fix

### Critical Issues (Must Fix)
1. **Thread Safety** - ops_transcribe.py updates properties from background thread
2. **Bare Except** - props.py:285 catches SystemExit/KeyboardInterrupt

### Files Already Fixed for Blender 5.0
- ✅ `utils/sequence_utils.py` - 3 sequences_all → sequences
- ✅ `props.py` - 1 sequences_all → sequences  
- ✅ `operators/ops_transcribe.py` - 2 sequences_all → sequences
- ✅ `operators/ops_strip_edit.py` - 2 sequences_all → sequences

### Compliance Checklist
| Requirement | Status |
|-------------|--------|
| Blender 5.0 API (sequences not sequences_all) | ✅ PASS |
| Type annotations for all bpy.props | ✅ PASS |
| No bpy imports in core/ modules | ✅ PASS |
| Threading for heavy operations | ✅ PASS |
| Error handling on imports | ✅ PASS |
| Valid Blender icons only | ✅ PASS |

---

**Current context loaded:** ✅ Subtitle Studio with Framework Integration
