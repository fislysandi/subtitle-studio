# Architecture Patterns - Subtitle Studio Addon

Design patterns and architectural decisions used throughout the codebase.

---

## Table of Contents

1. [Modal Operator Pattern](#modal-operator-pattern)
2. [Threading + bpy.app.timers Pattern](#threading-timers-pattern)
3. [Core/Operator Separation](#core-operator-separation)
4. [Property Group Organization](#property-group-organization)
5. [Download System Architecture](#download-system-architecture)
6. [Dependency Management Architecture](#dependency-management-architecture)

---

## Modal Operator Pattern

For non-blocking UI during CPU-intensive operations (downloads, transcription).

### Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     invoke()    │────▶│  Background     │     │   modal()       │
│   (Main Thread) │     │   Thread        │────▶│  (Main Thread)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
   Setup state            Do heavy work           Poll progress
   Start thread           Update shared state     Update UI
   Add timer/modal        (Thread-safe)           Force redraw
```

### Implementation

**File:** `operators/ops_model_download.py` (Reference Implementation)

```python
class SUBTITLE_OT_download_model(Operator):
    """Modal operator for non-blocking downloads"""
    
    bl_idname = "subtitle.download_model"
    bl_label = "Download Model"
    bl_options = {"REGISTER"}
    
    # Modal state (instance variables, not class)
    _timer = None
    _download_manager = None
    _thread = None
    _finished = False
    
    def invoke(self, context, event):
        """
        Entry point - runs on main thread.
        Sets up state, starts background thread, adds modal handler.
        """
        # Initialize state
        self._finished = False
        
        # Create download manager (pure Python, no Blender)
        cache_dir = file_utils.get_addon_models_dir()
        self._download_manager = create_download_manager(cache_dir)
        
        # Start background thread
        self._thread = threading.Thread(
            target=self._download_worker,
            args=(model_name, token),
            daemon=True
        )
        self._thread.start()
        
        # Setup modal infrastructure
        wm = context.window_manager
        wm.progress_begin(0, 100)  # Native progress bar
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        
        return {"RUNNING_MODAL"}
    
    def modal(self, context, event):
        """
        Called repeatedly by Blender's event loop (~10x/second).
        Must return quickly! Heavy work is in background thread.
        """
        # Handle cancellation (ESC key)
        if event.type == "ESC":
            self._cancel_download(context)
            return {"CANCELLED"}
        
        # Handle timer events (our 0.1s timer)
        if event.type == "TIMER":
            # Poll progress (fast operation)
            progress = self._download_manager.get_progress()
            
            # Update UI properties
            props.model_download_progress = progress.percentage
            props.model_download_status = progress.message
            
            # Update native progress bar
            context.window_manager.progress_update(
                int(progress.percentage * 100)
            )
            
            # Check completion
            if progress.status in (DownloadStatus.COMPLETE, 
                                   DownloadStatus.ERROR,
                                   DownloadStatus.CANCELLED):
                self._cleanup(context)
                return {"FINISHED"}
            
            # Force UI redraw (critical!)
            for area in context.screen.areas:
                area.tag_redraw()
        
        # PASS_THROUGH keeps Blender responsive
        return {"PASS_THROUGH"}
    
    def _download_worker(self, model_name, token):
        """Background thread - does heavy lifting."""
        try:
            self._download_manager.download(model_name, token=token)
        except Exception as e:
            print(f"[Download Error] {e}")
    
    def _cleanup(self, context):
        """Clean up timer and state - always call this!"""
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            context.window_manager.progress_end()
            self._timer = None
    
    def cancel(self, context):
        """Called when operator is cancelled externally."""
        self._cancel_download(context)
```

### Key Points

| Element | Purpose | Critical? |
|---------|---------|-----------|
| `invoke()` | Setup and start modal | Yes |
| `modal()` | Poll progress, update UI | Yes |
| `_timer` | Triggers modal calls every 0.1s | Yes |
| `wm.modal_handler_add()` | Registers with Blender event loop | Yes |
| `return {'RUNNING_MODAL'}` | Keeps operator alive | Yes |
| `return {'PASS_THROUGH'}` | Allows Blender to process other events | Yes |
| `area.tag_redraw()` | Forces UI to show progress | Yes |
| `cancel()` | Cleanup when done | Yes (memory leaks if skipped) |

---

## Threading + bpy.app.timers Pattern

For updating Blender properties from background threads safely.

### The Problem

```python
# ❌ CRASH - Cannot access Blender data from threads
def _worker(self, context):
    props = context.scene.subtitle_editor  # CRASH!
    props.progress = 0.5  # CRASH!
```

### The Solution

```python
# ✅ SAFE - Use timers to schedule updates on main thread
def _worker(self, context):
    """Background thread - no Blender access here"""
    
    # Prepare data to send to UI
    progress_data = {"value": 0.5, "text": "Processing..."}
    
    def update_ui():
        """This runs on main thread - safe to access Blender"""
        props = context.scene.subtitle_editor
        props.progress = progress_data["value"]
        props.progress_text = progress_data["text"]
        return None  # Don't repeat timer
    
    # Schedule update on main thread
    bpy.app.timers.register(update_ui, first_interval=0.0)
```

### Implementation Example

**File:** `operators/ops_transcribe.py`

```python
def _transcribe_thread(self, context, config):
    """Run transcription in background thread."""
    
    # Thread-local storage for progress
    progress_data = {"progress": 0.0, "text": "Starting..."}
    
    def update_props_on_main_thread(progress, text):
        """
        Thread-safe property update.
        Schedules update on main thread using bpy.app.timers.
        """
        progress_data["progress"] = progress
        progress_data["text"] = text
        
        def apply_updates():
            # Runs on main thread - safe!
            if context.scene:  # Check scene still valid
                props = context.scene.subtitle_editor
                props.progress = progress_data["progress"]
                props.progress_text = progress_data["text"]
            return None  # Don't repeat
        
        bpy.app.timers.register(apply_updates, first_interval=0.0)
    
    # Progress callback for transcription
    def progress_callback(progress, text):
        update_props_on_main_thread(progress, text)
    
    try:
        # Initialize transcriber
        tm = transcriber.TranscriptionManager(
            model_name=config["model"],
            device=config["device"]
        )
        
        tm.set_progress_callback(progress_callback)
        
        # Do transcription (blocks thread but not UI)
        segments = list(tm.transcribe(config["filepath"]))
        
        # Schedule strip creation on main thread
        bpy.app.timers.register(
            lambda: self._create_strips(context, segments, config),
            first_interval=0.0
        )
        
    except Exception as e:
        update_props_on_main_thread(0.0, f"Error: {str(e)}")
```

### When to Use What

| Pattern | Use For | UI Blocking |
|---------|---------|-------------|
| Simple `threading` | I/O operations (file read/write) | No |
| Simple `threading` | CPU-intensive work | **YES** (GIL) |
| `threading` + `bpy.app.timers` | I/O with UI updates | No |
| **Modal Operator** | CPU-intensive work | **No** |
| `multiprocessing` | Heavy CPU work | No |

---

## Core/Operator Separation

Separation of concerns: Core logic (pure Python) vs Operators (Blender UI).

### Architecture

```
subtitle_editor/
├── core/                    # NO Blender imports - pure Python
│   ├── download_manager.py  # Download logic
│   ├── transcriber.py       # Whisper transcription
│   └── subtitle_io.py       # File format handling
├── operators/               # Blender operators - UI layer
│   ├── ops_model_download.py
│   ├── ops_transcribe.py
│   └── ...
└── panels/                  # Blender UI
    └── main_panel.py
```

### Rules

**Core modules (`core/`):**
- ❌ NO `import bpy`
- ❌ NO `import bpy.props`
- ✅ Pure Python + third-party libraries
- ✅ Testable without Blender

**Operators (`operators/`):**
- ✅ `import bpy` allowed
- ✅ Access context, scene, UI
- ✅ Call core modules
- ❌ No heavy computation (use threads)

### Example

**File:** `core/download_manager.py`

```python
"""Pure Python download manager - no Blender dependencies."""

import os
import threading
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum

# Third-party imports OK
from huggingface_hub import snapshot_download


class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class DownloadProgress:
    status: DownloadStatus
    bytes_downloaded: int
    bytes_total: int
    message: str
    
    @property
    def percentage(self) -> float:
        if self.bytes_total == 0:
            return 0.0
        return self.bytes_downloaded / self.bytes_total


class DownloadManager:
    """Pure Python - knows nothing about Blender."""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self._cancel_event = threading.Event()
        self._lock = threading.Lock()
        self._progress = DownloadProgress(
            status=DownloadStatus.PENDING,
            bytes_downloaded=0,
            bytes_total=0,
            message="Ready"
        )
    
    def get_progress(self) -> DownloadProgress:
        """Thread-safe read."""
        with self._lock:
            return self._progress
    
    def download(self, model_name: str, token: Optional[str] = None):
        """Download model - blocks until complete."""
        # Implementation using huggingface_hub...
        pass
    
    def cancel(self):
        """Signal cancellation."""
        self._cancel_event.set()
```

**File:** `operators/ops_model_download.py`

```python
"""Blender operator - UI layer only."""

import bpy
import threading
from bpy.types import Operator

# Import from core (pure Python)
from ..core.download_manager import (
    DownloadManager, 
    DownloadStatus, 
    create_download_manager
)


class SUBTITLE_OT_download_model(Operator):
    """Operator handles Blender-specific concerns only."""
    
    bl_idname = "subtitle.download_model"
    bl_label = "Download Model"
    
    _download_manager = None
    _thread = None
    
    def execute(self, context):
        # Use core module
        cache_dir = file_utils.get_addon_models_dir()
        self._download_manager = create_download_manager(cache_dir)
        
        # Start background thread
        self._thread = threading.Thread(
            target=self._download_manager.download,
            args=("tiny",)
        )
        self._thread.start()
        
        return {"FINISHED"}
```

### Benefits

1. **Testability:** Core modules can be unit tested without Blender
2. **Reusability:** Core logic can be used in other contexts
3. **Maintainability:** Clear separation of concerns
4. **Safety:** No accidental thread safety violations in core

---

## Property Group Organization

Managing addon state through Blender's property system.

### Structure

```python
# props.py

class TextStripItem(PropertyGroup):
    """Individual subtitle item in list."""
    name: StringProperty(name="Name")
    text: StringProperty(name="Text")
    frame_start: IntProperty(name="Start Frame")
    frame_end: IntProperty(name="End Frame")
    channel: IntProperty(name="Channel", min=1, max=128)


class SubtitleEditorProperties(PropertyGroup):
    """Main addon properties - organized by section."""
    
    # --- Transcription Settings ---
    language: EnumProperty(
        name="Language",
        items=LANGUAGE_ITEMS,
        default="auto"
    )
    model: EnumProperty(
        name="Model",
        items=[...],
        default="base"
    )
    device: EnumProperty(
        name="Device",
        items=[("cpu", "CPU", ""), ("cuda", "GPU", "")],
        default="auto"
    )
    
    # --- UI State ---
    show_advanced: BoolProperty(default=False)
    is_transcribing: BoolProperty(default=False)
    progress: FloatProperty(min=0.0, max=1.0, default=0.0)
    
    # --- Dependencies ---
    deps_faster_whisper: BoolProperty(default=False)
    deps_torch: BoolProperty(default=False)
    is_installing_deps: BoolProperty(default=False)
    
    # --- Computed Properties ---
    @property
    def _get_is_cached(self):
        return file_utils.is_model_cached(self.model)
    
    is_cached: BoolProperty(get=_get_is_cached)
```

### Registration

```python
# __init__.py

classes = [
    TextStripItem,
    SubtitleEditorProperties,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Attach to scene
    bpy.types.Scene.subtitle_editor = PointerProperty(type=SubtitleEditorProperties)
    bpy.types.Scene.text_strip_items = CollectionProperty(type=TextStripItem)
    bpy.types.Scene.text_strip_items_index = IntProperty(default=-1)

def unregister():
    del bpy.types.Scene.text_strip_items_index
    del bpy.types.Scene.text_strip_items
    del bpy.types.Scene.subtitle_editor
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

### Usage in Panels

```python
def draw(self, context):
    props = context.scene.subtitle_editor
    
    # Section with box
    box = layout.box()
    box.label(text="Settings", icon="PREFERENCES")
    box.prop(props, "language")
    box.prop(props, "model")
    
    # Conditional display
    if props.show_advanced:
        box.prop(props, "beam_size")
        box.prop(props, "vad_filter")
```

---

## Download System Architecture

Three-layer architecture for downloading Whisper models.

### Layers

```
┌─────────────────────────────────────────────────────────────┐
│  UI Layer (operators/ops_model_download.py)                 │
│  - Modal operator                                           │
│  - Progress UI                                              │
│  - Cancellation handling                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Business Logic (core/download_manager.py)                  │
│  - DownloadState enum                                       │
│  - DownloadManager class                                    │
│  - Thread-safe progress tracking                            │
│  - HuggingFace integration                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Progress Tracking (ProgressTracker)                        │
│  - Custom tqdm-compatible class                             │
│  - Intercepts huggingface_hub progress                      │
│  - Forwards to DownloadManager                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

**1. DownloadStatus Enum**

```python
class DownloadStatus(Enum):
    PENDING = "pending"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"
```

**2. DownloadProgress Dataclass**

```python
@dataclass
class DownloadProgress:
    status: DownloadStatus
    bytes_downloaded: int
    bytes_total: int
    current_file: str
    message: str
    
    @property
    def percentage(self) -> float:
        if self.bytes_total == 0:
            return 0.0
        return min(self.bytes_downloaded / self.bytes_total, 1.0)
```

**3. ProgressTracker (tqdm-compatible)**

```python
class ProgressTracker:
    """Custom tqdm class that captures huggingface_hub progress."""
    
    _progress_callback: Optional[Callable] = None
    _cancel_event: Optional[threading.Event] = None
    
    def __init__(self, iterable=None, total=None, desc="", **kwargs):
        self.iterable = iterable
        self.total = total or 0
        self.n = 0
        self.desc = desc
        self._callback = ProgressTracker._progress_callback
        self.start_time = time.time()
    
    def update(self, n: int = 1):
        """Called by huggingface_hub to update progress."""
        self.n += n
        if self._callback:
            elapsed = time.time() - self.start_time
            self._callback(self.n, self.total, self.desc, elapsed)
```

**4. DownloadManager**

```python
class DownloadManager:
    REPO_MAP = {...}  # Model name → HuggingFace repo ID
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self._cancel_event = threading.Event()
        self._lock = threading.Lock()
        self._progress = DownloadProgress(...)
    
    def download(self, model_name: str, token: Optional[str] = None):
        # Setup ProgressTracker callbacks
        ProgressTracker._progress_callback = self._progress_callback
        ProgressTracker._cancel_event = self._cancel_event
        
        # Download using huggingface_hub
        snapshot_download(
            repo_id=self._get_repo_id(model_name),
            local_dir=str(model_dir),
            token=token,
            tqdm_class=ProgressTracker
        )
```

### Communication Flow

```
User clicks Download
        │
        ▼
┌──────────────────┐
│  Operator.invoke │──▶ Creates DownloadManager
│  (Main Thread)   │     Starts background thread
└──────────────────┘     Adds modal handler
        │
        ▼
┌──────────────────┐
│  Thread.download │──▶ Calls huggingface_hub
│  (Background)    │     snapshot_download()
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  ProgressTracker │──▶ Captures progress
│  (HF callback)   │     Calls _progress_callback()
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  DM._set_progress│──▶ Updates _progress
│  (Thread-safe)   │     (with lock)
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  Operator.modal  │──▶ Polls get_progress()
│  (Main Thread)   │     Updates UI props
│  (every 0.1s)    │     area.tag_redraw()
└──────────────────┘
```

---

## Dependency Management Architecture

UV-first dependency installation with pip fallback.

### Architecture

```
┌────────────────────────────────────────────┐
│  User clicks "Install Dependencies"        │
└────────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│  DependencyManager.get_install_command()   │
│  - Try to find uv                          │
│  - Fallback to pip                         │
└────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌──────────────┐          ┌──────────────┐
│  UV Path     │          │  Pip Fallback│
│  Found       │          │              │
└──────────────┘          └──────────────┘
        │                       │
        ▼                       ▼
┌──────────────┐          ┌──────────────┐
│ uv pip install│         │ python -m pip│
│ --python     │          │ install      │
│ <blender_py> │          │              │
└──────────────┘          └──────────────┘
```

### Implementation

**File:** `core/dependency_manager.py`

```python
class DependencyManager:
    @staticmethod
    def get_uv_path() -> Optional[str]:
        """Find uv executable in PATH or common locations."""
        # Check PATH first
        uv_in_path = shutil.which("uv")
        if uv_in_path:
            return uv_in_path
        
        # Check common installation locations
        candidates = []
        python_dir = Path(sys.executable).parent
        
        if platform.system() == "Windows":
            candidates.append(python_dir / "uv.exe")
            candidates.append(python_dir / "Scripts" / "uv.exe")
        else:
            candidates.append(python_dir / "uv")
            candidates.append(python_dir / "bin" / "uv")
            candidates.append(Path.home() / ".local" / "bin" / "uv")
        
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        
        return None
    
    @staticmethod
    def ensure_uv() -> Optional[str]:
        """Install uv if not found."""
        uv_path = DependencyManager.get_uv_path()
        if uv_path:
            return uv_path
        
        # Bootstrap uv via pip
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "uv"],
                check=True,
                capture_output=False
            )
            return DependencyManager.get_uv_path()
        except subprocess.CalledProcessError:
            return None
    
    @staticmethod
    def get_install_command(
        packages: list,
        constraint: str = None,
        extra_args: list = None,
        use_uv: bool = True
    ) -> list:
        """Generate install command."""
        
        uv_path = DependencyManager.ensure_uv() if use_uv else None
        cmd = []
        
        if uv_path:
            # UV command: uv pip install --python <blender_python> <packages>
            cmd = [uv_path, "pip", "install", "--python", sys.executable]
        else:
            # Pip fallback
            cmd = [sys.executable, "-m", "pip", "install"]
        
        if constraint:
            cmd.append(constraint)  # e.g., "numpy<2.0"
        
        cmd.extend(packages)
        
        if extra_args:
            cmd.extend(extra_args)
        
        return cmd
```

### Usage

```python
# In operator
from ..core.dependency_manager import DependencyManager

packages = ["faster-whisper", "pysubs2>=1.8.0"]
cmd = DependencyManager.get_install_command(
    packages,
    constraint="numpy<2.0",
    use_uv=True
)

# Execute
subprocess.run(cmd, check=True)
```

### Benefits of UV

1. **Speed:** 10-100x faster than pip
2. **Accuracy:** Explicit `--python` flag ensures correct environment
3. **Auto-bootstrap:** Installs itself if not present
4. **Optional:** User can disable via preferences

---

## Related Documentation

- [How-To Guides](./how-to-guides.md) - Step-by-step procedures
- [Troubleshooting](./troubleshooting.md) - Common issues
- [Agent Context](./agent-context.md) - Quick reference
