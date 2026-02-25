"""Blender smoke checks for strip workflows and MetaStrip copy-style.

Run inside Blender (UI session) after enabling the subtitle_studio add-on.
This script prints explicit PASS/FAIL lines and exits non-zero on failure.
"""

from __future__ import annotations

import sys
from typing import Iterable, Optional

import bpy


PREFIX = "SmokeSubtitle"


def _print_result(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    suffix = f" :: {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")


def _strip_collection(scene):
    seq = scene.sequence_editor
    return getattr(seq, "strips", None) if seq else None


def _iter_text_strips(scene) -> Iterable:
    strips = _strip_collection(scene)
    if not strips:
        return []
    return [s for s in strips if getattr(s, "type", "") == "TEXT"]


def _find_text_strip(scene, name: str):
    for strip in _iter_text_strips(scene):
        if getattr(strip, "name", "") == name:
            return strip
    return None


def _find_text_strip_by_prefix(scene, name_prefix: str):
    for strip in _iter_text_strips(scene):
        if getattr(strip, "name", "").startswith(name_prefix):
            return strip
    return None


def _ensure_sequence_editor(scene) -> None:
    if not scene.sequence_editor:
        scene.sequence_editor_create()


def _clear_smoke_strips(scene) -> None:
    strips = _strip_collection(scene)
    if not strips:
        return
    for strip in list(strips):
        if getattr(strip, "type", "") != "TEXT":
            continue
        if getattr(strip, "name", "").startswith(PREFIX):
            strips.remove(strip)


def _set_selected(scene, targets) -> None:
    for strip in _iter_text_strips(scene):
        strip.select = False
    for strip in targets:
        if strip is not None:
            strip.select = True


def _sequencer_override() -> Optional[dict]:
    window = bpy.context.window
    if not window:
        return None
    screen = window.screen
    if not screen:
        return None
    for area in screen.areas:
        if area.type != "SEQUENCE_EDITOR":
            continue
        for region in area.regions:
            if region.type == "WINDOW":
                return {
                    "window": window,
                    "screen": screen,
                    "area": area,
                    "region": region,
                }
    return None


def _run_add_update_remove(scene) -> tuple[bool, str]:
    props = scene.subtitle_editor
    before_count = len(scene.text_strip_items)

    scene.frame_current = 120
    add_result = bpy.ops.subtitle.add_strip_at_cursor()
    if add_result != {"FINISHED"}:
        return False, f"add_strip_at_cursor returned {add_result}"

    bpy.ops.subtitle.refresh_list()
    if len(scene.text_strip_items) <= before_count:
        return False, "strip list count did not increase"

    new_item = scene.text_strip_items[scene.text_strip_items_index]
    strip = _find_text_strip(scene, new_item.name)
    if strip is None:
        return False, "new strip missing from sequencer"

    props.current_text = "Smoke add/update/remove"
    update_result = bpy.ops.subtitle.update_text()
    if update_result != {"FINISHED"}:
        return False, f"update_text returned {update_result}"
    if strip.text != props.current_text:
        return False, "updated text not applied"

    remove_result = bpy.ops.subtitle.remove_selected_strip()
    if remove_result != {"FINISHED"}:
        return False, f"remove_selected_strip returned {remove_result}"

    bpy.ops.subtitle.refresh_list()
    if strip.name and _find_text_strip(scene, strip.name) is not None:
        return False, "strip still exists after remove"

    return True, "add/update/remove workflow ok"


def _run_apply_style(scene) -> tuple[bool, str]:
    props = scene.subtitle_editor
    props.font_size = 47
    if hasattr(props, "use_outline_color"):
        props.use_outline_color = True
    if hasattr(props, "outline_color"):
        props.outline_color = (0.2, 0.9, 0.4)

    scene.frame_current = 200
    first = bpy.ops.subtitle.add_strip_at_cursor()
    scene.frame_current = 240
    second = bpy.ops.subtitle.add_strip_at_cursor()
    if first != {"FINISHED"} or second != {"FINISHED"}:
        return False, "could not create strips for apply_style"

    text_strips = sorted(
        [s for s in _iter_text_strips(scene) if s.name.startswith("Subtitle_")],
        key=lambda s: s.frame_final_start,
    )
    if len(text_strips) < 2:
        return False, "not enough text strips for apply_style"

    a = text_strips[-2]
    b = text_strips[-1]
    a.name = f"{PREFIX}_StyleA"
    b.name = f"{PREFIX}_StyleB"

    _set_selected(scene, [a, b])
    scene.sequence_editor.active_strip = a

    apply_result = bpy.ops.subtitle.apply_style()
    if apply_result != {"FINISHED"}:
        return False, f"apply_style returned {apply_result}"

    if int(a.font_size) != int(props.font_size) or int(b.font_size) != int(
        props.font_size
    ):
        return False, "font_size not applied to both strips"

    return True, "apply_style workflow ok"


def _run_metastrip_copy_style(scene) -> tuple[bool, str]:
    src = _find_text_strip_by_prefix(scene, f"{PREFIX}_StyleA")
    dst = _find_text_strip_by_prefix(scene, f"{PREFIX}_StyleB")
    if src is None or dst is None:
        return False, "missing source/target strips before meta test"

    src.font_size = 61
    if hasattr(src, "use_outline"):
        src.use_outline = True
    if hasattr(src, "outline_width"):
        src.outline_width = 0.045

    if scene.sequence_editor.meta_stack:
        override = _sequencer_override()
        if not override:
            return False, "no SEQUENCE_EDITOR area available"
        with bpy.context.temp_override(**override):
            while scene.sequence_editor.meta_stack:
                toggle_out = bpy.ops.sequencer.meta_toggle()
                if toggle_out != {"FINISHED"}:
                    return False, f"meta_toggle(out) returned {toggle_out}"

    _set_selected(scene, [src, dst])
    scene.sequence_editor.active_strip = src
    bpy.context.view_layer.update()

    override = _sequencer_override()
    if not override:
        return False, "no SEQUENCE_EDITOR area available"

    with bpy.context.temp_override(**override):
        make_meta_result = bpy.ops.sequencer.meta_make()
    if make_meta_result != {"FINISHED"}:
        return False, (
            f"meta_make returned {make_meta_result}; "
            f"selected={sum(1 for s in _iter_text_strips(scene) if s.select)}"
        )

    meta_strip = scene.sequence_editor.active_strip
    if meta_strip is None or getattr(meta_strip, "type", "") != "META":
        return False, "active strip after meta_make is not META"

    with bpy.context.temp_override(**override):
        toggle_in = bpy.ops.sequencer.meta_toggle()
    if toggle_in != {"FINISHED"}:
        return False, f"meta_toggle(in) returned {toggle_in}"

    inner_collection = getattr(meta_strip, "strips", None) or getattr(
        meta_strip, "sequences", None
    )
    if not inner_collection:
        with bpy.context.temp_override(**override):
            bpy.ops.sequencer.meta_toggle()
        return False, "meta strip has no child collection"

    inner_src = None
    inner_dst = None
    for child in inner_collection:
        if getattr(child, "type", "") != "TEXT":
            continue
        child_name = getattr(child, "name", "")
        if child_name.startswith(f"{PREFIX}_StyleA"):
            inner_src = child
        elif child_name.startswith(f"{PREFIX}_StyleB"):
            inner_dst = child

    if inner_src is None or inner_dst is None:
        with bpy.context.temp_override(**override):
            bpy.ops.sequencer.meta_toggle()
        return False, "inner meta strips not found"

    _set_selected(scene, [inner_src, inner_dst])
    scene.sequence_editor.active_strip = inner_src
    copy_result = bpy.ops.subtitle.copy_style_from_active()

    ok = copy_result == {"FINISHED"}
    if ok:
        ok = int(inner_dst.font_size) == int(inner_src.font_size)
    if ok and hasattr(inner_src, "use_outline") and hasattr(inner_dst, "use_outline"):
        ok = bool(inner_dst.use_outline) == bool(inner_src.use_outline)

    with bpy.context.temp_override(**override):
        bpy.ops.sequencer.meta_toggle()

    if not ok:
        return False, f"copy_style_from_active returned {copy_result} or style mismatch"

    return True, "MetaStrip copy-style workflow ok"


def main() -> int:
    scene = bpy.context.scene
    if scene is None:
        _print_result("scene", False, "no active scene")
        return 1

    _ensure_sequence_editor(scene)
    _clear_smoke_strips(scene)
    bpy.ops.subtitle.refresh_list()

    checks = [
        ("strip add/update/remove", _run_add_update_remove),
        ("apply style", _run_apply_style),
        ("copy style in MetaStrip", _run_metastrip_copy_style),
    ]

    failures = 0
    for name, fn in checks:
        ok, detail = fn(scene)
        _print_result(name, ok, detail)
        if not ok:
            failures += 1

    _clear_smoke_strips(scene)
    bpy.ops.subtitle.refresh_list()

    _print_result("overall", failures == 0, f"failures={failures}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
