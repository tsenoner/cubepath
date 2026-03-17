"""SVG cube diagram generator for Cubepath guide.

Generates top-face plan-view diagrams for OLL and PLL cases.
Each diagram shows the U (top) face as a 3x3 grid with 4 side strips.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import svgwrite

# Colors
YELLOW = "#FFD500"
GREY = "#C0C0C0"
WHITE = "#FFFFFF"
RED = "#E00000"
ORANGE = "#FF8C00"
BLUE = "#0051BA"
GREEN = "#009E60"
STICKER_STROKE = "#333333"

# Layout constants
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


Y = YELLOW
G = GREY



def _arrow_pos(name: str) -> tuple[float, float]:
    """Return pixel center for a named arrow anchor position."""
    ox = MARGIN + SIDE_H + GAP  # 34
    oy = MARGIN + SIDE_H + GAP  # 34
    positions = {
        # Edge midpoints (center of middle side-strip sticker)
        "top": (ox + (CELL + GAP) + CELL / 2, MARGIN + SIDE_H / 2),
        "bottom": (ox + (CELL + GAP) + CELL / 2, oy + 3 * CELL + 2 * GAP + GAP + SIDE_H / 2),
        "left": (MARGIN + SIDE_H / 2, oy + (CELL + GAP) + CELL / 2),
        "right": (ox + 3 * CELL + 2 * GAP + GAP + SIDE_H / 2, oy + (CELL + GAP) + CELL / 2),
        # Corner midpoints (center of corner U-face stickers)
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
        # T-perm: adjacent corner swap (headlights on back, swap front two)
        CubeDiagram(
            name="pll_tperm",
            label="T-Perm",
            category="pll_corners",
            u_face=[Y] * 9,
            top_side=[RED, G, RED],
            right_side=[BLUE, G, GREEN],
            bottom_side=[ORANGE, G, ORANGE],
            left_side=[GREEN, G, BLUE],
            swaps=[("tl", "tr")],
        ),
        # Y-perm: diagonal corner swap
        CubeDiagram(
            name="pll_yperm",
            label="Y-Perm",
            category="pll_corners",
            u_face=[Y] * 9,
            top_side=[RED, G, ORANGE],
            right_side=[GREEN, G, RED],
            bottom_side=[ORANGE, G, BLUE],
            left_side=[BLUE, G, GREEN],
            swaps=[("tl", "br")],
        ),
    ]


def _pll_edge_cases() -> list[CubeDiagram]:
    """PLL edge permutation cases."""
    return [
        # Ua: 3-cycle (clockwise: top→right→bottom)
        CubeDiagram(
            name="pll_ua",
            label="Ua Perm",
            category="pll_edges",
            u_face=[Y] * 9,
            top_side=[RED, BLUE, RED],
            right_side=[BLUE, RED, BLUE],
            bottom_side=[ORANGE, ORANGE, ORANGE],
            left_side=[GREEN, GREEN, GREEN],
            cycles=[["top", "right", "bottom"]],
        ),
        # Ub: 3-cycle (counter-clockwise: top→left→bottom)
        CubeDiagram(
            name="pll_ub",
            label="Ub Perm",
            category="pll_edges",
            u_face=[Y] * 9,
            top_side=[RED, GREEN, RED],
            right_side=[BLUE, BLUE, BLUE],
            bottom_side=[ORANGE, ORANGE, ORANGE],
            left_side=[GREEN, RED, GREEN],
            cycles=[["top", "left", "bottom"]],
        ),
        # H-perm: opposite edge swap
        CubeDiagram(
            name="pll_hperm",
            label="H-Perm",
            category="pll_edges",
            u_face=[Y] * 9,
            top_side=[RED, ORANGE, RED],
            right_side=[BLUE, GREEN, BLUE],
            bottom_side=[ORANGE, RED, ORANGE],
            left_side=[GREEN, BLUE, GREEN],
            swaps=[("top", "bottom"), ("left", "right")],
        ),
        # Z-perm: adjacent edge swap
        CubeDiagram(
            name="pll_zperm",
            label="Z-Perm",
            category="pll_edges",
            u_face=[Y] * 9,
            top_side=[RED, BLUE, RED],
            right_side=[BLUE, RED, BLUE],
            bottom_side=[ORANGE, GREEN, ORANGE],
            left_side=[GREEN, ORANGE, GREEN],
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
    # Forward arrowhead
    marker = dwg.marker(
        id="arrowhead",
        insert=(6, 3),
        size=(8, 8),
        orient="auto",
        markerUnits="strokeWidth",
    )
    marker.add(dwg.polygon([(0, 0), (6, 3), (0, 6)], fill=ARROW_COLOR))
    dwg.defs.add(marker)

    # Reversed arrowhead (for marker-start on swaps)
    marker_rev = dwg.marker(
        id="arrowhead-rev",
        insert=(0, 3),
        size=(8, 8),
        orient="auto",
        markerUnits="strokeWidth",
    )
    marker_rev.add(dwg.polygon([(6, 0), (0, 3), (6, 6)], fill=ARROW_COLOR))
    dwg.defs.add(marker_rev)


def _curved_path(
    dwg: svgwrite.Drawing,
    start: tuple[float, float],
    end: tuple[float, float],
    curve_sign: float = 1.0,
) -> svgwrite.path.Path:
    """Create a curved SVG path between two points."""
    mx = (start[0] + end[0]) / 2
    my = (start[1] + end[1]) / 2
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return dwg.path(d="", fill="none")
    nx, ny = -dy / length, dx / length
    curve_offset = min(length * 0.3, 25) * curve_sign
    cx = mx + nx * curve_offset
    cy = my + ny * curve_offset

    return dwg.path(
        d=f"M {start[0]},{start[1]} Q {cx},{cy} {end[0]},{end[1]}",
        fill="none",
        stroke=ARROW_COLOR,
        stroke_width=2,
    )


def _draw_swap(
    dwg: svgwrite.Drawing,
    pos_a: str,
    pos_b: str,
) -> None:
    """Draw a single bidirectional arrow (swap) between two named positions."""
    start = _arrow_pos(pos_a)
    end = _arrow_pos(pos_b)
    path = _curved_path(dwg, start, end)
    path["marker-start"] = "url(#arrowhead-rev)"
    path["marker-end"] = "url(#arrowhead)"
    dwg.add(path)


def _draw_cycle(
    dwg: svgwrite.Drawing,
    positions: list[str],
) -> None:
    """Draw directional arrows forming a cycle through named positions."""
    for i in range(len(positions)):
        start = _arrow_pos(positions[i])
        end = _arrow_pos(positions[(i + 1) % len(positions)])
        path = _curved_path(dwg, start, end)
        path["marker-end"] = "url(#arrowhead)"
        dwg.add(path)


def render(case: CubeDiagram, output_dir: Path) -> Path:
    """Render a CubeDiagram to an SVG file."""
    grid_w = 3 * CELL + 2 * GAP
    grid_h = 3 * CELL + 2 * GAP
    total_w = 2 * MARGIN + 2 * (SIDE_H + GAP) + grid_w
    total_h = 2 * MARGIN + 2 * (SIDE_H + GAP) + grid_h

    filepath = output_dir / f"{case.name}.svg"
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
    has_arrows = case.swaps or case.cycles
    if has_arrows:
        _add_arrow_defs(dwg)
        for pos_a, pos_b in case.swaps:
            _draw_swap(dwg, pos_a, pos_b)
        for cycle in case.cycles:
            _draw_cycle(dwg, cycle)

    dwg.save(pretty=True)
    return filepath


def main() -> None:
    output_dir = Path(__file__).resolve().parents[2] / "guide" / "figures" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    cases = all_cases()
    for case in cases:
        path = render(case, output_dir)
        print(f"  {path.name}")

    print(f"\nGenerated {len(cases)} diagrams in {output_dir}")


if __name__ == "__main__":
    main()
