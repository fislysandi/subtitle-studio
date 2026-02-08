# How-To Guides - Subtitle Studio Addon

Step-by-step procedures for common development tasks.

---

## Table of Contents

1. [Adding a New Operator (Modal Pattern)](#adding-a-new-operator)
2. [Adding a New Property to the UI](#adding-a-new-property)
3. [Adding a New Panel Section](#adding-a-new-panel-section)
4. [Implementing File Downloads with Progress](#implementing-file-downloads)
5. [Testing with Hot-Reload](#testing-with-hot-reload)
6. [Adding a New Dependency](#adding-a-new-dependency)
7. [Debugging Common Issues](#debugging-common-issues)

---

## Adding a New Operator

### Modal Operator Pattern (For Non-Blocking Operations)

Use modal operators for heavy operations (downloads, long computations) to keep Blender responsive.

**File:** `operators/ops_my_feature.py`

```python
"""My Feature Operator - Modal Pattern Example"""

import bpy
import threading
from bpy.types import Operator


class SUBTITLE_OT_my_feature(Operator):
    """Description of what this operator does"""
    
    bl_idname = "subtitle.my_feature"
    bl_label = "My Feature"
    bl_description = "Does something without blocking the UI"
    bl_options = {"REGISTER"}
    
    # Instance variables for modal state
    _timer = None
    _thread = None
    _finished = False
    
    def invoke(self, context, event):
        """Start modal operator via invoke (required for interactive behavior)"""
        
        # Initialize state
        self._finished = False
        
        # Start background thread
        self._thread = threading.Thread(
            target=self._worker,
            daemon=True
        )
        self._thread.start()
        
        # Setup modal operator
        wm = context.window_manager
        wm.progress_begin(0, 100)
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        
        return {"RUNNING_MODAL"}
    
    def modal(self, context, event):
        """Called repeatedly by Blender's event loop"""
        
        # Handle ESC key for cancellation
        if event.type == "ESC":
            self._cleanup(context)
            self.report({"WARNING"}, "Operation cancelled")
            return {"CANCELLED"}
        
        # Handle timer events
        if event.type == "TIMER":
            # Check completion
            if self._finished:
                self._cleanup(context)
                self.report({"INFO"}, "Operation complete!")
                return {"FINISHED"}
            
            # Update progress if needed
            # self._update_progress(context)
            
            # Force UI redraw
            for area in context.screen.areas:
                area.tag_redraw()
        
        # Keep Blender responsive
        return {"PASS_THROUGH"}
    
    def _worker(self):
        """Background thread - do heavy work here"""
        # Your heavy computation here
        import time
        time.sleep(2)  # Example
        self._finished = True
    
    def _cleanup(self, context):
        """Clean up timer and state"""
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            context.window_manager.progress_end()
            self._timer = None
    
    def cancel(self, context):
        """Called when operator is cancelled externally"""
        self._cleanup(context)


classes = [SUBTITLE_OT_my_feature]
```

### Standard Operator Pattern (For Quick Operations)

For operations that complete quickly (< 1 second):

```python
class SUBTITLE_OT_quick_op(Operator):
    """Quick operation that completes immediately"""
    
    bl_idname = "subtitle.quick_op"
    bl_label = "Quick Operation"
    bl_description = "Does something quickly"
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        # Do work here
        self.report({"INFO"}, "Done!")
        return {"FINISHED"}


classes = [SUBTITLE_OT_quick_op]
```

---

## Adding a New Property

### Step 1: Add to Property Group

**File:** `props.py`

```python
class SubtitleEditorProperties(PropertyGroup):
    # ... existing properties ...
    
    # Add new property with type annotation
    my_new_setting: BoolProperty(
        name="My Setting",
        description="What this setting does",
        default=False
    )
    
    my_float_value: FloatProperty(
        name="Float Value",
        description="A numeric value",
        default=0.5,
        min=0.0,
        max=1.0,
        subtype="FACTOR"
    )
```

### Common Property Types

```python
# Boolean (checkbox)
enabled: BoolProperty(name="Enabled", default=True)

# Integer with limits
quality: IntProperty(name="Quality", default=5, min=1, max=10)

# Float with slider
threshold: FloatProperty(
    name="Threshold",
    default=0.5,
    min=0.0,
    max=1.0,
    subtype="FACTOR"  # Shows as slider
)

# String
token: StringProperty(name="Token", default="")

# Enum (dropdown)
mode: EnumProperty(
    name="Mode",
    items=[
        ("SIMPLE", "Simple", "Basic mode"),
        ("ADVANCED", "Advanced", "Advanced mode"),
    ],
    default="SIMPLE"
)

# Color
my_color: FloatVectorProperty(
    name="Color",
    subtype="COLOR",
    size=3,
    min=0.0,
    max=1.0,
    default=(1.0, 1.0, 1.0)
)
```

### Step 2: Add to Panel UI

**File:** `panels/main_panel.py`

```python
def draw(self, context):
    layout = self.layout
    props = context.scene.subtitle_editor
    
    # Simple property
    layout.prop(props, "my_new_setting")
    
    # In a box with label
    box = layout.box()
    box.label(text="My Section", icon="PREFERENCES")
    box.prop(props, "my_float_value")
    
    # Aligned row
    row = box.row(align=True)
    row.prop(props, "quality")
    row.prop(props, "threshold")
```

---

## Adding a New Panel Section

### Creating a New Panel

**File:** `panels/main_panel.py`

```python
class SEQUENCER_PT_my_section(Panel):
    """My Custom Panel Section"""
    
    bl_idname = "SEQUENCER_PT_my_section"
    bl_label = "My Section"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Subtitle Studio"
    
    @classmethod
    def poll(cls, context):
        """When to show this panel"""
        return context.scene is not None
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.subtitle_editor
        
        # Section content
        box = layout.box()
        box.label(text="Settings", icon="PREFERENCES")
        box.prop(props, "my_property")
        
        # Action button
        box.operator("subtitle.my_operator", icon="PLAY")
```

### Adding to Existing Panel

```python
class SEQUENCER_PT_whisper_panel(Panel):
    def draw(self, context):
        # ... existing code ...
        
        # Add new section at bottom
        box = col.box()
        box.label(text="My New Section", icon="NEW")
        box.prop(props, "my_setting")
        box.operator("subtitle.my_action")
```

---

## Implementing File Downloads

### Using DownloadManager (For Model Downloads)

**File:** `operators/ops_my_download.py`

```python
import bpy
import threading
from bpy.types import Operator
from ..core.download_manager import DownloadManager, DownloadStatus, create_download_manager


class SUBTITLE_OT_download_something(Operator):
    """Download something with progress"""
    
    bl_idname = "subtitle.download_something"
    bl_label = "Download"
    bl_options = {"REGISTER"}
    
    _timer = None
    _download_manager = None
    _thread = None
    _finished = False
    
    def invoke(self, context, event):
        props = context.scene.subtitle_editor
        
        # Create download manager
        cache_dir = "/path/to/cache"
        self._download_manager = create_download_manager(cache_dir)
        
        # Initialize UI state
        props.is_downloading = True
        props.download_progress = 0.0
        
        # Start download thread
        self._thread = threading.Thread(
            target=self._download_worker,
            args=("resource_name",),
            daemon=True
        )
        self._thread.start()
        
        # Setup modal
        wm = context.window_manager
        wm.progress_begin(0, 100)
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        
        return {"RUNNING_MODAL"}
    
    def modal(self, context, event):
        props = context.scene.subtitle_editor
        
        if event.type == "TIMER" and self._download_manager:
            # Poll progress
            progress = self._download_manager.get_progress()
            props.download_progress = progress.percentage
            props.download_status = progress.message
            
            # Update Blender progress bar
            context.window_manager.progress_update(
                int(progress.percentage * 100)
            )
            
            # Check if complete
            if progress.status in (
                DownloadStatus.COMPLETE,
                DownloadStatus.ERROR,
                DownloadStatus.CANCELLED
            ):
                self._cleanup(context)
                return {"FINISHED"}
            
            # Force redraw
            for area in context.screen.areas:
                area.tag_redraw()
        
        return {"PASS_THROUGH"}
    
    def _download_worker(self, resource_name):
        """Background thread"""
        self._download_manager.download(resource_name)
    
    def _cleanup(self, context):
        props = context.scene.subtitle_editor
        
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            context.window_manager.progress_end()
        
        props.is_downloading = False


classes = [SUBTITLE_OT_download_something]
```

---

## Testing with Hot-Reload

### Starting Hot-Reload Session

```bash
# Navigate to addon directory
cd /home/fislysandi/mainfiles/02\ work/06\ dev/Blender\ playground/blender-addon-framework/addons/subtitle_editor

# Start hot-reload testing
uv run test subtitle_editor
```

### Hot-Reload Workflow

1. **Start Blender** with the test command
2. **Make changes** to any Python file
3. **Save the file** (Ctrl+S)
4. **Changes auto-reload** in Blender

### What Gets Reloaded

| File Type | Reload Behavior |
|-----------|----------------|
| Operators | Auto-reloaded on save |
| Panels | Auto-reloaded on save |
| Properties | Auto-reloaded (may need panel refresh) |
| Core modules | Auto-reloaded on save |
| `__init__.py` | Requires manual restart |
| `config.py` | Requires manual restart |

### Testing Checklist

```bash
# 1. Start hot-reload
uv run test subtitle_editor

# 2. In Blender, open the addon panel
# 3. Make code changes
# 4. Save file
# 5. Verify changes appear in Blender
# 6. Test operator execution
# 7. Check System Console for errors (Window > Toggle System Console)
```

---

## Adding a New Dependency

### Step 1: Add to pyproject.toml

**File:** `pyproject.toml`

```toml
[project]
name = "subtitle-editor"
version = "1.0.0"
dependencies = [
    "faster-whisper>=1.0.0",
    "pysubs2>=1.8.0",
    "onnxruntime>=1.24.1",
    "new-package>=1.0.0",  # Add your new dependency
]
```

### Step 2: Lock Dependencies

```bash
# Generate/update uv.lock
uv lock

# Or sync directly
uv sync
```

### Step 3: Update Dependency Check

**File:** `operators/ops_dependencies.py`

```python
def check_dependencies():
    deps = {
        "faster_whisper": False,
        "torch": False,
        "pysubs2": False,
        "onnxruntime": False,
        "new_package": False,  # Add new check
    }
    
    # Add import check
    try:
        import new_package
        deps["new_package"] = True
    except ImportError:
        pass
    
    return deps
```

### Step 4: Add Property

**File:** `props.py`

```python
deps_new_package: BoolProperty(
    name="New Package",
    description="New package is installed",
    default=False
)
```

### Step 5: Update UI

**File:** `panels/main_panel.py`

```python
# Add to dependencies check display
if props.deps_new_package:
    row.label(text="New Package: Installed", icon="CHECKMARK")
else:
    row.label(text="New Package: Missing", icon="ERROR")
```

---

## Debugging Common Issues

### Enable System Console

**In Blender:** Window > Toggle System Console

This shows print statements and error traces.

### Adding Debug Prints

```python
def execute(self, context):
    print(f"[DEBUG] Starting {self.bl_idname}")
    print(f"[DEBUG] Context: {context}")
    print(f"[DEBUG] Scene: {context.scene.name}")
    
    # Your code here
    
    print("[DEBUG] Complete")
    return {"FINISHED"}
```

### Common Debug Patterns

```python
# Check if property exists
if hasattr(context.scene, "subtitle_editor"):
    print("[DEBUG] Property group exists")
else:
    print("[ERROR] Property group missing!")

# Check sequence editor
if context.scene.sequence_editor:
    print(f"[DEBUG] Strips: {len(context.scene.sequence_editor.strips)}")
else:
    print("[DEBUG] No sequence editor")

# Check selected strip
strip = sequence_utils.get_selected_strip(context)
print(f"[DEBUG] Selected strip: {strip}")
if strip:
    print(f"[DEBUG] Strip type: {strip.type}")
```

### Thread Debugging

```python
def _worker(self):
    import threading
    print(f"[DEBUG] Thread started: {threading.current_thread().name}")
    
    try:
        # Work here
        pass
    except Exception as e:
        import traceback
        print(f"[ERROR] Thread error: {e}")
        traceback.print_exc()
    
    print("[DEBUG] Thread complete")
```

---

## Related Documentation

- [Architecture Patterns](./architecture-patterns.md) - Design patterns reference
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions
- [Agent Context](./agent-context.md) - Quick reference for AI assistants
