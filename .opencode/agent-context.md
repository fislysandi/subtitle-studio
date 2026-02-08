# Agent Development Context - Subtitle Studio Addon

## 🎯 CRITICAL: Blender 5.0 API Changes

### Removed in Blender 5.0
```python
# ❌ REMOVED - Do not use
context.scene.sequence_editor.sequences_all

# ✅ CORRECT - Use this instead  
context.scene.sequence_editor.sequences
```

**Files already fixed:**
- `utils/sequence_utils.py`
- `props.py`
- `operators/ops_transcribe.py`
- `operators/ops_strip_edit.py`

## 📦 Installed Dependencies (UV Environment)

Location: `.venv/lib/python3.11/site-packages/`

### Core ML Libraries
- **faster-whisper** (1.1.0+) - Whisper transcription engine
  - Models: tiny, base, small, medium, large-v1/v2/v3, distil variants, turbo
  - Supports: CPU, CUDA, ROCm, Metal
  
- **torch** (2.x) - PyTorch framework with CUDA 11.8
  - Device support: cuda, cpu, mps (Apple), xpu (Intel)
  - Tensor operations for ML inference

- **torchaudio** - Audio preprocessing for PyTorch

### Subtitle Processing
- **pysubs2** (1.8.0+) - Subtitle format parser
  - Formats: SRT, VTT, ASS/SSA
  - Timecode handling, styling

- **onnxruntime** (1.24.1+) - ONNX model inference

## 🏗️ Code Architecture

### Module Separation
```
subtitle_editor/
├── core/               # NO Blender imports - pure Python
│   ├── transcriber.py  # Whisper transcription logic
│   └── subtitle_io.py  # File format handling
├── operators/          # Blender operators
├── panels/            # UI panels
└── utils/             # Blender utilities
```

**Rule:** Never import `bpy` in `core/` modules

### Property Groups
All properties must be typed:
```python
class MyProperties(PropertyGroup):
    name: StringProperty(name="Name", default="")
    count: IntProperty(name="Count", default=0, min=0)
    active: BoolProperty(name="Active", default=False)
```

### Async Operations Pattern
```python
def execute(self, context):
    # Start background thread
    thread = threading.Thread(target=self._worker, args=(context,))
    thread.daemon = True
    thread.start()
    return {'FINISHED'}

def _worker(self, context):
    # Do heavy work here...
    
    # Update UI from main thread
    bpy.app.timers.register(
        lambda: self._update_ui(context, result),
        first_interval=0.0
    )

def _update_ui(self, context, result):
    # Update Blender UI here
    return None  # Don't repeat
```

## 🎨 UI Guidelines

### Panel Layout
```python
def draw(self, context):
    layout = self.layout
    
    # Section with box
    box = layout.box()
    box.label(text="Section Title", icon="ICON_NAME")
    box.prop(props, "property_name")
    
    # Row with alignment
    row = box.row(align=True)
    row.prop(props, "prop1")
    row.prop(props, "prop2")
```

### Available Icons (Common)
- `"CHECKMARK"` / `"ERROR"` - Status indicators
- `"PREFERENCES"` - Settings
- `"IMPORT"` / `"EXPORT"` - File operations
- `"FILE_REFRESH"` - Refresh
- `"TRIA_UP"` / `"TRIA_DOWN"` - Navigation
- `"RADIOBUT_OFF"` / `"RADIOBUT_ON"` - Selection
- `"FONT_DATA"` - Text-related
- `"INFO"` - Information
- `"GPU"` - Does NOT exist, use `"PREFERENCES"`

## 🔧 Common Tasks

### Adding a New Property
1. Add to `props.py` with type annotation
2. Add to relevant operator logic
3. Add to panel UI

### Adding a New Operator
1. Create in `operators/ops_*.py`
2. Include `bl_idname`, `bl_label`, `bl_description`
3. Use `bl_options = {"REGISTER", "UNDO"}`
4. Return `{"FINISHED"}` or `{"CANCELLED"}`

### Adding a New Panel Section
1. Edit `panels/main_panel.py`
2. Use `box = col.box()` for sections
3. Add `row = box.row()` for horizontal layout
4. Use `row.prop()` or `row.operator()`

## ⚠️ Common Pitfalls

1. **sequences_all** - Removed in Blender 5.0, use `sequences`
2. **bpy imports in core/** - Keep core/ Blender-agnostic
3. **Missing type annotations** - All bpy.props need types
4. **GPU icon** - Does not exist, use `"PREFERENCES"`
5. **Blocking operations** - See Non-Blocking Operations section below

## 🔄 Non-Blocking Operations (CRITICAL)

### Python's GIL Problem
Python's **Global Interpreter Lock (GIL)** means CPU-bound operations in threads can STILL block Blender's UI. For heavy operations like model downloads, use **Modal Operators** instead of threading.

### ❌ INCORRECT - Threading blocks UI for CPU-intensive tasks
```python
def execute(self, context):
    thread = threading.Thread(target=self._worker)
    thread.start()
    return {'FINISHED'}

def _worker(self):
    # CPU-intensive work here STILL blocks UI due to GIL
    WhisperModel(...)  # Blocks!
```

### ✅ CORRECT - Modal Operator for non-blocking operations
```python
class ModalDownloadOperator(bpy.types.Operator):
    """Modal operator for non-blocking downloads"""
    bl_idname = "subtitle.modal_download"
    bl_label = "Download"
    
    _timer = None
    _queue = None
    
    def modal(self, context, event):
        if event.type == 'TIMER':
            # Check for updates from thread/process
            self.check_progress()
            
            # Force UI redraw
            for area in context.screen.areas:
                area.tag_redraw()
        
        if self.is_complete:
            self.cancel(context)
            return {'FINISHED'}
        
        return {'PASS_THROUGH'}
    
    def execute(self, context):
        self._queue = queue.Queue()
        self.is_complete = False
        
        # Start background work
        thread = threading.Thread(target=self._worker)
        thread.start()
        
        # Add timer and modal handler
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
    
    def _worker(self):
        # Do heavy work...
        # Put progress updates in queue
        self._queue.put({'progress': 0.5})
        # When done:
        self.is_complete = True
    
    def check_progress(self):
        # Process queue updates
        while not self._queue.empty():
            msg = self._queue.get()
            # Update properties from main thread
```

### Key Points for Non-Blocking Operations:

1. **Use Modal Operators** - `return {'RUNNING_MODAL'}` keeps operator alive
2. **Add Event Timer** - `wm.event_timer_add(0.1, window=context.window)`
3. **Force UI Redraw** - `area.tag_redraw()` updates progress bars
4. **Use Queues** - Thread-safe communication between thread and main thread
5. **Return 'PASS_THROUGH'** - Allows Blender to process other events
6. **Clean up in cancel()** - Always remove timers when done

### When to Use What:

| Pattern | Use For | UI Blocking |
|---------|---------|-------------|
| `threading` + `bpy.app.timers` | I/O operations (file read/write) | No |
| `threading` + `bpy.app.timers` | CPU-intensive work | **YES** (GIL) |
| **Modal Operator** + `threading` | CPU-intensive work | **No** |
| `multiprocessing` | Heavy CPU work | No (separate process) |

## 🧪 Testing

### Hot Reload
```bash
uv run test subtitle_editor
```
Changes auto-reload in Blender on file save.

### Verify Installation
```python
import torch
print(torch.cuda.is_available())  # Should be True for GPU
print(torch.cuda.get_device_name(0))  # Your GPU name

import faster_whisper
print(faster_whisper.__version__)
```

## 📦 UV Integration Usage

UV is a fast Python package manager used for dependency installation.

### Commands

```bash
# Test with hot-reload
uv run test subtitle_editor

# Install dependencies
uv run addon-deps list subtitle_editor
uv run addon-deps sync subtitle_editor
uv run addon-deps add subtitle_editor <package>

# Package for distribution
uv run release subtitle_editor
```

### In Code: Dependency Installation

```python
from ..core.dependency_manager import DependencyManager

# Generate install command
packages = ["faster-whisper", "pysubs2>=1.8.0"]
cmd = DependencyManager.get_install_command(
    packages,
    constraint="numpy<2.0",  # NumPy 2.x compatibility
    use_uv=True  # Use UV if available, fallback to pip
)

# cmd output with UV:
# ["uv", "pip", "install", "--python", "/path/to/blender/python", "faster-whisper", "pysubs2>=1.8.0"]

# cmd output without UV:
# ["/path/to/blender/python", "-m", "pip", "install", "faster-whisper", "pysubs2>=1.8.0"]

# Execute
subprocess.run(cmd, check=True)
```

### Benefits

- **10-100x faster** than pip
- **Explicit Python path** via `--python` flag
- **Auto-bootstraps** if not installed

---

## 📝 Modal Operator Template (Copy-Paste Ready)

```python
"""Modal Operator Template - Non-Blocking Operations"""

import bpy
import threading
import queue
from bpy.types import Operator


class SUBTITLE_OT_modal_template(Operator):
    """Template for non-blocking modal operator"""
    
    bl_idname = "subtitle.modal_template"
    bl_label = "Modal Template"
    bl_description = "Template for modal operations"
    bl_options = {"REGISTER"}
    
    # Modal state (instance variables, NOT class variables)
    _timer = None
    _thread = None
    _queue = None
    _is_complete = False
    
    def invoke(self, context, event):
        """Start modal operator - runs on main thread"""
        
        # Initialize state
        self._queue = queue.Queue()
        self._is_complete = False
        
        # Update UI state
        props = context.scene.subtitle_editor
        props.is_processing = True
        props.progress = 0.0
        
        # Start background thread
        self._thread = threading.Thread(
            target=self._worker,
            args=(context,),  # Pass context safely
            daemon=True
        )
        self._thread.start()
        
        # Setup modal infrastructure
        wm = context.window_manager
        wm.progress_begin(0, 100)
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        
        self.report({"INFO"}, "Starting operation...")
        return {"RUNNING_MODAL"}
    
    def modal(self, context, event):
        """Called by Blender's event loop ~10x/second"""
        props = context.scene.subtitle_editor
        
        # Handle ESC key for cancellation
        if event.type == "ESC":
            self._cleanup(context)
            self.report({"WARNING"}, "Cancelled")
            return {"CANCELLED"}
        
        # Handle timer events
        if event.type == "TIMER":
            # Process messages from worker thread
            while not self._queue.empty():
                try:
                    msg = self._queue.get_nowait()
                    
                    if msg.get("type") == "progress":
                        props.progress = msg.get("value", 0.0)
                        # Update Blender progress bar
                        context.window_manager.progress_update(
                            int(props.progress * 100)
                        )
                    
                    elif msg.get("type") == "complete":
                        self._is_complete = True
                        if msg.get("success"):
                            self.report({"INFO"}, "Complete!")
                        else:
                            self.report({"ERROR"}, msg.get("error", "Failed"))
                    
                except queue.Empty:
                    break
            
            # Check if complete
            if self._is_complete:
                self._cleanup(context)
                return {"FINISHED"}
            
            # Force UI redraw
            for area in context.screen.areas:
                area.tag_redraw()
        
        # Keep Blender responsive
        return {"PASS_THROUGH"}
    
    def _worker(self, context):
        """Background thread - do heavy work here"""
        try:
            # Simulate work with progress updates
            for i in range(10):
                progress = (i + 1) / 10.0
                self._queue.put({
                    "type": "progress",
                    "value": progress
                })
                import time
                time.sleep(0.5)
            
            # Signal completion
            self._queue.put({
                "type": "complete",
                "success": True
            })
            
        except Exception as e:
            self._queue.put({
                "type": "complete",
                "success": False,
                "error": str(e)
            })
    
    def _cleanup(self, context):
        """Clean up timer and state - ALWAYS call this"""
        props = context.scene.subtitle_editor
        
        if self._timer:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            wm.progress_end()
            self._timer = None
        
        props.is_processing = False
    
    def cancel(self, context):
        """Called when operator is cancelled externally"""
        self._cleanup(context)


classes = [SUBTITLE_OT_modal_template]
```

### Key Points

| Element | Critical | Description |
|---------|----------|-------------|
| `invoke()` | Yes | Setup and start modal |
| `modal()` | Yes | Poll progress, update UI |
| `_timer` | Yes | Triggers modal calls |
| `RUNNING_MODAL` | Yes | Keeps operator alive |
| `PASS_THROUGH` | Yes | Blender stays responsive |
| `area.tag_redraw()` | Yes | Updates progress UI |
| `_cleanup()` | Yes | Prevents memory leaks |

---

## 🔧 Common Property Types Reference

```python
# Boolean (checkbox)
enabled: BoolProperty(name="Enabled", default=True)

# Integer with limits
quality: IntProperty(name="Quality", default=5, min=1, max=10)

# Integer with slider
threshold: IntProperty(
    name="Threshold",
    default=50,
    min=0,
    max=100,
    subtype="PERCENTAGE"
)

# Float
speed: FloatProperty(name="Speed", default=1.0, min=0.1, max=10.0)

# Float with slider
factor: FloatProperty(
    name="Factor",
    default=0.5,
    min=0.0,
    max=1.0,
    subtype="FACTOR"  # Shows as 0-1 slider
)

# String
token: StringProperty(name="Token", default="")

# String with subtype
filepath: StringProperty(
    name="File Path",
    default="",
    subtype="FILE_PATH"
)

# Enum (dropdown)
mode: EnumProperty(
    name="Mode",
    items=[
        ("SIMPLE", "Simple", "Basic mode"),
        ("ADVANCED", "Advanced", "Advanced mode"),
    ],
    default="SIMPLE"
)

# Color (RGB)
color: FloatVectorProperty(
    name="Color",
    subtype="COLOR",
    size=3,
    min=0.0,
    max=1.0,
    default=(1.0, 1.0, 1.0)
)

# Color (RGBA) - Note: size=4
shadow_color: FloatVectorProperty(
    name="Shadow",
    subtype="COLOR",
    size=4,  # RGBA - Blender 5.0 requires 4 values
    min=0.0,
    max=1.0,
    default=(0.0, 0.0, 0.0, 1.0)
)

# CollectionProperty (for lists)
items: CollectionProperty(type=TextStripItem)
items_index: IntProperty(default=-1)

# Computed property
def _get_is_cached(self):
    return file_utils.is_model_cached(self.model)

is_cached: BoolProperty(get=_get_is_cached)
```

---

## ⚠️ Error Handling Patterns

### Pattern 1: Graceful Degradation

```python
def execute(self, context):
    try:
        result = self._do_work()
    except FileNotFoundError as e:
        self.report({"ERROR"}, f"File not found: {e}")
        return {"CANCELLED"}
    except PermissionError:
        self.report({"ERROR"}, "Permission denied")
        return {"CANCELLED"}
    except Exception as e:
        self.report({"ERROR"}, f"Unexpected error: {e}")
        return {"CANCELLED"}
    
    return {"FINISHED"}
```

### Pattern 2: Thread-Safe Error Reporting

```python
def _worker(self, context):
    """Background thread with safe error reporting"""
    
    def report_error(error_msg):
        """Schedule error report on main thread"""
        def show_error():
            self.report({"ERROR"}, error_msg)
            return None
        bpy.app.timers.register(show_error, first_interval=0.0)
    
    try:
        # Do work...
        pass
    except Exception as e:
        import traceback
        traceback.print_exc()  # Print to console
        report_error(str(e))   # Show in UI
```

### Pattern 3: Validation First

```python
def execute(self, context):
    # Validate inputs first
    strip = get_selected_strip(context)
    if not strip:
        self.report({"ERROR"}, "Please select a strip")
        return {"CANCELLED"}
    
    filepath = get_strip_filepath(strip)
    if not filepath:
        self.report({"ERROR"}, "Strip has no file path")
        return {"CANCELLED"}
    
    if not os.path.exists(filepath):
        self.report({"ERROR"}, f"File not found: {filepath}")
        return {"CANCELLED"}
    
    # All validations passed - proceed
    return self._do_work(context, filepath)
```

### Pattern 4: Context Managers

```python
# For temporary files
import tempfile

with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
    tmp_path = tmp.name
    try:
        # Use tmp_path
        process_audio(tmp_path)
    finally:
        # Always cleanup
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
```

---

## 🧪 Testing Procedures

### Hot Reload Workflow

```bash
# 1. Start hot-reload testing
uv run test subtitle_editor

# 2. Make code changes

# 3. Save file (Ctrl+S)

# 4. Changes auto-reload in Blender
```

### Manual Testing Checklist

```python
# In Blender's Python Console (Scripting tab)

# 1. Check dependencies
import faster_whisper
import torch
import pysubs2
print("All imports OK")

# 2. Check PyTorch GPU
torch.cuda.is_available()
torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No GPU"

# 3. Check model cache
from subtitle_editor.utils import file_utils
file_utils.is_model_cached("tiny")

# 4. Test sequence access
bpy.context.scene.sequence_editor.strips
# Should return collection, not raise AttributeError

# 5. Check properties
bpy.context.scene.subtitle_editor.model
bpy.context.scene.subtitle_editor.device
```

### Debug Output

```python
# Enable System Console
# Window > Toggle System Console

# Add debug prints
def execute(self, context):
    print(f"[DEBUG] Operator: {self.bl_idname}")
    print(f"[DEBUG] Scene: {context.scene.name}")
    print(f"[DEBUG] Selected: {context.selected_sequences}")
    
    # Your code here
    
    print("[DEBUG] Complete")
    return {"FINISHED"}
```

### Common Test Scenarios

| Scenario | Expected Result |
|----------|----------------|
| Click "Transcribe" with no strip selected | Error: "Please select a strip" |
| Click "Download" while downloading | Warning: "Already in progress" |
| Press ESC during modal operation | Operation cancels cleanly |
| Change model dropdown | Model size updates, cached status updates |
| Install dependencies | Progress bar shows, completes without error |
| Transcribe audio | Progress updates, strips created in sequencer |

---

## 📚 External Resources

- **Faster Whisper**: https://github.com/SYSTRAN/faster-whisper
- **Blender Python API**: https://docs.blender.org/api/current/
- **PyTorch**: https://pytorch.org/docs/stable/
- **Project Docs**: See `.opencode/` directory for detailed guides
