# Troubleshooting Guide - Subtitle Studio Addon

Common issues and their solutions.

---

## Table of Contents

1. [NumPy 2.x Compatibility Issues](#numpy-2x-compatibility)
2. [Thread Safety Problems](#thread-safety)
3. [Blender 5.0 API Migration Issues](#blender-50-api)
4. [File Path Resolution Issues](#file-path-resolution)
5. [Model Download Failures](#model-download-failures)
6. [Dependency Installation Problems](#dependency-installation)
7. [GPU/CUDA Detection Issues](#gpu-cuda-detection)
8. [UI Freezing/Blocking Issues](#ui-freezing)

---

## NumPy 2.x Compatibility

### Problem

```
ImportError: numpy.core.multiarray failed to import
# OR
RuntimeError: The numpy package is incompatible with Blender's aud module
```

### Root Cause

Blender 5.0 bundles an older NumPy version in its Python environment. NumPy 2.x has breaking API changes that conflict with Blender's bundled modules (especially `aud`).

### Solution

**Fix in pyproject.toml:**

```toml
[project]
dependencies = [
    "numpy<2.0",  # Pin to NumPy 1.x
    "faster-whisper>=1.0.0",
    # ... other deps
]
```

**Fix in dependency installation:**

```python
# In operators/ops_dependencies.py
def install_dependencies():
    cmd = [
        sys.executable, "-m", "pip", "install",
        "numpy<2.0",  # Explicitly specify version constraint
        "faster-whisper",
        # ... other packages
    ]
    subprocess.run(cmd, check=True)
```

**Verify the fix:**

```bash
# Check installed NumPy version
uv run python -c "import numpy; print(numpy.__version__)"
# Should output: 1.26.4 (or other 1.x version)
```

---

## Thread Safety Problems

### Problem

```
RuntimeError: Cannot access Blender data from thread
# OR
Crash/segfault when updating properties from background thread
```

### Root Cause

Blender's data is not thread-safe. Accessing `bpy.data`, `context.scene`, or properties from background threads causes crashes.

### Solution

**❌ INCORRECT - Direct property access from thread:**

```python
def _worker(self, context):
    props = context.scene.subtitle_editor  # DANGEROUS!
    props.progress = 0.5  # CRASH!
```

**✅ CORRECT - Use bpy.app.timers:**

```python
def _worker(self, context):
    """Background thread - NO Blender access here"""
    progress = 0.5
    
    # Schedule UI update on main thread
    def update_ui():
        props = context.scene.subtitle_editor  # Safe on main thread
        props.progress = progress
        return None  # Don't repeat
    
    bpy.app.timers.register(update_ui, first_interval=0.0)
```

**Pattern for transcription operators:**

```python
def _transcribe_thread(self, context, config):
    """Run in background thread"""
    
    def update_props_on_main_thread(progress, text):
        """Schedule property updates on main thread"""
        progress_data = {"progress": progress, "text": text}
        
        def apply_updates():
            if context.scene:  # Check scene still exists
                props = context.scene.subtitle_editor
                props.progress = progress_data["progress"]
                props.progress_text = progress_data["text"]
            return None
        
        bpy.app.timers.register(apply_updates, first_interval=0.0)
    
    # Do transcription work...
    update_props_on_main_thread(0.5, "Processing...")
```

**Key Rule:**

| Operation | Safe Location |
|-----------|---------------|
| Read `bpy.context` | Main thread only |
| Write properties | Main thread only (use timers) |
| Create/modify strips | Main thread only |
| Heavy computation | Background thread |
| File I/O | Background thread |

---

## Blender 5.0 API Migration

### Problem

```
AttributeError: 'bpy_struct' object has no attribute 'sequences_all'
# OR
TypeError: new_effect() got an unexpected keyword argument 'frame_end'
```

### Root Cause

Blender 5.0 removed deprecated APIs:
- `sequences_all` → `sequences`
- `frame_end` parameter → `length` parameter in `new_effect()`

### Solution

**Fix sequences access:**

```python
# ❌ OLD - Removed in Blender 5.0
for strip in context.scene.sequence_editor.sequences_all:
    pass

# ✅ NEW - Use sequences
for strip in context.scene.sequence_editor.strips:
    pass
```

**Files already fixed:**
- `utils/sequence_utils.py` (lines 16, 80, 96)
- `props.py`
- `operators/ops_transcribe.py`
- `operators/ops_strip_edit.py`

**Fix new_effect() call:**

```python
# ❌ OLD
strip = scene.sequence_editor.strips.new_effect(
    name="Text",
    type="TEXT",
    channel=3,
    frame_start=1,
    frame_end=100  # REMOVED
)

# ✅ NEW - Use length instead
length = frame_end - frame_start
strip = scene.sequence_editor.strips.new_effect(
    name="Text",
    type="TEXT",
    channel=3,
    frame_start=frame_start,
    length=length  # NEW parameter
)
```

**Fix shadow_color:**

```python
# ❌ OLD - 3 values
strip.shadow_color = (0, 0, 0)

# ✅ NEW - 4 values (RGBA)
strip.shadow_color = (0, 0, 0, 1)
```

---

## File Path Resolution

### Problem

```
FileNotFoundError: //path/to/file.mp4
# OR
Error: Cannot open file //path/to/file.mp4
```

### Root Cause

Blender uses `//` prefix for relative paths (relative to .blend file). External tools (ffmpeg, Whisper) don't understand this notation.

### Solution

**Always convert Blender paths to absolute:**

```python
def get_strip_filepath(strip) -> Optional[str]:
    """Get file path from a movie or sound strip"""
    filepath = None
    if strip.type == "MOVIE":
        filepath = strip.filepath
    elif strip.type == "SOUND":
        filepath = strip.sound.filepath if strip.sound else None
    
    if filepath:
        # Convert to absolute path (handles // prefix)
        abs_path = bpy.path.abspath(filepath)
        # Normalize path (handles .. and redundant separators)
        return os.path.abspath(abs_path)
    return None
```

**Usage pattern:**

```python
# Extract filepath on main thread BEFORE passing to worker
def execute(self, context):
    strip = get_selected_strip(context)
    
    # Get absolute path on main thread
    filepath = get_strip_filepath(strip)
    
    if not filepath or not os.path.exists(filepath):
        self.report({"ERROR"}, "File not found")
        return {"CANCELLED"}
    
    # Pass to thread
    thread = threading.Thread(
        target=self._worker,
        args=(filepath,)  # Pass absolute path
    )
    thread.start()
    
    return {"FINISHED"}
```

---

## Model Download Failures

### Problem

```
RepositoryNotFoundError: 404 Client Error
# OR
OSError: [Errno 39] Directory not empty
# OR
Download stuck at 0%
```

### Root Cause

1. Model name not mapped to correct Hugging Face repo ID
2. Partial/corrupted download leaving invalid directories
3. Filesystem locks during download

### Solution

**Fix 1: Verify repo mapping:**

```python
# In core/download_manager.py
REPO_MAP = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    # ... ensure all models are mapped
}
```

**Fix 2: Handle directory errors:**

```python
def download(self, model_name: str, token: Optional[str] = None):
    try:
        # Download logic...
        pass
    except OSError as e:
        if "Directory not empty" in str(e) or "Errno 39" in str(e):
            self._set_progress(
                status=DownloadStatus.ERROR,
                message=f"File Error: {str(e)[:100]}. Try deleting the 'models' folder."
            )
        raise
```

**Fix 3: Verify model files:**

```python
def is_cached(self, model_name: str) -> bool:
    """Check if model is fully downloaded"""
    model_dir = self._get_model_dir(model_name)
    
    if not model_dir.exists():
        return False
    
    # Check for essential files with size validation
    bin_path = model_dir / "model.bin"
    config_path = model_dir / "config.json"
    
    has_bin = bin_path.exists() and bin_path.stat().st_size > 1024
    has_config = config_path.exists() and config_path.stat().st_size > 10
    
    return has_bin and has_config
```

**Manual cleanup:**

```bash
# Delete corrupted models
cd /path/to/addon/models
rm -rf tiny base small  # Remove specific models
rm -rf *  # Remove all (WARNING: will re-download)
```

---

## Dependency Installation

### Problem

```
ModuleNotFoundError: No module named 'faster_whisper'
# OR
pip install fails silently
# OR
Packages installed but not found in Blender
```

### Root Cause

1. Installing to wrong Python environment
2. Blender's Python vs system Python mismatch
3. UV not available or pip falling back incorrectly

### Solution

**Fix 1: Use correct Python executable:**

```python
import sys

# Always use Blender's Python
python_exe = sys.executable  # Points to Blender's python

cmd = [python_exe, "-m", "pip", "install", "package"]
subprocess.run(cmd, check=True)
```

**Fix 2: Use UV with explicit Python path:**

```python
from ..core.dependency_manager import DependencyManager

# Get install command
packages = ["faster-whisper", "pysubs2>=1.8.0"]
cmd = DependencyManager.get_install_command(
    packages,
    constraint="numpy<2.0",
    use_uv=True  # Use UV if available
)

# cmd will be:
# With UV: ["uv", "pip", "install", "--python", "/path/to/blender/python", ...]
# Without UV: ["/path/to/blender/python", "-m", "pip", "install", ...]
```

**Fix 3: Verify installation:**

```python
def check_dependencies():
    """Check if all dependencies are installed"""
    deps = {}
    
    try:
        import faster_whisper
        deps["faster_whisper"] = True
    except ImportError:
        deps["faster_whisper"] = False
    
    try:
        import torch
        deps["torch"] = True
        deps["cuda_available"] = torch.cuda.is_available()
    except ImportError:
        deps["torch"] = False
    
    return deps
```

**Fix 4: Show verbose output:**

```python
# Don't use -q (quiet) flag during development
cmd = [
    python_exe, "-m", "pip", "install",
    # "-q",  # REMOVE this for debugging
    "package"
]

# Run with output visible
result = subprocess.run(cmd, capture_output=False)
```

---

## GPU/CUDA Detection

### Problem

```
No GPU detected - CPU fallback
# OR
torch.cuda.is_available() returns False
# OR
CUDA out of memory error
```

### Root Cause

1. PyTorch installed without CUDA support
2. Wrong CUDA version for GPU
3. GPU drivers not installed

### Solution

**Fix 1: Check PyTorch installation:**

```python
import torch

print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"Device: {torch.cuda.get_device_name(0)}")
```

**Fix 2: Install correct PyTorch version:**

```python
# In operators/ops_dependencies.py

def install_pytorch(self, context):
    props = context.scene.subtitle_editor
    version = props.pytorch_version  # e.g., "cu121", "cpu", "rocm57"
    
    index_urls = {
        "cu118": "https://download.pytorch.org/whl/cu118",
        "cu121": "https://download.pytorch.org/whl/cu121",
        "cu124": "https://download.pytorch.org/whl/cu124",
        "rocm57": "https://download.pytorch.org/whl/rocm5.7",
        "cpu": None,
        "mps": None,  # Built into macOS PyTorch
    }
    
    cmd = [
        sys.executable, "-m", "pip", "install",
        "torch", "torchaudio",
        "--index-url", index_urls[version]
    ]
    
    subprocess.run(cmd, check=True)
```

**Fix 3: Add GPU detection UI:**

```python
# In panel
if not props.gpu_detected and props.deps_torch:
    row = box.row()
    row.alert = True
    row.label(text="⚠ No GPU detected - CPU fallback", icon="ERROR")
elif props.gpu_detected:
    row = box.row()
    row.label(text="✓ GPU detected", icon="CHECKMARK")
```

**Fix 4: Handle out-of-memory:**

```python
def transcribe(self, audio_path):
    try:
        segments = self.model.transcribe(audio_path)
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            # Try with smaller batch size or CPU
            self.model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8"
            )
            segments = self.model.transcribe(audio_path)
        else:
            raise
```

---

## UI Freezing/Blocking

### Problem

```
Blender freezes during transcription
# OR
UI becomes unresponsive during download
# OR
"Not Responding" window title
```

### Root Cause

Python's GIL (Global Interpreter Lock) means CPU-intensive tasks in threads still block the main thread. Need to use Modal Operators or proper threading patterns.

### Solution

**Use Modal Operators for CPU-intensive tasks:**

See [Modal Operator Pattern](../architecture-patterns.md#modal-operator-pattern) for full details.

**Quick template:**

```python
class ModalOperator(Operator):
    bl_options = {"REGISTER"}
    
    _timer = None
    
    def modal(self, context, event):
        if event.type == "TIMER":
            # Check progress
            if self.is_complete:
                self.cancel(context)
                return {"FINISHED"}
            
            # Force redraw
            for area in context.screen.areas:
                area.tag_redraw()
        
        return {"PASS_THROUGH"}  # Keep responsive
    
    def execute(self, context):
        # Start background work
        thread = threading.Thread(target=self._worker)
        thread.start()
        
        # Setup modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        
        return {"RUNNING_MODAL"}
    
    def cancel(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
```

**Use queues for thread communication:**

```python
def execute(self, context):
    self._queue = queue.Queue()
    
    thread = threading.Thread(target=self._worker, args=(self._queue,))
    thread.start()
    
    # ... setup modal ...
    
def modal(self, context, event):
    if event.type == "TIMER":
        # Process all messages from queue
        while not self._queue.empty():
            msg = self._queue.get()
            # Update UI with msg
```

**Key differences:**

| Pattern | Use For | UI Blocking |
|---------|---------|-------------|
| Simple threading | I/O operations (file read) | No |
| Simple threading | CPU-intensive work | **YES** (GIL) |
| **Modal operator** | CPU-intensive work | **No** |
| Multiprocessing | Heavy CPU work | No |

---

## Quick Diagnostic Checklist

```bash
# 1. Check Python environment
uv run python -c "import sys; print(sys.executable)"

# 2. Check NumPy version
uv run python -c "import numpy; print(numpy.__version__)"
# Should be 1.x, not 2.x

# 3. Check PyTorch/CUDA
uv run python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# 4. Check faster-whisper
uv run python -c "import faster_whisper; print(faster_whisper.__version__)"

# 5. Verify model cache
ls -la /path/to/addon/models/
```

---

## Related Documentation

- [How-To Guides](./how-to-guides.md) - Step-by-step procedures
- [Architecture Patterns](./architecture-patterns.md) - Design patterns
- [Agent Context](./agent-context.md) - Quick reference
