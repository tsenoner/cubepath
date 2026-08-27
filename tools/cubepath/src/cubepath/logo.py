"""Brand mark generator for Cubepath.

Draws the logo — an isometric cube with a yellow route climbing the front face
and crossing the top — and writes it to `app/public/favicon.svg`, which every
other icon is then rasterized from (`gen-icons.mjs`). Run both with `make logo`.

This module, not the SVG, is the source of truth. The mark is parametric on
purpose: its 23 paths are quadratic-bezier strings that nobody can retune by
hand, so the trail shape, face tones, corner radii and sticker gap live here as
constants. `test_logo.py` fails the gate if the committed SVG drifts from what
this produces.

Note the route is drawn as flush yellow stickers, which is NOT a reachable cube
position: a contiguous sticker path can never legally cross a cube edge, because
the two facelets either side of an edge belong to the same piece. That is a
deliberate graphic choice — see CLAUDE.md.
"""

from __future__ import annotations

import math
from pathlib import Path

# ── Projection ──────────────────────────────────────────────────────────────
# True isometric, symmetric left-to-right (unlike the guide's notation cubes,
# which use a 35 degree yaw). The cube spans 0..3 on each axis; y is up.
COS30 = math.cos(math.radians(30))
VIEWBOX = 64.0
SCALE = 9.55
CENTER = VIEWBOX / 2

# ── Geometry constants (px in the 64x64 viewBox) ────────────────────────────
STICKER_INSET = 0.42  # gap between a sticker and its neighbours
STICKER_RADIUS = 0.95
BODY_RADIUS = 3.0  # rounding of the outer hexagon
TRAIL_INSET = 0.42  # keep in step with STICKER_INSET so the trail sits flush
TRAIL_RADIUS = 1.7

# ── Palette ─────────────────────────────────────────────────────────────────
# Mirrors the --logo-* tokens in app/src/styles/tokens.css.
LIGHT = {"b": "#17130f", "u": "#7a736b", "f": "#423c36", "r": "#2c2824"}
DARK = {"b": "#26221e", "u": "#a39c92", "f": "#6a645c", "r": "#4e4842"}
TRAIL_COLOR = "#ffd500"

# The three visible faces, as corners in cube coords.
FACES = {
    "U": [(0, 3, 0), (3, 3, 0), (3, 3, 3), (0, 3, 3)],
    "F": [(0, 3, 3), (3, 3, 3), (3, 0, 3), (0, 0, 3)],
    "R": [(3, 3, 0), (3, 3, 3), (3, 0, 3), (3, 0, 0)],
}
# Per face: (origin, u-axis, v-axis) so a face grid coord maps into cube coords.
FACE_BASIS = {
    "U": ((0, 3, 0), (1, 0, 0), (0, 0, 1)),
    "F": ((0, 3, 3), (1, 0, 0), (0, -1, 0)),
    "R": ((3, 3, 0), (0, 0, 1), (0, -1, 0)),
}
# The cube's outer silhouette — a hexagon.
SILHOUETTE = [(0, 3, 0), (3, 3, 0), (3, 0, 0), (3, 0, 3), (0, 0, 3), (0, 3, 3)]

# The route, as sticker cells per face. F rows run top(0) to bottom(2);
# U rows run far(0) to near(2). It enters at the cube's lower-left vertex,
# climbs two steps, crests the front-top edge and runs to the far edge.
TRAIL: dict[str, set[tuple[int, int]]] = {
    "F": {(0, 2), (0, 1), (1, 1), (1, 0)},
    "U": {(1, 2), (1, 1), (1, 0)},
}

# Face key -> CSS class used in the SVG.
FACE_CLASS = {"U": "u", "F": "f", "R": "r"}

Point = tuple[float, float]


def project(x: float, y: float, z: float) -> Point:
    """Cube coords -> viewBox coords."""
    return (
        (x - z) * COS30 * SCALE + CENTER,
        ((x + z) * 0.5 - y) * SCALE + CENTER,
    )


def face_point(face: str, u: float, v: float) -> Point:
    """Point on `face` at grid coords (u, v), each running 0..3."""
    origin, du, dv = FACE_BASIS[face]
    return project(*(origin[i] + du[i] * u + dv[i] * v for i in range(3)))


def inset(points: list[Point], amount: float) -> list[Point]:
    """Shrink a polygon toward its centroid by `amount` px."""
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    out = []
    for x, y in points:
        dx, dy = x - cx, y - cy
        dist = math.hypot(dx, dy) or 1.0
        out.append((x - dx / dist * amount, y - dy / dist * amount))
    return out


def rounded_path(points: list[Point], radius: float) -> str:
    """Closed path with `radius`-rounded corners (a quadratic through each vertex)."""
    if radius <= 0:
        return "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in points) + " Z"
    n = len(points)
    parts = []
    for i in range(n):
        prev, cur, nxt = points[(i - 1) % n], points[i], points[(i + 1) % n]
        len_prev, len_next = math.dist(prev, cur), math.dist(cur, nxt)
        # Never eat more than half of either adjacent edge.
        r = min(radius, len_prev / 2, len_next / 2)
        a = (
            cur[0] + (prev[0] - cur[0]) * r / len_prev,
            cur[1] + (prev[1] - cur[1]) * r / len_prev,
        )
        b = (
            cur[0] + (nxt[0] - cur[0]) * r / len_next,
            cur[1] + (nxt[1] - cur[1]) * r / len_next,
        )
        parts.append(f"{'M' if i == 0 else 'L'}{a[0]:.2f},{a[1]:.2f}")
        parts.append(f"Q{cur[0]:.2f},{cur[1]:.2f} {b[0]:.2f},{b[1]:.2f}")
    return " ".join(parts) + " Z"


def cell_corners(face: str, i: int, j: int) -> list[Point]:
    """The four corners of sticker (i, j) on `face`."""
    return [
        face_point(face, i, j),
        face_point(face, i + 1, j),
        face_point(face, i + 1, j + 1),
        face_point(face, i, j + 1),
    ]


def union_loops(cells: set[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    """Trace the outline of a set of grid cells, as loops of grid points.

    Edges shared by two cells cancel, leaving only the boundary; the remaining
    directed edges are then chained into loops. Iteration is sorted throughout
    so the emitted path string is reproducible run to run.
    """
    edges: dict[tuple[tuple[int, int], tuple[int, int]], bool] = {}
    for i, j in sorted(cells):
        corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
        for k in range(4):
            a, b = corners[k], corners[(k + 1) % 4]
            if (b, a) in edges:  # interior: the neighbour walks it the other way
                del edges[(b, a)]
            else:
                edges[(a, b)] = True

    successors: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for a, b in edges:
        successors.setdefault(a, []).append(b)
    for options in successors.values():
        options.sort()

    loops = []
    while successors:
        start = min(successors)
        loop, cur = [start], start
        while True:
            options = successors.get(cur)
            if not options:
                break
            nxt = options.pop(0)
            if not options:
                del successors[cur]
            if nxt == start:
                break
            loop.append(nxt)
            cur = nxt
        if len(loop) >= 3:
            loops.append(loop)
    return loops


def drop_collinear(points: list[Point], eps: float = 1e-6) -> list[Point]:
    """Remove vertices that lie on the straight line between their neighbours."""
    out = []
    n = len(points)
    for k in range(n):
        p, c, q = points[(k - 1) % n], points[k], points[(k + 1) % n]
        cross = (c[0] - p[0]) * (q[1] - c[1]) - (c[1] - p[1]) * (q[0] - c[0])
        if abs(cross) > eps:
            out.append(c)
    return out or points


def shapes() -> list[tuple[str, str]]:
    """(css class, path data) for every shape, in paint order."""
    out = [("b", rounded_path([project(*c) for c in SILHOUETTE], BODY_RADIUS))]
    for face in ("U", "F", "R"):
        for i in range(3):
            for j in range(3):
                if (i, j) in TRAIL.get(face, ()):
                    continue  # the trail is drawn as one merged shape below
                corners = inset(cell_corners(face, i, j), STICKER_INSET)
                out.append((FACE_CLASS[face], rounded_path(corners, STICKER_RADIUS)))
    for face in ("U", "F", "R"):
        for loop in union_loops(TRAIL.get(face, set())):
            screen = drop_collinear([face_point(face, i, j) for i, j in loop])
            out.append(("t", rounded_path(inset(screen, TRAIL_INSET), TRAIL_RADIUS)))
    return out


def render() -> str:
    """The complete favicon.svg, theme-aware.

    The favicon loads outside the page and so cannot read the --logo-* tokens;
    it carries its own prefers-color-scheme block instead.
    """
    light = "".join(f".{k}{{fill:{v}}}" for k, v in LIGHT.items())
    dark = "".join(f".{k}{{fill:{v}}}" for k, v in DARK.items())
    paths = "\n".join(f'  <path class="{cls}" d="{d}"/>' for cls, d in shapes())
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEWBOX:g} {VIEWBOX:g}"'
        ' role="img" aria-label="Cubepath">\n'
        "  <style>\n"
        f"    {light}.t{{fill:{TRAIL_COLOR}}}\n"
        "    @media (prefers-color-scheme:dark){\n"
        f"      {dark}\n"
        "    }\n"
        "  </style>\n"
        f"{paths}\n"
        "</svg>\n"
    )


def favicon_path() -> Path:
    """tools/diagrams/src/cubepath/logo.py -> repo root is 4 levels up."""
    return Path(__file__).resolve().parents[4] / "app" / "public" / "favicon.svg"


def main() -> None:
    target = favicon_path()
    target.write_text(render())
    print(f"  {target.relative_to(target.parents[2])} ({len(shapes())} paths)")
    print("Run `node scripts/gen-icons.mjs` in app/ to rasterize the PNG icon set.")
