"""SVG cube diagram generator for Cubepath guide.

Generates top-face plan-view diagrams for OLL and PLL cases,
plus 3D isometric notation move diagrams.
"""

from __future__ import annotations

import functools
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import svgwrite

from cubepath import palette
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
# not-reached tier is the one that moves, to a WARM neutral one step lighter —
# 8.3 ΔE from the mask (the just-noticeable difference is ~2.3), enough that
# the two read as different tones when two pictures sit adjacent on a page, and
# light enough that "not reached" stays the quietest thing in the picture
# rather than becoming the heaviest. That the two never share a FILE is a
# separate and absolute gate in `tests/test_diagrams.py`; this tone only has to
# survive being NEAR the mask, never inside the same picture as it.
#
# WHY WARM, and why not the cool tint this replaced. The tier has to clear the
# WHITE face and the page, which are 1.6 ΔE apart — so a neutral cannot be far
# from both at once, and buys that distance either with lightness or with a
# tint. The first version bought it with blue (#C0D4E6, b* -11.1): 19.7 ΔE off
# white for free. But the cube already OWNS a blue face, the five dim tones are
# all warm or muted (#BEAB7A tan, #CA8876 salmon, #9ABCA6 sage, #A07757,
# #797C9F), and a pale blue among them does not read as "no claim here" — it
# reads as a seventh sticker colour, which is exactly the report this replaces
# ("the grey looks blue").
#
# WHY THIS LIGHT AND NO LIGHTER. Warming the tier costs the cheap distance blue
# was buying, so the first warm attempt paid for it in lightness instead
# (#E6E3DD, L* 90.3) and came out glaringly bright — it read as a hole in the
# page rather than as a grey. The floor is set by DIM WHITE (#ABABAB), the one
# tone with no hue to separate it: the ≥15 ΔE dim gate puts the bottom at
# L* ~85, and #D8D5CF sits there at 15.7. That is also the value that reads as
# the SAME KIND OF GREY as the OLL mask — which is the point, because they are
# both "grey" to a reader and only the tone distinguishes the claim. Going
# lighter buys mask separation the split does not need and spends white-face
# separation the picture does need: #D8D5CF is 15.0 ΔE off white where #E6E3DD
# was 10.2 — and it sits ON that floor, so
# `test_a_full_face_is_separable_from_the_not_reached_tone_too` is the gate a
# brighter value fails first. Do not restore a cool value, and do not brighten
# it back, without re-reading this, that test, and
# `test_the_two_greys_are_different_tones`.
UNORIENTED = "#C0C0C0"  # OLL/PLL plan views: a real sticker, not yellow
UNREACHED = "#D8D5CF"  # step + F2L diagrams: the method has not got here yet

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
# Three things flip: `.ink` (a filled label or dot on the plate), `.ink-stroke`
# (a stroked line on the plate — a rule on `fill` does nothing to a <line>, and
# a rule on `stroke` would outline every label, so the two are separate
# classes) and `.paper` (an occluder that stands in for the page, which must
# follow the page's colour or it glares on a dark screen). Sticker strokes and
# arrows are read against coloured faces, so they stay as they are.
DARK_INK = "#ECE8E1"  # tokens.css --ink, dark
DARK_PAPER = "#161412"  # tokens.css --paper, dark

_THEME_CSS = (
    f".bg{{fill:{WHITE}}}.paper{{fill:{WHITE}}}"
    f".ink{{fill:{ARROW_COLOR}}}.ink-stroke{{stroke:{ARROW_COLOR}}}"
    "@media (prefers-color-scheme:light){.bg{fill:none}}"
    f"@media (prefers-color-scheme:dark){{.bg{{fill:none}}.paper{{fill:{DARK_PAPER}}}"
    f".ink{{fill:{DARK_INK}}}.ink-stroke{{stroke:{DARK_INK}}}}}"
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
    """Tag a filled label or dot drawn on the plate rather than on a sticker."""
    elem["class"] = "ink"
    return elem


def _ink_stroke(elem: Any) -> Any:
    """Tag a stroked line drawn on the plate rather than on a sticker."""
    elem["class"] = "ink-stroke"
    return elem


def _paper(elem: Any) -> Any:
    """Tag a fill that stands in for the page: an occluder painted in paper."""
    elem["class"] = "paper"
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
    masked=UNORIENTED,
    unreached=UNREACHED,
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
    # On a mono laser the lines are the only structure on a solid face.
    layer_lines=0.9,
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


@functools.cache
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
    category: str  # "oll_cross", "oll_corners", "pll_corners", "444_parity", ...
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


def _derived_cross_case(name: str, label: str, alg: str) -> CubeDiagram:
    """OLL cross case derived from its algorithm's pre-state.

    Shows the U-face edge/center pattern; corners carry the orientation mask
    (don't-care at the cross stage). The hold is the pre-state's own: pass the
    procedure the phase actually runs and the picture comes out at that angle.
    """
    cube = state_before(alg)
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

    The Hook is drawn twice, because the two phases hold it differently and the
    hold is the whole recognition cue. Each picture is the pre-state of the
    procedure its phase runs, so neither needs a view turn: `oll_hook` is two
    passes of the narrow F-sexy-F' (L in back-left — Phase 1, the guide's
    Phase 1 figure and Card 1); `oll_hook_wide` is the one-pass wide `f-sexy-f'`
    (L in front-right — the `eo.hook` icon, the guide's Phase 1.5 figure and
    Card 2). The web needs the second file because a `CaseDef.icon` is a path
    with nowhere to hang a rotation; the guide and cards used to rotate the
    first 180° instead and now read the second.
    """
    narrow = ALGORITHMS["F-sexy-F'"]
    return [
        _derived_cross_case("oll_dot", "Dot", DOT_SEQUENCE),
        _derived_cross_case("oll_hook", "Hook / L-shape", f"{narrow} {narrow}"),
        _derived_cross_case("oll_hook_wide", "Hook / L-shape (wide f)", ALGORITHMS["f-sexy-f'"]),
        _derived_cross_case("oll_line", "Line", narrow),
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
    # The big cubes get parity and nothing else: the course teaches reduction,
    # so a big cube becomes a 3x3 and the 3x3 sets above finish it. The 27+22
    # 4x4 last-layer cases and the 13 5x5 L2E cases are one-look optimisations,
    # locked out of the UI by app/src/lib/unlocks.ts, and were the only readers
    # of the "444-oll", "444-pll" and "555-l2e" trees. See fullsets.TAUGHT_BIG_CUBE.
    "444_parity": "444-parity",
    "555_parity": "555-parity",
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
    # Cube order. 3 leaves every existing step untouched; 4 and 5 are what the
    # course index uses to show a big cube as a big cube instead of borrowing a
    # 3x3 with a letter on it.
    n: int = 3


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


def _arrowhead(tip: Point, prev: Point, sz: float, spread: float) -> tuple[Point, list[Point]]:
    """A triangular arrowhead at `tip` pointing away from `prev` (which must
    differ from it): its base point `sz` back along the arrow, and the
    triangle, whose wings sit `sz * spread` either side of the base."""
    dx, dy = tip[0] - prev[0], tip[1] - prev[1]
    ln = math.hypot(dx, dy)
    if ln == 0:
        raise ValueError(f"arrowhead at {tip} has no direction: prev == tip")
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux
    base = (tip[0] - sz * ux, tip[1] - sz * uy)
    wings = [
        (base[0] + sz * spread * nx, base[1] + sz * spread * ny),
        (base[0] - sz * spread * nx, base[1] - sz * spread * ny),
    ]
    return base, [tip, *wings]


def _polyline(pts: list[Point], closed: bool = False) -> str:
    """SVG path data through `pts`, coordinates to a tenth."""
    d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return d + " Z" if closed else d


def _draw_arrowhead(
    dwg: svgwrite.Drawing,
    tip: tuple[float, float],
    prev: tuple[float, float],
    sz: float,
) -> None:
    """Draw a triangular arrowhead at tip pointing away from prev."""
    if tip != prev:
        _base, triangle = _arrowhead(tip, prev, sz, 0.4)
        dwg.add(
            dwg.polygon(
                triangle,
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
        d = _polyline(shortened)
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


Vec3 = tuple[float, float, float]


def _n_rect_corners(face: str, a0: float, a1: float, b0: float, b1: float) -> list[Vec3]:
    """3D corners of the rectangle a in [a0,a1], b in [b0,b1] on a visible face.
    The one place the (a, b) convention of the three visible faces is written
    down: sticker quads, `sticker_centre`, the overview's whole-face quads and
    the F2L slot outlines all derive from it."""
    if face == "U":
        return [(a0, 3, b0), (a1, 3, b0), (a1, 3, b1), (a0, 3, b1)]
    if face == "F":
        return [(a0, b1, 3), (a1, b1, 3), (a1, b0, 3), (a0, b0, 3)]
    if face == "R":
        return [(3, b1, a0), (3, b1, a1), (3, b0, a1), (3, b0, a0)]
    raise ValueError(f"not a visible face: {face!r}")


def _n_sticker_corners(face: str, a: int, b: int, size: int = 1) -> list[Vec3]:
    """3D corners of the `size`-wide square at (a, b) on a visible face — a
    sticker at 1, the whole face at 3."""
    return _n_rect_corners(face, a, a + size, b, b + size)


def _n_face_quad(
    face: str, a0: float, a1: float, b0: float, b1: float
) -> list[tuple[float, float]]:
    """Projected 2D corners of a rectangle spanning several cells — an F2L slot
    outline. One sticker is the a1=a0+1, b1=b0+1 case."""
    return [_n_proj(*c) for c in _n_rect_corners(face, a0, a1, b0, b1)]


def _n_sticker_pts(face: str, a: int, b: int, n: int = 3) -> list[tuple[float, float]]:
    """Projected 2D corners of sticker (a, b) on a visible face of an n-cube.

    The cube stays THREE UNITS WIDE whatever its order — only the cell size
    changes — so a 4x4 and a 5x5 project into the same box as a 3x3, share the
    outline and the viewBox, and sit at the same size beside one on a page.
    That is the whole reason the isometric renderer can draw a big cube at all:
    nothing about the projection, the camera or the arrows is per-order.
    """
    step = 3 / n
    return _n_face_quad(face, a * step, (a + 1) * step, b * step, (b + 1) * step)


Arrow3 = tuple[Vec3, Vec3, Vec3]  # src, dst, bezier control
# The move diagrams' one visual distinction: a dashed stroke means the whole
# cube turns.
_WHOLE_CUBE_DASH = "6,3"

# Arrow configs: (cw_src_3d, cw_dst_3d, control_3d)
# src/dst = center of affected stickers on each face for CW direction.
# control = edge point pushed outward (Bezier control for the bulge).
# When CCW, src and dst swap.
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
    sz = 16

    # Shorten arc at tip to make room for arrowhead
    head: list[Point] | None = None
    shortened = pts
    if tip != prev:
        arc_end, head = _arrowhead(tip, prev, sz, 0.5)
        shortened = pts[:-2] + [arc_end]

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

    if head is not None:
        dwg.add(dwg.polygon(head, fill=ARROW_COLOR))


def _draw_iso_stickers(
    dwg: svgwrite.Drawing, color_fn: Callable[[str, int, int], str], n: int = 3
) -> None:
    """Draw an n x n grid of stickers on each visible face (R → F → U, so the
    later faces paint over the earlier ones and the layering reads right).

    The stroke thins with the grid: 1.2px between 3x3 stickers is a hairline
    between 5x5 ones' worth of cube, and at the 92px the course index renders
    these it would close the gaps up into a solid block.
    """
    width = 1.2 * 3 / n
    for face in ("R", "F", "U"):
        for a in range(n):
            for b in range(n):
                pts = _n_sticker_pts(face, a, b, n)
                color = color_fn(face, a, b)
                dwg.add(dwg.polygon(pts, fill=color, stroke=STICKER_STROKE, stroke_width=width))


def _iso_viewbox(pad: float) -> tuple[float, float, float, float]:
    """Tight (x, y, w, h) around the projected cube, with `pad` on every side."""
    min_x, min_y, max_x, max_y = _N_CUBE_BOX
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
        step.n,
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
    subdir: str  # output subdirectory under app/public/diagrams/
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
    """Which of the two overview drawings to render: its filename and its
    painter. The two instances sit just above `render_overview`."""

    filename: str
    draw: Callable[[svgwrite.Drawing, _Bounds, DiagramStyle], None]


# Which coordinate a face's layer is sliced along, and which slab it is.
# `tests/test_diagrams.py` checks each row against the simulator.
_LAYER_OF: dict[str, tuple[int, int]] = {
    "L": (0, 0), "R": (0, 2),
    "D": (1, 0), "U": (1, 2),
    "B": (2, 0), "F": (2, 2),
}  # fmt: skip
_FACE_NORMAL: dict[str, Vec3] = {
    "U": (0, 1, 0), "D": (0, -1, 0), "F": (0, 0, 1),
    "B": (0, 0, -1), "R": (1, 0, 0), "L": (-1, 0, 0),
}  # fmt: skip
# The visible faces, in the order their pins are drawn. The set is what the
# view direction says it is (`_depth(normal) > 0`); the tests check that.
_OV_ON_FACE = ("F", "U", "R")
# Each visible face as one quad: the 3-wide "sticker" at its origin.
_OV_FACES: dict[str, list[Vec3]] = {f: _n_sticker_corners(f, 0, 0, 3) for f in _OV_ON_FACE}
_CUBE_CENTRE: Vec3 = (1.5, 1.5, 1.5)
# The direction toward the camera for `_n_proj`: screen-right x screen-down.
_VIEW_DIR: Vec3 = (_N_SIN_H, _N_ELEV, _N_COS_H)

# ── pins layout ──
# Screen distance from the cube centre to each tip, in viewBox units. The
# hidden faces' pins run behind the cube and need the extra reach for their
# ring to clear the silhouette.
_OV_PIN_TIP = {"front": 56.0, "back": 75.0}
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
_OV_HALO_RIM = 0.7  # a halo's rim either side of its ink, as a fraction of the stroke


def sticker_centre(face: str, a: int, b: int) -> Vec3:
    """3D centre of a visible-face sticker: the mean of its corners."""
    corners = _n_sticker_corners(face, a, b)
    return (
        sum(c[0] for c in corners) / 4,
        sum(c[1] for c in corners) / 4,
        sum(c[2] for c in corners) / 4,
    )


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
    (x, y or z == 3) belongs to the outer layer; a point off the cube is an
    error, not a layer."""
    if not 0 <= coord <= 3:
        raise ValueError(f"{coord} is not within the cube")
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
    cube.set_visible_sticker(face, a, b, "X")


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


def _depth(p: Vec3) -> float:
    """How far toward the camera `p` is: its component along `_VIEW_DIR`."""
    return sum(p[i] * _VIEW_DIR[i] for i in range(3))


def _view_coeffs(n: Vec3) -> tuple[float, float]:
    """(a, b) with depth(θ) = a cos θ + b sin θ for a ring around `n`: how
    much nearer the camera a ring point at angle θ is than the ring's centre."""
    u, v = _ring_basis(n)
    return _depth(u), _depth(v)


def _ring_pt(centre: Vec3, n: Vec3, radius: float, angle: float) -> Vec3:
    """The point at `angle` (radians) on the ring around `n` through `centre`,
    clockwise seen from +n."""
    u, v = _ring_basis(n)
    c, s = radius * math.cos(angle), radius * math.sin(angle)
    return (
        centre[0] + u[0] * c + v[0] * s,
        centre[1] + u[1] * c + v[1] * s,
        centre[2] + u[2] * c + v[2] * s,
    )


def _ring(
    centre: Vec3, n: Vec3, radius: float, start: float, sweep: float, samples: int = 40
) -> list[Vec3]:
    """A ring around `n` through `centre`, clockwise seen from +n. Angles in radians."""
    return [_ring_pt(centre, n, radius, start + sweep * i / samples) for i in range(samples + 1)]


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
    return (
        _CUBE_CENTRE[0] + 1.5 * n[0],
        _CUBE_CENTRE[1] + 1.5 * n[1],
        _CUBE_CENTRE[2] + 1.5 * n[2],
    )


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
    a, b = _view_coeffs(n)
    nearest = math.atan2(b, a)
    return centre, nearest - _OV_PIN_SWEEP - _OV_PIN_HEAD


def overview_pin_ring(face: str) -> list[Vec3]:
    """The ring's centre-line around a pin, as 3D points. Public for the tests."""
    centre, start = _pin_ring_frame(face)
    return _ring(centre, _FACE_NORMAL[face], _OV_PIN_RING_R, start, _OV_PIN_SWEEP)


def overview_pin_head(face: str) -> Vec3:
    """The 3D point of the arrowhead's tip: a little past the sweep end."""
    centre, start = _pin_ring_frame(face)
    return _ring_pt(
        centre, _FACE_NORMAL[face], _OV_PIN_RING_R, start + _OV_PIN_SWEEP + _OV_PIN_HEAD
    )


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
    does not, so ink drawn across a face — the hub's arrows, a pin's run from
    its face centre to the face edge — gets a paper-coloured halo. Measured,
    not chosen. The ribbons carry their own paper fill and need none.
    """
    faces = (recolor.get(c, c) for c in _CUBE_FACE_COLORS.values())
    return any(palette.contrast(ARROW_COLOR, f) < _OV_HALO_MIN_CONTRAST for f in faces)


def _ov_arrow(dwg: svgwrite.Drawing, bounds: _Bounds, pts3: list[Vec3], *, halo: bool) -> None:
    """A projected polyline with a filled head at its last point (the hub)."""
    pts = [_n_proj(*p) for p in pts3]
    tip, prev = pts[-1], pts[-3] if len(pts) > 2 else pts[0]
    stroke = _OV_STROKE
    base, triangle = _arrowhead(tip, prev, _OV_HEAD, 0.45)
    # The body stops at the head's base: every sample within the head's reach
    # of the tip goes, or the stroke would double back beside the head.
    body = [p for p in pts[:-1] if math.dist(p, tip) > _OV_HEAD] + [base]
    d = _polyline(body)
    head_pts = [(round(x, 1), round(y, 1)) for x, y in triangle]
    rim = _OV_HALO_RIM * stroke if halo else 0.0
    if halo:
        dwg.add(dwg.path(d=d, fill="none", stroke=WHITE, stroke_width=stroke + 2 * rim))
        dwg.add(dwg.polygon(head_pts, fill=WHITE, stroke=WHITE, stroke_width=2 * rim))
    dwg.add(
        dwg.path(d=d, fill="none", stroke=ARROW_COLOR, stroke_width=stroke, stroke_linecap="round")
    )
    dwg.add(dwg.polygon(head_pts, fill=ARROW_COLOR))
    for p in body:
        bounds.add(*p, stroke / 2 + rim)
    for p in head_pts:
        bounds.add(*p, rim)


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
    radius, sweep, band = _OV_PIN_RING_R, _OV_PIN_SWEEP, _OV_PIN_BAND
    n_pts = 48
    # depth(θ) > 0 means nearer the camera than the centre
    a_coeff, b_coeff = _view_coeffs(n)

    def ring_pt(angle: float) -> Vec3:
        return _ring_pt(centre, n, radius, angle)

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

    # The ribbon is paper with ink edges, and both flip with the theme: on a
    # dark page a white band glares and a dark edge vanishes.
    def edge(group: Any, pts: list[Point]) -> None:
        group.add(
            _ink_stroke(
                dwg.path(
                    d=_polyline(pts),
                    fill="none",
                    stroke=ARROW_COLOR,
                    stroke_width=_OV_PIN_STROKE,
                    stroke_linejoin="round",
                    stroke_linecap="round",
                )
            )
        )

    def cap(group: Any, p: Point, q: Point) -> None:
        line = dwg.line(p, q, stroke=ARROW_COLOR, stroke_width=_OV_PIN_STROKE)
        line["stroke-linecap"] = "round"
        group.add(_ink_stroke(line))

    def fill(group: Any, pts: list[Point]) -> None:
        group.add(_paper(dwg.path(d=_polyline(pts, closed=True), fill=WHITE, stroke="none")))

    segments: list[tuple[bool, list[Point], list[Point]]] = []
    for a0, a1 in zip(boundaries, boundaries[1:], strict=False):
        m = max(2, round(n_pts * (a1 - a0) / sweep))
        seg = [a0 + (a1 - a0) * j / m for j in range(m + 1)]
        is_front = depth((a0 + a1) / 2) > 0 or math.hypot(a_coeff, b_coeff) < 0.01
        segments.append((is_front, [band_pt(t, +1) for t in seg], [band_pt(t, -1) for t in seg]))

    # fills first, then continuous edges per depth zone, so no joints show
    for is_front, top, bot in segments:
        fill(front if is_front else back, top + bot[::-1])
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
        # A zone starts at the ribbon's open end or at a depth boundary. The
        # boundaries sit 90° from the pin, where the band is seen edge-on and
        # folds over itself, so the fold is a silhouette edge with the two
        # fills overlapping behind it: it is drawn on top of both — unless
        # the zone before it is the sliver at the open end, whose start cap
        # is already within a stroke of the fold. No cap at the sweep end,
        # where the band flows into the arrowhead.
        if i == 0:
            cap(group, top[0], bot[0])
        elif math.dist(top[0], segments[i - 1][1][0]) > 2 * _OV_PIN_STROKE:
            cap(front, top[0], bot[0])
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
    fill(arrow, [band_pt(back_in, +1), top_end, outer, tip, inner, bot_end, band_pt(back_in, -1)])
    edge(arrow, [band_pt(back_in, +1), top_end])
    edge(arrow, [band_pt(back_in, -1), bot_end])
    edge(arrow, [top_end, outer, tip, inner, bot_end])
    return back, front, arrow


def _ov_cube(dwg: svgwrite.Drawing, bounds: _Bounds, style: DiagramStyle) -> None:
    """Solid U / F / R faces with the two layer lines per face."""
    recolor = _restyle(style)
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
        line["stroke-opacity"] = f"{style.layer_lines:g}"
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


def _pin_exit(face: str, c: Point, tip: Point) -> Point:
    """Where a visible face's pin leaves its face on screen: the first point
    at which the projected pin, out from the projected face centre, crosses
    an edge of the projected face quad."""
    quad = [_n_proj(*p) for p in _OV_FACES[face]]
    dx, dy = tip[0] - c[0], tip[1] - c[1]
    best: float | None = None
    for p, q in zip(quad, quad[1:] + quad[:1], strict=True):
        ex, ey = q[0] - p[0], q[1] - p[1]
        denom = dx * ey - dy * ex
        if abs(denom) < 1e-9:
            continue  # the pin runs along this edge
        wx, wy = p[0] - c[0], p[1] - c[1]
        t = (wx * ey - wy * ex) / denom  # along the pin, in pin lengths
        s = (wx * dy - wy * dx) / denom  # along the edge, 0..1
        if t > 0 and 0 <= s <= 1 and (best is None or t < best):
            best = t
    if best is None:
        raise ValueError(f"{face}'s pin never leaves its face")
    return (round(c[0] + best * dx, 1), round(c[1] + best * dy, 1))


def _ov_pin_line(
    dwg: svgwrite.Drawing, bounds: _Bounds, a: Point, b: Point, *, on_plate: bool, halo: bool
) -> None:
    """One run of a pin. On the plate it flips with the theme; across a face
    it stays dark against the sticker colour, with a paper rim when the
    palette needs one — the same rule as `_ov_label`."""
    width = _OV_PIN_STROKE + 0.4
    rim = _OV_HALO_RIM * width if halo else 0.0
    if halo:
        # The rim stops one rim short of `b` (the face edge), so its round
        # cap ends exactly there instead of biting into the face outline.
        ln = math.dist(a, b)
        short = (b[0] - (b[0] - a[0]) / ln * rim, b[1] - (b[1] - a[1]) / ln * rim)
        under = dwg.line(a, short, stroke=WHITE, stroke_width=width + 2 * rim)
        under["stroke-linecap"] = "round"
        dwg.add(under)
    line = dwg.line(a, b, stroke=ARROW_COLOR, stroke_width=width)
    line["stroke-linecap"] = "round"
    dwg.add(_ink_stroke(line) if on_plate else line)
    for p in (a, b):
        bounds.add(*p, width / 2 + rim)


def _ov_pins(dwg: svgwrite.Drawing, bounds: _Bounds, style: DiagramStyle) -> None:
    """The pins layout. Draw order is the depth order: the hidden faces' pins
    and rings first so the cube occludes them, then the cube, then the
    visible faces'. Within one pin: the ring's back half, the pin through it,
    the front half and the head — and the dot at the tip, which sits
    `_OV_PIN_RING_IN` beyond the ring's plane along the normal, so it goes
    UNDER the ring when the pin points away from the camera (D, B, L) and
    over it when the pin points toward (U, F, R). A visible face's pin is
    split where it leaves the face: the run across the sticker stays dark
    (haloed when the palette needs it), the run across the plate flips with
    the theme. A hidden face's pin is all plate — the cube covers the rest.
    Letters last."""
    halo = _ov_needs_halo(_restyle(style))
    proj = {face: tuple(_n_proj(*p) for p in overview_pin(face)) for face in _FACE_NORMAL}
    rings = {}
    for face, n in _FACE_NORMAL.items():
        centre, start = _pin_ring_frame(face)
        rings[face] = _ribbon_arc(dwg, bounds, centre, n, start)

    def dot(face: str) -> None:
        tip = proj[face][1]
        circle = dwg.circle(
            center=(round(tip[0], 1), round(tip[1], 1)), r=_OV_PIN_DOT, fill=ARROW_COLOR
        )
        dwg.add(_ink(circle))
        bounds.add(*tip, _OV_PIN_DOT)

    def pin(face: str) -> None:
        c, tip = proj[face]
        back, front, head = rings[face]
        away = _depth(_FACE_NORMAL[face]) < 0
        if away:
            dot(face)
        dwg.add(back)
        if face in _OV_ON_FACE:
            leave = _pin_exit(face, c, tip)
            _ov_pin_line(dwg, bounds, c, leave, on_plate=False, halo=halo)
            _ov_pin_line(dwg, bounds, leave, tip, on_plate=True, halo=False)
        else:
            _ov_pin_line(dwg, bounds, c, tip, on_plate=True, halo=False)
        dwg.add(front)
        dwg.add(head)
        if not away:
            dot(face)

    for face in _FACE_NORMAL:
        if face not in _OV_ON_FACE:
            pin(face)
    _ov_cube(dwg, bounds, style)
    for face in _OV_ON_FACE:
        pin(face)
    for face in _FACE_NORMAL:
        c, tip = proj[face]
        dx, dy = tip[0] - c[0], tip[1] - c[1]
        ln = math.hypot(dx, dy)
        at = (
            tip[0] + dx / ln * _OV_PIN_LABEL_OUT,
            tip[1] + dy / ln * _OV_PIN_LABEL_OUT + 0.36 * _OV_PIN_LABEL,
        )
        _ov_label(
            dwg, bounds, face, at, size=_OV_PIN_LABEL, anchor="middle", on_plate=True, halo=False
        )


def _ov_hub(dwg: svgwrite.Drawing, bounds: _Bounds, style: DiagramStyle) -> None:
    halo = _ov_needs_halo(_restyle(style))
    _ov_cube(dwg, bounds, style)
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


OVERVIEW_PINS = OverviewLayout("overview", _ov_pins)
OVERVIEW_HUB = OverviewLayout("overview_hub", _ov_hub)


def render_overview(
    output_dir: Path, style: DiagramStyle = SCREEN, layout: OverviewLayout = OVERVIEW_PINS
) -> Path:
    """Render the notation overview: the six face turns on one cube."""
    subdir = output_dir / "notation"
    subdir.mkdir(parents=True, exist_ok=True)
    filepath = subdir / f"{layout.filename}.svg"

    dwg = svgwrite.Drawing(str(filepath))
    if style.themed:
        _add_theme(dwg)
    plate = _bg(dwg, (0, 0), (0, 0), 6)  # sized once the bounds are known
    dwg.add(plate)
    bounds = _Bounds()
    layout.draw(dwg, bounds, style)

    vb_x, vb_y = bounds.x0 - _OV_PAD, bounds.y0 - _OV_PAD
    vb_w, vb_h = bounds.x1 - bounds.x0 + 2 * _OV_PAD, bounds.y1 - bounds.y0 + 2 * _OV_PAD
    dwg["viewBox"] = f"{vb_x:.1f} {vb_y:.1f} {vb_w:.1f} {vb_h:.1f}"
    dwg["width"], dwg["height"] = f"{vb_w:.0f}px", f"{vb_h:.0f}px"
    plate["x"], plate["y"] = round(vb_x, 1), round(vb_y, 1)
    plate["width"], plate["height"] = round(vb_w, 1), round(vb_h, 1)

    dwg.save(pretty=True)
    return filepath


def _web_steps() -> list[StepDiagram]:
    """Step pictures the WEB needs and neither the guide nor a card does.

    DELIBERATELY NOT IN `all_steps()`. That list is what the guide and the CARD
    SET render, and a card is 85.6mm of paper — nothing belongs on it that no
    lesson teaches. `main()` renders this group into the web tree only.

    Two jobs. Four are course-index art, one per phase that had nothing honest
    to point at. The fifth is a CASE ICON: `444.edge-flip` was the one entry on
    /reference with no picture beside it, which on a page whose whole job is a
    picture per case is the gap that shows.

    The index shows one cube per phase, and it is the only place on the site
    that has to say what a phase gets you before you have read a word of it.
    Two of the eight phases had nothing honest to point at:

      * 4x4 and 5x5 borrowed a NOTATION diagram — a 3x3 with a large black "r
        (Rw)" or "M" printed over it. Wrong puzzle, wrong size, and a letter
        where a picture should be. They are real big cubes now: the isometric
        renderer takes an order, so a 4x4 and a 5x5 project into the same box
        a 3x3 does and sit at the same size beside one.
      * Phase 3 is "every case, one look" — the last layer FINISHED as a face,
        with the sides still to permute. The nearest existing picture was
        `step_6_ycorners_pos`, which is the beginner ladder's step 6 and reads
        as almost the same cube as step 5 at 92px.

    The two big-cube cubes are drawn MID-REDUCTION: centres built, edges not
    yet paired. That is the phase's actual content — reduction is the method,
    and a finished big cube would be indistinguishable from a finished 3x3,
    which is exactly what a solved-cube picture would fail to say.
    """
    # OLL done: the whole top face yellow, sides not yet permuted. Not a
    # milestone on either ladder — it is where the two 2-look halves meet, so
    # the subject is the U face and everything under it is the dim tier.
    oll_done = _SECOND_LAYER | {("U", a, b) for a in range(3) for b in range(3)}

    def centres(n: int) -> set[tuple[str, int, int]]:
        """The interior of each visible face at any order: everything but the
        outermost ring, which is corners and edges."""
        return {(f, a, b) for f in "UFR" for a in range(1, n - 1) for b in range(1, n - 1)}

    big = [
        StepDiagram(
            f"{n}x{n} centres", f"step_{n}{n}{n}_centres", centres(n), subject=centres(n), n=n
        )
        for n in (4, 5)
    ]
    # The edge flip's subject is the front-right edge pair — the piece it turns
    # over. On a 4x4 that is the two middle cells of F's rightmost column and of
    # R's frontmost column; both run off `n`, so the coordinates are arithmetic
    # rather than a table. Centres are dim (built already, and the flip is seven
    # outer turns so it cannot touch them); everything else is grey, because at
    # pairing time the method has not reached the corners.
    flip_n = 4
    flip_centres = centres(flip_n)
    # Both halves sit at the LAST index of their face's `a` axis, and that is
    # not a coincidence to be simplified away: on F, `a` runs left-to-right so
    # `a = n-1` is the edge shared with R; on R, `a` runs back-to-front (see
    # `_n_rect_corners`, where R's quad puts `a` on the z axis) so `a = n-1` is
    # the same shared edge seen from the other side. Using 0 for R highlights
    # the column at the BACK of the cube, which is invisible.
    flip_pair = {(face, flip_n - 1, b) for face in ("F", "R") for b in range(1, flip_n - 1)}
    return [
        StepDiagram(
            "Edge flip",
            "step_444_flip",
            flip_centres | flip_pair,
            subject=flip_pair,
            n=flip_n,
        ),
        # Basics: a whole cube, and a move. The index used to point this phase
        # at `step_flip`, whose cube is three-quarters grey because it is drawn
        # for the moment BEFORE the first layer exists — at 96px that reads as
        # a blank card rather than as "know your cube, read the moves".
        StepDiagram("Know Your Cube", "step_anatomy", set(_SOLVED), arrow="x"),
        StepDiagram("Top Face Oriented", "step_oll_done", set(oll_done), oll_done - _SECOND_LAYER),
        *big,
    ]


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
    # tools/cubepath/src/cubepath/diagrams.py -> repo root is 4 levels up.
    # ONE tree. These SVGs used to be written to guide/figures/generated/ and
    # then copied to app/public/diagrams/, so every diagram was committed twice
    # and a byte-identity test existed solely to prove the copy had happened.
    # The app is the only thing that must serve them from a fixed URL, so the
    # app's tree is the home and the guide reaches up into it — see
    # guide/cubepath.md's figure paths and the `--root ..` in defaults/pdf.yaml.
    output_dir = Path(__file__).resolve().parents[4] / "app" / "public" / "diagrams"
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

    # Big cubes: the three parity pictures the course teaches (two 4x4, one
    # 5x5), derived from the kpuzzle states in case-states.json because cube.py
    # cannot model a 4x4 and must not be taught to.
    total += render_big_sets(output_dir)

    for move in _notation_moves():
        path = render_notation(move, output_dir)
        print(f"  {path.relative_to(output_dir)}")
        total += 1

    for layout in (OVERVIEW_HUB, OVERVIEW_PINS):
        print(f"  {render_overview(output_dir, layout=layout).relative_to(output_dir)}")
        total += 1

    for step in [*all_steps(), *_web_steps()]:
        path = render_step(step, output_dir)
        print(f"  {path.relative_to(output_dir)}")
        total += 1

    print(f"\nGenerated {total} SVG diagrams in {output_dir}")


if __name__ == "__main__":
    main()
