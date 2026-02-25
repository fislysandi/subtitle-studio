"""Pure style patch planning helpers."""

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class StylePatch:
    """Immutable style values derived from editor state."""

    font_size: float
    text_color_rgba: tuple[float, float, float, float]
    use_outline: bool
    outline_color_rgba: tuple[float, float, float, float]
    v_align: str
    wrap_width: float


def _to_rgba(color: Sequence[float]) -> tuple[float, float, float, float]:
    return (float(color[0]), float(color[1]), float(color[2]), 1.0)


def build_style_patch(
    font_size: float,
    text_color: Sequence[float],
    use_outline_color: bool,
    outline_color: Sequence[float],
    v_align: str,
    wrap_width: float,
) -> StylePatch:
    """Build immutable style values from primitive editor fields."""
    return StylePatch(
        font_size=float(font_size),
        text_color_rgba=_to_rgba(text_color),
        use_outline=bool(use_outline_color),
        outline_color_rgba=_to_rgba(outline_color),
        v_align=str(v_align),
        wrap_width=float(wrap_width),
    )


def build_style_patch_from_props(props) -> StylePatch:
    """Build a style patch from subtitle editor properties."""
    return build_style_patch(
        font_size=getattr(props, "font_size", 24.0),
        text_color=getattr(props, "text_color", (1.0, 1.0, 1.0)),
        use_outline_color=getattr(props, "use_outline_color", True),
        outline_color=getattr(props, "outline_color", (0.0, 0.0, 0.0)),
        v_align=getattr(props, "v_align", "BOTTOM"),
        wrap_width=getattr(props, "wrap_width", 0.7),
    )
