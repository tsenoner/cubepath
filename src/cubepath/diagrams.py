"""SVG cube diagram generator for Cubepath guide.

Generates top-face plan-view diagrams for OLL and PLL cases,
plus 3D isometric notation move diagrams.
"""

from __future__ import annotations

import math
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
_N_COS30 = math.cos(math.radians(30))
_N_W, _N_H = 155, 190
_N_CX, _N_CY = _N_W / 2, 66

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


def _notation_moves() -> list[NotationMove]:
    return [
        NotationMove("R", "move_r", "R", True),
        NotationMove("R'", "move_r_prime", "R", False),
        NotationMove("R2", "move_r2", "R2", True),
        NotationMove("U", "move_u", "U", True),
        NotationMove("L", "move_l", "L", True),
        NotationMove("F", "move_f", "F", True),
        NotationMove("D", "move_d", "D", True),
        NotationMove("B", "move_b", "B", True),
        NotationMove("M", "move_m", "M", True),
        NotationMove("S", "move_s", "S", True),
        NotationMove("E", "move_e", "E", True),
        NotationMove("r", "move_rw", "r", True),
        NotationMove("x", "move_x", "x", True),
        NotationMove("y", "move_y", "y", True),
        NotationMove("z", "move_z", "z", True),
    ]


def _n_proj(x: float, y: float, z: float) -> tuple[float, float]:
    """Isometric 3D→2D projection for notation diagrams."""
    return (
        round((x - z) * _N_COS30 * _N_SCALE + _N_CX, 1),
        round(((x + z) * 0.5 - y) * _N_SCALE + _N_CY, 1),
    )


def _n_sticker_color(face: str, a: int, b: int, layer: str, cw: bool) -> str:
    """Get sticker color at (face, a, b) after one move applied to a solved cube.

    This shows the RESULT of the move so readers see which stickers moved where.
    Hidden face colors: B=Orange, L=Blue, D=White.
    """
    base = _CUBE_FACE_COLORS[face]
    # R2 (180°: U↔D, F↔B on the R column)
    if layer == "R2":
        if face == "U" and a == 2:
            return WHITE  # from D
        if face == "F" and a == 2:
            return ORANGE  # from B
        return base
    # R / R'
    if layer == "R" and cw:
        if face == "U" and a == 2:
            return RED  # from F
        if face == "F" and a == 2:
            return WHITE  # from D
    elif layer == "R" and not cw:
        if face == "U" and a == 2:
            return ORANGE  # from B
        if face == "F" and a == 2:
            return YELLOW  # from U
    # L CW
    elif layer == "L":
        if face == "U" and a == 0:
            return ORANGE  # from B
        if face == "F" and a == 0:
            return YELLOW  # from U
    # U CW
    elif layer == "U":
        if face == "F" and b == 2:
            return GREEN  # from R
        if face == "R" and b == 2:
            return ORANGE  # from B
    # D CW
    elif layer == "D":
        if face == "F" and b == 0:
            return BLUE  # from L
        if face == "R" and b == 0:
            return RED  # from F
    # F CW
    elif layer == "F":
        if face == "U" and b == 2:
            return BLUE  # from L
        if face == "R" and a == 2:
            return YELLOW  # from U
    # B CW
    elif layer == "B":
        if face == "U" and b == 0:
            return GREEN  # from R
        if face == "R" and a == 0:
            return WHITE  # from D
    # M CW (follows L)
    elif layer == "M":
        if face == "U" and a == 1:
            return ORANGE
        if face == "F" and a == 1:
            return YELLOW
    # S CW (follows F)
    elif layer == "S":
        if face == "U" and b == 1:
            return BLUE  # from L
        if face == "R" and a == 1:
            return YELLOW  # from U
    # E CW (follows D)
    elif layer == "E":
        if face == "F" and b == 1:
            return GREEN  # from R
        if face == "R" and b == 1:
            return ORANGE  # from B
    # r CW (wide R)
    elif layer == "r":
        if face == "U" and a >= 1:
            return RED
        if face == "F" and a >= 1:
            return WHITE
    # x CW (whole cube like R)
    elif layer == "x":
        if face == "U":
            return RED
        if face == "F":
            return WHITE
    # y CW (whole cube like U)
    elif layer == "y":
        if face == "F":
            return GREEN
        if face == "R":
            return ORANGE
    # z CW (whole cube like F)
    elif layer == "z":
        if face == "U":
            return BLUE
        if face == "R":
            return YELLOW
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

    # Generate quadratic Bezier curve in 3D, then project to 2D
    n_pts = 20
    pts_3d = []
    for i in range(n_pts + 1):
        t = i / n_pts
        t1 = (1 - t) ** 2
        t2 = 2 * t * (1 - t)
        t3 = t**2
        pts_3d.append(
            (
                t1 * src[0] + t2 * ctrl[0] + t3 * dst[0],
                t1 * src[1] + t2 * ctrl[1] + t3 * dst[1],
                t1 * src[2] + t2 * ctrl[2] + t3 * dst[2],
            )
        )
    pts = [_n_proj(*p) for p in pts_3d]

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


def render_notation(move: NotationMove, output_dir: Path) -> Path:
    """Render a notation move diagram (3D isometric cube) to SVG."""
    subdir = output_dir / "notation"
    subdir.mkdir(parents=True, exist_ok=True)
    filepath = subdir / f"{move.filename}.svg"
    dwg = svgwrite.Drawing(
        str(filepath),
        size=(f"{_N_W}px", f"{_N_H}px"),
        viewBox=f"0 0 {_N_W} {_N_H}",
    )
    dwg.add(dwg.rect((0, 0), (_N_W, _N_H), fill=WHITE, rx=6, ry=6))
    # Stickers (draw order: right → front → top for correct layering)
    for vis_face in ("R", "F", "U"):
        for a in range(3):
            for b in range(3):
                pts = _n_sticker_pts(vis_face, a, b)
                color = _n_sticker_color(vis_face, a, b, move.layer, move.clockwise)
                dwg.add(dwg.polygon(pts, fill=color, stroke=STICKER_STROKE, stroke_width=1.2))
    # Cube outline
    for edge_a, edge_b in _CUBE_OUTLINE_EDGES:
        dwg.add(
            dwg.line(
                _n_proj(*edge_a),
                _n_proj(*edge_b),
                stroke=STICKER_STROKE,
                stroke_width=1.5,
            )
        )
    # Rotation arrow
    _n_draw_arrow(dwg, move.layer, move.clockwise)
    # Label (large, prominent)
    dwg.add(
        dwg.text(
            move.name,
            insert=(_N_W / 2, _N_H - 6),
            text_anchor="middle",
            font_size="24px",
            font_family="sans-serif",
            font_weight="bold",
            fill="#222",
        )
    )
    dwg.save(pretty=True)
    return filepath


def render_overview(output_dir: Path) -> Path:
    """Render a summary overview diagram: one isometric cube with 6 labeled axis arrows."""
    subdir = output_dir / "notation"
    subdir.mkdir(parents=True, exist_ok=True)
    filepath = subdir / "overview.svg"

    ov_w, ov_h = 240, 200
    ov_cx, ov_cy = ov_w / 2, 90
    scale = 22
    cos30 = _N_COS30

    def proj(x: float, y: float, z: float) -> tuple[float, float]:
        return (
            round((x - z) * cos30 * scale + ov_cx, 1),
            round(((x + z) * 0.5 - y) * scale + ov_cy, 1),
        )

    dwg = svgwrite.Drawing(
        str(filepath),
        size=(f"{ov_w}px", f"{ov_h}px"),
        viewBox=f"0 0 {ov_w} {ov_h}",
    )
    dwg.add(dwg.rect((0, 0), (ov_w, ov_h), fill=WHITE, rx=8, ry=8))

    # Draw cube faces (solid colors, no sticker grid)
    face_colors = [
        # U face (top) — Yellow
        ([(0, 3, 0), (3, 3, 0), (3, 3, 3), (0, 3, 3)], YELLOW),
        # F face (front-left) — Red
        ([(0, 0, 3), (3, 0, 3), (3, 3, 3), (0, 3, 3)], RED),
        # R face (front-right) — Green
        ([(3, 0, 0), (3, 0, 3), (3, 3, 3), (3, 3, 0)], GREEN),
    ]
    for corners, color in face_colors:
        pts = [proj(*c) for c in corners]
        dwg.add(dwg.polygon(pts, fill=color, stroke=STICKER_STROKE, stroke_width=1.5))

    # Cube outline
    for ea, eb in _CUBE_OUTLINE_EDGES:
        dwg.add(dwg.line(proj(*ea), proj(*eb), stroke=STICKER_STROKE, stroke_width=1.5))

    # Axis arrows: face center → outward, with label
    axes = [
        ("U", (1.5, 3, 1.5), (1.5, 4.8, 1.5)),
        ("D", (1.5, 0, 1.5), (1.5, -1.2, 1.5)),
        ("F", (1.5, 1.5, 3), (1.5, 1.5, 4.8)),
        ("B", (1.5, 1.5, 0), (1.5, 1.5, -1.2)),
        ("R", (3, 1.5, 1.5), (4.8, 1.5, 1.5)),
        ("L", (0, 1.5, 1.5), (-1.2, 1.5, 1.5)),
    ]

    # Add arrowhead marker
    marker = dwg.marker(
        id="ov-arrow",
        insert=(5, 5),
        size=(10, 10),
        orient="auto",
        markerUnits="userSpaceOnUse",
    )
    marker.add(dwg.polygon([(0, 1), (10, 5), (0, 9)], fill=ARROW_COLOR))
    dwg.defs.add(marker)

    for label, start_3d, end_3d in axes:
        s = proj(*start_3d)
        e = proj(*end_3d)
        line = dwg.line(s, e, stroke=ARROW_COLOR, stroke_width=2)
        line["marker-end"] = "url(#ov-arrow)"
        dwg.add(line)
        # Label offset: push text slightly past the arrow tip
        dx, dy = e[0] - s[0], e[1] - s[1]
        ln = math.hypot(dx, dy)
        if ln > 0:
            lx = e[0] + dx / ln * 12
            ly = e[1] + dy / ln * 12
        else:
            lx, ly = e[0], e[1]
        dwg.add(
            dwg.text(
                label,
                insert=(lx, ly + 5),
                text_anchor="middle",
                font_size="16px",
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

    cases = all_cases()
    for case in cases:
        path = render(case, output_dir)
        print(f"  {path.relative_to(output_dir)}")

    moves = _notation_moves()
    for move in moves:
        path = render_notation(move, output_dir)
        print(f"  {path.relative_to(output_dir)}")

    overview_path = render_overview(output_dir)
    print(f"  {overview_path.relative_to(output_dir)}")

    print(
        f"\nGenerated {len(cases)} case diagrams + {len(moves)} notation moves"
        f" + 1 overview in {output_dir}"
    )


if __name__ == "__main__":
    main()
