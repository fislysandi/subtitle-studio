# Functional Style Review Roadmap

Date: 2026-02-25
Feature Task: `.tmp/tasks/functional-style-review/task.json`

## Evidence Sources

- Core/utils assessment: `.tmp/sessions/functional-style-review/review-core-utils.md`
- Operators/panels/props assessment: `.tmp/sessions/functional-style-review/review-ops-panels-props.md`
- Rubric and inventory: `.tmp/sessions/functional-style-review/rubric-and-inventory.md`

## Prioritization Model

- **No-risk**: refactors that should preserve behavior exactly (internal extraction, naming, pure helpers).
- **Behavior-sensitive**: changes touching event timing, selection resolution, modal cancellation, or live UI callbacks.

Effort scale:
- `S` = 0.5-1 day
- `M` = 1-3 days
- `L` = 3-5 days

## Now (Highest ROI)

1. Extract pure style patch planning from `props.py` and `operators/ops_strip_edit.py`  
   - Type: **No-risk**  
   - Effort: `M`  
   - Evidence: low scores/hotspots in `props.py` and `ops_strip_edit.py` from both review docs.  
   - Affected files: `props.py`, `operators/ops_strip_edit.py`, `utils/sequence_utils.py`.

2. Split transcription retry and VAD policy into pure decision helpers  
   - Type: **Behavior-sensitive**  
   - Effort: `M`  
   - Evidence: monolithic worker orchestration in `operators/ops_transcribe.py`, `core/transcriber.py`.  
   - Affected files: `operators/ops_transcribe.py`, `core/transcriber.py`.

3. Remove class-global callback state in download progress tracker  
   - Type: **Behavior-sensitive**  
   - Effort: `M`  
   - Evidence: violation #1 in core/utils review (`ProgressTracker._progress_callback`, `_cancel_event`).  
   - Affected files: `core/download_manager.py`, `operators/ops_model_download.py`.

## Next (Stability + Maintainability)

4. Convert dependency install flows to command-plan + boundary executor  
   - Type: **Behavior-sensitive**  
   - Effort: `L`  
   - Evidence: mixed concerns and broad exception paths in `operators/ops_dependencies.py` and `core/dependency_manager.py`.  
   - Affected files: `operators/ops_dependencies.py`, `operators/ops_dependency_download.py`, `core/dependency_manager.py`.

5. Isolate selection/sync pure transforms from Blender mutators  
   - Type: **Behavior-sensitive**  
   - Effort: `L`  
   - Evidence: low functional score and mutation density in `utils/sequence_utils.py`; coupling with UI sync paths.  
   - Affected files: `utils/sequence_utils.py`, `props.py`, `operators/ops_strip_edit.py`.

6. Replace print/error side-channeling with typed result envelopes  
   - Type: **No-risk**  
   - Effort: `S`  
   - Evidence: print-based error channeling noted in `core/transcriber.py`, `core/dependency_manager.py`.  
   - Affected files: `core/transcriber.py`, `core/dependency_manager.py`, `operators/ops_dependencies.py`.

## Later (Polish and Consistency)

7. Make panel rendering more declarative via section descriptors  
   - Type: **No-risk**  
   - Effort: `S`  
   - Evidence: maintainability hotspot in `panels/main_panel.py` long draw family.  
   - Affected files: `panels/main_panel.py`, `panels/main_panel_sections.py`.

8. Split `ops_strip_edit.py` into feature-focused operator modules  
   - Type: **No-risk** (if moves only) then **Behavior-sensitive** (if logic changes)  
   - Effort: `M`  
   - Evidence: 900+ LOC concentration and duplicated mutation logic.  
   - Affected files: `operators/ops_strip_edit.py`, `operators/__init__.py`.

9. Separate path-resolution helpers from filesystem mutation in file utils  
   - Type: **No-risk**  
   - Effort: `S`  
   - Evidence: hidden side effects in utility getters from core/utils review.  
   - Affected files: `utils/file_utils.py`, `hardening/path_safety.py`.

## Recommended Execution Order

1. `props.py` and strip style extraction
2. transcription policy extraction
3. download progress state deglobalization
4. dependency install architecture cleanup
5. sequence sync transform split
6. panel and utility polish

## Validation Expectations per Roadmap Item

- Unit tests for pure helper outputs (input->output only)
- Existing hardening suite remains green
- Blender runtime sanity checks for modal operations and strip editing paths
