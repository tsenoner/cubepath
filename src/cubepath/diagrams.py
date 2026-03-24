"""SVG cube diagram generator for Cubepath guide.

Generates top-face plan-view diagrams for OLL and PLL cases,
plus 3D isometric notation move diagrams.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import svgwrite

# Colors — standard Western Rubik's cube (Yellow top, Red front)
YELLOW = "#FFD500"
GREY = "#C0C0C0"
WHITE = "#FFFFFF"
RED = "#E00000"
ORANGE = "#FF8C00"
BLUE = "#0051BA"
GREEN = "#009E60"
STICKER_STROKE = "#333333"

# Layout constants (plan-view diagrams)
CELL = 40  # sticker size in px
GAP = 2  # gap between stickers
SIDE_H = 12  # height of side-strip stickers
MARGIN = 20  # margin around diagram
RADIUS = 4  # corner radius for rounded rects
ARROW_COLOR = "#222222"


@dataclass
class CubeDiagram:
    """A single cube diagram case."""

    name: str  # filename (no extension)
    label: str  # human-readable label
    category: str  # "oll_cross", "oll_corners", "pll_corners", "pll_edges"
    # U-face colors: 9 cells, row-major (0=TL, 1=TC, 2=TR, 3=ML, 4=C, 5=MR, 6=BL, 7=BC, 8=BR)
    u_face: list[str]
    # Side stickers: top[3], right[3], bottom[3], left[3] — each from left-to-right as viewed
    top_side: list[str] = field(default_factory=lambda: [GREY, GREY, GREY])
    right_side: list[str] = field(default_factory=lambda: [GREY, GREY, GREY])
    bottom_side: list[str] = field(default_factory=lambda: [GREY, GREY, GREY])
    left_side: list[str] = field(default_factory=lambda: [GREY, GREY, GREY])
    # Arrows for PLL: bidirectional swaps and directional cycles
    swaps: list[tuple[str, str]] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)
    # Secondary arrows (dashed) for edge movement in corner PLLs
    dashed_swaps: list[tuple[str, str]] = field(default_factory=list)


Y = YELLOW
G = GREY


def _arrow_pos(name: str) -> tuple[float, float]:
    """Return pixel center for a named arrow anchor on the U-face grid."""
    ox = MARGIN + SIDE_H + GAP  # 34
    oy = MARGIN + SIDE_H + GAP  # 34
    positions = {
        # Edge midpoints (center of U-face edge stickers)
        "top": (ox + (CELL + GAP) + CELL / 2, oy + CELL / 2),
        "bottom": (ox + (CELL + GAP) + CELL / 2, oy + 2 * (CELL + GAP) + CELL / 2),
        "left": (ox + CELL / 2, oy + (CELL + GAP) + CELL / 2),
        "right": (ox + 2 * (CELL + GAP) + CELL / 2, oy + (CELL + GAP) + CELL / 2),
        # Corner midpoints (center of U-face corner stickers)
        "tl": (ox + CELL / 2, oy + CELL / 2),
        "tr": (ox + 2 * (CELL + GAP) + CELL / 2, oy + CELL / 2),
        "bl": (ox + CELL / 2, oy + 2 * (CELL + GAP) + CELL / 2),
        "br": (ox + 2 * (CELL + GAP) + CELL / 2, oy + 2 * (CELL + GAP) + CELL / 2),
    }
    return positions[name]


def _oll_cross_cases() -> list[CubeDiagram]:
    """OLL cross cases: Dot, Hook (L-shape), Line."""
    return [
        CubeDiagram(
            name="oll_dot",
            label="Dot",
            category="oll_cross",
            u_face=[G, G, G, G, Y, G, G, G, G],
        ),
        CubeDiagram(
            name="oll_hook",
            label="Hook / L-shape",
            category="oll_cross",
            u_face=[G, Y, G, Y, Y, G, G, G, G],  # L in back-left
        ),
        CubeDiagram(
            name="oll_line",
            label="Line",
            category="oll_cross",
            u_face=[G, G, G, Y, Y, Y, G, G, G],
        ),
    ]


def _oll_corner_cases() -> list[CubeDiagram]:
    """OLL corner orientation cases (yellow cross already done)."""

    def with_corners(tl: str, tr: str, bl: str, br: str) -> list[str]:
        return [tl, Y, tr, Y, Y, Y, bl, Y, br]

    return [
        # Sune: 1 yellow corner (front-left), other 3 CW-twisted
        CubeDiagram(
            name="oll_sune",
            label="Sune",
            category="oll_corners",
            u_face=with_corners(G, G, Y, G),
            top_side=[Y, G, G],
            right_side=[Y, G, G],
            bottom_side=[G, G, Y],
            left_side=[G, G, G],
        ),
        # Anti-Sune: 1 yellow corner (back-right), other 3 CCW-twisted
        CubeDiagram(
            name="oll_antisune",
            label="Anti-Sune",
            category="oll_corners",
            u_face=with_corners(G, Y, G, G),
            top_side=[G, G, G],
            right_side=[G, G, Y],
            bottom_side=[Y, G, G],
            left_side=[Y, G, G],
        ),
        CubeDiagram(
            name="oll_pi",
            label="Pi / Double Sune",
            category="oll_corners",
            u_face=with_corners(G, G, G, G),
            top_side=[Y, G, Y],
            right_side=[G, G, G],
            bottom_side=[Y, G, Y],
            left_side=[G, G, G],
        ),
        CubeDiagram(
            name="oll_headlights",
            label="Headlights",
            category="oll_corners",
            u_face=with_corners(G, G, G, G),
            top_side=[G, G, G],
            right_side=[Y, G, Y],
            bottom_side=[G, G, G],
            left_side=[Y, G, Y],
        ),
        CubeDiagram(
            name="oll_chameleon",
            label="Chameleon",
            category="oll_corners",
            u_face=with_corners(Y, G, G, Y),
            top_side=[G, G, Y],
            right_side=[G, G, G],
            bottom_side=[Y, G, G],
            left_side=[G, G, G],
        ),
        CubeDiagram(
            name="oll_bowtie",
            label="Bowtie",
            category="oll_corners",
            u_face=with_corners(G, Y, Y, G),
            top_side=[Y, G, G],
            right_side=[G, G, G],
            bottom_side=[G, G, Y],
            left_side=[G, G, G],
        ),
        CubeDiagram(
            name="oll_solved",
            label="All Corners Yellow",
            category="oll_corners",
            u_face=[Y, Y, Y, Y, Y, Y, Y, Y, Y],
        ),
    ]


def _pll_corner_cases() -> list[CubeDiagram]:
    """PLL corner permutation cases."""
    return [
        # T-perm: adjacent corner swap (headlights on left, swap right-side corners)
        CubeDiagram(
            name="pll_tperm",
            label="T-Perm",
            category="pll_corners",
            u_face=[Y] * 9,
            top_side=[RED, G, ORANGE],
            right_side=[GREEN, G, GREEN],
            bottom_side=[ORANGE, G, RED],
            left_side=[BLUE, G, BLUE],
            swaps=[("tr", "br")],
            dashed_swaps=[("right", "left")],
        ),
        # Y-perm: diagonal corner swap (UBL↔UFR) + edge swap (UB↔UL)
        CubeDiagram(
            name="pll_yperm",
            label="Y-Perm",
            category="pll_corners",
            u_face=[Y] * 9,
            top_side=[GREEN, G, RED],
            right_side=[GREEN, G, RED],
            bottom_side=[ORANGE, G, BLUE],
            left_side=[ORANGE, G, BLUE],
            swaps=[("tl", "br")],
            dashed_swaps=[("top", "left")],
        ),
    ]


def _pll_edge_cases() -> list[CubeDiagram]:
    """PLL edge permutation cases."""
    return [
        # Ua: 3-cycle (front→right→left, solved edge at back)
        CubeDiagram(
            name="pll_ua",
            label="Ua Perm",
            category="pll_edges",
            u_face=[Y] * 9,
            top_side=[RED, RED, RED],
            right_side=[GREEN, BLUE, GREEN],
            bottom_side=[ORANGE, GREEN, ORANGE],
            left_side=[BLUE, ORANGE, BLUE],
            cycles=[["bottom", "right", "left"]],
        ),
        # Ub: 3-cycle (front→left→right, solved edge at back)
        CubeDiagram(
            name="pll_ub",
            label="Ub Perm",
            category="pll_edges",
            u_face=[Y] * 9,
            top_side=[RED, RED, RED],
            right_side=[GREEN, ORANGE, GREEN],
            bottom_side=[ORANGE, BLUE, ORANGE],
            left_side=[BLUE, GREEN, BLUE],
            cycles=[["bottom", "left", "right"]],
        ),
        # H-perm: opposite edge swap
        CubeDiagram(
            name="pll_hperm",
            label="H-Perm",
            category="pll_edges",
            u_face=[Y] * 9,
            top_side=[RED, ORANGE, RED],
            right_side=[GREEN, BLUE, GREEN],
            bottom_side=[ORANGE, RED, ORANGE],
            left_side=[BLUE, GREEN, BLUE],
            swaps=[("top", "bottom"), ("left", "right")],
        ),
        # Z-perm: adjacent edge swap
        CubeDiagram(
            name="pll_zperm",
            label="Z-Perm",
            category="pll_edges",
            u_face=[Y] * 9,
            top_side=[RED, GREEN, RED],
            right_side=[GREEN, RED, GREEN],
            bottom_side=[ORANGE, BLUE, ORANGE],
            left_side=[BLUE, ORANGE, BLUE],
            swaps=[("top", "right"), ("left", "bottom")],
        ),
    ]


def all_cases() -> list[CubeDiagram]:
    return _oll_cross_cases() + _oll_corner_cases() + _pll_corner_cases() + _pll_edge_cases()


def _grid_to_px(col: float, row: float) -> tuple[float, float]:
    """Convert grid coordinates to pixel coordinates (top-left of cell)."""
    ox = MARGIN + SIDE_H + GAP
    oy = MARGIN + SIDE_H + GAP
    return (ox + col * (CELL + GAP), oy + row * (CELL + GAP))


def _add_arrow_defs(dwg: svgwrite.Drawing) -> None:
    """Add arrowhead marker definitions to the SVG."""
    marker = dwg.marker(
        id="arrowhead",
        insert=(5, 5),
        size=(10, 10),
        orient="auto",
        markerUnits="userSpaceOnUse",
    )
    marker.add(dwg.polygon([(0, 0), (10, 5), (0, 10)], fill=ARROW_COLOR))
    dwg.defs.add(marker)

    marker_rev = dwg.marker(
        id="arrowhead-rev",
        insert=(5, 5),
        size=(10, 10),
        orient="auto",
        markerUnits="userSpaceOnUse",
    )
    marker_rev.add(dwg.polygon([(10, 0), (0, 5), (10, 10)], fill=ARROW_COLOR))
    dwg.defs.add(marker_rev)


def _arrow_path(
    dwg: svgwrite.Drawing,
    pos_a: str,
    pos_b: str,
) -> svgwrite.path.Path:
    """Create a straight arrow path between two named positions."""
    start = _arrow_pos(pos_a)
    end = _arrow_pos(pos_b)
    return dwg.path(
        d=f"M {start[0]},{start[1]} L {end[0]},{end[1]}",
        fill="none",
        stroke=ARROW_COLOR,
        stroke_width=2,
    )


def _draw_swap(
    dwg: svgwrite.Drawing,
    pos_a: str,
    pos_b: str,
    *,
    dashed: bool = False,
) -> None:
    """Draw a single bidirectional arrow (swap) between two named positions."""
    path = _arrow_path(dwg, pos_a, pos_b)
    path["marker-start"] = "url(#arrowhead-rev)"
    path["marker-end"] = "url(#arrowhead)"
    if dashed:
        path.dasharray([4, 3])
    dwg.add(path)


def _draw_cycle(
    dwg: svgwrite.Drawing,
    positions: list[str],
) -> None:
    """Draw directional arrows forming a cycle through named positions."""
    for i in range(len(positions)):
        a = positions[i]
        b = positions[(i + 1) % len(positions)]
        path = _arrow_path(dwg, a, b)
        path["marker-end"] = "url(#arrowhead)"
        dwg.add(path)


def _case_subdir(category: str) -> str:
    """Return subdirectory name for a diagram category."""
    if category.startswith("oll"):
        return "oll"
    if category.startswith("pll"):
        return "pll"
    return ""


def render(case: CubeDiagram, output_dir: Path) -> Path:
    """Render a CubeDiagram to an SVG file."""
    grid_w = 3 * CELL + 2 * GAP
    grid_h = 3 * CELL + 2 * GAP
    total_w = 2 * MARGIN + 2 * (SIDE_H + GAP) + grid_w
    total_h = 2 * MARGIN + 2 * (SIDE_H + GAP) + grid_h

    subdir = output_dir / _case_subdir(case.category)
    subdir.mkdir(parents=True, exist_ok=True)
    filepath = subdir / f"{case.name}.svg"
    dwg = svgwrite.Drawing(
        str(filepath),
        size=(f"{total_w}px", f"{total_h}px"),
        viewBox=f"0 0 {total_w} {total_h}",
    )

    # Background
    dwg.add(dwg.rect((0, 0), (total_w, total_h), fill=WHITE, rx=8, ry=8))

    # Draw U face (3x3 grid)
    for idx, color in enumerate(case.u_face):
        r, c = idx // 3, idx % 3
        x, y = _grid_to_px(c, r)
        dwg.add(
            dwg.rect(
                (x, y),
                (CELL, CELL),
                fill=color,
                stroke=STICKER_STROKE,
                stroke_width=1.5,
                rx=RADIUS,
                ry=RADIUS,
            )
        )

    # Draw side strips (top, bottom, left, right)
    ox = MARGIN + SIDE_H + GAP
    oy = MARGIN + SIDE_H + GAP
    step = CELL + GAP
    side_strips = [
        # (colors, x0, y0, dx, dy, width, height)
        (case.top_side, ox, MARGIN, step, 0, CELL, SIDE_H),
        (case.bottom_side, ox, oy + grid_h + GAP, step, 0, CELL, SIDE_H),
        (case.left_side, MARGIN, oy, 0, step, SIDE_H, CELL),
        (case.right_side, ox + grid_w + GAP, oy, 0, step, SIDE_H, CELL),
    ]
    for colors, x0, y0, sx, sy, w, h in side_strips:
        for i, color in enumerate(colors):
            dwg.add(
                dwg.rect(
                    (x0 + i * sx, y0 + i * sy),
                    (w, h),
                    fill=color,
                    stroke=STICKER_STROKE,
                    stroke_width=1,
                    rx=2,
                    ry=2,
                )
            )

    # Draw arrows for PLL cases
    has_arrows = case.swaps or case.cycles or case.dashed_swaps
    if has_arrows:
        _add_arrow_defs(dwg)
        for pos_a, pos_b in case.swaps:
            _draw_swap(dwg, pos_a, pos_b)
        for cycle in case.cycles:
            _draw_cycle(dwg, cycle)
        for pos_a, pos_b in case.dashed_swaps:
            _draw_swap(dwg, pos_a, pos_b, dashed=True)

    dwg.save(pretty=True)
    return filepath


# ── Notation move diagrams (3D isometric cube) ──────────────────────────────

_N_SCALE = 20
_N_H_ANGLE = math.radians(35)
_N_COS_H, _N_SIN_H = math.cos(_N_H_ANGLE), math.sin(_N_H_ANGLE)
_N_ELEV = 0.40
_N_W = 155
_N_CX, _N_CY = _N_W / 2, 84

# Standard cube face colors (Yellow top, Red front, Green right)
_CUBE_FACE_COLORS = {"U": YELLOW, "F": RED, "R": GREEN}
# Hidden faces: B=Orange, L=Blue, D=White

# 3D isometric cube outline edges (shared by notation and overview diagrams)
_CUBE_OUTLINE_EDGES = [
    ((0, 3, 0), (3, 3, 0)),
    ((3, 3, 0), (3, 0, 0)),
    ((3, 0, 0), (3, 0, 3)),
    ((3, 0, 3), (0, 0, 3)),
    ((0, 0, 3), (0, 3, 3)),
    ((0, 3, 3), (0, 3, 0)),
    ((3, 3, 3), (0, 3, 3)),
    ((3, 3, 3), (3, 3, 0)),
    ((3, 3, 3), (3, 0, 3)),
]


@dataclass
class NotationMove:
    """A single notation move diagram."""

    name: str
    filename: str
    layer: str  # R/L/U/D/F/B/M/S/E/f/r/x/y/z/R2
    clockwise: bool
    desc: str = ""


@dataclass
class StepDiagram:
    """A single step progress diagram."""

    name: str
    filename: str
    solved: set[tuple[str, int, int]]
    face_colors: dict[str, str] | None = None  # override face colors (e.g. white on top)
    arrow: str | None = None  # rotation arrow layer (e.g. "x" for flip)
    overrides: dict[tuple[str, int, int], str] = field(default_factory=dict)
    swap_arrows: list[tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]] = field(
        default_factory=list
    )  # Each: (src_3d, dst_3d, ctrl_3d) — bidirectional 3D Bezier arrows
    dir_arrows: list[tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]] = field(
        default_factory=list
    )  # Each: (src_3d, dst_3d, ctrl_3d) — unidirectional 3D Bezier arrows


def _notation_moves() -> list[NotationMove]:
    return [
        NotationMove("R", "move_r", "R", True, "Right CW"),
        NotationMove("R'", "move_r_prime", "R", False, "Right CCW"),
        NotationMove("R2", "move_r2", "R2", True, "Right 180°"),
        NotationMove("U", "move_u", "U", True, "Up CW"),
        NotationMove("L", "move_l", "L", True, "Left CW"),
        NotationMove("F", "move_f", "F", True, "Front CW"),
        NotationMove("D", "move_d", "D", True, "Down CW"),
        NotationMove("B", "move_b", "B", True, "Back CW"),
        NotationMove("M", "move_m", "M", True, "Mid (L dir)"),
        NotationMove("S", "move_s", "S", True, "Standing (F dir)"),
        NotationMove("E", "move_e", "E", True, "Equator (D dir)"),
        NotationMove("r (Rw)", "move_rw", "r", True, "Wide R CW"),
        NotationMove("x", "move_x", "x", True, "Rotate on R"),
        NotationMove("y", "move_y", "y", True, "Rotate on U"),
        NotationMove("z", "move_z", "z", True, "Rotate on F"),
    ]


_CENTERS = {("U", 1, 1), ("F", 1, 1), ("R", 1, 1)}

# Shared solved-sticker-set progression (cumulative, each builds on the previous)
_FIRST_LAYER = _CENTERS | {
    ("F", 0, 0), ("F", 1, 0), ("F", 2, 0),
    ("R", 0, 0), ("R", 1, 0), ("R", 2, 0),
}
_SECOND_LAYER = _FIRST_LAYER | {("F", 0, 1), ("F", 2, 1), ("R", 0, 1), ("R", 2, 1)}
_YELLOW_CROSS = _SECOND_LAYER | {("U", 1, 0), ("U", 0, 1), ("U", 2, 1), ("U", 1, 2)}
_EDGES_ALIGNED = _YELLOW_CROSS | {("F", 1, 2), ("R", 1, 2)}
_CORNERS_POSITIONED = _EDGES_ALIGNED | {("F", 0, 2), ("F", 2, 2), ("R", 0, 2), ("R", 2, 2)}


def _step_sticker_color(
    face: str,
    a: int,
    b: int,
    solved: set[tuple[str, int, int]],
    face_colors: dict[str, str] | None = None,
    overrides: dict[tuple[str, int, int], str] | None = None,
) -> str:
    """Return face color if sticker is solved, GREY otherwise. Overrides take priority."""
    if overrides and (face, a, b) in overrides:
        return overrides[(face, a, b)]
    colors = face_colors or _CUBE_FACE_COLORS
    return colors[face] if (face, a, b) in solved else GREY


def _bezier_2d(
    src: tuple[float, ...],
    dst: tuple[float, ...],
    ctrl: tuple[float, ...],
    n_pts: int = 20,
) -> list[tuple[float, float]]:
    """Generate projected 2D points along a 3D quadratic Bezier curve."""
    pts = []
    for i in range(n_pts + 1):
        t = i / n_pts
        t1, t2, t3 = (1 - t) ** 2, 2 * t * (1 - t), t**2
        pts.append(_n_proj(
            t1 * src[0] + t2 * ctrl[0] + t3 * dst[0],
            t1 * src[1] + t2 * ctrl[1] + t3 * dst[1],
            t1 * src[2] + t2 * ctrl[2] + t3 * dst[2],
        ))
    return pts


def _draw_arrowhead(
    dwg: svgwrite.Drawing,
    tip: tuple[float, float],
    prev: tuple[float, float],
    sz: float,
) -> None:
    """Draw a triangular arrowhead at tip pointing away from prev."""
    dx, dy = tip[0] - prev[0], tip[1] - prev[1]
    ln = math.hypot(dx, dy)
    if ln > 0:
        ux, uy = dx / ln, dy / ln
        nx, ny = -uy, ux
        base = (tip[0] - sz * ux, tip[1] - sz * uy)
        dwg.add(dwg.polygon([
            tip,
            (base[0] + sz * 0.4 * nx, base[1] + sz * 0.4 * ny),
            (base[0] - sz * 0.4 * nx, base[1] - sz * 0.4 * ny),
        ], fill=ARROW_COLOR))


def _render_bezier_arrow(
    dwg: svgwrite.Drawing,
    src: tuple[float, ...],
    dst: tuple[float, ...],
    ctrl: tuple[float, ...],
    *,
    bidirectional: bool = False,
    sz: float = 8,
    stroke_width: float = 2.5,
) -> None:
    """Draw a 3D Bezier arrow projected to 2D, with arrowhead(s)."""
    pts = _bezier_2d(src, dst, ctrl)
    # Arrowhead at end
    _draw_arrowhead(dwg, pts[-1], pts[-3], sz)
    # Arrowhead at start (pointing backward) for bidirectional
    if bidirectional:
        _draw_arrowhead(dwg, pts[0], pts[2], sz)
    # Trim arc at arrowhead ends
    start = 1 if bidirectional else 0
    end = -2 if bidirectional else -1
    shortened = pts[start:end]
    if len(shortened) >= 2:
        d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in shortened)
        dwg.add(dwg.path(d=d, fill="none", stroke=ARROW_COLOR, stroke_width=stroke_width))


def _step_cases() -> list[StepDiagram]:
    """Define step progress diagrams: white-on-top → flip → yellow-on-top."""
    white_top = {"U": WHITE, "F": GREEN, "R": RED}

    # Step 1: White Cross on top
    cross = set(_CENTERS) | {
        ("U", 1, 0), ("U", 0, 1), ("U", 2, 1), ("U", 1, 2),
        ("F", 1, 2), ("R", 1, 2),
    }
    solved = _CORNERS_POSITIONED | {("U", 0, 0), ("U", 2, 0), ("U", 0, 2), ("U", 2, 2)}
    return [
        StepDiagram("White Cross", "step_1_cross", cross, white_top),
        StepDiagram("Flip", "step_flip", set(cross), white_top, arrow="x"),
        StepDiagram("White Corners", "step_2_corners", set(_FIRST_LAYER)),
        StepDiagram("Middle Edges", "step_3_edges", set(_SECOND_LAYER)),
        StepDiagram("Yellow Cross", "step_4_ycross", set(_YELLOW_CROSS)),
        StepDiagram("Align Edges", "step_5_yedges", set(_EDGES_ALIGNED)),
        StepDiagram("Position Corners", "step_6_ycorners_pos", set(_CORNERS_POSITIONED)),
        StepDiagram("Solved", "step_7_solved", set(solved)),
    ]


def _corner_case_steps() -> list[StepDiagram]:
    """Corner insertion case diagrams: white faces right/front/up."""
    # Cross done on bottom: centers + bottom edge stickers visible on F and R
    cross_done = set(_CENTERS) | {("F", 1, 0), ("R", 1, 0)}
    return [
        StepDiagram(
            "White Right",
            "corner_right",
            cross_done,
            overrides={("R", 2, 2): WHITE, ("U", 2, 2): RED, ("F", 2, 2): GREEN},
        ),
        StepDiagram(
            "White Front",
            "corner_front",
            cross_done,
            overrides={("F", 2, 2): WHITE, ("R", 2, 2): RED, ("U", 2, 2): GREEN},
        ),
        StepDiagram(
            "White Up",
            "corner_up",
            cross_done,
            overrides={("U", 2, 2): WHITE, ("F", 2, 2): RED, ("R", 2, 2): GREEN},
        ),
    ]


def _align_edge_cases() -> list[StepDiagram]:
    """Yellow edge alignment case diagrams: adjacent vs diagonal."""
    return [
        StepDiagram(
            "Adjacent Edges",
            "align_adjacent",
            _YELLOW_CROSS | {("R", 1, 2)},  # R+B correct
            overrides={("F", 1, 2): BLUE},  # F has L's color
            swap_arrows=[  # front ↔ left, arc to the left
                ((1.5, 2.5, 3), (0.5, 3, 1.5), (-0.5, 4.5, 3.5)),
            ],
        ),
        StepDiagram(
            "Opposite Edges",
            "align_diagonal",
            _YELLOW_CROSS | {("R", 1, 2)},  # R+L correct
            overrides={("F", 1, 2): ORANGE},  # F has B's color
            swap_arrows=[  # front ↔ back, arc upward
                ((1.5, 2.5, 3), (1.5, 3, 0.5), (-0.4, 4.5, 1.5)),
            ],
        ),
    ]


def _orient_corner_case() -> StepDiagram:
    """Orient corners diagram (flipped, white on top): DFR corner with yellow on R face."""
    flipped = {"U": WHITE, "F": ORANGE, "R": GREEN}
    # After x2 flip: white on top (fully solved), orange in front, green on right.
    # All stickers solved except D-layer corner orientations (bottom corners of F and R).
    # Derive from _CORNERS_POSITIONED: add all U-face stickers, remove F/R bottom corners.
    solved = (
        _CORNERS_POSITIONED
        | {(f, a, b) for f in ("U",) for a in range(3) for b in range(3)}
    ) - {("F", 0, 0), ("F", 2, 0), ("R", 0, 0), ("R", 2, 0)}
    return StepDiagram(
        "Orient Corner",
        "orient_corner",
        solved,
        face_colors=flipped,
        overrides={
            ("R", 2, 0): YELLOW,  # DFR: yellow on R face (CW twist)
            ("F", 2, 0): GREEN,   # DFR: green wraps to F face
            ("F", 0, 0): YELLOW,  # DFL: yellow on F face (CCW twist)
            ("R", 0, 0): RED,     # DBR: red on R face (CCW twist)
        },
    )


def _orient_corner_cases_15() -> list[StepDiagram]:
    """Phase 1.5 orient corner diagrams: yellow on R face vs yellow on F face."""
    step6 = _CORNERS_POSITIONED | {("U", 0, 2)}
    return [
        StepDiagram(
            "Orient Right",
            "orient_right",
            step6,
            overrides={
                ("U", 2, 2): RED,      # UFR: red on top
                ("R", 2, 2): YELLOW,   # UFR: yellow on R face
                ("F", 2, 2): GREEN,    # UFR: green on F face
            },
        ),
        StepDiagram(
            "Orient Front",
            "orient_front",
            step6,
            overrides={
                ("U", 2, 2): GREEN,    # UFR: green on top
                ("F", 2, 2): YELLOW,   # UFR: yellow on F face
                ("R", 2, 2): RED,      # UFR: red on R face
            },
        ),
    ]


def _corner_pos_case() -> StepDiagram:
    """Corner positioning diagram: 3-cycle with Niklas, FL corner solved."""
    return StepDiagram(
        "Corner Cycle",
        "corner_cycle",
        _EDGES_ALIGNED | {("F", 0, 2)},  # FL corner F-sticker correct
        overrides={("U", 0, 2): RED, ("F", 0, 2): BLUE},  # FL corner: red on top, blue on front
        dir_arrows=[
            ((0.5, 3, 0.5), (2.5, 3, 2.5), (1.5, 3, 1.5)),    # BL → FR (straight)
            ((2.5, 3, 2.5), (2.5, 3, 0.5), (2.5, 3, 1.5)),    # FR → BR (straight)
            ((2.5, 3, 0.5), (0.5, 3, 0.5), (1.5, 3, 0.5)),    # BR → BL (straight)
        ],
    )


def _edge_case_steps() -> list[StepDiagram]:
    """Edge insertion case diagrams: edge goes right/left."""
    return [
        StepDiagram(
            "Edge Right",
            "edge_right",
            set(_FIRST_LAYER),
            overrides={("F", 1, 2): RED, ("U", 1, 2): GREEN},
        ),
        StepDiagram(
            "Edge Left",
            "edge_left",
            set(_FIRST_LAYER),
            overrides={("F", 1, 2): RED, ("U", 1, 2): BLUE},
        ),
    ]


def _n_proj(x: float, y: float, z: float) -> tuple[float, float]:
    """Tilted 3D→2D projection for notation diagrams (matches overview)."""
    return (
        round((x * _N_COS_H - z * _N_SIN_H) * _N_SCALE + _N_CX, 1),
        round(((x * _N_SIN_H + z * _N_COS_H) * _N_ELEV - y) * _N_SCALE + _N_CY, 1),
    )


# Condition types for _STICKER_COLOR_RULES
_EQ_A, _EQ_B, _GE_A, _ANY = "a", "b", "A", "*"

# Lookup table for _n_sticker_color: (layer, cw) → [(face, cond_type, value, color), ...]
# Each entry lists the 2 rules that override the base face color for that move.
_STICKER_COLOR_RULES: dict[tuple[str, bool], list[tuple[str, str, int, str]]] = {
    ("R2", True):  [("U", _EQ_A, 2, WHITE), ("F", _EQ_A, 2, ORANGE)],
    ("R", True):   [("U", _EQ_A, 2, RED), ("F", _EQ_A, 2, WHITE)],
    ("R", False):  [("U", _EQ_A, 2, ORANGE), ("F", _EQ_A, 2, YELLOW)],
    ("L", True):   [("U", _EQ_A, 0, ORANGE), ("F", _EQ_A, 0, YELLOW)],
    ("U", True):   [("F", _EQ_B, 2, GREEN), ("R", _EQ_B, 2, ORANGE)],
    ("D", True):   [("F", _EQ_B, 0, BLUE), ("R", _EQ_B, 0, RED)],
    ("F", True):   [("U", _EQ_B, 2, BLUE), ("R", _EQ_A, 2, YELLOW)],
    ("B", True):   [("U", _EQ_B, 0, GREEN), ("R", _EQ_A, 0, WHITE)],
    ("M", True):   [("U", _EQ_A, 1, ORANGE), ("F", _EQ_A, 1, YELLOW)],
    ("S", True):   [("U", _EQ_B, 1, BLUE), ("R", _EQ_A, 1, YELLOW)],
    ("E", True):   [("F", _EQ_B, 1, GREEN), ("R", _EQ_B, 1, ORANGE)],
    ("r", True):   [("U", _GE_A, 1, RED), ("F", _GE_A, 1, WHITE)],
    ("x", True):   [("U", _ANY, 0, RED), ("F", _ANY, 0, WHITE)],
    ("y", True):   [("F", _ANY, 0, GREEN), ("R", _ANY, 0, ORANGE)],
    ("z", True):   [("U", _ANY, 0, BLUE), ("R", _ANY, 0, YELLOW)],
}


def _n_sticker_color(face: str, a: int, b: int, layer: str, cw: bool) -> str:
    """Get sticker color at (face, a, b) after one move applied to a solved cube.

    This shows the RESULT of the move so readers see which stickers moved where.
    Hidden face colors: B=Orange, L=Blue, D=White.
    """
    base = _CUBE_FACE_COLORS[face]
    # R has separate CW/CCW entries; all others are CW-only in the table
    key = (layer, cw) if layer == "R" else (layer, True)
    rules = _STICKER_COLOR_RULES.get(key)
    if not rules:
        return base
    for rule_face, cond, val, color in rules:
        if face != rule_face:
            continue
        if (
            (cond == _EQ_A and a == val)
            or (cond == _EQ_B and b == val)
            or (cond == _GE_A and a >= val)
            or cond == _ANY
        ):
            return color
    return base


def _n_sticker_pts(face: str, a: int, b: int) -> list[tuple[float, float]]:
    """Get projected 2D corners of sticker (a,b) on a visible face."""
    if face == "U":
        corners = [(a, 3, b), (a + 1, 3, b), (a + 1, 3, b + 1), (a, 3, b + 1)]
    elif face == "F":
        corners = [(a, b + 1, 3), (a + 1, b + 1, 3), (a + 1, b, 3), (a, b, 3)]
    elif face == "R":
        corners = [(3, b + 1, a), (3, b + 1, a + 1), (3, b, a + 1), (3, b, a)]
    else:
        return []
    return [_n_proj(*c) for c in corners]


def _n_draw_arrow(dwg: svgwrite.Drawing, layer: str, clockwise: bool) -> None:
    """Draw a curved arrow from source face sticker center to destination face sticker center.

    Each arrow is a quadratic Bezier curve in 3D, going from the center of the
    affected row/column on one visible face to the center on the other visible face,
    curving outward over the edge between them.
    """
    is_whole = layer in ("x", "y", "z")

    # Arrow configs: (cw_src_3d, cw_dst_3d, control_3d)
    # src/dst = center of affected stickers on each face for CW direction.
    # control = edge point pushed outward (Bezier control for the bulge).
    # When CCW, src and dst swap.
    _b = 0.5  # bulge offset from edge
    _cfgs: dict[str, tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]] = {
        # R CW: F col a=2 → U col a=2.  Edge: F-U at x=2.5
        "R": ((2.5, 1.5, 3), (2.5, 3, 1.5), (2.5, 3 + _b, 3 + _b)),
        "R2": ((2.5, 1.5, 3), (2.5, 3, 1.5), (2.5, 3 + _b, 3 + _b)),
        # L CW: U col a=0 → F col a=0.  Edge: F-U at x=0.5
        "L": ((0.5, 3, 1.5), (0.5, 1.5, 3), (0.5, 3 + _b, 3 + _b)),
        # U CW: R row b=2 → F row b=2.  Edge: F-R at y=2.5
        "U": ((3, 2.5, 1.5), (1.5, 2.5, 3), (3 + _b, 2.5, 3 + _b)),
        # D CW: F row b=0 → R row b=0.  Edge: F-R at y=0.5
        "D": ((1.5, 0.5, 3), (3, 0.5, 1.5), (3 + _b, 0.5, 3 + _b)),
        # F CW: U row b=2 → R col a=2.  Edge: U-R at z=2.5
        "F": ((1.5, 3, 2.5), (3, 1.5, 2.5), (3 + _b, 3 + _b, 2.5)),
        # B CW: R col a=0 → U row b=0.  Edge: U-R at z=0.5
        "B": ((3, 1.5, 0.5), (1.5, 3, 0.5), (3 + _b, 3 + _b, 0.5)),
        # M CW (follows L): U col a=1 → F col a=1.  Edge: F-U at x=1.5
        "M": ((1.5, 3, 1.5), (1.5, 1.5, 3), (1.5, 3 + _b, 3 + _b)),
        # S CW (follows F): U row b=1 → R col a=1.  Edge: U-R at z=1.5
        "S": ((1.5, 3, 1.5), (3, 1.5, 1.5), (3 + _b, 3 + _b, 1.5)),
        # E CW (follows D): R row b=1 → F row b=1.  Edge: F-R at y=1.5
        "E": ((3, 1.5, 1.5), (1.5, 1.5, 3), (3 + _b, 1.5, 3 + _b)),
        # r CW (wide R): F cols a=1,2 → U cols a=1,2.  Edge: F-U at x=2
        "r": ((2, 1.5, 3), (2, 3, 1.5), (2, 3 + _b, 3 + _b)),
        # x CW (whole cube, like R): F center → U center.  Edge: F-U at x=1.5
        "x": ((1.5, 1.5, 3), (1.5, 3, 1.5), (1.5, 3 + _b, 3 + _b)),
        # y CW (whole cube, like U): R center → F center.  Edge: F-R at y=1.5
        "y": ((3, 1.5, 1.5), (1.5, 1.5, 3), (3 + _b, 1.5, 3 + _b)),
        # z CW (whole cube, like F): U center → R center.  Edge: U-R at z=1.5
        "z": ((1.5, 3, 1.5), (3, 1.5, 1.5), (3 + _b, 3 + _b, 1.5)),
    }

    cw_src, cw_dst, ctrl = _cfgs[layer]
    if clockwise:
        src, dst = cw_src, cw_dst
    else:
        src, dst = cw_dst, cw_src

    pts = _bezier_2d(src, dst, ctrl)

    # Compute tip direction for arrowhead
    tip = pts[-1]
    prev = pts[-4]
    dx, dy = tip[0] - prev[0], tip[1] - prev[1]
    ln = math.hypot(dx, dy)
    sz = 16

    # Shorten arc at tip to make room for arrowhead
    if ln > 0:
        dx, dy = dx / ln, dy / ln
        nx, ny = -dy, dx
        arc_end = (tip[0] - sz * dx, tip[1] - sz * dy)
        shortened = pts[:-2] + [arc_end]
    else:
        shortened = pts

    d = "M " + " L ".join(f"{x},{y}" for x, y in shortened)
    stroke_extra = {"stroke_dasharray": "6,3"} if is_whole else {}
    dwg.add(
        dwg.path(
            d=d,
            fill="none",
            stroke=ARROW_COLOR,
            stroke_width=5,
            **stroke_extra,
        )
    )

    # Tip arrowhead
    if ln > 0:
        base1 = (tip[0] - sz * dx + sz * 0.5 * nx, tip[1] - sz * dy + sz * 0.5 * ny)
        base2 = (tip[0] - sz * dx - sz * 0.5 * nx, tip[1] - sz * dy - sz * 0.5 * ny)
        dwg.add(dwg.polygon([tip, base1, base2], fill=ARROW_COLOR))


def _draw_iso_stickers(
    dwg: svgwrite.Drawing, color_fn: Callable[[str, int, int], str]
) -> None:
    """Draw 3×3 stickers on each visible face (R → F → U for correct layering)."""
    for face in ("R", "F", "U"):
        for a in range(3):
            for b in range(3):
                pts = _n_sticker_pts(face, a, b)
                color = color_fn(face, a, b)
                dwg.add(dwg.polygon(pts, fill=color, stroke=STICKER_STROKE, stroke_width=1.2))


def _draw_cube_outline(dwg: svgwrite.Drawing) -> None:
    """Draw the cube outline edges."""
    for edge_a, edge_b in _CUBE_OUTLINE_EDGES:
        p1, p2 = _n_proj(*edge_a), _n_proj(*edge_b)
        dwg.add(dwg.line(p1, p2, stroke=STICKER_STROKE, stroke_width=1.5))


def render_notation(move: NotationMove, output_dir: Path) -> Path:
    """Render a notation move diagram (3D isometric cube) to SVG."""
    subdir = output_dir / "notation"
    subdir.mkdir(parents=True, exist_ok=True)
    filepath = subdir / f"{move.filename}.svg"

    # Compute layout from cube bounding box
    cube_top_y = min(_n_proj(x, y, z)[1] for x in (0, 3) for y in (0, 3) for z in (0, 3))
    cube_bot_y = max(_n_proj(x, y, z)[1] for x in (0, 3) for y in (0, 3) for z in (0, 3))
    label_font = 30
    label_y = cube_top_y - 8
    vb_top = label_y - label_font
    vb_bot = cube_bot_y + 6
    vb_h = vb_bot - vb_top

    dwg = svgwrite.Drawing(
        str(filepath),
        size=(f"{_N_W}px", f"{vb_h:.0f}px"),
        viewBox=f"0 {vb_top:.1f} {_N_W} {vb_h:.1f}",
    )
    dwg.add(dwg.rect((0, vb_top), (_N_W, vb_h), fill=WHITE, rx=6, ry=6))
    _draw_iso_stickers(dwg, lambda f, a, b: _n_sticker_color(f, a, b, move.layer, move.clockwise))
    _draw_cube_outline(dwg)
    # Rotation arrow
    _n_draw_arrow(dwg, move.layer, move.clockwise)
    # Label (top, above cube)
    dwg.add(
        dwg.text(
            move.name,
            insert=(_N_W / 2, label_y),
            text_anchor="middle",
            font_size=f"{label_font}px",
            font_family="sans-serif",
            font_weight="bold",
            fill="#222",
        )
    )
    dwg.save(pretty=True)
    return filepath


def render_step(step: StepDiagram, output_dir: Path) -> Path:
    """Render a step progress diagram (3D isometric cube) to SVG."""
    subdir = output_dir / "steps"
    subdir.mkdir(parents=True, exist_ok=True)
    filepath = subdir / f"{step.filename}.svg"

    # Tight canvas from cube bounding box
    all_corners = [(x, y, z) for x in (0, 3) for y in (0, 3) for z in (0, 3)]
    proj_pts = [_n_proj(*c) for c in all_corners]
    min_x = min(p[0] for p in proj_pts)
    max_x = max(p[0] for p in proj_pts)
    min_y = min(p[1] for p in proj_pts)
    max_y = max(p[1] for p in proj_pts)
    pad = 6 if step.arrow or step.swap_arrows or step.dir_arrows else 4
    vb_x = min_x - pad
    vb_y = min_y - pad
    vb_w = max_x - min_x + 2 * pad
    vb_h = max_y - min_y + 2 * pad

    dwg = svgwrite.Drawing(
        str(filepath),
        size=(f"{vb_w:.0f}px", f"{vb_h:.0f}px"),
        viewBox=f"{vb_x:.1f} {vb_y:.1f} {vb_w:.1f} {vb_h:.1f}",
    )
    dwg.add(dwg.rect((vb_x, vb_y), (vb_w, vb_h), fill=WHITE, rx=6, ry=6))
    _draw_iso_stickers(
        dwg,
        lambda f, a, b: _step_sticker_color(f, a, b, step.solved, step.face_colors, step.overrides),
    )
    _draw_cube_outline(dwg)

    # Rotation arrow (for flip step)
    if step.arrow:
        _n_draw_arrow(dwg, step.arrow, True)

    # Swap arrows (bidirectional 3D Bezier)
    for src, dst, ctrl in step.swap_arrows:
        _render_bezier_arrow(dwg, src, dst, ctrl, bidirectional=True, sz=12, stroke_width=5)

    # Directional arrows (unidirectional 3D Bezier)
    for src, dst, ctrl in step.dir_arrows:
        _render_bezier_arrow(dwg, src, dst, ctrl)

    dwg.save(pretty=True)
    return filepath


def _draw_rotation_arc(
    dwg: svgwrite.Drawing,
    proj_fn,
    center: tuple[float, ...],
    v1: tuple[float, ...],
    v2: tuple[float, ...],
    radius: float = 0.5,
    start_angle: float = 0.0,
    view_dir: tuple[float, float, float] = (0, -1, 0),
) -> tuple[svgwrite.container.Group, svgwrite.container.Group, svgwrite.container.Group]:
    """Draw a 3D ribbon-style CW rotation arc, split into back/front/arrow groups.

    Returns (back_group, front_group, arrow_group) so the caller can control
    z-ordering of the ring, axis line, and arrowhead independently.
    """
    n_pts = 48
    sweep = math.radians(280)
    band_w = 0.17

    normal = (
        v1[1] * v2[2] - v1[2] * v2[1],
        v1[2] * v2[0] - v1[0] * v2[2],
        v1[0] * v2[1] - v1[1] * v2[0],
    )

    # Depth coefficients: depth(θ) = A*cos(θ) + B*sin(θ)
    A = v1[0] * view_dir[0] + v1[1] * view_dir[1] + v1[2] * view_dir[2]
    B = v2[0] * view_dir[0] + v2[1] * view_dir[1] + v2[2] * view_dir[2]
    depth_amplitude = math.hypot(A, B)

    def _pt_3d(angle: float, offset_sign: float) -> tuple[float, float]:
        co, si = math.cos(angle), math.sin(angle)
        return proj_fn(
            center[0] + radius * (v1[0] * co + v2[0] * si) + offset_sign * band_w * normal[0],
            center[1] + radius * (v1[1] * co + v2[1] * si) + offset_sign * band_w * normal[1],
            center[2] + radius * (v1[2] * co + v2[2] * si) + offset_sign * band_w * normal[2],
        )

    def _depth(angle: float) -> float:
        return A * math.cos(angle) + B * math.sin(angle)

    # Generate arc sample points with depths
    angles = [start_angle + sweep * i / n_pts for i in range(n_pts + 1)]
    depths = [_depth(a) for a in angles]

    # Find zero-crossing indices and interpolate boundary angles
    crossings: list[float] = []
    for i in range(len(depths) - 1):
        if depths[i] * depths[i + 1] < 0:
            t = depths[i] / (depths[i] - depths[i + 1])
            crossings.append(angles[i] + t * (angles[i + 1] - angles[i]))

    # Build segment boundaries
    boundaries = [angles[0]] + sorted(crossings) + [angles[-1]]

    # Classify segments and build ribbon pieces.
    # Separate fill from stroke: draw polygon fills first (no stroke), then
    # draw top/bottom edges as continuous polylines per depth zone so there
    # are no visible joints between adjacent segments.
    back_group = dwg.g()
    front_group = dwg.g()

    def _svg_polyline(pts: list[tuple[float, float]], closed: bool = False) -> str:
        d = "M " + " L ".join(f"{x},{y}" for x, y in pts)
        return d + " Z" if closed else d

    stroke_kw = dict(
        fill="none",
        stroke=ARROW_COLOR,
        stroke_width=1.5,
        stroke_linejoin="round",
        stroke_linecap="round",
    )

    def _add_cap(group, pt_a, pt_b):
        cap = dwg.line(pt_a, pt_b, stroke=ARROW_COLOR, stroke_width=1.5)
        cap["stroke-linecap"] = "round"
        group.add(cap)

    # Collect per-segment data for two-pass rendering
    seg_data: list[tuple[bool, list, list]] = []
    for seg_i in range(len(boundaries) - 1):
        a0, a1 = boundaries[seg_i], boundaries[seg_i + 1]
        span = a1 - a0
        n_seg = max(2, round(n_pts * span / sweep))
        seg_angles = [a0 + span * j / n_seg for j in range(n_seg + 1)]

        is_front = _depth((a0 + a1) / 2) > 0 or depth_amplitude < 0.01
        seg_data.append(
            (
                is_front,
                [_pt_3d(a, +1) for a in seg_angles],
                [_pt_3d(a, -1) for a in seg_angles],
            )
        )

    # Pass 1: white polygon fills (no stroke)
    for is_front, top_pts, bot_pts in seg_data:
        group = front_group if is_front else back_group
        group.add(
            dwg.path(
                d=_svg_polyline(top_pts + list(reversed(bot_pts)), closed=True),
                fill="white",
                stroke="none",
            )
        )

    # Pass 2: merge consecutive same-zone segments into continuous polylines
    i = 0
    while i < len(seg_data):
        is_front = seg_data[i][0]
        group = front_group if is_front else back_group
        merged_top = list(seg_data[i][1])
        merged_bot = list(seg_data[i][2])
        j = i + 1
        while j < len(seg_data) and seg_data[j][0] == is_front:
            merged_top.extend(seg_data[j][1][1:])  # skip shared boundary point
            merged_bot.extend(seg_data[j][2][1:])
            j += 1
        group.add(dwg.path(d=_svg_polyline(merged_top), **stroke_kw))
        group.add(dwg.path(d=_svg_polyline(merged_bot), **stroke_kw))
        _add_cap(group, merged_top[0], merged_bot[0])
        _add_cap(group, merged_top[-1], merged_bot[-1])
        i = j

    # Arrowhead — always at sweep end
    end_angle = start_angle + sweep

    def _ring_pt(angle: float) -> tuple[float, float, float]:
        """3D point on the ring center-line at the given angle."""
        co, si = math.cos(angle), math.sin(angle)
        return (
            center[0] + radius * (v1[0] * co + v2[0] * si),
            center[1] + radius * (v1[1] * co + v2[1] * si),
            center[2] + radius * (v1[2] * co + v2[2] * si),
        )

    tip = proj_fn(*_ring_pt(end_angle + math.radians(42)))

    arrow_w = band_w * 2.5
    base_center_3d = _ring_pt(end_angle)
    base_inner = proj_fn(*(base_center_3d[j] - arrow_w * normal[j] for j in range(3)))
    base_outer = proj_fn(*(base_center_3d[j] + arrow_w * normal[j] for j in range(3)))

    # Combined background covering last ribbon segment + arrowhead (no gap)
    last_seg_a0 = boundaries[-2]
    n_last = max(2, round(n_pts * (end_angle - last_seg_a0) / sweep))
    last_span = end_angle - last_seg_a0
    last_top = [_pt_3d(last_seg_a0 + last_span * j / n_last, +1) for j in range(n_last + 1)]
    last_bot = [_pt_3d(last_seg_a0 + last_span * j / n_last, -1) for j in range(n_last + 1)]

    # Arrowhead in a separate group so callers can control its z-order.
    bg_pts = last_top + [base_outer, tip, base_inner] + list(reversed(last_bot))
    arrow_g = dwg.g()
    arrow_g.add(dwg.path(d=_svg_polyline(bg_pts, closed=True), fill="white", stroke="none"))
    # Re-stroke the last ribbon segment edges (covered by the white background)
    arrow_g.add(dwg.path(d=_svg_polyline(last_top), **stroke_kw))
    arrow_g.add(dwg.path(d=_svg_polyline(last_bot), **stroke_kw))
    # Re-stroke the end-cap at the front/back boundary (also covered by background)
    if last_seg_a0 not in (angles[0], angles[-1]):
        _add_cap(arrow_g, _pt_3d(last_seg_a0, +1), _pt_3d(last_seg_a0, -1))
    # Arrowhead: stroke sides + partial base (skip the segment between ribbon edges)
    ribbon_top_end = _pt_3d(end_angle, +1)
    ribbon_bot_end = _pt_3d(end_angle, -1)
    arrow_g.add(
        dwg.path(
            d=_svg_polyline([ribbon_top_end, base_outer, tip, base_inner, ribbon_bot_end]),
            fill="white",
            **{k: v for k, v in stroke_kw.items() if k != "fill"},
        )
    )

    return back_group, front_group, arrow_g


def render_overview(output_dir: Path) -> Path:
    """Render a summary overview diagram: one isometric cube with 6 labeled axis arrows."""
    subdir = output_dir / "notation"
    subdir.mkdir(parents=True, exist_ok=True)
    filepath = subdir / "overview.svg"

    # Projection origin (arbitrary; viewBox is computed from content bounds).
    # Tilted view: higher viewpoint + rotated left so D/B/L axes go behind the cube.
    ov_cx, ov_cy = 155.0, 110.0
    scale = 22
    # Horizontal rotation ~40° (instead of 45°): F face wider, R face narrower
    h_angle = math.radians(40)
    cos_h, sin_h = math.cos(h_angle), math.sin(h_angle)
    elev = 0.40  # elevation factor (0.5 = standard iso, lower = more top visible)

    def proj(x: float, y: float, z: float) -> tuple[float, float]:
        return (
            round((x * cos_h - z * sin_h) * scale + ov_cx, 1),
            round(((x * sin_h + z * cos_h) * elev - y) * scale + ov_cy, 1),
        )

    # Axis definitions: (label, face_center, tip, arc_v1, arc_v2)
    c = 1.5  # cube center coordinate
    axes = [
        ("U", (c, 3, c), (c, c + 3.0, c), (1, 0, 0), (0, 0, 1)),
        ("D", (c, 0, c), (c, c - 3.5, c), (1, 0, 0), (0, 0, -1)),
        ("F", (c, c, 3), (c, c, c + 4.2), (1, 0, 0), (0, -1, 0)),
        ("B", (c, c, 0), (c, c, c - 4.8), (-1, 0, 0), (0, -1, 0)),
        ("R", (3, c, c), (c + 3.8, c, c), (0, 0, 1), (0, 1, 0)),
        ("L", (0, c, c), (c - 4.3, c, c), (0, 0, -1), (0, 1, 0)),
    ]
    front = {"U", "F", "R"}

    # Pre-compute label positions to determine tight viewBox
    label_dist = 18
    label_positions: list[tuple[float, float]] = []
    for _, face_center, tip, _, _ in axes:
        e = proj(*tip)
        fc = proj(*face_center)
        pdx, pdy = e[0] - fc[0], e[1] - fc[1]
        pln = math.hypot(pdx, pdy)
        if pln > 0:
            label_positions.append((e[0] + pdx / pln * label_dist, e[1] + pdy / pln * label_dist))
        else:
            label_positions.append(e)

    # Compute tight viewBox with uniform padding
    pad = 16
    text_half = 10  # approximate half-extent of 18px label text
    all_x = [lx for lx, _ in label_positions]
    all_y = [ly for _, ly in label_positions]
    vb_x = min(all_x) - text_half - pad
    vb_y = min(all_y) - text_half - pad
    vb_w = max(all_x) - min(all_x) + 2 * (text_half + pad)
    vb_h = max(all_y) - min(all_y) + 2 * (text_half + pad)

    dwg = svgwrite.Drawing(
        str(filepath),
        size=(f"{vb_w:.0f}px", f"{vb_h:.0f}px"),
        viewBox=f"{vb_x:.1f} {vb_y:.1f} {vb_w:.1f} {vb_h:.1f}",
    )
    dwg.add(dwg.rect((vb_x, vb_y), (vb_w, vb_h), fill=WHITE, rx=8, ry=8))

    # Cube face definitions (needed before step 1 for clip path)
    face_colors = [
        ([(0, 3, 0), (3, 3, 0), (3, 3, 3), (0, 3, 3)], YELLOW),
        ([(0, 0, 3), (3, 0, 3), (3, 3, 3), (0, 3, 3)], RED),
        ([(3, 0, 0), (3, 0, 3), (3, 3, 3), (3, 3, 0)], GREEN),
    ]

    # Clip path: viewport minus cube face polygons (evenodd punches holes).
    # Behind-axis lines use this so they're only visible outside the cube silhouette.
    clip = dwg.defs.add(dwg.clipPath(id="behind-clip"))
    m = 5  # margin
    outer = f"M{vb_x - m},{vb_y - m} h{vb_w + 2 * m} v{vb_h + 2 * m} h-{vb_w + 2 * m} Z"
    inner = ""
    for corners, _ in face_colors:
        pts = [proj(*p) for p in corners]
        inner += " M " + " L ".join(f"{x},{y}" for x, y in pts) + " Z"
    clip_elem = dwg.path(d=outer + inner)
    clip_elem["clip-rule"] = "evenodd"
    clip.add(clip_elem)

    # Pre-compute all rotation arcs so we can control z-ordering precisely.
    view_dir = (sin_h, elev, cos_h)
    arc_radius = 0.6
    arc_sweep = math.radians(280)
    arc_data = {}
    for label, face_center, tip, v1, v2 in axes:
        d = tuple(tip[j] - face_center[j] for j in range(3))
        ln = math.hypot(*d)
        d_norm = tuple(x / ln for x in d) if ln > 0 else (0, 0, 0)

        arc_center = tuple(tip[j] - d_norm[j] * 0.7 for j in range(3))

        a_coeff = sum(v1[j] * view_dir[j] for j in range(3))
        b_coeff = sum(v2[j] * view_dir[j] for j in range(3))
        theta_max = math.atan2(b_coeff, a_coeff)
        start_angle = theta_max - arc_sweep - math.radians(42)

        back_g, front_g, arrow_g = _draw_rotation_arc(
            dwg,
            proj,
            arc_center,
            v1,
            v2,
            radius=arc_radius,
            start_angle=start_angle,
            view_dir=view_dir,
        )
        arc_data[label] = (back_g, front_g, arrow_g, d_norm, arc_center)

    # B's back ring drawn behind the cube for correct 3D occlusion
    dwg.add(arc_data["B"][0])

    def _add_line(start, end, color=STICKER_STROKE, **extra):
        line = dwg.line(start, end, stroke=color, stroke_width=1.5)
        line["stroke-linecap"] = "round"
        for k, v in extra.items():
            line[k] = v
        dwg.add(line)

    # 2b. Visible cube faces (solid, colored)
    for corners, color in face_colors:
        pts = [proj(*p) for p in corners]
        dwg.add(
            dwg.polygon(
                pts,
                fill=color,
                stroke=STICKER_STROKE,
                stroke_width=1.5,
                stroke_linejoin="round",
            )
        )

    # 3. Cube outline
    for ea, eb in _CUBE_OUTLINE_EDGES:
        _add_line(proj(*ea), proj(*eb))

    # 4. Redraw "front" axis lines (U, F, R) on top of cube faces
    for label, face_center, tip, _, _ in axes:
        if label in front:
            _add_line(proj(*face_center), proj(*tip), color=ARROW_COLOR)

    # 5. Draw rotation arcs with front/back splitting around axis lines
    for label, face_center, tip, _, _ in axes:
        back_g, front_g, arrow_g, d_norm, arc_center = arc_data[label]

        # B's back_g already drawn before the cube
        if label != "B":
            dwg.add(back_g)

        if label in front:
            seg_len = 1.2 * arc_radius
            seg_out = proj(*tuple(arc_center[j] + seg_len * d_norm[j] for j in range(3)))
            seg_in = proj(*tuple(arc_center[j] - seg_len * d_norm[j] for j in range(3)))
            _add_line(seg_in, seg_out, color=ARROW_COLOR)
            dwg.add(front_g)
            dwg.add(arrow_g)
        else:
            dwg.add(front_g)
            _add_line(
                proj(*face_center),
                proj(*tip),
                color=ARROW_COLOR,
                **{"clip-path": "url(#behind-clip)"},
            )
            if label in ("B", "L"):
                dwg.add(dwg.circle(center=proj(*tip), r=5, fill=ARROW_COLOR))
            dwg.add(arrow_g)

    # 6. Dots and labels at each tip
    for i, (label, face_center, tip, _, _) in enumerate(axes):
        e = proj(*tip)
        if label not in ("B", "L"):
            dwg.add(dwg.circle(center=e, r=5, fill=ARROW_COLOR))

        lx, ly = label_positions[i]
        dwg.add(
            dwg.text(
                label,
                insert=(lx, ly),
                text_anchor="middle",
                dominant_baseline="central",
                font_size="18px",
                font_family="sans-serif",
                font_weight="bold",
                fill="#222",
            )
        )

    dwg.save(pretty=True)
    return filepath


def main() -> None:
    output_dir = Path(__file__).resolve().parents[2] / "guide" / "figures" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    total = 0

    for case in all_cases():
        path = render(case, output_dir)
        print(f"  {path.relative_to(output_dir)}")
        total += 1

    for move in _notation_moves():
        path = render_notation(move, output_dir)
        print(f"  {path.relative_to(output_dir)}")
        total += 1

    print(f"  {render_overview(output_dir).relative_to(output_dir)}")
    total += 1

    all_steps = [
        *_step_cases(),
        *_corner_case_steps(),
        *_edge_case_steps(),
        _orient_corner_case(),
        *_orient_corner_cases_15(),
        _corner_pos_case(),
        *_align_edge_cases(),
    ]
    for step in all_steps:
        path = render_step(step, output_dir)
        print(f"  {path.relative_to(output_dir)}")
        total += 1

    print(f"\nGenerated {total} SVG diagrams in {output_dir}")


if __name__ == "__main__":
    main()
