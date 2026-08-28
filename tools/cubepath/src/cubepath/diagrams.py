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

from cubepath.algs import ALGORITHMS, DOT_SEQUENCE
from cubepath.cube import Cube, state_before

# Colors — standard Western Rubik's cube (Yellow top, Red front)
YELLOW = "#FFD500"
WHITE = "#FFFFFF"
RED = "#E00000"
ORANGE = "#FF8C00"
BLUE = "#0051BA"
GREEN = "#009E60"
STICKER_STROKE = "#333333"

# ── The two greys, and why there are two ──────────────────────────────
# A grey sticker used to mean two incompatible things across the shipped set,
# and nothing said which. On an OLL plan view it means "this facelet is a real
# sticker that is not yellow" — the piece is in frame, in the layer you are
# working on, and the diagram is asking you to read its ORIENTATION. On a step
# or F2L diagram it means "nothing is claimed here yet" — the region has not
# been REACHED by the method, and the picture says nothing about what is in it.
#
# Those are different claims and they meet on the page: `yellow-cross.mdx`
# prints `steps/step_4_ycross.svg` above `oll/oll_{dot,hook,line}.svg`, and the
# guide's Phase-1 table does the same. One token doing both jobs silently is
# what this split ends.
#
# The orientation mask keeps #C0C0C0 to the byte: it is correct, it is what
# every OLL reference draws, and 95 shipped plan views are built on it. The
# not-reached tier is the one that moves, to a cooler and slightly lighter
# neutral — 13.1 ΔE from the mask (the just-noticeable difference is ~2.3), far
# enough that the two read as different tones on one page, and light enough
# that "not reached" stays the quietest thing in the picture rather than
# becoming the heaviest. `tests/test_diagrams.py` measures both claims against
# the emitted SVGs, including that no single file ever contains both tones.
UNORIENTED = "#C0C0C0"  # OLL/PLL plan views: a real sticker, not yellow
UNREACHED = "#C0D4E6"  # step + F2L diagrams: the method has not got here yet

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
# Only the plate and the label ink flip. Sticker strokes are read between two
# coloured fills and the rotation-ribbon occluders carry their own surface, so
# both stay as they are.
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
# (x, y, z) -> projected (x, y); every 3D diagram takes one.
Projector = Callable[[float, float, float], Point]


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
    masked: str  # OLL plan views: a real sticker that is not yellow
    unreached: str  # step/F2L diagrams: the method has not got here yet
    band_u: int  # side-band thickness in viewBox units
    stroke_main: float  # U-face sticker outline
    stroke_side: float  # side-band sticker outline
    stroke_arrow: float  # PLL permutation arrows
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
    masked=UNORIENTED,
    unreached=UNREACHED,
    band_u=SIDE_H,
    stroke_main=1.5,
    # ints, not floats: svgwrite writes the value verbatim, so 1.0 would
    # rewrite every committed screen SVG for no visual change.
    stroke_side=1,
    stroke_arrow=2,
)
CARD = DiagramStyle(
    faces=CARD_FACES,
    # A printed card is ink on paper: no page behind it to show through.
    themed=False,
    masked="#5F5F5F",
    # Print inverts the not-reached tier, and the reason is the medium, not
    # taste. On screen "nothing here yet" is the lightest thing in the picture
    # because the page shows through behind it. A card is ink on paper with no
    # page behind it, and the tone has to clear three light neighbours at once
    # — the white face, its own dim tone (#ABABAB) and the mask — so the only
    # room left is below all three. 13.7 ΔE from the mask, and every card face
    # and dim tone at least 15 ΔE clear of it; both gated.
    unreached="#3F3F3F",
    band_u=20,
    stroke_main=3.2,
    stroke_side=2.4,
    stroke_arrow=4.5,
)


# ── The dim tier ──────────────────────────────────────────────────────
# Two tiers (face colour / mask) are enough for a last-layer plan view, where
# everything below the top layer is off-screen anyway. They are not enough for
# a picture that has to say three things at once: *this* is what the step
# solves, *that* was solved earlier and must survive, and the rest has not been
# reached yet. An F2L case needs all three. So does every step diagram whose
# lesson builds on a finished layer — 16 of the 19, which is why the white
# cross used to be drawn exactly as loudly as the white corners it sits under.
#
# THE TRANSFORM, and why it is not a mix toward the grey. It used to be
# a straight sRGB blend two thirds of the way to the grey, tuned by eye on
# F2L's colour mix. Measured across
# the six faces that number gives 15.1 ΔE at worst — white, which has no chroma
# to spend, moved almost nowhere (1.48:1 against itself, against the player's
# own 1.36:1 that this pipeline exists to beat) — and dim yellow landed 7.2 ΔE
# from the not-reached grey, close enough to read as a second grey. Both
# failures come from the same cause: one linear target moves every face by a
# different amount, and it moves an achromatic face hardly at all.
#
# So the tier is stated as what it means instead. A dim sticker is the SAME
# HUE, a THIRD OF THE CHROMA, and a LIGHTNESS STEP away from its face colour:
#
#   * chroma × DIM_CHROMA — the loss of saturation is the "quiet" signal, and
#     keeping a third of it is what still lets a learner see that the cross is
#     intact rather than merely that something is there.
#   * L* moved DIM_TARGET_DE away in total, with the chroma drop paying for as
#     much of that distance as it can and the lightness step paying the rest.
#     A saturated face has already covered it, so it pays only the DIM_MIN_DL
#     floor that a mono laser needs; white pays the whole 30, which is exactly
#     the per-face retune the old single mix could not express.
#   * the step goes AWAY from DIM_PIVOT: light faces darken, dark faces lighten.
#     Every face therefore gets a real greyscale move (>= 1.59:1 in both
#     palettes) instead of one direction that flattens half of them in print.
#
# Because it is a function of the colour alone, `_restyle` can map a screen dim
# tone onto the card's own dim tone without either palette listing one, and the
# card gets the same guarantees measured against ITS faces. Every number above
# is asserted in `tests/test_diagrams.py` against both palettes, and against
# the fills of the emitted SVGs — not against this comment.
DIM_CHROMA = 0.32  # fraction of the face's chroma a dim sticker keeps
DIM_TARGET_DE = 30.0  # total CIE76 distance a dim sticker must travel
DIM_MIN_DL = 16.0  # ... of which at least this much is lightness
DIM_PIVOT = 62.0  # L* the step moves away from, so no face flattens


def _srgb_to_linear(channel: float) -> float:
    c = channel / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(value: float) -> int:
    v = min(1.0, max(0.0, value))
    out = 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
    return round(out * 255)


# D65, 2°. The same white point `palette.relative_luminance` implies.
_WHITE_POINT = (0.95047, 1.0, 1.08883)


def to_lab(hex_color: str) -> tuple[float, float, float]:
    """sRGB hex -> CIE L*a*b*.

    Lab is the space the tier arithmetic has to happen in: it is the only one
    in this repo where "a third of the chroma" and "16 points of lightness" are
    the same kind of quantity, and where the distance between two tones matches
    what a reader sees. `palette.contrast` stays the right tool for text and
    for a mono printer; it is the wrong one for two swatches that differ mostly
    in saturation, which is why dim yellow measured 1.20:1 against yellow and
    still reads as a different tone.
    """
    h = hex_color.lstrip("#")
    r, g, b = (_srgb_to_linear(int(h[i : i + 2], 16)) for i in (0, 2, 4))
    xyz = (
        0.4124 * r + 0.3576 * g + 0.1805 * b,
        0.2126 * r + 0.7152 * g + 0.0722 * b,
        0.0193 * r + 0.1192 * g + 0.9505 * b,
    )

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 216 / 24389 else (841 / 108) * t + 4 / 29

    fx, fy, fz = (f(v / w) for v, w in zip(xyz, _WHITE_POINT, strict=True))
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def from_lab(lightness: float, a: float, b: float) -> str:
    """CIE L*a*b* -> sRGB hex, clamped into gamut."""
    fy = (lightness + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200

    def g(t: float) -> float:
        return t**3 if t**3 > 216 / 24389 else (108 / 841) * (t - 4 / 29)

    x, y, z = (g(v) * w for v, w in zip((fx, fy, fz), _WHITE_POINT, strict=True))
    rgb = (
        3.2406 * x - 1.5372 * y - 0.4986 * z,
        -0.9689 * x + 1.8758 * y + 0.0415 * z,
        0.0557 * x - 0.2040 * y + 1.0570 * z,
    )
    return "#" + "".join(f"{_linear_to_srgb(c):02X}" for c in rgb)


def delta_e(a: str, b: str) -> float:
    """CIE76 distance between two hex colours. ~2.3 is one just-noticeable
    difference, which is the unit every tier separation in this module is
    quoted in."""
    return math.dist(to_lab(a), to_lab(b))


def dim(face_color: str) -> str:
    """The "solved earlier, keep it" tone of a face colour.

    A pure function of the colour, so the card's dim tone is derived from the
    card's face colour rather than carrying a screen tone onto paper, and
    neither palette has to list one.
    """
    lightness, a, b = to_lab(face_color)
    chroma = math.hypot(a, b)
    spent = chroma * (1 - DIM_CHROMA)
    step = max(DIM_MIN_DL, math.sqrt(max(0.0, DIM_TARGET_DE**2 - spent**2)))
    moved = lightness - step if lightness >= DIM_PIVOT else lightness + step
    return from_lab(moved, a * DIM_CHROMA, b * DIM_CHROMA)


def _restyle(style: DiagramStyle) -> dict[str, str]:
    """SCREEN hex -> this style's hex. Derived from the two palettes, so a
    face colour can never be remapped by a hand-written substitution — the dim
    tier included, which is computed from each palette rather than listed."""
    remap = {SCREEN_FACES[k]: style.faces[k] for k in SCREEN_FACES}
    remap |= {dim(SCREEN_FACES[k]): dim(style.faces[k]) for k in SCREEN_FACES}
    remap[UNORIENTED] = style.masked
    remap[UNREACHED] = style.unreached
    return remap


@dataclass
class CubeDiagram:
    """A single last-layer plan-view case, on a cube of any order.

    `n` is the cube's order, and it is the only thing that differs between a
    3x3 diagram and a 4x4 one: the U grid is n x n, each side band is n cells,
    and the eight arrow anchors are computed from n rather than listed. There
    is no second renderer, because a 4x4 last layer is not new geometry — it
    is the same picture with different grid arithmetic.
    """

    name: str  # filename (no extension)
    label: str  # human-readable label
    category: str  # "oll_cross", "oll_corners", "pll_corners", "444_oll", ...
    # U-face colors: n*n cells, row-major (row 0 = back of the cube).
    u_face: list[str]
    # Side stickers: n each, left-to-right (top/bottom) or back-to-front
    # (left/right) as seen from above. Empty means "nothing solved here yet".
    top_side: list[str] = field(default_factory=list)
    right_side: list[str] = field(default_factory=list)
    bottom_side: list[str] = field(default_factory=list)
    left_side: list[str] = field(default_factory=list)
    # Arrows for PLL: bidirectional swaps and directional cycles
    swaps: list[tuple[str, str]] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)
    # Secondary arrows (dashed) for edge movement in corner PLLs
    dashed_swaps: list[tuple[str, str]] = field(default_factory=list)
    # Cube order. 3 keeps every existing call site untouched.
    n: int = 3

    def __post_init__(self) -> None:
        """Fill the unstated side bands and check every strip against `n`.

        A length that disagrees with `n` used to be undrawable-but-silent: the
        renderer indexed whatever it was handed and produced a plausible
        picture of the wrong cube. It is cheap to make it impossible.
        """
        if len(self.u_face) != self.n * self.n:
            raise ValueError(
                f"{self.name}: {len(self.u_face)} U facelets on a {self.n}x{self.n} cube"
            )
        for side in ("top_side", "right_side", "bottom_side", "left_side"):
            strip: list[str] = getattr(self, side)
            if not strip:
                setattr(self, side, [UNORIENTED] * self.n)
            elif len(strip) != self.n:
                raise ValueError(
                    f"{self.name}: {side} has {len(strip)} cells on a {self.n}x{self.n} cube"
                )


Y = YELLOW
G = UNORIENTED

# Simulator color letter → diagram hex color
_SIM_COLOR = {"Y": YELLOW, "R": RED, "G": GREEN, "O": ORANGE, "B": BLUE, "W": WHITE}


def _colorize(strip: list[str]) -> list[str]:
    """Simulator color letters → diagram hex colors."""
    return [_SIM_COLOR[s] for s in strip]


def plan_view(faces: dict[str, Any], n: int = 3) -> tuple[list[str], dict[str, list[str]]]:
    """Plan-view of the U layer of an n x n x n cube: u_face + side strips.

    `faces` is any mapping face letter -> that face's n*n stickers, row-major,
    read from outside the cube — `Cube.faces` and the face strings in
    case-states.json are both exactly that, which is why one function serves
    both and the convention cannot drift between them.

    Only the top row of each side face is on the last layer. Which end of that
    row is which follows from how the faces meet, not from a choice: looking at
    R from outside, F is on your left, so R's row runs front-to-back and the
    plan view (front at the bottom) reads it reversed. B is the same, seen from
    behind. F and L already run the way the plan view reads them.
    """
    row = {f: list(faces[f])[:n] for f in "BRFL"}
    sides = {
        "top": row["B"][::-1],
        "right": row["R"][::-1],
        "bottom": row["F"],
        "left": row["L"],
    }
    return list(faces["U"]), sides


def _u_layer_views(cube: Cube) -> tuple[list[str], dict[str, list[str]]]:
    """The 3x3 plan view, straight off the simulator."""
    return plan_view(cube.faces, 3)


def _yellow_mask(stickers: list[str]) -> list[str]:
    return [YELLOW if s == "Y" else UNORIENTED for s in stickers]


def _derived_cross_case(name: str, label: str, alg: str, *, view_turn: str = "") -> CubeDiagram:
    """OLL cross case derived from its algorithm's pre-state.

    Shows the U-face edge/center pattern; corners carry the orientation mask
    (don't-care at the cross stage). `view_turn` reorients the derived state so the diagram
    matches how the guide tells the learner to hold the cube.
    """
    cube = state_before(alg)
    if view_turn:
        cube.apply(view_turn)
    u, _ = _u_layer_views(cube)
    u_face = _yellow_mask(u)
    for corner in (0, 2, 6, 8):
        u_face[corner] = UNORIENTED
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

    The U face is drawn `dim(YELLOW)`, not yellow. PLL runs AFTER OLL, so every
    one of those nine stickers is a finished result the step must preserve —
    the textbook dim tier, and the reason a PLL plan view is a three-tier
    picture where an OLL plan view is a two-tier one. Full saturation there put
    nine loud cells in the middle of a diagram whose entire content is the
    twelve side stickers around them.
    """
    cube = state_before(alg)
    u, sides = _u_layer_views(cube)
    assert all(s == "Y" for s in u), f"{name}: U face not fully yellow in pre-state"
    return CubeDiagram(
        name=name,
        label=label,
        category=category,
        u_face=[dim(YELLOW)] * 9,
        top_side=_colorize(sides["top"]),
        right_side=_colorize(sides["right"]),
        bottom_side=_colorize(sides["bottom"]),
        left_side=_colorize(sides["left"]),
        swaps=swaps or [],
        cycles=cycles or [],
        dashed_swaps=dashed_swaps or [],
    )


# The eight arrow anchors, in grid coordinates on an n x n U face. A corner
# anchor is a cell; an edge anchor is the CENTRE OF THE EDGE — one cell on a
# 3x3, the midpoint of the dedge's two wings on a 4x4 — which is why the
# coordinate is (n - 1) / 2 rather than an index. The eight literal pixel
# anchors this replaces could only ever describe a 3x3.
ARROW_ANCHORS = ("top", "right", "bottom", "left", "tl", "tr", "bl", "br")


def _anchor_cell(name: str, n: int) -> tuple[float, float]:
    """(col, row) of a named anchor on an n x n U-face grid."""
    mid = (n - 1) / 2
    last = n - 1
    cells = {
        "top": (mid, 0.0),
        "bottom": (mid, float(last)),
        "left": (0.0, mid),
        "right": (float(last), mid),
        "tl": (0.0, 0.0),
        "tr": (float(last), 0.0),
        "bl": (0.0, float(last)),
        "br": (float(last), float(last)),
    }
    return cells[name]


def _arrow_pos(name: str, n: int = 3) -> tuple[float, float]:
    """Return pixel center for a named arrow anchor on the U-face grid."""
    ox = MARGIN + SIDE_H + GAP  # 34
    oy = MARGIN + SIDE_H + GAP  # 34
    col, row = _anchor_cell(name, n)
    return (ox + col * (CELL + GAP) + CELL / 2, oy + row * (CELL + GAP) + CELL / 2)


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
    n: int = 3,
) -> svgwrite.path.Path:
    """Create a straight arrow path between two named positions."""
    start = _arrow_pos(pos_a, n)
    end = _arrow_pos(pos_b, n)
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
    n: int = 3,
    *,
    dashed: bool = False,
) -> None:
    """Draw a single bidirectional arrow (swap) between two named positions."""
    path = _arrow_path(dwg, pos_a, pos_b, width, n)
    path["marker-start"] = "url(#arrowhead-rev)"
    path["marker-end"] = "url(#arrowhead)"
    if dashed:
        path.dasharray([4, 3])
    dwg.add(path)


def _draw_cycle(
    dwg: svgwrite.Drawing,
    positions: list[str],
    width: float,
    n: int = 3,
) -> None:
    """Draw directional arrows forming a cycle through named positions."""
    for i in range(len(positions)):
        a = positions[i]
        b = positions[(i + 1) % len(positions)]
        path = _arrow_path(dwg, a, b, width, n)
        path["marker-end"] = "url(#arrowhead)"
        dwg.add(path)


# category -> output subdirectory. A table rather than an if-chain with a
# fallthrough: the chain returned "" for anything it did not recognise, which
# wrote a new group into the root of the tree, where `scripts/sync-diagrams.sh`
# (which copies subdirectories) would never have shipped it.
_CASE_SUBDIRS = {
    "oll_cross": "oll",
    "oll_corners": "oll",
    "oll_full": "oll-full",
    "pll_corners": "pll",
    "pll_edges": "pll",
    "pll_full": "pll-full",
    "444_oll": "444-oll",
    "444_pll": "444-pll",
}


def _case_subdir(category: str) -> str:
    """Return subdirectory name for a diagram category."""
    try:
        return _CASE_SUBDIRS[category]
    except KeyError:
        raise ValueError(
            f"unknown diagram category {category!r} — add it to _CASE_SUBDIRS, or it "
            f"lands in the tree root and never ships"
        ) from None


def render(case: CubeDiagram, output_dir: Path, style: DiagramStyle = SCREEN) -> Path:
    """Render a CubeDiagram to an SVG file in the given style."""
    recolor = _restyle(style)
    n = case.n
    grid_w = n * CELL + (n - 1) * GAP
    grid_h = n * CELL + (n - 1) * GAP
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

    # Draw U face (n x n grid)
    for idx, color in enumerate(case.u_face):
        r, c = idx // n, idx % n
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
            _draw_swap(dwg, pos_a, pos_b, style.stroke_arrow, n)
        for cycle in case.cycles:
            _draw_cycle(dwg, cycle, style.stroke_arrow, n)
        for pos_a, pos_b in case.dashed_swaps:
            _draw_swap(dwg, pos_a, pos_b, style.stroke_arrow, n, dashed=True)

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
    """A single step progress diagram, in three tiers.

    `solved` is every sticker the cube has right at this point in the method.
    `subject` is the part of it THIS picture is about — what its lesson
    teaches — and everything in `solved` that is not in `subject` is what an
    earlier step already finished and this one must not wreck, so it renders
    through `dim()`. Anything outside `solved` has not been reached and renders
    in `UNREACHED`.

    `subject is None` says the picture has no earlier-solved tier at all, which
    is a claim about the method rather than a default: it holds for exactly the
    three diagrams where nothing was solved before (`step_1_cross`), where
    nothing is solved at all (`step_flip`, a rotation, not a step), and where
    everything is the subject (`step_7_solved`). `tests/test_derivation.py`
    pins that list, so a new diagram cannot quietly join it.

    `overrides` are always subject: they exist to paint the piece the lesson is
    pointing at, in the wrong place or the wrong twist.
    """

    name: str
    filename: str
    solved: set[tuple[str, int, int]]
    subject: set[tuple[str, int, int]] | None = None
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

# Shared solved-sticker-set progression, cumulative: each milestone is the one
# before it plus exactly what its step adds. Written that way on purpose — a
# step diagram's SUBJECT is then `milestone - previous`, derived rather than
# declared, so the highlighted region cannot drift from what the method says
# that step does. `_CROSS_DONE` is the cube after step 1 and the `x2` flip:
# white is on the bottom and out of the isometric view, and all that remains of
# it in frame are the two cross edges' side stickers.
_CROSS_DONE = _CENTERS | {("F", 1, 0), ("R", 1, 0)}
_FIRST_LAYER = _CROSS_DONE | {("F", 0, 0), ("F", 2, 0), ("R", 0, 0), ("R", 2, 0)}
_SECOND_LAYER = _FIRST_LAYER | {("F", 0, 1), ("F", 2, 1), ("R", 0, 1), ("R", 2, 1)}
_YELLOW_CROSS = _SECOND_LAYER | {("U", 1, 0), ("U", 0, 1), ("U", 2, 1), ("U", 1, 2)}
_EDGES_ALIGNED = _YELLOW_CROSS | {("F", 1, 2), ("R", 1, 2)}
_CORNERS_POSITIONED = _EDGES_ALIGNED | {("F", 0, 2), ("F", 2, 2), ("R", 0, 2), ("R", 2, 2)}
_SOLVED = _CORNERS_POSITIONED | {("U", 0, 0), ("U", 2, 0), ("U", 0, 2), ("U", 2, 2)}


def _step_sticker_color(
    face: str,
    a: int,
    b: int,
    solved: set[tuple[str, int, int]],
    face_colors: dict[str, str] | None = None,
    overrides: dict[tuple[str, int, int], str] | None = None,
    subject: set[tuple[str, int, int]] | None = None,
) -> str:
    """One sticker, in whichever of the three tiers it belongs to.

    Overrides come first: they are the piece the lesson is pointing at, so they
    are always full colour. Then solved-and-subject in full colour, solved-but-
    earlier through `dim()`, and everything else `UNREACHED`.
    """
    if overrides and (face, a, b) in overrides:
        return overrides[(face, a, b)]
    colors = face_colors or _CUBE_FACE_COLORS
    if (face, a, b) not in solved:
        return UNREACHED
    if subject is None or (face, a, b) in subject:
        return colors[face]
    return dim(colors[face])


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
    """The eight goal-state figures: white-on-top → flip → yellow-on-top.

    Each one's subject is the difference between its milestone and the one
    before, which is the same sentence its lesson opens with. Three carry no
    dim tier and each has its own reason: `step_1_cross` is the first step, so
    nothing was solved before it; `step_flip` is an `x2` and solves nothing, so
    dimming the cross it carries would claim a step happened; `step_7_solved`
    is captioned "Solved", and a solved cube with three quarters of it dimmed
    would say the opposite.
    """
    white_top = {"U": WHITE, "F": GREEN, "R": RED}

    # Step 1: White Cross on top — the same six stickers `_CROSS_DONE` keeps,
    # seen from the other end of the cube before the flip puts them underneath.
    cross = set(_CENTERS) | {
        ("U", 1, 0),
        ("U", 0, 1),
        ("U", 2, 1),
        ("U", 1, 2),
        ("F", 1, 2),
        ("R", 1, 2),
    }
    return [
        StepDiagram("White Cross", "step_1_cross", cross, face_colors=white_top),
        StepDiagram("Flip", "step_flip", set(cross), face_colors=white_top, arrow="x"),
        StepDiagram(
            "White Corners", "step_2_corners", set(_FIRST_LAYER), _FIRST_LAYER - _CROSS_DONE
        ),
        StepDiagram(
            "Middle Edges", "step_3_edges", set(_SECOND_LAYER), _SECOND_LAYER - _FIRST_LAYER
        ),
        StepDiagram(
            "Yellow Cross", "step_4_ycross", set(_YELLOW_CROSS), _YELLOW_CROSS - _SECOND_LAYER
        ),
        StepDiagram(
            "Align Edges", "step_5_yedges", set(_EDGES_ALIGNED), _EDGES_ALIGNED - _YELLOW_CROSS
        ),
        StepDiagram(
            "Position Corners",
            "step_6_ycorners_pos",
            set(_CORNERS_POSITIONED),
            _CORNERS_POSITIONED - _EDGES_ALIGNED,
        ),
        StepDiagram("Solved", "step_7_solved", set(_SOLVED)),
    ]


def _corner_case_steps() -> list[StepDiagram]:
    """Corner insertion case diagrams: white faces right/front/up.

    The white-red-green corner sits above its slot at up-front-right. Its
    three legal orientations (simulator-verified — the mirror orders are
    physically impossible) are, as (U, F, R) sticker triples:
    white right = (G, R, W); white front = (R, W, G); white up = (W, G, R).
    """
    # Everything solved here is the cross, which step 1 finished; the subject
    # is the corner, and the corner is entirely in `overrides`. So `subject` is
    # empty rather than None — "all of this was done earlier", not "no earlier
    # tier exists".
    return [
        StepDiagram(
            "White Right",
            "corner_right",
            set(_CROSS_DONE),
            set(),
            overrides={("U", 2, 2): GREEN, ("F", 2, 2): RED, ("R", 2, 2): WHITE},
        ),
        StepDiagram(
            "White Front",
            "corner_front",
            set(_CROSS_DONE),
            set(),
            overrides={("U", 2, 2): RED, ("F", 2, 2): WHITE, ("R", 2, 2): GREEN},
        ),
        StepDiagram(
            "White Up",
            "corner_up",
            set(_CROSS_DONE),
            set(),
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
            # Step 5 is read on the edges' SIDE stickers: the one already over
            # its centre and the one that is not. The yellow cross above them
            # is step 4's and must survive, which is what dim says.
            {("R", 1, 2)},
            overrides={("F", 1, 2): BLUE},  # F has L's color
            swap_arrows=[  # front ↔ left, arc to the left
                ((1.5, 2.5, 3), (0.5, 3, 1.5), (-0.5, 4.5, 3.5)),
            ],
        ),
        StepDiagram(
            "Opposite Edges",
            "align_diagonal",
            _YELLOW_CROSS | {("R", 1, 2)},  # R+L correct
            {("R", 1, 2)},
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
        # Every piece is already in its slot — the lesson says so in its first
        # line. The only thing this step changes is the twist of the four
        # bottom corners, and those are the overrides.
        set(),
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
            set(),
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
            set(),
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
        # The picture is the held corner and the three that cycle past it;
        # everything under the last layer is steps 1-5 and stays put.
        set(),
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
            set(),  # the first layer is step 2's; the edge above it is the case
            overrides={("F", 1, 2): RED, ("U", 1, 2): GREEN},
        ),
        StepDiagram(
            "Edge Left",
            "edge_left",
            set(_FIRST_LAYER),
            set(),
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


def _n_face_quad(face: str, a0: int, a1: int, b0: int, b1: int) -> list[tuple[float, float]]:
    """Projected 2D corners of the rectangle a in [a0,a1], b in [b0,b1] on a
    visible face. One sticker is the a1=a0+1, b1=b0+1 case; a slot outline
    spans several cells, which is the only reason this is not just
    `_n_sticker_pts`."""
    if face == "U":
        corners = [(a0, 3, b0), (a1, 3, b0), (a1, 3, b1), (a0, 3, b1)]
    elif face == "F":
        corners = [(a0, b1, 3), (a1, b1, 3), (a1, b0, 3), (a0, b0, 3)]
    elif face == "R":
        corners = [(3, b1, a0), (3, b1, a1), (3, b0, a1), (3, b0, a0)]
    else:
        return []
    return [_n_proj(*c) for c in corners]


def _n_sticker_pts(face: str, a: int, b: int) -> list[tuple[float, float]]:
    """Get projected 2D corners of sticker (a,b) on a visible face."""
    return _n_face_quad(face, a, a + 1, b, b + 1)


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
        # E CW (follows D): F row b=1 → R row b=1.  Edge: F-R at y=1.5
        "E": ((1.5, 1.5, 3), (3, 1.5, 1.5), (3 + _b, 1.5, 3 + _b)),
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


def _draw_iso_stickers(dwg: svgwrite.Drawing, color_fn: Callable[[str, int, int], str]) -> None:
    """Draw 3×3 stickers on each visible face (R → F → U for correct layering)."""
    for face in ("R", "F", "U"):
        for a in range(3):
            for b in range(3):
                pts = _n_sticker_pts(face, a, b)
                color = color_fn(face, a, b)
                dwg.add(dwg.polygon(pts, fill=color, stroke=STICKER_STROKE, stroke_width=1.2))


def _iso_viewbox(pad: float) -> tuple[float, float, float, float]:
    """Tight (x, y, w, h) around the projected cube, with `pad` on every side."""
    proj_pts = [_n_proj(x, y, z) for x in (0, 3) for y in (0, 3) for z in (0, 3)]
    min_x, max_x = min(p[0] for p in proj_pts), max(p[0] for p in proj_pts)
    min_y, max_y = min(p[1] for p in proj_pts), max(p[1] for p in proj_pts)
    return (min_x - pad, min_y - pad, max_x - min_x + 2 * pad, max_y - min_y + 2 * pad)


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

    pad = 6 if step.arrow or step.swap_arrows or step.dir_arrows else 4
    vb_x, vb_y, vb_w, vb_h = _iso_viewbox(pad)

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
            c := _step_sticker_color(
                f, a, b, step.solved, step.face_colors, step.overrides, step.subject
            ),
            c,
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


# ── Slot-and-pair case diagrams (F2L) ─────────────────────────────────
# A last-layer case is a plan view because everything that identifies it faces
# up. An F2L case is the opposite: it is a corner and an edge whose identity
# lives in sideways-facing stickers, one layer under the U face, and in how far
# the pair sits from the slot it belongs in. A top-down grid cannot say any of
# that, so these reuse the isometric U/F/R projection the 19 step diagrams
# already draw — the same picture, at the same scale, so an F2L tile sits
# beside the guide's step figures without looking like a different product.
#
# U/F/R is sufficient and that is a measured claim, not a hope. Across the 41
# cases the corner is only ever at UFR or DFR and the edge only at FR, UR, UF,
# UL or UB, so at least one facelet of each piece is always in view; 18 cases
# show all five, and the other 23 hide exactly one, which the two visible ones
# determine (the FR edge is *the* red/green edge — one sticker fixes the
# other). The FR slot itself lands on the near vertical edge, dead centre of
# the projection, which is where the eye goes first anyway.
#
# What it must NOT copy is `StepDiagram`'s idiom. A step diagram hand-declares
# its solved set, which is the one place in this repo that writes sticker
# layouts by hand; it gets away with it because a progress figure is an
# illustration, not a case. A case is data. So `SlotDiagram` carries a complete
# 27-entry colour map and a slot set, both computed in `fullsets.py` from the
# case's setup algorithm through the simulator, and this renderer has no
# opinion about cubes at all.

SLOT_STROKE_W = 3.0


@dataclass
class SlotDiagram:
    """An isometric case diagram with a marked target slot.

    Every field is derived: `colors` is the complete map over the 27 visible
    facelets and `slot` names the facelets of the slot being filled. Nothing
    here is declared by hand — see `fullsets.f2l_cases`.
    """

    name: str  # filename stem
    label: str  # human-readable label
    subdir: str  # output subdirectory under guide/figures/generated/
    colors: dict[tuple[str, int, int], str]
    slot: frozenset[tuple[str, int, int]]


def _slot_outline_quads(
    slot: frozenset[tuple[str, int, int]],
) -> list[list[tuple[float, float]]]:
    """One outline per visible face, around the union of that face's slot cells.

    Drawn as a single pocket per face rather than a box per sticker: the slot
    is one hole with a corner half and an edge half, and four separate squares
    read as four separate things.
    """
    quads = []
    for face in ("F", "R", "U"):
        cells = [(a, b) for f, a, b in slot if f == face]
        if not cells:
            continue
        a_vals = [a for a, _ in cells]
        b_vals = [b for _, b in cells]
        quads.append(_n_face_quad(face, min(a_vals), max(a_vals) + 1, min(b_vals), max(b_vals) + 1))
    return quads


def render_slot(case: SlotDiagram, output_dir: Path, style: DiagramStyle = SCREEN) -> Path:
    """Render a slot-and-pair case diagram (3D isometric cube) to SVG."""
    recolor = _restyle(style)
    subdir = output_dir / case.subdir
    subdir.mkdir(parents=True, exist_ok=True)
    filepath = subdir / f"{case.name}.svg"

    vb_x, vb_y, vb_w, vb_h = _iso_viewbox(4)
    dwg = svgwrite.Drawing(
        str(filepath),
        size=(f"{vb_w:.0f}px", f"{vb_h:.0f}px"),
        viewBox=f"{vb_x:.1f} {vb_y:.1f} {vb_w:.1f} {vb_h:.1f}",
    )
    if style.themed:
        _add_theme(dwg)
    dwg.add(_bg(dwg, (vb_x, vb_y), (vb_w, vb_h), 6))
    _draw_iso_stickers(dwg, lambda f, a, b: recolor.get(c := case.colors[f, a, b], c))
    _draw_cube_outline(dwg)

    # The slot marker goes on last so it reads over the stickers it frames.
    # It is not themed: it is drawn on sticker fills, which never flip, so an
    # ink colour that followed the page would disappear on one of the two.
    for quad in _slot_outline_quads(case.slot):
        dwg.add(
            dwg.polygon(
                quad,
                fill="none",
                stroke=ARROW_COLOR,
                stroke_width=SLOT_STROKE_W,
                stroke_linejoin="round",
            )
        )

    dwg.save(pretty=True)
    return filepath


def _draw_rotation_arc(
    dwg: svgwrite.Drawing,
    proj_fn: Projector,
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

    def _add_cap(group: Any, pt_a: Point, pt_b: Point) -> None:
        cap = dwg.line(pt_a, pt_b, stroke=ARROW_COLOR, stroke_width=1.5)
        cap["stroke-linecap"] = "round"
        group.add(cap)

    # Collect per-segment data for two-pass rendering
    seg_data: list[tuple[bool, list[Point], list[Point]]] = []
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
                fill=WHITE,
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
    arrow_g.add(dwg.path(d=_svg_polyline(bg_pts, closed=True), fill=WHITE, stroke="none"))
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
            fill=WHITE,
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
    _add_theme(dwg)
    dwg.add(_bg(dwg, (vb_x, vb_y), (vb_w, vb_h), 8))

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

    def _add_line(start: Point, end: Point, color: str = STICKER_STROKE, **extra: str) -> None:
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
                dwg.add(_ink(dwg.circle(center=proj(*tip), r=5, fill=ARROW_COLOR)))
            dwg.add(arrow_g)

    # 6. Dots and labels at each tip
    for i, (label, face_center, tip, _, _) in enumerate(axes):
        e = proj(*tip)
        if label not in ("B", "L"):
            dwg.add(_ink(dwg.circle(center=e, r=5, fill=ARROW_COLOR)))

        lx, ly = label_positions[i]
        dwg.add(
            _ink(
                dwg.text(
                    label,
                    insert=(lx, ly),
                    text_anchor="middle",
                    dominant_baseline="central",
                    font_size="18px",
                    font_family="sans-serif",
                    font_weight="bold",
                    fill=ARROW_COLOR,
                )
            )
        )

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
    from cubepath.fullsets import render_big_sets, render_f2l, render_fullsets

    total += render_fullsets(output_dir)

    # F2L: 41 slot-and-pair isometric cases, derived from the same extraction.
    total += render_f2l(output_dir)

    # 4x4: 27 OLL + 22 PLL, derived from the kpuzzle states in case-states.json
    # because cube.py cannot model a 4x4 and must not be taught to.
    total += render_big_sets(output_dir)

    for move in _notation_moves():
        path = render_notation(move, output_dir)
        print(f"  {path.relative_to(output_dir)}")
        total += 1

    print(f"  {render_overview(output_dir).relative_to(output_dir)}")
    total += 1

    for step in all_steps():
        path = render_step(step, output_dir)
        print(f"  {path.relative_to(output_dir)}")
        total += 1

    print(f"\nGenerated {total} SVG diagrams in {output_dir}")


if __name__ == "__main__":
    main()
