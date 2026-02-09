# Subtitle Studio Code Review Report

**Context:** Deep review for Blender 5.0 API compatibility, thread safety, runtime errors, and high-risk issues in `subtitle_editor`.

## Findings (Security First)

### Security
- **[Medium | Security] Insecure temp file creation**
  - **Where:** `addons/subtitle_editor/core/transcriber.py:249`
  - **Issue:** `tempfile.mktemp()` is vulnerable to race conditions.
  - **Impact:** Potential overwrite or injection into a predictable temp file path.
  - **Fix:** Use `NamedTemporaryFile(delete=False)` or `mkstemp()`.
  - **Suggested diff:**
    ```diff
    --- a/addons/subtitle_editor/core/transcriber.py
    +++ b/addons/subtitle_editor/core/transcriber.py
    @@
     -        if output_path is None:
     -            output_path = tempfile.mktemp(suffix=".wav")
     +        if output_path is None:
     +            fd, output_path = tempfile.mkstemp(suffix=".wav")
     +            os.close(fd)
    ```

### High
- **[High | Thread Safety] Background threads mutating Blender properties**
  - **Where:** `addons/subtitle_editor/operators/ops_dependencies.py:240`, `:361`
  - **Issue:** Background threads write to `props.*` directly.
  - **Impact:** Blender data access from threads can crash or corrupt state.
  - **Fix:** Queue updates and apply via `bpy.app.timers.register(...)` or use a modal operator.
  - **Suggested diff (pattern):**
    ```diff
    --- a/addons/subtitle_editor/operators/ops_dependencies.py
    +++ b/addons/subtitle_editor/operators/ops_dependencies.py
    @@
     -        props.deps_install_status = "Starting installation..."
     +        def _set_status(msg):
     +            def _apply():
     +                props = context.scene.subtitle_editor
     +                props.deps_install_status = msg
     +                return None
     +            bpy.app.timers.register(_apply, first_interval=0.0)
     +        _set_status("Starting installation...")
    ```

- **[High | Correctness] Writing to `frame_final_*` (read-only)**
  - **Where:** `addons/subtitle_editor/props.py:120-139`
  - **Issue:** `_update_frames` assigns `frame_final_start/end`.
  - **Impact:** Update callbacks can raise `AttributeError`.
  - **Fix:** Set `frame_start` and `frame_duration`, then read `frame_final_*` for display.
  - **Suggested diff:**
    ```diff
    --- a/addons/subtitle_editor/props.py
    +++ b/addons/subtitle_editor/props.py
    @@
     -                target_strip.frame_final_start = new_start
     -                target_strip.frame_final_end = end
     +                target_strip.frame_start = new_start
     +                target_strip.frame_duration = max(1, end - new_start)
     @@
     -                target_strip.frame_final_end = new_end
     -                target_strip.frame_final_start = start
     +                target_strip.frame_start = start
     +                target_strip.frame_duration = max(1, new_end - start)
    ```

- **[High | Performance/UX] CPU-bound transcription uses plain threading**
  - **Where:** `addons/subtitle_editor/operators/ops_transcribe.py:58-156`
  - **Issue:** Heavy transcription runs in a thread with only timers.
  - **Impact:** UI can freeze due to GIL contention.
  - **Fix:** Move transcription into a modal operator or multiprocessing.

### Medium
- **[Medium | Correctness] FPS math ignores `fps_base`**
  - **Where:** `addons/subtitle_editor/operators/ops_transcribe.py:47-50`, `:208-216`, `addons/subtitle_editor/operators/ops_import_export.py:35-44`, `:99-103`
  - **Issue:** Using `scene.render.fps` only; effective FPS is `fps / fps_base`.
  - **Impact:** Subtitle timing drift when `fps_base != 1.0`.
  - **Fix:** Use `fps = scene.render.fps / (scene.render.fps_base or 1.0)`.

- **[Medium | Correctness] Import ignores configured subtitle channel**
  - **Where:** `addons/subtitle_editor/operators/ops_import_export.py:31-44`
  - **Issue:** Import hard-codes `channel = 3`.
  - **Impact:** Imported strips may not appear in the list or align with speaker channels.
  - **Fix:** Use `scene.subtitle_editor.subtitle_channel`.

- **[Medium | Correctness] Operator returns no status**
  - **Where:** `addons/subtitle_editor/operators/ops_strip_edit.py:379-407`
  - **Issue:** `SUBTITLE_OT_update_text.execute()` never returns a status set.
  - **Impact:** Blender treats this as a failed operator or logs errors.
  - **Fix:** Return `{"FINISHED"}` at the end.

- **[Medium | Compatibility] Use of `sequence_editor.strips`**
  - **Where:** `addons/subtitle_editor/utils/sequence_utils.py:16-27` and other operators
  - **Issue:** Project standard recommends `.sequences` for Blender 5.0; `strips` may not be supported.
  - **Impact:** Potential AttributeError at runtime.
  - **Fix:** Verify Blender 5.0 API; migrate to `.sequences` if needed.

### Low
- **[Low | Correctness/UI] Cached model check ignores file size**
  - **Where:** `addons/subtitle_editor/utils/file_utils.py:40-49`
  - **Issue:** Only checks existence, not size.
  - **Impact:** UI shows “Model Ready” even for partial downloads.
  - **Fix:** Mirror DownloadManager’s size checks.

- **[Low | Maintainability] Duplicate unreachable code**
  - **Where:** `addons/subtitle_editor/operators/ops_dependencies.py:119-215`
  - **Issue:** Duplicate dependency check block after `return {"FINISHED"}`.
  - **Impact:** Dead code, confusion during maintenance.
  - **Fix:** Remove the duplicate block.

## Summary of Top Issues
- Thread-unsafe property updates in dependency installers can crash Blender (`ops_dependencies.py`).
- `frame_final_*` writes likely throw at runtime when editing timings (`props.py`).
- CPU-heavy transcription runs in a plain thread, risking UI freezes (`ops_transcribe.py`).
- Insecure temp file creation via `tempfile.mktemp` (`core/transcriber.py`).
