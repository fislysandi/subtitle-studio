# Subtitle Editor - Project State

**Last Updated:** 2025-02-07 (Commit: c4bb551 - Code Review & Agent Context)  
**Addon Location:** `addons/subtitle_editor/`

## 📍 Current Status

**Status:** ✅ Migrated to Blender Addon Framework  
**Git Branch:** master  
**Framework Version:** Using auto-loading + UV dependency management

## 🎬 About This Addon

**Subtitle Editor** - AI-powered subtitle transcription and editing for Blender Video Sequence Editor (VSE)

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
- [x] Category: "Subtitle Editor"

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
│   ├── ops_import_export.py # Import/export operators
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
- `subtitle.install_dependencies` - Install missing dependencies
- `subtitle.check_gpu` - Check GPU availability for PyTorch
- `subtitle.install_pytorch` - Install PyTorch with selected CUDA/ROCm version

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

## 🐛 Known Issues / TODO

### Critical (Fix Before Release)
- [ ] **Thread Safety** - Property updates from background thread (ops_transcribe.py:69-70)
  - Properties updated directly from thread can cause crashes
  - Fix: Use `bpy.app.timers` for all property updates from threads
- [ ] **Bare Except Clauses** - Replace with `except Exception:` (props.py:285, ops_dependencies.py:105)

### Medium Priority
- [ ] Implement batch styling (copy style to selected)
- [ ] Add line break insertion
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

## 🔄 To Resume Work

**In a new chat, say:**
> "Load from PROJECT_STATE.md in subtitle_editor addon and continue"

Or navigate to addon and:
```bash
cd addons/subtitle_editor
cat PROJECT_STATE.md
```

## 📝 Recent Changes

### 1. Code Review & Agent Context (Latest)
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

- **Total Files:** 29
- **Operators:** 9
- **Panels:** 2
- **Property Groups:** 2
- **Dependencies:** 3 (faster-whisper, pysubs2, onnxruntime)
- **Whisper Models:** 19 (multilingual, English-only, distilled, turbo)
- **Lines of Code:** ~2600+

## 🔗 Important Links

- **Upstream Repo:** https://github.com/tin2tin/Subtitle_Editor
- **Faster Whisper:** https://github.com/SYSTRAN/faster-whisper
- **Framework Docs:** See main repo README.md

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

**Current context loaded:** ✅ Subtitle Editor with Framework Integration
