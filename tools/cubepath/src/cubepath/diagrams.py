"""SVG cube diagram generator for Cubepath guide.

Generates top-face plan-view diagrams for OLL and PLL cases,
plus 3D isometric notation move diagrams.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import svgwrite

from cubepath import palette
from cubepath.algs import ALGORITHMS, DOT_SEQUENCE
from cubepath.cube import Cube, diagram_to_sim, state_before

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


# ── Theme ─────────────────────────────────────────────────────────────
# An <img>-loaded SVG cannot read the host page's CSS custom properties, so —
# exactly like `logo.render()` and app/public/favicon.svg — every screen
# diagram carries its own colour-scheme rules. A class rule beats a `fill=`
# presentation attribute everywhere (Chromium, Firefox, resvg), so callers
# keep emitting `fill=WHITE` as the no-CSS fallback.
#
# The plate is transparent on the *web* in both schemes: the diagram should sit
# on the page surface it is printed on, not on a second card. resvg (typst)
# skips every @media block, so the declaration order below leaves the guide PDF
# with the opaque white plate it has always had — which it needs, because 13
# figures sit inside a tinted `.algorithm` callout. Verified with a real
# `typst compile`, not assumed.
#
# Only the plate and the label ink flip. Sticker strokes and arrows are read
# against coloured faces, so they stay as they are.
DARK_INK = "#ECE8E1"  # tokens.css --ink, dark

_THEME_CSS = (
    f".bg{{fill:{WHITE}}}.ink{{fill:{ARROW_COLOR}}}"
    "@media (prefers-color-scheme:light){.bg{fill:none}}"
    f"@media (prefers-color-scheme:dark){{.bg{{fill:none}}.ink{{fill:{DARK_INK}}}}}"
)


def _add_theme(dwg: svgwrite.Drawing) -> None:
    """Give the drawing its own light/dark rules."""
    dwg.defs.add(dwg.style(_THEME_CSS))


# svgwrite ships no type information, so every element it hands back is Any.
Point = tuple[float, float]


def _bg(dwg: svgwrite.Drawing, insert: Point, size: Point, radius: int) -> Any:
    """The rounded background plate, tagged so the web themes can drop it."""
    rect = dwg.rect(insert, size, fill=WHITE, rx=radius, ry=radius)
    rect["class"] = "bg"
    return rect


def _ink(elem: Any) -> Any:
    """Tag a label or dot drawn on the plate rather than on a sticker."""
    elem["class"] = "ink"
    return elem


# ── Render styles ─────────────────────────────────────────────────────
# The app is backlit and the guide is read on paper at full size. A card
# sticker is under 5 mm wide and often printed on a mono laser, where hue is
# gone and only luminance survives — #FFD500 on #C0C0C0 is 1.28:1, ten
# identical grey squares. So the card re-renders every diagram in its own
# palette rather than post-processing the screen SVG.


@dataclass(frozen=True)
class DiagramStyle:
    """Everything that differs between a screen diagram and a printed one."""

    faces: dict[str, str]  # simulator colour letter -> hex
    masked: str  # the "not solved yet" fill on OLL diagrams
    band_u: int  # side-band thickness in viewBox units
    stroke_main: float  # U-face sticker outline
    stroke_side: float  # side-band sticker outline
    stroke_arrow: float  # PLL permutation arrows
    layer_lines: float  # opacity of the overview's layer lines on a solid face
    themed: bool = True  # emit the light/dark <style> block (screen only)


SCREEN_FACES: dict[str, str] = {
    "Y": YELLOW,
    "R": RED,
    "G": GREEN,
    "O": ORANGE,
    "B": BLUE,
    "W": WHITE,
}

# Measured against `palette.contrast`, not chosen by eye. Every side-face pair
# improves in greyscale — the worst (red/green) goes 1.45 -> 1.96, and the
# inverting pair red/orange, which are opposite faces and so appear together
# on every diagram, goes 2.16 -> 4.00. Yellow keeps its screen value: it is
# the reference every OLL diagram reads against, and the masked grey moves
# instead (1.28 -> 4.49 against it). `tests/test_diagrams.py` gates all of it.
#
# The one pair that gets worse is yellow/orange, 1.64 -> 1.42. It is not
# load-bearing: a yellow U sticker never abuts an orange band directly, both
# carry a #333333 outline at stroke width 2.4, and a band is a different shape
# from a grid cell. Buying it back would cost the red/orange separation.
CARD_FACES: dict[str, str] = {
    "Y": YELLOW,
    "R": "#A30A0A",
    "G": "#0A9048",
    "O": "#FFA13C",
    "B": "#001A5C",
    "W": WHITE,
}

SCREEN = DiagramStyle(
    faces=SCREEN_FACES,
    masked=GREY,
    band_u=SIDE_H,
    stroke_main=1.5,
    # ints, not floats: svgwrite writes the value verbatim, so 1.0 would
    # rewrite every committed screen SVG for no visual change.
    stroke_side=1,
    stroke_arrow=2,
    layer_lines=0.5,
)
CARD = DiagramStyle(
    faces=CARD_FACES,
    # A printed card is ink on paper: no page behind it to show through.
    themed=False,
    masked="#5F5F5F",
    band_u=20,
    stroke_main=3.2,
    stroke_side=2.4,
    stroke_arrow=4.5,
    # On a mono laser the lines are the only structure on a solid face.
    layer_lines=0.9,
)


def _restyle(style: DiagramStyle) -> dict[str, str]:
    """SCREEN hex -> this style's hex. Derived from the two palettes, so a
    face colour can never be remapped by a hand-written substitution."""
    remap = {SCREEN_FACES[k]: style.faces[k] for k in SCREEN_FACES}
    remap[GREY] = style.masked
    return remap


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

# Simulator color letter → diagram hex color
_SIM_COLOR = {"Y": YELLOW, "R": RED, "G": GREEN, "O": ORANGE, "B": BLUE, "W": WHITE}


def _colorize(strip: list[str]) -> list[str]:
    """Simulator color letters → diagram hex colors."""
    return [_SIM_COLOR[s] for s in strip]


def _u_layer_views(cube: Cube) -> tuple[list[str], dict[str, list[str]]]:
    """Plan-view of the U layer: u_face (row 0 = back) + side strips.

    Side strips are read left-to-right (top/bottom) and top-to-bottom
    (left/right) as viewed from above with the front face at the bottom.
    """
    sides = {
        "top": [cube.faces["B"][2], cube.faces["B"][1], cube.faces["B"][0]],
        "right": [cube.faces["R"][2], cube.faces["R"][1], cube.faces["R"][0]],
        "bottom": [cube.faces["F"][0], cube.faces["F"][1], cube.faces["F"][2]],
        "left": [cube.faces["L"][0], cube.faces["L"][1], cube.faces["L"][2]],
    }
    return list(cube.faces["U"]), sides


def _yellow_mask(stickers: list[str]) -> list[str]:
    return [YELLOW if s == "Y" else GREY for s in stickers]


def _derived_cross_case(name: str, label: str, alg: str, *, view_turn: str = "") -> CubeDiagram:
    """OLL cross case derived from its algorithm's pre-state.

    Shows the U-face edge/center pattern; corners are GREY (don't-care at
    the cross stage). `view_turn` reorients the derived state so the diagram
    matches how the guide tells the learner to hold the cube.
    """
    cube = state_before(alg)
    if view_turn:
        cube.apply(view_turn)
    u, _ = _u_layer_views(cube)
    u_face = _yellow_mask(u)
    for corner in (0, 2, 6, 8):
        u_face[corner] = GREY
    return CubeDiagram(name=name, label=label, category="oll_cross", u_face=u_face)


def _derived_oll_corner_case(name: str, label: str, alg: str) -> CubeDiagram:
    """OLL corner case derived from its algorithm's pre-state (cross solved)."""
    cube = state_before(alg)
    u, sides = _u_layer_views(cube)
    assert all(u[i] == "Y" for i in (1, 3, 4, 5, 7)), f"{name}: cross not solved in pre-state"
    return CubeDiagram(
        name=name,
        label=label,
        category="oll_corners",
        u_face=_yellow_mask(u),
        top_side=_yellow_mask(sides["top"]),
        right_side=_yellow_mask(sides["right"]),
        bottom_side=_yellow_mask(sides["bottom"]),
        left_side=_yellow_mask(sides["left"]),
    )


def _derived_pll_case(
    name: str,
    label: str,
    alg: str,
    *,
    category: str,
    swaps: list[tuple[str, str]] | None = None,
    cycles: list[list[str]] | None = None,
    dashed_swaps: list[tuple[str, str]] | None = None,
) -> CubeDiagram:
    """PLL case with true side-sticker colors derived from the algorithm's pre-state.

    Arrows stay hand-declared for layout, but tests verify them against the
    piece permutation implied by the same pre-state.
    """
    cube = state_before(alg)
    u, sides = _u_layer_views(cube)
    assert all(s == "Y" for s in u), f"{name}: U face not fully yellow in pre-state"
    return CubeDiagram(
        name=name,
        label=label,
        category=category,
        u_face=[YELLOW] * 9,
        top_side=_colorize(sides["top"]),
        right_side=_colorize(sides["right"]),
        bottom_side=_colorize(sides["bottom"]),
        left_side=_colorize(sides["left"]),
        swaps=swaps or [],
        cycles=cycles or [],
        dashed_swaps=dashed_swaps or [],
    )


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
    """OLL cross cases: Dot, Hook (L-shape), Line — derived from their algorithms.

    The Hook diagram is drawn at the Phase-1 angle (L in back-left, where
    F-sexy-F' turns it into a Line); Phase 1.5 rotates the image 180° to the
    f-sexy-f' angle (L in front-right).
    """
    return [
        _derived_cross_case("oll_dot", "Dot", DOT_SEQUENCE),
        _derived_cross_case("oll_hook", "Hook / L-shape", ALGORITHMS["f-sexy-f'"], view_turn="y2"),
        _derived_cross_case("oll_line", "Line", ALGORITHMS["F-sexy-F'"]),
    ]


def _oll_corner_cases() -> list[CubeDiagram]:
    """OLL corner orientation cases (yellow cross done) — derived from their algorithms."""
    cases = [
        _derived_oll_corner_case("oll_sune", "Sune", ALGORITHMS["Sune"]),
        _derived_oll_corner_case("oll_antisune", "Anti-Sune", ALGORITHMS["Anti-Sune"]),
        _derived_oll_corner_case("oll_pi", "Pi / Double Sune", ALGORITHMS["Pi"]),
        _derived_oll_corner_case("oll_headlights", "Headlights", ALGORITHMS["Headlights"]),
        _derived_oll_corner_case(
            "oll_double_headlights", "Double Headlights", ALGORITHMS["Double Headlights"]
        ),
        _derived_oll_corner_case("oll_chameleon", "Chameleon", ALGORITHMS["Chameleon"]),
        _derived_oll_corner_case("oll_bowtie", "Bowtie", ALGORITHMS["Bowtie"]),
    ]
    cases.append(
        CubeDiagram(
            name="oll_solved",
            label="All Corners Yellow",
            category="oll_corners",
            u_face=[Y, Y, Y, Y, Y, Y, Y, Y, Y],
        )
    )
    return cases


def _pll_corner_cases() -> list[CubeDiagram]:
    """PLL corner permutation cases — side colors derived from their algorithms."""
    return [
        # T-perm: adjacent corner swap (headlights left, swap right-side corners)
        _derived_pll_case(
            "pll_tperm",
            "T-Perm",
            ALGORITHMS["T-Perm"],
            category="pll_corners",
            swaps=[("tr", "br")],
            dashed_swaps=[("right", "left")],
        ),
        # Y-perm: diagonal corner swap (UBL↔UFR) + edge swap (UB↔UL)
        _derived_pll_case(
            "pll_yperm",
            "Y-Perm",
            ALGORITHMS["Y-Perm"],
            category="pll_corners",
            swaps=[("tl", "br")],
            dashed_swaps=[("top", "left")],
        ),
    ]


def _pll_edge_cases() -> list[CubeDiagram]:
    """PLL edge permutation cases — side colors derived from their algorithms."""
    return [
        # Ua: 3-cycle (front→right→left, solved edge at back)
        _derived_pll_case(
            "pll_ua",
            "Ua Perm",
            ALGORITHMS["Ua"],
            category="pll_edges",
            cycles=[["bottom", "right", "left"]],
        ),
        # Ub: 3-cycle (front→left→right, solved edge at back)
        _derived_pll_case(
            "pll_ub",
            "Ub Perm",
            ALGORITHMS["Ub"],
            category="pll_edges",
            cycles=[["bottom", "left", "right"]],
        ),
        # H-perm: opposite edge swap
        _derived_pll_case(
            "pll_hperm",
            "H-Perm",
            ALGORITHMS["H-Perm"],
            category="pll_edges",
            swaps=[("top", "bottom"), ("left", "right")],
        ),
        # Z-perm: adjacent edge swap
        _derived_pll_case(
            "pll_zperm",
            "Z-Perm",
            ALGORITHMS["Z-Perm"],
            category="pll_edges",
            swaps=[("bottom", "right"), ("left", "top")],
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
    width: float,
) -> svgwrite.path.Path:
    """Create a straight arrow path between two named positions."""
    start = _arrow_pos(pos_a)
    end = _arrow_pos(pos_b)
    return dwg.path(
        d=f"M {start[0]},{start[1]} L {end[0]},{end[1]}",
        fill="none",
        stroke=ARROW_COLOR,
        stroke_width=width,
    )


def _draw_swap(
    dwg: svgwrite.Drawing,
    pos_a: str,
    pos_b: str,
    width: float,
    *,
    dashed: bool = False,
) -> None:
    """Draw a single bidirectional arrow (swap) between two named positions."""
    path = _arrow_path(dwg, pos_a, pos_b, width)
    path["marker-start"] = "url(#arrowhead-rev)"
    path["marker-end"] = "url(#arrowhead)"
    if dashed:
        path.dasharray([4, 3])
    dwg.add(path)


def _draw_cycle(
    dwg: svgwrite.Drawing,
    positions: list[str],
    width: float,
) -> None:
    """Draw directional arrows forming a cycle through named positions."""
    for i in range(len(positions)):
        a = positions[i]
        b = positions[(i + 1) % len(positions)]
        path = _arrow_path(dwg, a, b, width)
        path["marker-end"] = "url(#arrowhead)"
        dwg.add(path)


def _case_subdir(category: str) -> str:
    """Return subdirectory name for a diagram category."""
    if category == "oll_full":
        return "oll-full"
    if category == "pll_full":
        return "pll-full"
    if category.startswith("oll"):
        return "oll"
    if category.startswith("pll"):
        return "pll"
    return ""


def render(case: CubeDiagram, output_dir: Path, style: DiagramStyle = SCREEN) -> Path:
    """Render a CubeDiagram to an SVG file in the given style."""
    recolor = _restyle(style)
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
    if style.themed:
        _add_theme(dwg)
    dwg.add(_bg(dwg, (0, 0), (total_w, total_h), 8))

    # Draw U face (3x3 grid)
    for idx, color in enumerate(case.u_face):
        r, c = idx // 3, idx % 3
        x, y = _grid_to_px(c, r)
        dwg.add(
            dwg.rect(
                (x, y),
                (CELL, CELL),
                fill=recolor.get(color, color),
                stroke=STICKER_STROKE,
                stroke_width=style.stroke_main,
                rx=RADIUS,
                ry=RADIUS,
            )
        )

    # Draw side strips (top, bottom, left, right)
    ox = MARGIN + SIDE_H + GAP
    oy = MARGIN + SIDE_H + GAP
    step = CELL + GAP
    # A thicker band grows *outward* into the margin: the inner edge stays put,
    # so the viewBox is unchanged and every downstream size still holds.
    band = style.band_u
    lead = MARGIN + SIDE_H - band
    side_strips = [
        # (colors, x0, y0, dx, dy, width, height)
        (case.top_side, ox, lead, step, 0, CELL, band),
        (case.bottom_side, ox, oy + grid_h + GAP, step, 0, CELL, band),
        (case.left_side, lead, oy, 0, step, band, CELL),
        (case.right_side, ox + grid_w + GAP, oy, 0, step, band, CELL),
    ]
    for colors, x0, y0, sx, sy, w, h in side_strips:
        for i, color in enumerate(colors):
            dwg.add(
                dwg.rect(
                    (x0 + i * sx, y0 + i * sy),
                    (w, h),
                    fill=recolor.get(color, color),
                    stroke=STICKER_STROKE,
                    stroke_width=style.stroke_side,
                    rx=2,
                    ry=2,
                )
            )

    # Draw arrows for PLL cases
    has_arrows = case.swaps or case.cycles or case.dashed_swaps
    if has_arrows:
        _add_arrow_defs(dwg)
        for pos_a, pos_b in case.swaps:
            _draw_swap(dwg, pos_a, pos_b, style.stroke_arrow)
        for cycle in case.cycles:
            _draw_cycle(dwg, cycle, style.stroke_arrow)
        for pos_a, pos_b in case.dashed_swaps:
            _draw_swap(dwg, pos_a, pos_b, style.stroke_arrow, dashed=True)

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

# 3D isometric cube outline edges (the notation and step diagrams)
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
    ("F", 0, 0),
    ("F", 1, 0),
    ("F", 2, 0),
    ("R", 0, 0),
    ("R", 1, 0),
    ("R", 2, 0),
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
        pts.append(
            _n_proj(
                t1 * src[0] + t2 * ctrl[0] + t3 * dst[0],
                t1 * src[1] + t2 * ctrl[1] + t3 * dst[1],
                t1 * src[2] + t2 * ctrl[2] + t3 * dst[2],
            )
        )
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
        dwg.add(
            dwg.polygon(
                [
                    tip,
                    (base[0] + sz * 0.4 * nx, base[1] + sz * 0.4 * ny),
                    (base[0] - sz * 0.4 * nx, base[1] - sz * 0.4 * ny),
                ],
                fill=ARROW_COLOR,
            )
        )


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
        ("U", 1, 0),
        ("U", 0, 1),
        ("U", 2, 1),
        ("U", 1, 2),
        ("F", 1, 2),
        ("R", 1, 2),
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
    """Corner insertion case diagrams: white faces right/front/up.

    The white-red-green corner sits above its slot at up-front-right. Its
    three legal orientations (simulator-verified — the mirror orders are
    physically impossible) are, as (U, F, R) sticker triples:
    white right = (G, R, W); white front = (R, W, G); white up = (W, G, R).
    """
    # Cross done on bottom: centers + bottom edge stickers visible on F and R
    cross_done = set(_CENTERS) | {("F", 1, 0), ("R", 1, 0)}
    return [
        StepDiagram(
            "White Right",
            "corner_right",
            cross_done,
            overrides={("U", 2, 2): GREEN, ("F", 2, 2): RED, ("R", 2, 2): WHITE},
        ),
        StepDiagram(
            "White Front",
            "corner_front",
            cross_done,
            overrides={("U", 2, 2): RED, ("F", 2, 2): WHITE, ("R", 2, 2): GREEN},
        ),
        StepDiagram(
            "White Up",
            "corner_up",
            cross_done,
            overrides={("U", 2, 2): WHITE, ("F", 2, 2): GREEN, ("R", 2, 2): RED},
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
        _CORNERS_POSITIONED | {(f, a, b) for f in ("U",) for a in range(3) for b in range(3)}
    ) - {("F", 0, 0), ("F", 2, 0), ("R", 0, 0), ("R", 2, 0)}
    return StepDiagram(
        "Orient Corner",
        "orient_corner",
        solved,
        face_colors=flipped,
        overrides={
            ("R", 2, 0): YELLOW,  # DFR: yellow on R face (CW twist)
            ("F", 2, 0): GREEN,  # DFR: green wraps to F face
            ("F", 0, 0): YELLOW,  # DFL: yellow on F face (CCW twist)
            ("R", 0, 0): RED,  # DBR: red on R face (CCW twist)
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
                ("U", 2, 2): RED,  # UFR: red on top
                ("R", 2, 2): YELLOW,  # UFR: yellow on R face
                ("F", 2, 2): GREEN,  # UFR: green on F face
            },
        ),
        StepDiagram(
            "Orient Front",
            "orient_front",
            step6,
            overrides={
                ("U", 2, 2): GREEN,  # UFR: green on top
                ("F", 2, 2): YELLOW,  # UFR: yellow on F face
                ("R", 2, 2): RED,  # UFR: red on R face
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
            ((0.5, 3, 0.5), (2.5, 3, 2.5), (1.5, 3, 1.5)),  # BL → FR (straight)
            ((2.5, 3, 2.5), (2.5, 3, 0.5), (2.5, 3, 1.5)),  # FR → BR (straight)
            ((2.5, 3, 0.5), (0.5, 3, 0.5), (1.5, 3, 0.5)),  # BR → BL (straight)
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
    """Tilted 3D→2D projection for every isometric diagram, the overview included."""
    return (
        round((x * _N_COS_H - z * _N_SIN_H) * _N_SCALE + _N_CX, 1),
        round(((x * _N_SIN_H + z * _N_COS_H) * _N_ELEV - y) * _N_SCALE + _N_CY, 1),
    )


def _cube_box() -> tuple[float, float, float, float]:
    """Projected bounding box of the cube: x0, y0, x1, y1."""
    pts = [_n_proj(x, y, z) for x in (0, 3) for y in (0, 3) for z in (0, 3)]
    return (
        min(p[0] for p in pts),
        min(p[1] for p in pts),
        max(p[0] for p in pts),
        max(p[1] for p in pts),
    )


_N_CUBE_BOX = _cube_box()

# Condition types for _STICKER_COLOR_RULES
_EQ_A, _EQ_B, _GE_A, _ANY = "a", "b", "A", "*"

# Lookup table for _n_sticker_color: (layer, cw) → [(face, cond_type, value, color), ...]
# Each entry lists the 2 rules that override the base face color for that move.
_STICKER_COLOR_RULES: dict[tuple[str, bool], list[tuple[str, str, int, str]]] = {
    ("R2", True): [("U", _EQ_A, 2, WHITE), ("F", _EQ_A, 2, ORANGE)],
    ("R", True): [("U", _EQ_A, 2, RED), ("F", _EQ_A, 2, WHITE)],
    ("R", False): [("U", _EQ_A, 2, ORANGE), ("F", _EQ_A, 2, YELLOW)],
    ("L", True): [("U", _EQ_A, 0, ORANGE), ("F", _EQ_A, 0, YELLOW)],
    ("U", True): [("F", _EQ_B, 2, GREEN), ("R", _EQ_B, 2, ORANGE)],
    ("D", True): [("F", _EQ_B, 0, BLUE), ("R", _EQ_B, 0, RED)],
    ("F", True): [("U", _EQ_B, 2, BLUE), ("R", _EQ_A, 2, YELLOW)],
    ("B", True): [("U", _EQ_B, 0, GREEN), ("R", _EQ_A, 0, WHITE)],
    ("M", True): [("U", _EQ_A, 1, ORANGE), ("F", _EQ_A, 1, YELLOW)],
    ("S", True): [("U", _EQ_B, 1, BLUE), ("R", _EQ_A, 1, YELLOW)],
    ("E", True): [("F", _EQ_B, 1, BLUE), ("R", _EQ_B, 1, RED)],
    ("r", True): [("U", _GE_A, 1, RED), ("F", _GE_A, 1, WHITE)],
    ("x", True): [("U", _ANY, 0, RED), ("F", _ANY, 0, WHITE)],
    ("y", True): [("F", _ANY, 0, GREEN), ("R", _ANY, 0, ORANGE)],
    ("z", True): [("U", _ANY, 0, BLUE), ("R", _ANY, 0, YELLOW)],
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


Vec3 = tuple[float, float, float]
Arrow3 = tuple[Vec3, Vec3, Vec3]  # src, dst, bezier control
# The move diagrams' one visual distinction: a dashed stroke means the whole
# cube turns. The overview reuses it rather than inventing a third style.
_WHOLE_CUBE_DASH = "6,3"

# Arrow configs: (cw_src_3d, cw_dst_3d, control_3d)
# src/dst = center of affected stickers on each face for CW direction.
# control = edge point pushed outward (Bezier control for the bulge).
# When CCW, src and dst swap. Shared by the move diagrams and the overview.
_N_BULGE = 0.5  # bulge offset from edge
_N_ARROW_CFGS: dict[str, Arrow3] = {
    # R CW: F col a=2 → U col a=2.  Edge: F-U at x=2.5
    "R": ((2.5, 1.5, 3), (2.5, 3, 1.5), (2.5, 3 + _N_BULGE, 3 + _N_BULGE)),
    "R2": ((2.5, 1.5, 3), (2.5, 3, 1.5), (2.5, 3 + _N_BULGE, 3 + _N_BULGE)),
    # L CW: U col a=0 → F col a=0.  Edge: F-U at x=0.5
    "L": ((0.5, 3, 1.5), (0.5, 1.5, 3), (0.5, 3 + _N_BULGE, 3 + _N_BULGE)),
    # U CW: R row b=2 → F row b=2.  Edge: F-R at y=2.5
    "U": ((3, 2.5, 1.5), (1.5, 2.5, 3), (3 + _N_BULGE, 2.5, 3 + _N_BULGE)),
    # D CW: F row b=0 → R row b=0.  Edge: F-R at y=0.5
    "D": ((1.5, 0.5, 3), (3, 0.5, 1.5), (3 + _N_BULGE, 0.5, 3 + _N_BULGE)),
    # F CW: U row b=2 → R col a=2.  Edge: U-R at z=2.5
    "F": ((1.5, 3, 2.5), (3, 1.5, 2.5), (3 + _N_BULGE, 3 + _N_BULGE, 2.5)),
    # B CW: R col a=0 → U row b=0.  Edge: U-R at z=0.5
    "B": ((3, 1.5, 0.5), (1.5, 3, 0.5), (3 + _N_BULGE, 3 + _N_BULGE, 0.5)),
    # M CW (follows L): U col a=1 → F col a=1.  Edge: F-U at x=1.5
    "M": ((1.5, 3, 1.5), (1.5, 1.5, 3), (1.5, 3 + _N_BULGE, 3 + _N_BULGE)),
    # S CW (follows F): U row b=1 → R col a=1.  Edge: U-R at z=1.5
    "S": ((1.5, 3, 1.5), (3, 1.5, 1.5), (3 + _N_BULGE, 3 + _N_BULGE, 1.5)),
    # E CW (follows D): F row b=1 → R row b=1.  Edge: F-R at y=1.5
    "E": ((1.5, 1.5, 3), (3, 1.5, 1.5), (3 + _N_BULGE, 1.5, 3 + _N_BULGE)),
    # r CW (wide R): F cols a=1,2 → U cols a=1,2.  Edge: F-U at x=2
    "r": ((2, 1.5, 3), (2, 3, 1.5), (2, 3 + _N_BULGE, 3 + _N_BULGE)),
    # x CW (whole cube, like R): F center → U center.  Edge: F-U at x=1.5
    "x": ((1.5, 1.5, 3), (1.5, 3, 1.5), (1.5, 3 + _N_BULGE, 3 + _N_BULGE)),
    # y CW (whole cube, like U): R center → F center.  Edge: F-R at y=1.5
    "y": ((3, 1.5, 1.5), (1.5, 1.5, 3), (3 + _N_BULGE, 1.5, 3 + _N_BULGE)),
    # z CW (whole cube, like F): U center → R center.  Edge: U-R at z=1.5
    "z": ((1.5, 3, 1.5), (3, 1.5, 1.5), (3 + _N_BULGE, 3 + _N_BULGE, 1.5)),
}


def _n_draw_arrow(dwg: svgwrite.Drawing, layer: str, clockwise: bool) -> None:
    """Draw a curved arrow from source face sticker center to destination face sticker center.

    Each arrow is a quadratic Bezier curve in 3D, going from the center of the
    affected row/column on one visible face to the center on the other visible face,
    curving outward over the edge between them.
    """
    is_whole = layer in ("x", "y", "z")

    cw_src, cw_dst, ctrl = _N_ARROW_CFGS[layer]
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
    stroke_extra = {"stroke_dasharray": _WHOLE_CUBE_DASH} if is_whole else {}
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


def _draw_iso_stickers(dwg: svgwrite.Drawing, color_fn: Callable[[str, int, int], str]) -> None:
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
    _, cube_top_y, _, cube_bot_y = _N_CUBE_BOX
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
    _add_theme(dwg)
    dwg.add(_bg(dwg, (0, vb_top), (_N_W, vb_h), 6))
    _draw_iso_stickers(dwg, lambda f, a, b: _n_sticker_color(f, a, b, move.layer, move.clockwise))
    _draw_cube_outline(dwg)
    # Rotation arrow
    _n_draw_arrow(dwg, move.layer, move.clockwise)
    # Label (top, above cube) — on the plate, so it flips with the theme
    dwg.add(
        _ink(
            dwg.text(
                move.name,
                insert=(_N_W / 2, label_y),
                text_anchor="middle",
                font_size=f"{label_font}px",
                font_family="sans-serif",
                font_weight="bold",
                fill=ARROW_COLOR,
            )
        )
    )
    dwg.save(pretty=True)
    return filepath


def render_step(step: StepDiagram, output_dir: Path, style: DiagramStyle = SCREEN) -> Path:
    """Render a step progress diagram (3D isometric cube) to SVG.

    The style remaps the finished sticker colour rather than the inputs, so
    `face_colors` overrides (a white-on-top hold, a flipped cube) restyle with
    everything else instead of leaking a screen colour onto a printed card.
    """
    recolor = _restyle(style)
    subdir = output_dir / "steps"
    subdir.mkdir(parents=True, exist_ok=True)
    filepath = subdir / f"{step.filename}.svg"

    # Tight canvas from cube bounding box
    min_x, min_y, max_x, max_y = _N_CUBE_BOX
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
    if style.themed:
        _add_theme(dwg)
    dwg.add(_bg(dwg, (vb_x, vb_y), (vb_w, vb_h), 6))
    _draw_iso_stickers(
        dwg,
        lambda f, a, b: recolor.get(
            c := _step_sticker_color(f, a, b, step.solved, step.face_colors, step.overrides), c
        ),
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


# ── Notation overview ───────────────────────────────────────────────────────
# The six face turns on one cube. Two layouts come out of `render_overview`.
#
# `OVERVIEW_PINS` (the shipped `overview.svg`) is the original figure's idea,
# drawn to read: a pin out of every face centre, a dot at its tip, the letter
# beyond the dot, and a 3D ribbon ring around the pin showing which way that
# face turns — clockwise as seen from outside it. The hidden faces' pins and
# rings run behind the cube, which occludes their inner half: that is what
# says "behind". The ribbon is the original geometry (a band around the axis,
# split into a back and a front half around the pin, an arrowhead in the
# band's own plane) at a radius and sweep that survive 272 px.
#
# `OVERVIEW_HUB` (`overview_hub.svg`, the backup) shows the turns as the
# reader sees them from their seat: F — the face they are looking at — spins,
# a clockwise ring in the middle of the front face with the letter inside;
# every other letter slides its layer along the edge of a face they can see.
# Which way each strip slides is derived: `_strip_arrow` marks the strip on a
# solved cube, applies the move, and points at the face the marks left for.
#
# The slices, rotations and modifiers did not fit on the same cube without
# giving it a second idiom, so they stay in the fifteen move diagrams.


@dataclass(frozen=True)
class OverviewLayout:
    """Which of the two overview drawings to render."""

    filename: str
    pins: bool  # True: six pins with ribbon rings; False: the F hub


OVERVIEW_PINS = OverviewLayout("overview", pins=True)
OVERVIEW_HUB = OverviewLayout("overview_hub", pins=False)

# Which coordinate a letter's layer is sliced along, and which slab it is.
# `tests/test_diagrams.py` checks each row against the simulator.
_LAYER_OF: dict[str, tuple[int, int]] = {
    "L": (0, 0), "M": (0, 1), "R": (0, 2),
    "D": (1, 0), "E": (1, 1), "U": (1, 2),
    "B": (2, 0), "S": (2, 1), "F": (2, 2),
}  # fmt: skip
_FACE_NORMAL: dict[str, Vec3] = {
    "U": (0, 1, 0), "D": (0, -1, 0), "F": (0, 0, 1),
    "B": (0, 0, -1), "R": (1, 0, 0), "L": (-1, 0, 0),
}  # fmt: skip
_OV_FACES: dict[str, list[Vec3]] = {
    "U": [(0, 3, 0), (3, 3, 0), (3, 3, 3), (0, 3, 3)],
    "F": [(0, 3, 3), (3, 3, 3), (3, 0, 3), (0, 0, 3)],
    "R": [(3, 3, 3), (3, 3, 0), (3, 0, 0), (3, 0, 3)],
}
_OV_ON_FACE = ("F", "U", "R")
_CUBE_CENTRE: Vec3 = (1.5, 1.5, 1.5)
# The direction toward the camera for `_n_proj`: screen-right x screen-down.
_VIEW_DIR: Vec3 = (_N_SIN_H, _N_ELEV, _N_COS_H)

# ── pins layout ──
# Screen distance from the cube centre to each tip, in viewBox units. The
# hidden faces' pins run behind the cube and need the extra reach for their
# ring to clear the silhouette.
_OV_PIN_TIP = {"front": 56.0, "back": 73.0}
_OV_PIN_RING_R = 0.72  # ring radius, in stickers
_OV_PIN_RING_IN = 0.7  # ring centre, this far back from the tip along the pin
_OV_PIN_SWEEP = math.radians(250)
_OV_PIN_HEAD = math.radians(34)  # the arrowhead's reach past the sweep end
_OV_PIN_BAND = 0.19  # ribbon half-width along the axis, in stickers
_OV_PIN_STROKE = 1.6
_OV_PIN_DOT = 4.2
_OV_PIN_LABEL_OUT = 13.0  # letter, this far beyond the dot on screen
_OV_PIN_LABEL = 15

# ── hub layout ──
_OV_HOST: dict[str, str] = {"U": "F", "L": "F", "D": "F", "R": "F", "B": "U"}
_OV_STRIP_REACH = 0.85  # half-length of a strip arrow, in stickers from the strip centre
_OV_RING_R = 0.62  # F ring radius, in stickers
_OV_RING_START = 135.0  # degrees; the gap sits top-left, away from the letter
_OV_RING_SWEEP = 270.0
_OV_LABEL = 16
_OV_LABEL_AT: dict[str, tuple[Vec3, str]] = {
    "F": ((1.5, 1.22, 3), "middle"),
    "U": ((1.5, 3, 2.35), "middle"),
    "R": ((3, 1.25, 2.35), "middle"),
    "L": ((-0.3, 1.25, 3), "end"),
    "D": ((1.5, -0.62, 3), "middle"),
    "B": ((3.3, 3.05, 0.35), "start"),
}
_OV_CHAR_W = 0.68  # bold sans-serif advance per glyph, as a fraction of size
_OV_STROKE = 3.4
_OV_HEAD = 10.0
_OV_PAD = 6
_OV_HALO_MIN_CONTRAST = 3.0


def sticker_centre(face: str, a: int, b: int) -> Vec3:
    """3D centre of a visible-face sticker (the face convention of `_n_sticker_pts`)."""
    if face == "U":
        return (a + 0.5, 3, b + 0.5)
    if face == "F":
        return (a + 0.5, b + 0.5, 3)
    if face == "R":
        return (3, b + 0.5, a + 0.5)
    raise ValueError(f"not a visible face: {face!r}")


def sticker_of(p: Vec3) -> tuple[str, int, int]:
    """The visible-face sticker a 3D point on the cube surface lies in."""
    x, y, z = p
    if y == 3:
        return ("U", math.floor(x), math.floor(z))
    if z == 3:
        return ("F", math.floor(x), math.floor(y))
    if x == 3:
        return ("R", math.floor(z), math.floor(y))
    raise ValueError(f"{p} is not on a visible face")


def slab_of(coord: float) -> int:
    """Which of the three layers a coordinate falls in. The face plane itself
    (x, y or z == 3) belongs to the outer layer."""
    return min(int(coord), 2)


def strip_stickers(face: str, token: str) -> list[tuple[str, int, int]]:
    """The stickers of `face` that lie in the layer `token` turns."""
    axis, slab = _LAYER_OF[token]
    return [
        (face, a, b)
        for a in range(3)
        for b in range(3)
        if slab_of(sticker_centre(face, a, b)[axis]) == slab
    ]


def _mark(cube: Cube, face: str, a: int, b: int) -> None:
    sim_face, row, col = diagram_to_sim(face, a, b)
    cube.faces[sim_face][row * 3 + col] = "X"


def exit_face(token: str, host: str) -> str:
    """Where `host`'s strip goes under `token`: mark it, turn, look."""
    cube = Cube.solved()
    for sticker in strip_stickers(host, token):
        _mark(cube, *sticker)
    cube.apply(token)
    landed = {face for face, stickers in cube.faces.items() if "X" in stickers}
    landed.discard(host)
    if len(landed) != 1:
        raise ValueError(f"{token} moves {host}'s strip to {sorted(landed)}, expected one face")
    return landed.pop()


def _strip_arrow(token: str, host: str) -> tuple[Vec3, Vec3]:
    """A straight arrow along `host`'s strip, pointing at the face it leaves for."""
    centres = [sticker_centre(*s) for s in strip_stickers(host, token)]
    mid = tuple(sum(c[i] for c in centres) / len(centres) for i in range(3))
    d = _FACE_NORMAL[exit_face(token, host)]
    r = _OV_STRIP_REACH
    return (
        (mid[0] - d[0] * r, mid[1] - d[1] * r, mid[2] - d[2] * r),
        (mid[0] + d[0] * r, mid[1] + d[1] * r, mid[2] + d[2] * r),
    )


def overview_strips() -> dict[str, tuple[Vec3, Vec3]]:
    """token -> (tail, tip) of the hub's five strip arrows. Public for the tests."""
    return {token: _strip_arrow(token, host) for token, host in _OV_HOST.items()}


def _ring_basis(n: Vec3) -> tuple[Vec3, Vec3]:
    """(u, v) in the face plane with u x v = -n: increasing angle is clockwise
    as seen from outside the face."""
    u: Vec3 = (0, 1, 0) if n[1] == 0 else (1, 0, 0)
    v: Vec3 = (
        u[1] * n[2] - u[2] * n[1],
        u[2] * n[0] - u[0] * n[2],
        u[0] * n[1] - u[1] * n[0],
    )
    return u, v


def _ring(
    centre: Vec3, n: Vec3, radius: float, start: float, sweep: float, samples: int = 40
) -> list[Vec3]:
    """A ring around `n` through `centre`, clockwise seen from +n. Angles in radians."""
    u, v = _ring_basis(n)
    pts = []
    for i in range(samples + 1):
        t = start + sweep * i / samples
        c, s = radius * math.cos(t), radius * math.sin(t)
        pts.append(
            (
                centre[0] + u[0] * c + v[0] * s,
                centre[1] + u[1] * c + v[1] * s,
                centre[2] + u[2] * c + v[2] * s,
            )
        )
    return pts


def overview_ring() -> list[Vec3]:
    """The hub's F ring as 3D points, clockwise as seen from the front. Public
    for the tests, which check the order it passes the edge-middle stickers in."""
    return _ring(
        sticker_centre("F", 1, 1),
        _FACE_NORMAL["F"],
        _OV_RING_R,
        math.radians(_OV_RING_START),
        math.radians(_OV_RING_SWEEP),
    )


def _face_centre(face: str) -> Vec3:
    n = _FACE_NORMAL[face]
    return (1.5 + 1.5 * n[0], 1.5 + 1.5 * n[1], 1.5 + 1.5 * n[2])


def overview_pin(face: str) -> tuple[Vec3, Vec3]:
    """(face centre, tip) of a pin. Its 3D length is whatever puts the tip at
    the layout's screen radius, so the six tips sit on two circles."""
    n = _FACE_NORMAL[face]
    c = _face_centre(face)
    o = _n_proj(*_CUBE_CENTRE)
    per_unit = math.dist(_n_proj(*c), _n_proj(c[0] + n[0], c[1] + n[1], c[2] + n[2]))
    reach = _OV_PIN_TIP["front" if face in _OV_ON_FACE else "back"]
    # projection is affine, so |proj(c + t n) - o| = reach is linear in t
    t = (reach - math.dist(_n_proj(*c), o)) / per_unit
    return c, (c[0] + n[0] * t, c[1] + n[1] * t, c[2] + n[2] * t)


def _pin_ring_frame(face: str) -> tuple[Vec3, float]:
    """The ring's centre and start angle. The start is chosen so the
    arrowhead lands at the point of the ring nearest the camera — derived
    from the view direction, never hand-set."""
    n = _FACE_NORMAL[face]
    _c, tip = overview_pin(face)
    k = _OV_PIN_RING_IN
    centre = (tip[0] - n[0] * k, tip[1] - n[1] * k, tip[2] - n[2] * k)
    u, v = _ring_basis(n)
    a = sum(u[i] * _VIEW_DIR[i] for i in range(3))
    b = sum(v[i] * _VIEW_DIR[i] for i in range(3))
    nearest = math.atan2(b, a)
    return centre, nearest - _OV_PIN_SWEEP - _OV_PIN_HEAD


def overview_pin_ring(face: str) -> list[Vec3]:
    """The ring's centre-line around a pin, as 3D points. Public for the tests."""
    centre, start = _pin_ring_frame(face)
    return _ring(centre, _FACE_NORMAL[face], _OV_PIN_RING_R, start, _OV_PIN_SWEEP)


def overview_pin_head(face: str) -> Vec3:
    """The 3D point of the arrowhead's tip: a little past the sweep end."""
    centre, start = _pin_ring_frame(face)
    return _ring(
        centre, _FACE_NORMAL[face], _OV_PIN_RING_R, start + _OV_PIN_SWEEP, _OV_PIN_HEAD, 1
    )[-1]


class _Bounds:
    """Running bounding box of everything drawn, for the computed viewBox."""

    def __init__(self) -> None:
        self.x0 = self.y0 = math.inf
        self.x1 = self.y1 = -math.inf

    def add(self, x: float, y: float, r: float = 0.0) -> None:
        self.x0, self.x1 = min(self.x0, x - r), max(self.x1, x + r)
        self.y0, self.y1 = min(self.y0, y - r), max(self.y1, y + r)

    def text(self, x: float, y: float, s: str, size: float, anchor: str) -> None:
        w = _OV_CHAR_W * size * len(s)
        left = {"middle": x - w / 2, "start": x, "end": x - w}[anchor]
        self.add(left, y - 0.74 * size)
        self.add(left + w, y + 0.22 * size)


def _ov_needs_halo(recolor: dict[str, str]) -> bool:
    """Whether the ink separates from every visible face in this palette.

    Screen faces all clear 3:1 against the arrow ink; the card's darkened red
    does not, so the hub's arrows get a paper-coloured halo. Measured, not
    chosen. The pins' ribbons carry their own paper fill.
    """
    faces = (recolor.get(c, c) for c in _CUBE_FACE_COLORS.values())
    return any(palette.contrast(ARROW_COLOR, f) < _OV_HALO_MIN_CONTRAST for f in faces)


def _ov_arrow(dwg: svgwrite.Drawing, bounds: _Bounds, pts3: list[Vec3], *, halo: bool) -> None:
    """A projected polyline with a filled head at its last point (the hub)."""
    pts = [_n_proj(*p) for p in pts3]
    tip, prev = pts[-1], pts[-3] if len(pts) > 2 else pts[0]
    dx, dy = tip[0] - prev[0], tip[1] - prev[1]
    ln = math.hypot(dx, dy)
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux
    head, stroke = _OV_HEAD, _OV_STROKE
    base = (tip[0] - head * ux, tip[1] - head * uy)
    body = (pts[:-2] if len(pts) > 2 else pts[:-1]) + [base]
    d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in body)
    head_pts = [
        (round(tip[0], 1), round(tip[1], 1)),
        (round(base[0] + head * 0.45 * nx, 1), round(base[1] + head * 0.45 * ny, 1)),
        (round(base[0] - head * 0.45 * nx, 1), round(base[1] - head * 0.45 * ny, 1)),
    ]
    if halo:
        rim = 0.7 * stroke
        dwg.add(dwg.path(d=d, fill="none", stroke=WHITE, stroke_width=stroke + 2 * rim))
        dwg.add(dwg.polygon(head_pts, fill=WHITE, stroke=WHITE, stroke_width=2 * rim))
    dwg.add(
        dwg.path(d=d, fill="none", stroke=ARROW_COLOR, stroke_width=stroke, stroke_linecap="round")
    )
    dwg.add(dwg.polygon(head_pts, fill=ARROW_COLOR))
    for p in pts:
        bounds.add(*p, stroke)
    for p in head_pts:
        bounds.add(*p)


def _ribbon_arc(
    dwg: svgwrite.Drawing,
    bounds: _Bounds,
    centre: Vec3,
    n: Vec3,
    start: float,
) -> tuple[Any, Any, Any]:
    """A 3D ribbon ring around the axis `n` — a band of half-width
    `_OV_PIN_BAND` along the axis, clockwise seen from +n — split into a back
    group, a front group and the arrowhead so the caller can thread the pin
    through it. The original overview's geometry, kept because it reads as a
    solid object; the radius, sweep and head are what changed.

    Returns (back_group, front_group, arrow_group).
    """
    v1, v2 = _ring_basis(n)
    radius, sweep, band = _OV_PIN_RING_R, _OV_PIN_SWEEP, _OV_PIN_BAND
    n_pts = 48
    # depth(θ) = A cos θ + B sin θ: positive means nearer the camera than the centre
    a_coeff = sum(v1[i] * _VIEW_DIR[i] for i in range(3))
    b_coeff = sum(v2[i] * _VIEW_DIR[i] for i in range(3))

    def ring_pt(angle: float) -> Vec3:
        co, si = math.cos(angle), math.sin(angle)
        return (
            centre[0] + radius * (v1[0] * co + v2[0] * si),
            centre[1] + radius * (v1[1] * co + v2[1] * si),
            centre[2] + radius * (v1[2] * co + v2[2] * si),
        )

    def band_pt(angle: float, side: float) -> Point:
        p = ring_pt(angle)
        q = _n_proj(p[0] + side * band * n[0], p[1] + side * band * n[1], p[2] + side * band * n[2])
        bounds.add(*q, _OV_PIN_STROKE)
        return q

    def depth(angle: float) -> float:
        return a_coeff * math.cos(angle) + b_coeff * math.sin(angle)

    angles = [start + sweep * i / n_pts for i in range(n_pts + 1)]
    depths = [depth(t) for t in angles]
    crossings = []
    for i in range(n_pts):
        if depths[i] * depths[i + 1] < 0:
            k = depths[i] / (depths[i] - depths[i + 1])
            crossings.append(angles[i] + k * (angles[i + 1] - angles[i]))
    boundaries = [angles[0], *sorted(crossings), angles[-1]]

    back, front = dwg.g(), dwg.g()

    def poly(pts: list[Point], closed: bool = False) -> str:
        d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        return d + " Z" if closed else d

    def edge(group: Any, pts: list[Point]) -> None:
        group.add(
            dwg.path(
                d=poly(pts),
                fill="none",
                stroke=ARROW_COLOR,
                stroke_width=_OV_PIN_STROKE,
                stroke_linejoin="round",
                stroke_linecap="round",
            )
        )

    def cap(group: Any, p: Point, q: Point) -> None:
        line = dwg.line(p, q, stroke=ARROW_COLOR, stroke_width=_OV_PIN_STROKE)
        line["stroke-linecap"] = "round"
        group.add(line)

    segments: list[tuple[bool, list[Point], list[Point]]] = []
    for a0, a1 in zip(boundaries, boundaries[1:], strict=False):
        m = max(2, round(n_pts * (a1 - a0) / sweep))
        seg = [a0 + (a1 - a0) * j / m for j in range(m + 1)]
        is_front = depth((a0 + a1) / 2) > 0 or math.hypot(a_coeff, b_coeff) < 0.01
        segments.append((is_front, [band_pt(t, +1) for t in seg], [band_pt(t, -1) for t in seg]))

    # fills first, then continuous edges per depth zone, so no joints show
    for is_front, top, bot in segments:
        (front if is_front else back).add(
            dwg.path(d=poly(top + bot[::-1], closed=True), fill=WHITE, stroke="none")
        )
    i = 0
    while i < len(segments):
        is_front, top, bot = segments[i]
        top, bot = list(top), list(bot)
        j = i + 1
        while j < len(segments) and segments[j][0] == is_front:
            top += segments[j][1][1:]
            bot += segments[j][2][1:]
            j += 1
        group = front if is_front else back
        edge(group, top)
        edge(group, bot)
        if i == 0:
            cap(group, top[0], bot[0])  # the ribbon's open start
        # no cap at a depth boundary (the band continues behind the pin) and
        # none at the sweep end (the band flows into the arrowhead)
        i = j

    # the arrowhead: a triangle in the band's own plane, past the sweep end
    end = start + sweep
    tip = _n_proj(*ring_pt(end + _OV_PIN_HEAD))
    base = ring_pt(end)
    wing = band * 2.4
    outer = _n_proj(base[0] + wing * n[0], base[1] + wing * n[1], base[2] + wing * n[2])
    inner = _n_proj(base[0] - wing * n[0], base[1] - wing * n[1], base[2] - wing * n[2])
    for p in (tip, outer, inner):
        bounds.add(*p, _OV_PIN_STROKE)
    arrow = dwg.g()
    top_end, bot_end = band_pt(end, +1), band_pt(end, -1)
    # The fill reaches a little back into the band so no hairline shows where
    # the ribbon's fill polygon and the head's meet.
    back_in = end - sweep / n_pts
    arrow.add(
        dwg.path(
            d=poly(
                [band_pt(back_in, +1), top_end, outer, tip, inner, bot_end, band_pt(back_in, -1)],
                closed=True,
            ),
            fill=WHITE,
            stroke="none",
        )
    )
    edge(arrow, [band_pt(back_in, +1), top_end])
    edge(arrow, [band_pt(back_in, -1), bot_end])
    arrow.add(
        dwg.path(
            d=poly([top_end, outer, tip, inner, bot_end]),
            fill="none",
            stroke=ARROW_COLOR,
            stroke_width=_OV_PIN_STROKE,
            stroke_linejoin="round",
            stroke_linecap="round",
        )
    )
    return back, front, arrow


def _ov_cube(
    dwg: svgwrite.Drawing, bounds: _Bounds, recolor: dict[str, str], opacity: float
) -> None:
    """Solid U / F / R faces with the two layer lines per face."""
    for face, corners in _OV_FACES.items():
        color = _CUBE_FACE_COLORS[face]
        pts = [_n_proj(*c) for c in corners]
        dwg.add(
            dwg.polygon(
                pts,
                fill=recolor.get(color, color),
                stroke=STICKER_STROKE,
                stroke_width=1.5,
                stroke_linejoin="round",
            )
        )
        for p in pts:
            bounds.add(*p, 1)
    lines: list[tuple[Vec3, Vec3]] = []
    for i in (1, 2):
        lines += [((i, 3, 0), (i, 3, 3)), ((0, 3, i), (3, 3, i))]  # U
        lines += [((i, 0, 3), (i, 3, 3)), ((0, i, 3), (3, i, 3))]  # F
        lines += [((3, 0, i), (3, 3, i)), ((3, i, 0), (3, i, 3))]  # R
    for a, b in lines:
        line = dwg.line(_n_proj(*a), _n_proj(*b), stroke=STICKER_STROKE, stroke_width=1)
        line["stroke-opacity"] = f"{opacity:g}"
        dwg.add(line)


def _ov_label(
    dwg: svgwrite.Drawing,
    bounds: _Bounds,
    text: str,
    at: Point,
    *,
    size: float,
    anchor: str,
    on_plate: bool,
    halo: bool,
) -> None:
    """A letter. On the plate it is ink-tagged and flips with the theme; on a
    face it stays dark against the sticker colour, with a paper rim when the
    palette needs one."""

    def text_elem() -> Any:
        return dwg.text(
            text,
            insert=(round(at[0], 1), round(at[1], 1)),
            text_anchor=anchor,
            font_size=f"{size:g}px",
            font_family="sans-serif",
            font_weight="bold",
            fill=ARROW_COLOR,
        )

    if halo and not on_plate:
        rim = text_elem()
        rim["fill"] = WHITE
        rim["stroke"] = WHITE
        rim["stroke-width"] = 3
        rim["stroke-linejoin"] = "round"
        dwg.add(rim)
    elem = text_elem()
    dwg.add(_ink(elem) if on_plate else elem)
    bounds.text(at[0], at[1], text, size, anchor)


def _ov_pin_line(dwg: svgwrite.Drawing, bounds: _Bounds, a: Point, b: Point) -> None:
    line = dwg.line(a, b, stroke=ARROW_COLOR, stroke_width=_OV_PIN_STROKE + 0.4)
    line["stroke-linecap"] = "round"
    dwg.add(_ink(line))
    bounds.add(*b, 2)


def _ov_pins(
    dwg: svgwrite.Drawing, bounds: _Bounds, recolor: dict[str, str], opacity: float
) -> None:
    """The pins layout. Draw order is the depth order: the hidden faces' pins
    and rings first so the cube occludes them, then the cube, then each
    visible face's ring back half, the pin through it, its front half and
    head, then every dot and letter on top."""
    proj = {face: tuple(_n_proj(*p) for p in overview_pin(face)) for face in _FACE_NORMAL}
    rings = {}
    for face, n in _FACE_NORMAL.items():
        centre, start = _pin_ring_frame(face)
        rings[face] = _ribbon_arc(dwg, bounds, centre, n, start)

    for face in "DBL":
        c, tip = proj[face]
        back, front, head = rings[face]
        dwg.add(back)
        _ov_pin_line(dwg, bounds, c, tip)
        dwg.add(front)
        dwg.add(head)
    _ov_cube(dwg, bounds, recolor, opacity)
    for face in _OV_ON_FACE:
        c, tip = proj[face]
        back, front, head = rings[face]
        dwg.add(back)
        _ov_pin_line(dwg, bounds, c, tip)
        dwg.add(front)
        dwg.add(head)
    for face in "UDFBRL":
        c, tip = proj[face]
        dot = dwg.circle(
            center=(round(tip[0], 1), round(tip[1], 1)), r=_OV_PIN_DOT, fill=ARROW_COLOR
        )
        dwg.add(_ink(dot))
        bounds.add(*tip, _OV_PIN_DOT)
        dx, dy = tip[0] - c[0], tip[1] - c[1]
        ln = math.hypot(dx, dy)
        at = (
            tip[0] + dx / ln * _OV_PIN_LABEL_OUT,
            tip[1] + dy / ln * _OV_PIN_LABEL_OUT + 0.36 * _OV_PIN_LABEL,
        )
        _ov_label(
            dwg, bounds, face, at, size=_OV_PIN_LABEL, anchor="middle", on_plate=True, halo=False
        )


def _ov_hub(
    dwg: svgwrite.Drawing, bounds: _Bounds, recolor: dict[str, str], opacity: float
) -> None:
    halo = _ov_needs_halo(recolor)
    _ov_cube(dwg, bounds, recolor, opacity)
    _ov_arrow(dwg, bounds, overview_ring(), halo=halo)
    for tail, tip in overview_strips().values():
        _ov_arrow(dwg, bounds, [tail, tip], halo=halo)
    for token, (at, anchor) in _OV_LABEL_AT.items():
        on_face = token in _OV_ON_FACE
        _ov_label(
            dwg,
            bounds,
            token,
            _n_proj(*at),
            size=_OV_LABEL,
            anchor=anchor,
            on_plate=not on_face,
            halo=halo,
        )


def render_overview(
    output_dir: Path, style: DiagramStyle = SCREEN, layout: OverviewLayout = OVERVIEW_PINS
) -> Path:
    """Render the notation overview: the six face turns on one cube."""
    recolor = _restyle(style)
    subdir = output_dir / "notation"
    subdir.mkdir(parents=True, exist_ok=True)
    filepath = subdir / f"{layout.filename}.svg"

    dwg = svgwrite.Drawing(str(filepath))
    if style.themed:
        _add_theme(dwg)
    plate = _bg(dwg, (0, 0), (0, 0), 6)  # sized once the bounds are known
    dwg.add(plate)
    bounds = _Bounds()

    if layout.pins:
        _ov_pins(dwg, bounds, recolor, style.layer_lines)
    else:
        _ov_hub(dwg, bounds, recolor, style.layer_lines)

    vb_x, vb_y = bounds.x0 - _OV_PAD, bounds.y0 - _OV_PAD
    vb_w, vb_h = bounds.x1 - bounds.x0 + 2 * _OV_PAD, bounds.y1 - bounds.y0 + 2 * _OV_PAD
    dwg["viewBox"] = f"{vb_x:.1f} {vb_y:.1f} {vb_w:.1f} {vb_h:.1f}"
    dwg["width"], dwg["height"] = f"{vb_w:.0f}px", f"{vb_h:.0f}px"
    plate["x"], plate["y"] = round(vb_x, 1), round(vb_y, 1)
    plate["width"], plate["height"] = round(vb_w, 1), round(vb_h, 1)

    dwg.save(pretty=True)
    return filepath


def all_steps() -> list[StepDiagram]:
    """Every 3D step diagram, in guide order.

    The guide and the card set both render this list. Listing the groups twice
    is how a new step group reaches one output and not the other.
    """
    return [
        *_step_cases(),
        *_corner_case_steps(),
        *_edge_case_steps(),
        _orient_corner_case(),
        *_orient_corner_cases_15(),
        _corner_pos_case(),
        *_align_edge_cases(),
    ]


def main() -> None:
    # tools/cubepath/src/cubepath/diagrams.py -> repo root is 4 levels up
    output_dir = Path(__file__).resolve().parents[4] / "guide" / "figures" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    total = 0

    for case in all_cases():
        path = render(case, output_dir)
        print(f"  {path.relative_to(output_dir)}")
        total += 1

    # Full OLL/PLL sets, derived from the extracted (machine-verified) dataset.
    from cubepath.fullsets import render_fullsets

    total += render_fullsets(output_dir)

    for move in _notation_moves():
        path = render_notation(move, output_dir)
        print(f"  {path.relative_to(output_dir)}")
        total += 1

    for layout in (OVERVIEW_HUB, OVERVIEW_PINS):
        print(f"  {render_overview(output_dir, layout=layout).relative_to(output_dir)}")
        total += 1

    for step in all_steps():
        path = render_step(step, output_dir)
        print(f"  {path.relative_to(output_dir)}")
        total += 1

    print(f"\nGenerated {total} SVG diagrams in {output_dir}")


if __name__ == "__main__":
    main()
