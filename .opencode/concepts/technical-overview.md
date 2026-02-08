<!-- Context: subtitle_editor/concepts | Priority: critical | Version: 1.0 | Updated: 2026-02-08 -->
# Concept: Subtitle Studio Technical Overview

**Core Idea**: AI-powered subtitle transcription/editing lives inside `addons/subtitle_editor/` with framework auto-load, Blender-friendly operators, and UV-managed dependencies (no embedded `libs/` bundle).

**Key Points**:
- Core logic lives in `core/` (no `bpy`), operators/panels live in their directories, and `scene.subtitle_editor` keeps shared state.
- Dependency work flows through `core/dependency_manager.py` → modal operators (see `operators/ops_dependencies.py`) that install via UV or pip.
- `pyproject.toml` + `uv.lock` lock the ML stack (`faster-whisper`, `pysubs2`, `onnxruntime`) and the addon now installs on demand rather than shipping `libs/`.
- Release work leans on repository-wide tooling (`release.py` → `framework.release_addon`) plus `uv run release subtitle_editor` for packaging.
- `PROJECT_STATE.md` captures features, commands, and the new dependency history for quick onboarding.

**Quick Example**:
```python
def draw(self, context):
    props = context.scene.subtitle_editor
    row = self.layout.row()
    row.prop(props, "model")
    row.operator("subtitle.download_model", text="Download")
```

**Reference**: `addons/subtitle_editor/PROJECT_STATE.md` covers layout, commands, and migration history for this addon (see sections "Available Commands" and "File Structure").

**Related**:
- `guides/dependency-management.md`
- `guides/release-process.md`
- `.opencode/agent-context.md` for the deep agent playbook

## 📂 Codebase References

**Implementation**:
- `addons/subtitle_editor/__init__.py` – Framework auto-load + `PointerProperty` registration.
- `addons/subtitle_editor/panels/main_panel.py` – Main UI with dependency and model controls.

**Supporting Files**:
- `addons/subtitle_editor/core/dependency_manager.py` – UV-first installation helpers.
- `addons/subtitle_editor/operators/ops_dependencies.py` – Modal operators that orchestrate installs and checks.
