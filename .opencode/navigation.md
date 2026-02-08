<!-- Context: subtitle_editor/navigation | Priority: critical | Version: 1.0 | Updated: 2026-02-08 -->
# Subtitle Studio Context Map

**Purpose**: Surface the technical overview, dependency architecture, and release expectations so agents onboard quickly.

---

## Quick Navigation

### Concepts
| File | Description | Priority |
|------|-------------|----------|
| [concepts/technical-overview.md](concepts/technical-overview.md) | Architecture, layout, and UV-focused dependency stance | critical |

### Guides
| File | Description | Priority |
|------|-------------|----------|
| [guides/dependency-management.md](guides/dependency-management.md) | UV-first install flow, verification, and why there is no `libs/` bundle | high |
| [guides/release-process.md](guides/release-process.md) | Release commands, packaging script, and coordination with framework tooling | high |

### Lookup
| File | Description | Priority |
|------|-------------|----------|
| [lookup/context-index.md](lookup/context-index.md) | Directory of existing context files and sections for each subsystem | high |

---

## Loading Strategy

1. Read `concepts/technical-overview.md` to understand the addon layout, workflows, and dependency rationale.
2. Follow `guides/dependency-management.md` when adjusting installs or docs; it links to `core/dependency_manager.py` and the dependency operators.
3. Use `guides/release-process.md` for packaging work before running `uv run release subtitle_editor`.
4. Reference `lookup/context-index.md` whenever deeper `.opencode/` documents are needed (agent-context, architecture patterns, troubleshooting).

---

## 📂 Codebase References

**Primary References**
- `addons/subtitle_editor/PROJECT_STATE.md` - Current feature inventory, commands, and dependency history.
- `release.py` - Packages the addon with `framework.release_addon()` (see `framework.py` for behavior).
- `addons/subtitle_editor/__init__.py` - Entry point that wires up the framework auto-registration and `scene.subtitle_editor` pointer.
