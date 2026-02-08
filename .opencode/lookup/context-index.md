<!-- Context: subtitle_editor/lookup | Priority: high | Version: 1.0 | Updated: 2026-02-08 -->
# Lookup: Subtitle Studio Context Catalog

**Purpose**: Point agents to every existing `.opencode/` document so they can dive into the right sections without guessing.

| File | Sections to Read | Immediate Use |
|------|------------------|----------------|
| `.opencode/context.md` | Project overview, Blender 5.0 API changes, dependency list, code standards | Learn the current stack (Blender 5.0, faster-whisper, torch, pysubs2, onnxruntime) before coding.
| `.opencode/agent-context.md` | Module separation, UI guidelines, async/modal patterns, dependency manager snippet, UV commands | Follow this when building operators or rewriting dependency installers; it also lists the modal operator template.
| `.opencode/architecture-patterns.md` | “Dependency Management Architecture” and download flow diagrams, modal operator diagrams | Reference when reworking install/system flows or verifying download logic.
| `.opencode/troubleshooting.md` | Dependency Installation, GPU detection, modal operator blocking, cleanup instructions | Use as first stop for errors during installs, GPU checks, or blocking downloads.
| `.opencode/how-to-guides.md` | Step-by-step commands for testing, dependency commands, release hints (sections around `uv run test`, dependency management) | Follow when automating tests or documenting release/hot-reload steps.

**Documentation to Refresh**:
- `README.md` and `PROJECT_STATE.md` should mention the UV-first dependency commands and explicitly note that the previous `libs/` bundle has been removed so all installs happen at runtime.
- `PROJECT_STATE.md` also needs to call out the new release process via `uv run release subtitle_editor` and `release.py` so this context stays current.

## 📂 Codebase References

**Context Files**:
- `addons/subtitle_editor/.opencode/context.md` – High-level standards and dependency list.
- `addons/subtitle_editor/.opencode/agent-context.md` – Deep agent playbook with code samples.
- `addons/subtitle_editor/.opencode/architecture-patterns.md` – Diagrams and architecture sections (dependency mgmt, modal ops).
- `addons/subtitle_editor/.opencode/troubleshooting.md` – Error patterns and dependency fixes.
- `addons/subtitle_editor/.opencode/how-to-guides.md` – Procedural commands for daily work.
