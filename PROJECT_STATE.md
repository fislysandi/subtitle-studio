# Subtitle Editor - Project State

**Last Updated:** 2025-02-07 (Commit: 5862a7e - Explicit PyTorch Selection)  
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

- [x] Add progress callback during transcription
- [x] Implement dependency management UI
- [ ] Implement batch styling (copy style to selected)
- [ ] Add line break insertion
- [ ] Test all import/export formats
- [ ] Add file browser panels for import/export
- [ ] Optimize transcription performance
- [x] Add PyTorch version selection in dependency installer
- [ ] Implement word count splitting in transcription
- [ ] Test PyTorch installation on different GPU types

## 🔄 To Resume Work

**In a new chat, say:**
> "Load from PROJECT_STATE.md in subtitle_editor addon and continue"

Or navigate to addon and:
```bash
cd addons/subtitle_editor
cat PROJECT_STATE.md
```

## 📝 Recent Changes

1. **PyTorch GPU Support** - New PyTorch installation section with multi-GPU support
   - GPU detection with visual warning if not detected (CPU fallback)
   - Multi-backend support: NVIDIA CUDA, AMD ROCm, Apple Metal (MPS), Intel XPU
   - PyTorch version dropdown with clear platform indicators:
     * CUDA 11.8/12.1/12.4 for NVIDIA GPUs (all platforms)
     * ROCm 5.7 for AMD RX 7900 series (Linux only)
     * Metal (MPS) for Apple Silicon Macs
   - **Explicit selection required** - Removed "auto" option, users must select their backend
   - Install Dependencies button now only installs base packages (faster-whisper, etc.)
   - PyTorch must be installed separately via dedicated "Install PyTorch" button
   - Status messages during installation
   - New operators: `check_gpu`, `install_pytorch`

2. **Major UI Redesign** - Complete overhaul of Transcription & Translation panel
   - Added Dependencies section with install/verify functionality
   - Reorganized layout: Dependencies → PyTorch → Model → Device/Compute → Language → Settings → Actions
   - Added 19 Whisper models with clear multilingual/English grouping
   - New controls: Beam Size, Max Words per Strip, Channel, Font Size, V Align, Wrap Width
   - Integrated edit section into main panel (removed separate panel)
   - VAD Filter now displays as checkbox

3. **New Operators**
   - `subtitle.translate` - Dedicated translation to English
   - `subtitle.check_dependencies` - Check dependency installation status
   - `subtitle.install_dependencies` - Install missing dependencies
   - `subtitle.check_gpu` - Check GPU availability
   - `subtitle.install_pytorch` - Install PyTorch with CUDA/ROCm support

4. **New Properties**
   - `compute_type` - Computation precision (int8, float16, float32)
   - `beam_size` - Beam search size (1-10)
   - `max_words_per_strip` - Word limit per subtitle strip (0-20)
   - `subtitle_channel` - Default channel for new strips
   - `subtitle_font_size` - Font size control (8-200)
   - `v_align` - Vertical alignment (Top/Center/Bottom)
   - `wrap_width` - Text wrapping factor (0-1)
   - PyTorch settings: `pytorch_version`, `gpu_detected`, `is_installing_pytorch`, `pytorch_install_status`
   - Dependency tracking: `deps_*` status properties

5. **Previous**
   - UI Update - Matched upstream tin2tin layout style
   - Framework Migration - Migrated to auto-load system
   - UV Integration - Dependency management via UV

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

---

**Current context loaded:** ✅ Subtitle Editor with Framework Integration
