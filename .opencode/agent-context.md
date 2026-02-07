# Agent Development Context - Subtitle Editor Addon

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
5. **Blocking operations** - Use threading + timers for heavy work

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

## 📚 External Resources

- **Faster Whisper**: https://github.com/SYSTRAN/faster-whisper
- **Blender Python API**: https://docs.blender.org/api/current/
- **PyTorch**: https://pytorch.org/docs/stable/
