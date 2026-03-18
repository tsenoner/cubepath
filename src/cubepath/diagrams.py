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

    # Draw side strips
    ox = MARGIN + SIDE_H + GAP
    oy = MARGIN + SIDE_H + GAP

    # Top side strip
    for i, color in enumerate(case.top_side):
        x = ox + i * (CELL + GAP)
        y = MARGIN
        dwg.add(
            dwg.rect(
                (x, y),
                (CELL, SIDE_H),
                fill=color,
                stroke=STICKER_STROKE,
                stroke_width=1,
                rx=2,
                ry=2,
            )
        )

    # Bottom side strip
    for i, color in enumerate(case.bottom_side):
        x = ox + i * (CELL + GAP)
        y = oy + grid_h + GAP
        dwg.add(
            dwg.rect(
                (x, y),
                (CELL, SIDE_H),
                fill=color,
                stroke=STICKER_STROKE,
                stroke_width=1,
                rx=2,
                ry=2,
            )
        )

    # Left side strip (top to bottom)
    for i, color in enumerate(case.left_side):
        x = MARGIN
        y = oy + i * (CELL + GAP)
        dwg.add(
            dwg.rect(
                (x, y),
                (SIDE_H, CELL),
                fill=color,
                stroke=STICKER_STROKE,
                stroke_width=1,
                rx=2,
                ry=2,
            )
        )

    # Right side strip (top to bottom)
    for i, color in enumerate(case.right_side):
        x = ox + grid_w + GAP
        y = oy + i * (CELL + GAP)
        dwg.add(
            dwg.rect(
                (x, y),
                (SIDE_H, CELL),
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


@dataclass
class NotationMove:
    """A single notation move diagram."""

    name: str
    filename: str
    layer: str  # R/L/U/D/F/M/f/r/x/y/z
    clockwise: bool


def _notation_moves() -> list[NotationMove]:
    return [
        NotationMove("R", "move_r", "R", True),
        NotationMove("R'", "move_r_prime", "R", False),
        NotationMove("U", "move_u", "U", True),
        NotationMove("U'", "move_u_prime", "U", False),
        NotationMove("L", "move_l", "L", True),
        NotationMove("L'", "move_l_prime", "L", False),
        NotationMove("F", "move_f", "F", True),
        NotationMove("F'", "move_f_prime", "F", False),
        NotationMove("D", "move_d", "D", True),
        NotationMove("D'", "move_d_prime", "D", False),
        NotationMove("M", "move_m", "M", True),
        NotationMove("f", "move_fw", "f", True),
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


def _n_in_layer(face: str, a: int, b: int, layer: str) -> bool:
    """Check if sticker (a,b) on visible face belongs to turning layer.

    Face U: a=col_x, b=col_z.  Face F: a=col_x, b=col_y.  Face R: a=col_z, b=col_y.
    """
    tbl = {
        "U": {
            "R": a == 2,
            "L": a == 0,
            "U": True,
            "D": False,
            "F": b == 2,
            "M": a == 1,
            "f": b >= 1,
            "r": a >= 1,
            "x": True,
            "y": True,
            "z": True,
        },
        "F": {
            "R": a == 2,
            "L": a == 0,
            "U": b == 2,
            "D": b == 0,
            "F": True,
            "M": a == 1,
            "f": True,
            "r": a >= 1,
            "x": True,
            "y": True,
            "z": True,
        },
        "R": {
            "R": True,
            "L": False,
            "U": b == 2,
            "D": b == 0,
            "F": a == 2,
            "M": False,
            "f": a >= 1,
            "r": True,
            "x": True,
            "y": True,
            "z": True,
        },
    }
    return tbl.get(face, {}).get(layer, False)


def _n_sticker_color(face: str, a: int, b: int, layer: str, cw: bool) -> str:
    """Get sticker color at (face, a, b) after one move applied to a solved cube.

    This shows the RESULT of the move so readers see which stickers moved where.
    Hidden face colors: B=Orange, L=Blue, D=White.
    """
    base = _CUBE_FACE_COLORS[face]
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
    # L / L'
    elif layer == "L" and cw:
        if face == "U" and a == 0:
            return ORANGE  # from B
        if face == "F" and a == 0:
            return YELLOW  # from U
    elif layer == "L" and not cw:
        if face == "U" and a == 0:
            return RED  # from F
        if face == "F" and a == 0:
            return WHITE  # from D
    # U / U'
    elif layer == "U" and cw:
        if face == "F" and b == 2:
            return BLUE  # from L
        if face == "R" and b == 2:
            return RED  # from F
    elif layer == "U" and not cw:
        if face == "F" and b == 2:
            return GREEN  # from R
        if face == "R" and b == 2:
            return ORANGE  # from B
    # D / D'
    elif layer == "D" and cw:
        if face == "F" and b == 0:
            return BLUE  # from L
        if face == "R" and b == 0:
            return RED  # from F
    elif layer == "D" and not cw:
        if face == "F" and b == 0:
            return GREEN  # from R
        if face == "R" and b == 0:
            return ORANGE  # from B
    # F / F'
    elif layer == "F" and cw:
        if face == "U" and b == 2:
            return BLUE  # from L
        if face == "R" and a == 2:
            return YELLOW  # from U
    elif layer == "F" and not cw:
        if face == "U" and b == 2:
            return GREEN  # from R
        if face == "R" and a == 2:
            return WHITE  # from D
    # M (same direction as L)
    elif layer == "M" and cw:
        if face == "U" and a == 1:
            return ORANGE
        if face == "F" and a == 1:
            return YELLOW
    # f (wide F)
    elif layer == "f" and cw:
        if face == "U" and b >= 1:
            return BLUE
        if face == "R" and a >= 1:
            return YELLOW
    # r (wide R)
    elif layer == "r" and cw:
        if face == "U" and a >= 1:
            return RED
        if face == "F" and a >= 1:
            return WHITE
    # x (whole cube like R)
    elif layer == "x" and cw:
        if face == "U":
            return RED
        if face == "F":
            return WHITE
    # y (whole cube like U) — show green on front (from R), orange on right (from B)
    elif layer == "y" and cw:
        if face == "F":
            return GREEN
        if face == "R":
            return ORANGE
    # z (whole cube like F)
    elif layer == "z" and cw:
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
    """Draw a quarter-arc arrow curving over a cube corner, detached from the surface.

    Each arrow is a 90° arc in the rotation plane, placed at a cube corner where
    two visible faces meet. The arc is offset outward so it floats outside the cube.
    One leg points toward each face; the arrowhead shows the sticker flow direction
    (e.g. R CW: from F face over the corner to U face = white→red).
    """
    is_whole = layer in ("x", "y", "z")

    # Per-move config: (corner, v1, v2, offset_dir, cw_to_v2)
    #   corner:     3D point where the arrow sits (cube corner or mid-edge)
    #   v1, v2:     outward face normals at the corner (arc curves OUTSIDE the cube)
    #   offset_dir: push the arc center for detachment
    #   cw_to_v2:   True → CW arrowhead at v2 end; False → at v1 end
    _cfgs: dict[str, tuple[
        tuple[float, ...], tuple[float, ...], tuple[float, ...],
        tuple[float, ...], bool,
    ]] = {
        # R: top of F-R ridge. v1=F outward(+z), v2=U outward(+y). R CW → F→U.
        "R": ((3, 3, 3), (0, 0, 1), (0, 1, 0), (-1, 0, 0), True),
        # L: top of F-L edge. v1=F outward(+z), v2=U outward(+y). L CW → U→F.
        "L": ((0, 3, 3), (0, 0, 1), (0, 1, 0), (1, 0, 0), False),
        # U: top-front-right. v1=F outward(+z), v2=R outward(+x). U CW → F→R.
        "U": ((3, 3, 3), (0, 0, 1), (1, 0, 0), (0, 1, 0), True),
        # D: bottom-front-right. v1=F outward(+z), v2=R outward(+x). D CW → F→R.
        "D": ((3, 0, 3), (0, 0, 1), (1, 0, 0), (0, 1, 0), True),
        # F: top-front-right. v1=U outward(+y), v2=R outward(+x). F CW → U→R.
        "F": ((3, 3, 3), (0, 1, 0), (1, 0, 0), (0, 0, 1), True),
        # M: top of mid-F at x=1. Same plane as L. M CW → U→F.
        "M": ((1, 3, 3), (0, 0, 1), (0, 1, 0), (1, 0, 0), False),
        # f: wide F, centered between two front layers at z=2 on U-R ridge.
        "f": ((3, 3, 2), (0, 1, 0), (1, 0, 0), (0, 0, 1), True),
        # r: wide R, centered at x=2 on F-R ridge (over 2nd and 3rd columns).
        "r": ((2, 3, 3), (0, 0, 1), (0, 1, 0), (1, 0, 0), True),
        # x: whole cube (like R), centered at x=1.5 on F-R ridge edge.
        "x": ((1.5, 3, 3), (0, 0, 1), (0, 1, 0), (1, 0, 0), True),
        # y: whole cube (like U), on F-R ridge midpoint, arrow from orange(R) to green(F).
        "y": ((3, 1.5, 3), (0, 0, 1), (1, 0, 0), (-1, 0, 0), False),
        # z: whole cube (like F), centered at midpoint of U-R ridge (top to right).
        "z": ((3, 3, 1.5), (0, 1, 0), (1, 0, 0), (0, 0, 1), True),
    }

    corner, v1, v2, offset_dir, cw_to_v2 = _cfgs[layer]

    # Determine which end gets the arrowhead
    if clockwise == cw_to_v2:
        start_v, end_v = v1, v2
    else:
        start_v, end_v = v2, v1

    # Build 3D quarter-circle arc, offset outward from the corner
    offset_dist = 0.5
    radius = 0.8
    cx = corner[0] + offset_dir[0] * offset_dist
    cy = corner[1] + offset_dir[1] * offset_dist
    cz = corner[2] + offset_dir[2] * offset_dist

    n_pts = 20
    pts_3d = []
    for i in range(n_pts + 1):
        t = (math.pi / 2) * i / n_pts
        px = cx + radius * (start_v[0] * math.cos(t) + end_v[0] * math.sin(t))
        py = cy + radius * (start_v[1] * math.cos(t) + end_v[1] * math.sin(t))
        pz = cz + radius * (start_v[2] * math.cos(t) + end_v[2] * math.sin(t))
        pts_3d.append((px, py, pz))

    pts = [_n_proj(*p) for p in pts_3d]

    # Shorten arc at tip end and add arrowhead
    tip = pts[-1]
    prev = pts[-4]
    dx, dy = tip[0] - prev[0], tip[1] - prev[1]
    ln = math.hypot(dx, dy)
    sz = 10
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
            stroke_width=2.5,
            **stroke_extra,
        )
    )

    if ln > 0:
        base1 = (tip[0] - sz * dx + sz * 0.4 * nx, tip[1] - sz * dy + sz * 0.4 * ny)
        base2 = (tip[0] - sz * dx - sz * 0.4 * nx, tip[1] - sz * dy - sz * 0.4 * ny)
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
    for edge_a, edge_b in [
        ((0, 3, 0), (3, 3, 0)),
        ((3, 3, 0), (3, 0, 0)),
        ((3, 0, 0), (3, 0, 3)),
        ((3, 0, 3), (0, 0, 3)),
        ((0, 0, 3), (0, 3, 3)),
        ((0, 3, 3), (0, 3, 0)),
        ((3, 3, 3), (0, 3, 3)),
        ((3, 3, 3), (3, 3, 0)),
        ((3, 3, 3), (3, 0, 3)),
    ]:
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

    print(f"\nGenerated {len(cases)} case diagrams + {len(moves)} notation moves in {output_dir}")


if __name__ == "__main__":
    main()
