<!-- Context: subtitle_editor/guides | Priority: high | Version: 1.0 | Updated: 2026-02-08 -->
# Guide: Dependency Management Flow

**Core Idea**: Subtitle Studio installs packages on demand via UV (with pip fallback) instead of bundling `libs/` or shipping a static dependency tree.

**Key Steps**:
1. `operators/ops_dependencies.py` calls `DependencyManager.get_install_command()` to resolve UV or fall back to pip, always targeting Blender's `sys.executable`.
2. Install commands draw from locked `pyproject.toml`/`uv.lock` entries (`faster-whisper`, `pysubs2`, `onnxruntime`, and any extras) and honor `numpy<2.0` as a constraint.
3. Verification and GPU checks live in the same modal operators (see `subtitle.check_dependencies` and `subtitle.check_gpu`), so installations are rerun until `addons/subtitle_editor/.venv` contains the requested modules.
4. When documentation references dependency steps (e.g., `PROJECT_STATE.md`, `README.md`), call out that `libs/` is abandoned and the UI uses UV/pip paths.

**Key Points**:
- Dependencies are UV-first but pip fallback ensures compatibility if `uv` cannot be bootstrapped.
- No vendored `libs/` directory remains; the new workflow replaces `core/dependencies.py` entirely and relies on the framework's dependency commands (`uv run addon-deps ...`).
- Modal operators keep Blender responsive, streaming progress via `context.window_manager` and `props.deps_install_status`.
- Document the UV steps in onboarding docs (see `PROJECT_STATE.md` sections "Phase 1" and "Available Commands").

**Quick Example**:
```python
cmd = DependencyManager.get_install_command(
    ["faster-whisper", "pysubs2>=1.8.0"],
    constraint="numpy<2.0",
)
subprocess.run(cmd, check=True)
```

**Reference**: Revise `PROJECT_STATE.md` and `README.md` so they mention the UV-first installer and removal of `libs/` deployment artifacts.

**Related**:
- `concepts/technical-overview.md`
- `lookup/context-index.md`

## 📂 Codebase References

**Implementation**:
- `addons/subtitle_editor/core/dependency_manager.py` – UV discovery, auto-bootstrapping, and install command builder.
- `addons/subtitle_editor/operators/ops_dependencies.py` – Blender operators that use the command and update UI state.

**Configuration**:
- `addons/subtitle_editor/pyproject.toml` – Declares the dependency list.
- `addons/subtitle_editor/uv.lock` – Locks the versions shipped by UV.
