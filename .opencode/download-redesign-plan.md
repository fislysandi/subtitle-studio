# Model Download System - Redesign Plan

## 🚨 Critical Issues with Current Implementation

### 1. **Wrong Download Method** (CRITICAL)
**Current:** `WhisperModel(model_name, ...)` 
- Loads ENTIRE model into memory just to download it
- Memory usage: 39MB (tiny) to 1.5GB (large-v3) wasted
- Takes 2-3x longer than necessary
- No actual download progress - just loading progress

**Should Use:** `huggingface_hub.snapshot_download()`
- Downloads files only, no memory loading
- Real file-by-file progress
- Supports resume and caching
- Proper cancelation support

### 2. **No Real Progress Tracking**
**Current:** Hardcoded progress values (0.1, 0.2, 1.0)
- Fake progress that doesn't reflect reality
- User sees 20% then jumps to 100%
- No way to know actual download status

**Should Use:** HuggingFace's `tqdm` callbacks or custom callbacks
- Real bytes downloaded / total bytes
- File-by-file progress
- Actual remaining time estimation

### 3. **No Cancelation Support**
**Current:** Cannot stop download once started
- User must wait for completion or kill Blender
- Bad UX for large models on slow connections

**Should Use:** Threading.Event() for cancel signals
- Cancel button stops download cleanly
- Partial downloads can be resumed

### 4. **No Download Integrity**
**Current:** Just checks if folder exists
- Corrupted downloads not detected
- Partial downloads not handled
- No checksum verification

**Should Use:** huggingface_hub's built-in verification
- SHA256 checksums for all files
- Resume partial downloads
- Auto-retry on network errors

### 5. **Mixed Concerns**
**Current:** UI logic + download logic in one file
- Hard to test
- Hard to maintain
- Violates single responsibility principle

**Should Use:** Separate download manager class
- Core/download_manager.py - Pure download logic
- operators/ops_model_download.py - UI only

---

## ✅ Proposed Architecture

### Core Components

```
subtitle_editor/
├── core/
│   ├── download_manager.py     # NEW: Pure download logic
│   └── transcriber.py
```

### 1. Download Manager (core/download_manager.py)

```python
"""Pure Python download manager - no Blender dependencies"""

import os
import threading
from typing import Optional, Callable
from pathlib import Path

try:
    from huggingface_hub import snapshot_download, hf_hub_download
    from huggingface_hub.utils import RepositoryNotFoundError
    HAS_HF = True
except ImportError:
    HAS_HF = False


class DownloadManager:
    """
    Manages model downloads with real progress tracking and cancel support.
    No Blender dependencies - pure Python.
    """
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cancel_event = threading.Event()
        self.current_download: Optional[threading.Thread] = None
        
    def download_model(
        self,
        model_name: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        token: Optional[str] = None
    ) -> bool:
        """
        Download a Whisper model from HuggingFace.
        
        Args:
            model_name: Model name (e.g., 'tiny', 'base', 'large-v3')
            progress_callback: Called with (progress_0_to_1, status_message)
            token: Optional HuggingFace token for authentication (None = anonymous download)
            
        Returns:
            True if successful, False if cancelled or failed
            
        Note:
            Token is OPTIONAL. Downloads work without authentication, but having a token
            provides higher rate limits and faster downloads. Users can get a free token
            at https://huggingface.co/settings/tokens
        """
        if not HAS_HF:
            raise ImportError("huggingface_hub not installed")
        
        # Map model names to HF repo IDs
        repo_id = self._get_repo_id(model_name)
        
        # Check if already downloaded
        if self._is_model_cached(model_name):
            if progress_callback:
                progress_callback(1.0, f"Model {model_name} already cached")
            return True
        
        # Custom progress callback for huggingface_hub
        def hf_progress_callback(files, total_files, downloaded_bytes, total_bytes):
            if self.cancel_event.is_set():
                raise InterruptedError("Download cancelled by user")
            
            progress = downloaded_bytes / total_bytes if total_bytes > 0 else 0
            file_name = files[-1] if files else "unknown"
            
            if progress_callback:
                progress_callback(
                    progress,
                    f"Downloading {file_name} ({downloaded_bytes}/{total_bytes} bytes)"
                )
        
        try:
            # Download using huggingface_hub
            snapshot_download(
                repo_id=repo_id,
                cache_dir=self.cache_dir,
                token=token,
                local_files_only=False,
                tqdm_class=None,  # Disable default tqdm
                # Use custom callback (may need to subclass or use wrapper)
            )
            
            return True
            
        except InterruptedError:
            # User cancelled
            return False
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            raise
    
    def cancel_download(self):
        """Cancel the current download"""
        self.cancel_event.set()
        
    def _get_repo_id(self, model_name: str) -> str:
        """Map model name to HuggingFace repo ID"""
        repo_map = {
            "tiny": "Systran/faster-whisper-tiny",
            "tiny.en": "Systran/faster-whisper-tiny.en",
            "base": "Systran/faster-whisper-base",
            "base.en": "Systran/faster-whisper-base.en",
            "small": "Systran/faster-whisper-small",
            "small.en": "Systran/faster-whisper-small.en",
            "medium": "Systran/faster-whisper-medium",
            "medium.en": "Systran/faster-whisper-medium.en",
            "large-v1": "Systran/faster-whisper-large-v1",
            "large-v2": "Systran/faster-whisper-large-v2",
            "large-v3": "Systran/faster-whisper-large-v3",
            "large": "Systran/faster-whisper-large-v3",
            "distil-small.en": "Systran/faster-distil-whisper-small.en",
            "distil-medium.en": "Systran/faster-distil-whisper-medium.en",
            "distil-large-v2": "Systran/faster-distil-whisper-large-v2",
            "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
            "distil-large-v3.5": "distil-whisper/distil-large-v3.5-ct2",
            "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
            "turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
        }
        return repo_map.get(model_name, f"Systran/faster-whisper-{model_name}")
    
    def _is_model_cached(self, model_name: str) -> bool:
        """Check if model is already fully cached"""
        # Check huggingface_hub cache structure
        # Models are stored in cache_dir/models--{org}--{repo}/snapshots/{hash}
        repo_id = self._get_repo_id(model_name)
        cache_path = self.cache_dir / f"models--{repo_id.replace('/', '--')}"
        return cache_path.exists()
    
    def get_model_size(self, model_name: str) -> Optional[int]:
        """Get model size in bytes from remote (without downloading)"""
        # Use huggingface_hub to get model info
        pass
```

### 2. Updated Operator (operators/ops_model_download.py)

```python
"""
Model Download Operator using Modal Operator pattern.
UI only - all download logic in core/download_manager.py
"""

import bpy
import threading
import queue
from bpy.types import Operator
from ..core.download_manager import DownloadManager
from ..utils import file_utils


class SUBTITLE_OT_download_model(Operator):
    """Download the selected Whisper model with real progress"""

    bl_idname = "subtitle.download_model"
    bl_label = "Download Model"
    bl_description = "Download the selected Whisper model"
    bl_options = {"REGISTER", "UNDO"}

    _timer = None
    _thread = None
    _queue = None
    _download_manager = None
    _is_complete = False
    _model_name = None

    def modal(self, context, event):
        """Process download updates from thread"""
        props = context.scene.subtitle_editor

        if event.type == "TIMER":
            # Process messages from worker thread
            while not self._queue.empty():
                try:
                    msg = self._queue.get_nowait()
                    msg_type = msg.get("type")

                    if msg_type == "progress":
                        progress = msg.get("value", 0.0)
                        status = msg.get("text", "")
                        props.model_download_progress = progress
                        props.model_download_status = status
                        # Update Blender's progress bar
                        wm = context.window_manager
                        wm.progress_update(int(progress * 100))
                        
                    elif msg_type == "complete":
                        success = msg.get("success", False)
                        if success:
                            self.report({"INFO"}, f"Model {self._model_name} ready!")
                        self._is_complete = True
                        
                    elif msg_type == "error":
                        self.report({"ERROR"}, msg.get("text", "Download failed"))
                        self._is_complete = True
                        
                except queue.Empty:
                    break

            # Force UI redraw
            for area in context.screen.areas:
                area.tag_redraw()

        if self._is_complete:
            self.cancel(context)
            return {"FINISHED"}

        return {"PASS_THROUGH"}

    def execute(self, context):
        """Start modal operator and download"""
        props = context.scene.subtitle_editor
        self._model_name = props.model

        # Initialize
        self._queue = queue.Queue()
        self._is_complete = False
        props.is_downloading_model = True
        props.model_download_progress = 0.0
        
        # Create download manager
        cache_dir = file_utils.get_addon_models_dir()
        self._download_manager = DownloadManager(cache_dir)

        # Get HF token from preferences
        preferences = bpy.context.preferences.addons.get("subtitle_editor")
        hf_token = None
        if preferences and hasattr(preferences, "preferences"):
            hf_token = preferences.preferences.hf_token

        # Start download thread
        self._thread = threading.Thread(
            target=self._download_worker,
            args=(self._model_name, hf_token)
        )
        self._thread.daemon = True
        self._thread.start()

        # Setup modal operator
        wm = context.window_manager
        wm.progress_begin(0, 100)
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        return {"RUNNING_MODAL"}

    def cancel(self, context):
        """Clean up"""
        if self._download_manager:
            self._download_manager.cancel_download()
        
        if self._timer:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            wm.progress_end()
            self._timer = None
            
        props = context.scene.subtitle_editor
        props.is_downloading_model = False

    def _download_worker(self, model_name: str, hf_token: Optional[str]):
        """Download in background thread"""
        try:
            def progress_callback(progress: float, status: str):
                self._queue.put({
                    "type": "progress",
                    "value": progress,
                    "text": status
                })
            
            success = self._download_manager.download_model(
                model_name,
                progress_callback=progress_callback,
                token=hf_token
            )
            
            self._queue.put({"type": "complete", "success": success})
            
        except Exception as e:
            self._queue.put({"type": "error", "text": str(e)})
            self._queue.put({"type": "complete", "success": False})


classes = [SUBTITLE_OT_download_model]
```

### 3. UI Improvements

**Add Cancel Button:**
```python
# In panel UI
if props.is_downloading_model:
    row = box.row(align=True)
    row.prop(props, "model_download_progress", text="Download Progress", slider=True)
    row.operator("subtitle.cancel_download", text="Cancel", icon="CANCEL")
else:
    row.operator("subtitle.download_model", text="Download", icon="IMPORT")
```

**Add Model Size Info:**
```python
# Show estimated size before download
model_sizes = {
    "tiny": "39 MB",
    "base": "74 MB",
    "small": "244 MB",
    "medium": "769 MB",
    "large-v3": "1550 MB",
}
# Show in UI next to model dropdown
```

---

## 🔐 Authentication (Optional)

### Design Principle: Token is OPTIONAL, Not Required

The download system works **completely without authentication**:

**Without Token (Default):**
- ✅ Downloads work normally
- ✅ All models available
- ⚠️ Lower rate limits (may be slower during peak times)
- ⚠️ Warning message about unauthenticated requests

**With Token (Optional):**
- ✅ Higher rate limits
- ✅ Faster downloads
- ✅ No warnings
- ✅ Better reliability

### Implementation:
```python
# In download_manager.py - token is optional parameter
def download_model(self, model_name, token=None, ...):
    snapshot_download(
        repo_id=repo_id,
        token=token,  # None = anonymous download
        ...
    )

# In UI - clearly mark as optional
row.label(text="Hugging Face Token (Optional):", icon="INFO")
row.label(text="Get faster downloads with a free token")
```

### User Flow:
1. User clicks "Download" without token → Works fine
2. User sees warning about rate limits → Optional improvement
3. User can add token anytime in preferences
4. Token is saved but never required

---

## 📋 Implementation Steps

### Phase 1: Create Download Manager
1. Create `core/download_manager.py`
2. Implement `DownloadManager` class
3. Test with sample downloads
4. Add unit tests

### Phase 2: Update Operator
1. Rewrite `ops_model_download.py` to use download manager
2. Add real progress tracking
3. Add cancel button
4. Test modal operator

### Phase 3: Add Dependencies
1. Add `huggingface_hub` to pyproject.toml
2. Update uv.lock
3. Document new dependency

### Phase 4: UI Enhancements
1. Add model size display
2. Add cancel button
3. Improve status messages
4. Add estimated time remaining

---

## 🎯 Benefits

1. **Real Progress**: Shows actual bytes downloaded, not fake percentages
2. **Cancel Support**: Users can stop downloads mid-way
3. **No Memory Waste**: Downloads files without loading into RAM
4. **Resume Support**: Can continue partial downloads
5. **Better Errors**: Clear error messages from huggingface_hub
6. **Testable**: Download manager can be unit tested
7. **Maintainable**: Separated concerns (UI vs Logic)

---

## ⚠️ Dependencies to Add

```toml
# pyproject.toml
dependencies = [
    "faster-whisper",
    "huggingface_hub>=0.19.0",  # NEW
    "pysubs2>=1.8.0",
    "onnxruntime>=1.24.1",
]
```

## Migration Notes

- Old downloads remain compatible (huggingface_hub uses same cache)
- Can remove progress bar from custom UI (use Blender's built-in only)
- Add setting for "auto-download missing models"

---

**Estimated Time**: 4-6 hours  
**Priority**: HIGH - Current implementation is fundamentally broken  
**Impact**: Users will see real progress, can cancel, and downloads will be faster
