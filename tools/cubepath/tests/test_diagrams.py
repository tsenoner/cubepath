"""Tests for cubepath diagram generation."""

import itertools
import math
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from cubepath.cube import Cube
from cubepath.diagrams import (
    _CENTERS,
    _CORNERS_POSITIONED,
    _EDGES_ALIGNED,
    _FACE_NORMAL,
    _FIRST_LAYER,
    _LAYER_OF,
    _OV_HOST,
    _OV_LABEL_AT,
    _OV_ON_FACE,
    _OV_PIN_BAND,
    _OV_PIN_DOT,
    _OV_PIN_STROKE,
    _OV_PIN_TIP,
    _OV_STRIP_REACH,
    _SECOND_LAYER,
    _THEME_CSS,
    _YELLOW_CROSS,
    ARROW_COLOR,
    BLUE,
    CARD,
    CARD_FACES,
    DARK_INK,
    DARK_PAPER,
    DIM_TARGET_DE,
    GREEN,
    ORANGE,
    OVERVIEW_HUB,
    OVERVIEW_PINS,
    RED,
    SCREEN,
    SCREEN_FACES,
    SLOT_STROKE_W,
    UNORIENTED,
    UNREACHED,
    WHITE,
    YELLOW,
    CubeDiagram,
    _align_edge_cases,
    _arrow_pos,
    _corner_case_steps,
    _corner_pos_case,
    _depth,
    _edge_case_steps,
    _mark,
    _n_proj,
    _n_sticker_color,
    _notation_moves,
    _orient_corner_case,
    _orient_corner_cases_15,
    _ov_needs_halo,
    _pin_exit,
    _pll_corner_cases,
    _pll_edge_cases,
    _restyle,
    _ring_basis,
    _step_cases,
    _web_steps,
    all_cases,
    all_steps,
    delta_e,
    dim,
    exit_face,
    overview_pin,
    overview_pin_head,
    overview_pin_ring,
    overview_ring,
    overview_strips,
    render,
    render_notation,
    render_overview,
    render_slot,
    render_step,
    slab_of,
    sticker_centre,
    sticker_of,
    to_lab,
)
from cubepath.fullsets import (
    _plan_permutation,
    _states_of,
    big_oll_cases,
    big_pll_cases,
    card_pll_cases,
    diagram_name,
    f2l_cases,
    full_oll_cases,
    full_pll_cases,
    l2e_cases,
    parity_cases,
    plan_oll_cases,
    plan_pll_cases,
    render_big_sets,
    render_f2l,
    render_fullsets,
)
from cubepath.notation import case_states
from cubepath.palette import contrast

# ViewBox dimensions (computed from layout constants)
VIEWBOX_SIZE = 192


def test_all_cases_count():
    # 18, not 17: the Hook is drawn at both phases' holds (see
    # `_oll_cross_cases`). Everything else is one picture per case.
    assert len(all_cases()) == 18


def test_case_names_unique():
    cases = all_cases()
    names = [c.name for c in cases]
    assert len(names) == len(set(names))


def test_render_creates_svg(tmp_path):
    case = all_cases()[0]
    path = render(case, tmp_path)
    assert path.exists()
    assert path.suffix == ".svg"
    content = path.read_text()
    assert "<svg" in content


def test_arrows_within_viewbox():
    valid_names = {"top", "bottom", "left", "right", "tl", "tr", "bl", "br"}
    for name in valid_names:
        x, y = _arrow_pos(name)
        assert 0 <= x <= VIEWBOX_SIZE, f"{name}: x={x} out of bounds"
        assert 0 <= y <= VIEWBOX_SIZE, f"{name}: y={y} out of bounds"


def test_svg_contains_expected_rects(tmp_path):
    """9 U-face + 12 side stickers + 1 background = 22 rects."""
    case = all_cases()[0]
    path = render(case, tmp_path)
    content = path.read_text()
    assert content.count("<rect") == 22


def test_oll_cases_have_no_arrows():
    for case in all_cases():
        if case.category.startswith("oll"):
            assert not case.swaps, f"{case.name} has swaps"
            assert not case.cycles, f"{case.name} has cycles"


def test_pll_cases_have_arrows():
    for case in all_cases():
        if case.category.startswith("pll"):
            assert case.swaps or case.cycles, f"{case.name} has no arrows"


def test_step_cases_count():
    assert len(_step_cases()) == 8


def test_step_render_creates_svg(tmp_path):
    steps = _step_cases()
    for step in steps:
        path = render_step(step, tmp_path)
        assert path.exists()
        assert path.suffix == ".svg"
        content = path.read_text()
        assert "<svg" in content


def test_orient_corner_cases_15():
    cases = _orient_corner_cases_15()
    assert len(cases) == 2
    assert cases[0].filename == "orient_right"
    assert cases[1].filename == "orient_front"


def test_solve_state_progression():
    assert _CENTERS < _FIRST_LAYER < _SECOND_LAYER < _YELLOW_CROSS
    assert _YELLOW_CROSS < _EDGES_ALIGNED < _CORNERS_POSITIONED


# ── Sticker color rules vs simulator ────────────────────────────────

# Map diagram sticker colors to simulator single-char color codes
_COLOR_TO_SIM = {
    YELLOW: "Y",
    RED: "R",
    GREEN: "G",
    ORANGE: "O",
    BLUE: "B",
    "#FFFFFF": "W",
}


def test_sticker_color_rules_match_simulator():
    """For each notation move, verify diagram sticker colors match simulator state.

    This is the highest-value test: it catches any mismatch between the
    hand-coded _STICKER_COLOR_RULES table and actual cube physics.
    """
    # Map notation move layer+CW to algorithm string for the simulator
    _MOVE_ALG = {
        ("R", True): "R",
        ("R", False): "R'",
        ("R2", True): "R2",
        ("U", True): "U",
        ("L", True): "L",
        ("F", True): "F",
        ("D", True): "D",
        ("B", True): "B",
        ("M", True): "M",
        ("S", True): "S",
        ("E", True): "E",
        ("r", True): "r",
        ("x", True): "x",
        ("y", True): "y",
        ("z", True): "z",
    }
    mismatches = []
    for move in _notation_moves():
        key = (move.layer, move.clockwise)
        alg = _MOVE_ALG.get(key)
        if alg is None:
            continue
        cube = Cube.solved()
        cube.apply(alg)
        for face in ("U", "F", "R"):
            for a in range(3):
                for b in range(3):
                    rule_color = _n_sticker_color(face, a, b, move.layer, move.clockwise)
                    sim_color_char = cube.visible_sticker(face, a, b)
                    rule_char = _COLOR_TO_SIM.get(rule_color)
                    if rule_char is None:
                        continue
                    if rule_char != sim_color_char:
                        mismatches.append(
                            f"{move.name}: {face}({a},{b}) rule={rule_char} sim={sim_color_char}"
                        )
    assert mismatches == [], "Sticker color mismatches:\n" + "\n".join(mismatches)


def test_pll_edge_cases_have_correct_corner_colors():
    """PLL edge cases (Ua, Ub, H, Z) should show correct corner colors (all same per face)."""
    for case in _pll_edge_cases():
        # Edge PLLs don't move corners, so each side should have matching corner stickers
        for side_name, side in [
            ("top", case.top_side),
            ("right", case.right_side),
            ("bottom", case.bottom_side),
            ("left", case.left_side),
        ]:
            assert side[0] == side[2], (
                f"{case.name} {side_name}: corners don't match ({side[0]} vs {side[2]})"
            )


def test_pll_corner_cases_show_true_edge_colors():
    """PLL corner cases show real (non-grey) edge sticker colors from the pre-state."""
    for case in _pll_corner_cases():
        for side in (case.top_side, case.right_side, case.bottom_side, case.left_side):
            assert UNORIENTED not in side, f"{case.name}: masked sticker in side strip"


# ── Render smoke tests ──────────────────────────────────────────────


def test_render_notation_all(tmp_path):
    """All 15 notation move SVGs render and contain <svg>."""
    moves = _notation_moves()
    assert len(moves) == 15
    for move in moves:
        path = render_notation(move, tmp_path)
        assert path.exists(), f"{move.filename} not created"
        content = path.read_text()
        assert "<svg" in content, f"{move.filename} missing <svg>"


def test_render_overview(tmp_path):
    path = render_overview(tmp_path)
    assert path.exists()
    content = path.read_text()
    assert "<svg" in content


# ── Notation overview ───────────────────────────────────────────────
# The six face turns on one cube, in two layouts. The shipped pins: a pin out
# of every face centre with a ribbon ring around it. The hub (the backup): F
# as a ring, the other five as a strip arrow along the edge of a visible face,
# the strip directions derived (mark the strip, apply the move, point at the
# face it left for). The gates below check the geometry against the
# simulator and the SVG against the geometry.

_HIDDEN = tuple(face for face in _FACE_NORMAL if face not in _OV_ON_FACE)
_ALL_FACES = "".join(_FACE_NORMAL)


def test_visible_faces_are_the_ones_facing_the_camera():
    """`_OV_ON_FACE` is a draw order; its set is decided by the view direction."""
    assert set(_OV_ON_FACE) == {f for f, n in _FACE_NORMAL.items() if _depth(n) > 0}


def test_layer_table_matches_simulator():
    """`_LAYER_OF` names the slab each face turns: marking every visible
    sticker distinctly and applying the letter must move exactly that slab
    (centres excepted — they spin in place)."""
    stickers = [(f, a, b) for f in _OV_ON_FACE for a in range(3) for b in range(3)]
    for token, (axis, slab) in _LAYER_OF.items():
        cube = Cube.solved()
        for face, a, b in stickers:
            cube.set_visible_sticker(face, a, b, f"{face}{a}{b}")
        cube.apply(token)
        moved = {(f, a, b) for f, a, b in stickers if cube.visible_sticker(f, a, b) != f"{f}{a}{b}"}
        in_slab = {
            (f, a, b) for f, a, b in stickers if slab_of(sticker_centre(f, a, b)[axis]) == slab
        }
        assert moved <= in_slab, (token, moved - in_slab)
        centres = {(f, 1, 1) for f in _OV_ON_FACE}
        assert in_slab - centres <= moved, (token, in_slab - centres - moved)


def test_overview_strips_point_where_the_layer_goes():
    """Independently of the renderer (no `exit_face`, no `strip_stickers`,
    no `_LAYER_OF`): mark the whole host face, apply the letter, and the one
    face that received marks must be the face the arrow points at — while
    the face behind the arrow's tail got nothing, so the arrow cannot be
    read the other way. The arrow also lies in the strip it names."""
    face_of: dict[tuple[float, ...], str] = {tuple(n): f for f, n in _FACE_NORMAL.items()}
    strips = overview_strips()
    assert set(strips) == set(_OV_HOST)
    for token, (tail, tip) in strips.items():
        host = _OV_HOST[token]
        assert sticker_of(tail)[0] == host == sticker_of(tip)[0], token
        d = tuple(round((tip[i] - tail[i]) / (2 * _OV_STRIP_REACH)) for i in range(3))
        cube = Cube.solved()
        for a in range(3):
            for b in range(3):
                _mark(cube, host, a, b)
        cube.apply(token)
        landed = {f for f, s in cube.faces.items() if "X" in s} - {host}
        assert landed == {face_of[d]}, (token, landed, d)
        assert face_of[tuple(-c for c in d)] not in landed, (token, "reads both ways")
        assert exit_face(token, host) == face_of[d], token
        axis, slab = _LAYER_OF[token]
        for p in (tail, tip):
            assert slab_of(p[axis]) == slab, (token, p)


def _assert_ring_follows_turn(points: list[tuple[float, float, float]], face: str) -> None:
    """`points` lie on `face`. The edge-middle stickers they pass must come in
    the order one turn of `face` carries a sticker: mark one, turn, and it is
    at the next."""
    order: list[tuple[str, int, int]] = []
    for p in points:
        s = sticker_of(p)
        if s[1:] in ((1, 2), (2, 1), (1, 0), (0, 1)) and (not order or order[-1] != s):
            order.append(s)
    assert len(order) >= 3, (face, order)
    for here, there in zip(order, order[1:], strict=False):
        cube = Cube.solved()
        _mark(cube, *here)
        cube.apply(face)
        assert cube.visible_sticker(*there) == "X", (face, here, there)


def test_overview_ring_turns_clockwise():
    """The hub's F ring passes F's four edge-middle stickers in turn order."""
    _assert_ring_follows_turn([(p[0], p[1], 3.0) for p in overview_ring()], "F")


def _texts(svg: str) -> list[str]:
    return re.findall(r"<text[^>]*>([^<]*)</text>", svg)


def test_overview_labels_each_face_once(tmp_path):
    svg = render_overview(tmp_path, layout=OVERVIEW_HUB).read_text()
    assert sorted(_texts(svg)) == sorted(_ALL_FACES)
    for face in _OV_ON_FACE:
        assert re.search(rf'<text(?![^>]*class="ink")[^>]*>{face}</text>', svg), face
    for face in _HIDDEN:
        assert re.search(rf'<text[^>]*class="ink"[^>]*>{face}</text>', svg), face


def test_overview_letters_sit_beside_their_arrow():
    """Every letter is within a sticker and a half of its own arrow, and
    farther from every other arrow than from its own."""
    arrows: dict[str, list[tuple[float, float, float]]] = {
        t: [
            (
                tail[0] + (tip[0] - tail[0]) * k / 20,
                tail[1] + (tip[1] - tail[1]) * k / 20,
                tail[2] + (tip[2] - tail[2]) * k / 20,
            )
            for k in range(21)
        ]
        for t, (tail, tip) in overview_strips().items()
    }
    arrows["F"] = overview_ring()

    def dist(token: str, at) -> float:
        return min(math.dist(at, p) for p in arrows[token])

    for token, (at, _anchor) in _OV_LABEL_AT.items():
        own = dist(token, at)
        assert own < 1.5, (token, own)
        for other in arrows:
            if other != token:
                assert dist(other, at) > own, (token, "closer to", other)


def _points(attr: str) -> list[tuple[float, float]]:
    """The (x, y) pairs of a `d=` or `points=` value. Every path here is an
    M/L polyline of `x,y` pairs, so an odd count means the format changed
    and the pairing would be garbage."""
    nums = re.findall(r"-?\d+(?:\.\d+)?", attr)
    assert len(nums) % 2 == 0, attr
    return [(float(a), float(b)) for a, b in zip(nums[::2], nums[1::2], strict=True)]


def _coords(svg: str) -> list[tuple[float, float]]:
    """Every coordinate the SVG paints: path and polygon vertices, line
    ends, and the four extremes of each circle."""
    pairs: list[tuple[float, float]] = []
    for attr in re.findall(r'(?:\bd|\bpoints)="([^"]*)"', svg):
        pairs += _points(attr)
    for elem in re.findall(r"<line\b[^>]*>", svg):
        x1, y1, x2, y2 = (float(_attr(elem, k)) for k in ("x1", "y1", "x2", "y2"))
        pairs += [(x1, y1), (x2, y2)]
    for elem in re.findall(r"<circle\b[^>]*>", svg):
        cx, cy, r = (float(_attr(elem, k)) for k in ("cx", "cy", "r"))
        pairs += [(cx - r, cy), (cx + r, cy), (cx, cy - r), (cx, cy + r)]
    return pairs


def _attr(attrs: str, name: str) -> str:
    match = re.search(rf'(?<![\w-]){name}="([^"]*)"', attrs)
    assert match is not None, (name, attrs)
    return match.group(1)


def _assert_frame_holds_coords(svg: str) -> tuple[float, float, float, float]:
    """Every path and polygon coordinate lies inside the viewBox, which is
    returned as (x, y, w, h)."""
    view_box = re.search(r'viewBox="([^"]*)"', svg)
    assert view_box is not None
    x, y, w, h = map(float, view_box.group(1).split())
    for px, py in _coords(svg):
        assert x <= px <= x + w and y <= py <= y + h, (px, py)
    return x, y, w, h


def _assert_frame_holds_text(svg: str, frame: tuple[float, float, float, float]) -> None:
    """Every label fits the viewBox with a generous glyph box — wider than
    the one `_Bounds.text` reserves, so the pad has to absorb the difference."""
    x, y, w, h = frame
    for match in re.finditer(r"<text([^>]*)>([^<]*)</text>", svg):
        attrs, text = match.groups()
        size = float(_attr(attrs, "font-size").removesuffix("px"))
        anchor = _attr(attrs, "text-anchor")
        tx, ty = float(_attr(attrs, "x")), float(_attr(attrs, "y"))
        width = 0.95 * size * len(text)
        left = {"middle": tx - width / 2, "start": tx, "end": tx - width}[anchor]
        assert x <= left and left + width <= x + w, (text, left)
        assert y <= ty - 0.75 * size and ty + 0.25 * size <= y + h, (text, ty)


@pytest.mark.parametrize("layout", [OVERVIEW_PINS, OVERVIEW_HUB], ids=lambda lo: lo.filename)
@pytest.mark.parametrize("style", [SCREEN, CARD], ids=["screen", "card"])
def test_overview_frame_holds_everything_it_draws(tmp_path, layout, style):
    """The viewBox is computed from what was drawn, so nothing may poke out —
    paths, heads, halos and labels — in either layout and either palette."""
    svg = render_overview(tmp_path, style=style, layout=layout).read_text()
    _assert_frame_holds_text(svg, _assert_frame_holds_coords(svg))


def test_overview_heads_land_on_their_destination(tmp_path):
    """The SVG, not the table: every arrowhead's tip is the projected end of
    an arrow."""
    svg = render_overview(tmp_path, layout=OVERVIEW_HUB).read_text()
    heads = re.findall(r'<polygon fill="#222222" points="([^ ]+)', svg)
    got = sorted(tuple(map(float, h.split(","))) for h in heads)
    tips = [tip for _tail, tip in overview_strips().values()] + [overview_ring()[-1]]
    assert got == sorted(_n_proj(*t) for t in tips), got


# ── The pins layout ──────────────────────────────────────────────────


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def test_pin_rings_turn_clockwise_seen_from_outside():
    """The ring basis for every face has u x v = -n, which is clockwise as
    seen from outside that face; and for the three visible faces the ring,
    dropped onto its face, passes the edge-middle stickers in the order one
    turn of that face carries a sticker."""
    for face, n in _FACE_NORMAL.items():
        u, v = _ring_basis(n)
        assert _cross(u, v) == tuple(-c for c in n), face
    for face in _OV_ON_FACE:
        n = _FACE_NORMAL[face]
        axis = n.index(max(n, key=abs))
        on_face = []
        for p in overview_pin_ring(face):
            q = list(p)
            q[axis] = 3.0  # drop the ring onto the face
            on_face.append((q[0], q[1], q[2]))
        _assert_ring_follows_turn(on_face, face)


def test_pins_leave_the_face_centre_along_its_normal():
    """Each pin starts at its face centre and runs straight out along the
    normal, to the layout's screen radius from the cube centre."""
    for face, n in _FACE_NORMAL.items():
        c, tip = overview_pin(face)
        assert c == tuple(1.5 + 1.5 * k for k in n), face
        d = tuple(tip[i] - c[i] for i in range(3))
        assert all(d[i] == 0 for i in range(3) if n[i] == 0), (face, d)
        assert sum(d[i] * n[i] for i in range(3)) > 1.0, (face, "pin too short to clear the cube")
        reach = math.dist(_n_proj(*tip), _n_proj(1.5, 1.5, 1.5))
        # `_n_proj` rounds to a tenth, so the tip lands within a few tenths
        expected = _OV_PIN_TIP["front" if face in _OV_ON_FACE else "back"]
        assert abs(reach - expected) < 0.3, (face, reach)


def test_hidden_rings_clear_the_cube():
    """D, B and L's rings sit behind the cube; their pins are long enough that
    no part of the ring — either edge of the band, the head's tip and wings,
    and half the stroke beyond them — projects onto the cube's silhouette,
    so the ring is never sliced by the cube and reads as one object around
    its pin. (The centre line alone once passed while B's inner edge was a
    tenth inside the hull.)"""
    corners = [_n_proj(x, y, z) for x in (0, 3) for y in (0, 3) for z in (0, 3)]
    # the silhouette is the convex hull of the projected corners
    pts = sorted(set(corners))

    def half(points):
        hull: list[tuple[float, float]] = []
        for p in points:
            while (
                len(hull) >= 2
                and (
                    (hull[-1][0] - hull[-2][0]) * (p[1] - hull[-2][1])
                    - (hull[-1][1] - hull[-2][1]) * (p[0] - hull[-2][0])
                )
                <= 0
            ):
                hull.pop()
            hull.append(p)
        return hull

    hull = half(pts)[:-1] + half(pts[::-1])[:-1]
    edges = list(zip(hull, hull[1:] + hull[:1], strict=True))
    cx = sum(p[0] for p in hull) / len(hull)
    cy = sum(p[1] for p in hull) / len(hull)

    def outward(a: tuple[float, float], b: tuple[float, float], p: tuple[float, float]) -> float:
        cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        return cross / math.dist(a, b)

    # the hull is convex, so its orientation is whatever puts the centroid inside
    orient = -1.0 if outward(*edges[0], (cx, cy)) > 0 else 1.0

    def clearance(p) -> float:
        """Distance outside the hull (negative inside), by the nearest edge line."""
        return max(orient * outward(a, b, p) for a, b in edges)

    for face in _HIDDEN:
        n = _FACE_NORMAL[face]
        head = overview_pin_head(face)
        drawn = [
            (p[0] + k * n[0], p[1] + k * n[1], p[2] + k * n[2])
            for p in overview_pin_ring(face)
            for k in (+_OV_PIN_BAND, -_OV_PIN_BAND)
        ]
        # the head's tip, and its wings at the sweep end
        end = overview_pin_ring(face)[-1]
        drawn += [head] + [
            (end[0] + k * n[0], end[1] + k * n[1], end[2] + k * n[2])
            for k in (+2.4 * _OV_PIN_BAND, -2.4 * _OV_PIN_BAND)
        ]
        worst = min(clearance(_n_proj(*p)) for p in drawn)
        assert worst >= _OV_PIN_STROKE / 2, (face, worst)


def test_pins_layout_labels_and_heads(tmp_path):
    """Six letters, six dots, and every arrowhead's tip in the drawing exactly
    where the ring says; the frame holds every coordinate. (That the letters
    are ink-tagged is `test_plate_labels_are_ink_tagged`.)"""
    svg = render_overview(tmp_path, layout=OVERVIEW_PINS).read_text()
    assert sorted(_texts(svg)) == sorted(_ALL_FACES)
    assert len(re.findall(r'<circle[^>]*class="ink"', svg)) == 6, "a dot on every pin"
    # six pins reach the plate (2.0 wide; the ribbons' caps are 1.6), and the
    # three visible faces' pins start with an untagged run across their face
    pin = 'stroke-linecap="round" stroke-width="2.0"'
    assert len(re.findall(rf'<line class="ink-stroke" stroke="{ARROW_COLOR}" {pin}', svg)) == 6
    on_face = re.findall(rf'<line stroke="{ARROW_COLOR}" {pin}', svg)
    assert len(on_face) == len(_OV_ON_FACE), on_face
    coords = set(_coords(svg))
    for face in _FACE_NORMAL:
        x, y = _n_proj(*overview_pin_head(face))
        assert (x, y) in coords, (face, x, y)
    _assert_frame_holds_coords(svg)


def test_pin_dots_sit_in_depth_order(tmp_path):
    """The dot at a pin's tip is `_OV_PIN_RING_IN` beyond the ring's plane
    along the face normal, so a pin that points away from the camera has
    its dot BEHIND the ring and one that points toward has it in FRONT.
    Where a ribbon vertex lands within the dot on screen, the SVG must
    paint the dot before that path when the ribbon is nearer the camera
    and after it when it is farther — and all such vertices of one pin
    must be on one side, or the dot would need splitting. B's dot used to
    be painted last and covered its own ring."""
    svg = render_overview(tmp_path, layout=OVERVIEW_PINS).read_text()
    reach = _OV_PIN_DOT + _OV_PIN_STROKE
    elems = list(re.finditer(r"<(circle|path)\b[^>]*>", svg))

    covered = set()
    for face, n in _FACE_NORMAL.items():
        _c, tip = overview_pin(face)
        tx, ty = _n_proj(*tip)
        nearer = farther = 0
        for p in overview_pin_ring(face) + [overview_pin_head(face)]:
            for side in (+1, -1):
                q = (
                    p[0] + side * _OV_PIN_BAND * n[0],
                    p[1] + side * _OV_PIN_BAND * n[1],
                    p[2] + side * _OV_PIN_BAND * n[2],
                )
                if math.dist(_n_proj(*q), (tx, ty)) < reach:
                    if _depth(q) > _depth(tip):
                        nearer += 1
                    else:
                        farther += 1
        assert not (nearer and farther), (face, nearer, farther)
        away = _depth(n) < 0
        if nearer or farther:
            assert (nearer > 0) == away, face

        dot_at = f'cx="{tx:.1f}" cy="{ty:.1f}"'
        (dot_idx,) = [i for i, m in enumerate(elems) if m.group(1) == "circle" and dot_at in m[0]]
        near_paths = []
        for i, m in enumerate(elems):
            if m.group(1) != "path":
                continue
            pts = _points(_attr(m[0], "d"))
            if any(math.dist(pt, (tx, ty)) < reach for pt in pts):
                near_paths.append(i)
        if not near_paths:
            continue
        covered.add(face)
        if away:
            assert dot_idx < min(near_paths), (face, "dot painted over a nearer ribbon")
        else:
            assert dot_idx > max(near_paths), (face, "dot painted under a farther ribbon")
    assert "B" in covered, "B's dot meets its ring on screen — the check has teeth"


def test_overview_card_ink_gets_a_halo_when_the_face_is_too_dark(tmp_path):
    """`_ov_needs_halo` measures the palette; the card's darkened red fails
    3:1 against the ink, the screen palette passes. On the card every run of
    ink across a face gets a paper rim: the hub's arrows and face letters,
    and — in the layout the annex actually prints — each visible face's pin
    from its centre to the face edge."""
    assert _ov_needs_halo(_restyle(CARD)) is True
    assert _ov_needs_halo(_restyle(SCREEN)) is False
    card = render_overview(tmp_path / "c", style=CARD, layout=OVERVIEW_HUB).read_text()
    screen = render_overview(tmp_path / "s", layout=OVERVIEW_HUB).read_text()
    # a rim under each of six bodies and heads, and under the three face letters
    assert card.count(f'stroke="{WHITE}"') == 2 * 6 + 3
    assert f'stroke="{WHITE}"' not in screen
    assert "<style" not in card and CARD_FACES["R"] in card

    card = render_overview(tmp_path / "pc", style=CARD, layout=OVERVIEW_PINS).read_text()
    screen = render_overview(tmp_path / "ps", layout=OVERVIEW_PINS).read_text()
    rims = re.findall(rf'<line stroke="{WHITE}"[^>]*>', card)
    assert len(rims) == len(_OV_ON_FACE), "one rim per on-face pin run"
    assert f'stroke="{WHITE}"' not in screen
    for face in _OV_ON_FACE:
        c, tip = (_n_proj(*p) for p in overview_pin(face))
        leave = _pin_exit(face, c, tip)
        (rim,) = [r for r in rims if (_attr(r, "x1"), _attr(r, "y1")) == (str(c[0]), str(c[1]))]
        end = (float(_attr(rim, "x2")), float(_attr(rim, "y2")))
        # the rim stops one rim short of the face edge, so its round cap ends
        # exactly there instead of biting into the face outline
        half_rim = (float(_attr(rim, "stroke-width")) - (_OV_PIN_STROKE + 0.4)) / 2
        assert abs(math.dist(end, leave) - half_rim) < 0.05, (face, end, leave)
        assert math.dist(end, c) < math.dist(leave, c), (face, "rim overshoots the face edge")


def test_sub_case_counts():
    assert len(_corner_case_steps()) == 3
    assert len(_edge_case_steps()) == 2
    assert len(_align_edge_cases()) == 2


def test_all_step_diagrams_render(tmp_path):
    """All 19 step diagrams render without error."""
    all_steps = [
        *_step_cases(),
        *_corner_case_steps(),
        *_edge_case_steps(),
        _orient_corner_case(),
        *_orient_corner_cases_15(),
        _corner_pos_case(),
        *_align_edge_cases(),
    ]
    assert len(all_steps) == 19
    for step in all_steps:
        path = render_step(step, tmp_path)
        assert path.exists(), f"{step.filename} not created"
        content = path.read_text()
        assert "<svg" in content, f"{step.filename} missing <svg>"


# ── Card style: greyscale legibility and band thickness ───────────────
# A card is printed, often on a mono laser, at under 5 mm per sticker. These
# gate the palette by measurement so nobody re-picks a colour by eye.

_SIDE_FACES = ("R", "G", "O", "B")  # red, green, orange, blue
CARD_SIDE_CONTRAST_MIN = 1.95


def test_card_side_faces_are_separable_in_greyscale() -> None:
    for a, b in itertools.combinations(_SIDE_FACES, 2):
        ratio = contrast(CARD_FACES[a], CARD_FACES[b])
        assert ratio >= CARD_SIDE_CONTRAST_MIN, f"{a}/{b} at {ratio:.2f}:1 prints as one grey"


def test_card_palette_beats_the_screen_palette_on_every_side_pair() -> None:
    """Not a tie-break: the card palette exists only because it separates
    better. If an edit makes any pair worse, it is the wrong edit."""
    for a, b in itertools.combinations(_SIDE_FACES, 2):
        card, screen = (
            contrast(CARD_FACES[a], CARD_FACES[b]),
            contrast(SCREEN_FACES[a], SCREEN_FACES[b]),
        )
        assert card > screen, f"{a}/{b} got worse: {screen:.2f} -> {card:.2f}"


def test_masked_grey_is_readable_against_yellow() -> None:
    """The whole job of an OLL diagram: solved sticker vs not. On screen this
    is 1.28:1 — ten identical grey squares on a mono printer."""
    assert contrast(SCREEN_FACES["Y"], SCREEN.masked) < 1.5
    assert contrast(CARD_FACES["Y"], CARD.masked) >= 4.0


def test_card_bands_grow_outward_only(tmp_path) -> None:
    """A thicker side band must not move the inner edge, or every diagram
    size measured for the card silently changes."""
    case = _pll_edge_cases()[0]
    screen = render(case, tmp_path / "s", style=SCREEN).read_text()
    card = render(case, tmp_path / "c", style=CARD).read_text()

    assert 'viewBox="0 0 192 192"' in screen
    assert 'viewBox="0 0 192 192"' in card, "card render changed the viewBox"

    assert f'height="{SCREEN.band_u}"' in screen
    assert f'height="{CARD.band_u}"' in card
    # inner edge pinned: top band ends at 32, bottom band starts at 160
    assert 'y="20"' in screen and 'y="12"' in card
    assert 'y="160"' in screen and 'y="160"' in card


# ── Theming ───────────────────────────────────────────────────────────
# The generated SVGs are loaded as plain <img src>, which cannot see the
# page's CSS custom properties, so each one carries its own colour-scheme
# rules. resvg (typst) skips every @media block, which is what leaves the
# guide PDF with the opaque plate it needs behind the 13 figures that sit in a
# tinted `.algorithm` callout. These tests pin all three halves of that: the
# block is emitted, the print style is exempt, and the two shipped trees agree.

_REPO = Path(__file__).resolve().parents[3]
_APP_SVG = _REPO / "app" / "public" / "diagrams"
# Derived, never listed: a hardcoded tuple silently skipped `f2l/` when it
# landed, which is the same failure scripts/sync-diagrams.sh guards against.
_SVG_DIRS = tuple(sorted(p.name for p in _APP_SVG.iterdir() if p.is_dir()))


# The count is PINNED, not measured off the tree it is checking. Deriving it
# from `guide/figures/generated/` only proves the two trees agree, so a
# generator that silently stopped emitting a whole group would drop it from
# both and still pass. The pin is cross-checked against the generators' own
# inventories below, so a deliberate change fails in exactly one obvious place.
EXPECTED_DIAGRAMS = 181


def _render_everything(out: Path) -> None:
    """Every SVG `cubepath-diagrams` writes, into `out`. One list, so a group
    cannot be gated here and forgotten in `diagrams.main()` or the reverse."""
    for case in all_cases():
        render(case, out)
    render_fullsets(out)
    render_f2l(out)
    render_big_sets(out)
    for move in _notation_moves():
        render_notation(move, out)
    for layout in (OVERVIEW_HUB, OVERVIEW_PINS):
        render_overview(out, layout=layout)
    for step in [*all_steps(), *_web_steps()]:
        render_step(step, out)


def test_the_pinned_diagram_count_matches_the_generators() -> None:
    inventory = (
        len(all_cases())
        + len(full_oll_cases())
        + len(full_pll_cases())
        + len(f2l_cases())
        + len(parity_cases())
        + len(_notation_moves())
        + 2  # the overview, in both its layouts
        + len(all_steps())
        + len(_web_steps())
    )
    assert inventory == EXPECTED_DIAGRAMS, (
        f"the generators now produce {inventory} diagrams; if that is intended, "
        f"update EXPECTED_DIAGRAMS and re-run `make diagrams`"
    )


def _themed_renders(tmp_path) -> dict[str, str]:
    """One output from each of the four screen render entry points."""
    return {
        "render": render(all_cases()[0], tmp_path / "r").read_text(),
        "render_step": render_step(_step_cases()[0], tmp_path / "s").read_text(),
        "render_notation": render_notation(_notation_moves()[0], tmp_path / "n").read_text(),
        "render_overview": render_overview(tmp_path / "o").read_text(),
    }


def test_screen_diagrams_carry_a_theme_block(tmp_path) -> None:
    for name, content in _themed_renders(tmp_path).items():
        assert "prefers-color-scheme" in content, f"{name}: no colour-scheme rules"
        assert content.count('class="bg"') == 1, f"{name}: expected exactly one plate"


def test_no_screen_diagram_paints_an_unconditional_plate(tmp_path) -> None:
    """The bug this fixes: an opaque plate that no theme can turn off. The
    `fill=` attribute stays as the no-CSS fallback, but a class rule beats it
    everywhere, so the plate must be reachable by one."""
    for name, content in _themed_renders(tmp_path).items():
        plates = re.findall(r"<rect[^>]*/>", content)
        opaque = [r for r in plates if f'fill="{WHITE}"' in r and "rx=" in r]
        assert opaque, f"{name}: no plate found at all"
        for rect in opaque:
            assert 'class="bg"' in rect, f"{name}: unreachable opaque plate {rect}"


def test_the_web_plate_is_transparent_in_both_schemes() -> None:
    """The user-visible fix: on a page the diagram sits on the page surface,
    not on a second card. Both browser branches drop it; the media-free
    default is what resvg keeps for print, and it must stay opaque."""
    assert _THEME_CSS.startswith(f".bg{{fill:{WHITE}}}"), "print default lost its plate"
    for scheme in ("light", "dark"):
        head, _, tail = _THEME_CSS.partition(f"@media (prefers-color-scheme:{scheme}){{")
        assert tail, f"no {scheme} block"
        assert tail.split("}}")[0].count("fill:none") == 1, f"{scheme} still paints a plate"


def test_theme_css_uses_the_module_constants() -> None:
    """The T2 lesson: colour must never be respelled beside the palette."""
    assert WHITE in _THEME_CSS
    assert ARROW_COLOR in _THEME_CSS
    assert DARK_INK in _THEME_CSS
    assert DARK_PAPER in _THEME_CSS


def test_theme_flips_strokes_and_paper_too() -> None:
    """A `fill` rule does nothing to a <line>, and a `stroke` rule on `.ink`
    would outline every label — so plate strokes and paper occluders have
    their own classes, each defined in the default and flipped in the dark
    block (the pins used to be tagged `.ink` and stayed dark on a dark page)."""
    default, _, dark = _THEME_CSS.partition("@media (prefers-color-scheme:dark){")
    assert f".ink-stroke{{stroke:{ARROW_COLOR}}}" in default
    assert f".paper{{fill:{WHITE}}}" in default
    assert f".ink-stroke{{stroke:{DARK_INK}}}" in dark
    assert f".paper{{fill:{DARK_PAPER}}}" in dark
    assert ".ink{stroke" not in _THEME_CSS, "a stroke on .ink would outline the labels"


def test_dark_theme_colours_are_the_app_tokens() -> None:
    """`DARK_INK` and `DARK_PAPER` are copies of tokens.css. `.paper` only
    occludes if it IS the page: a retuned `--paper` that this did not follow
    would leave six ring-shaped patches on every dark screen."""
    css = (_REPO / "app" / "src" / "styles" / "tokens.css").read_text()
    dark = css.partition('[data-theme="dark"]')[2]
    tokens: dict[str, str] = {}
    for name, value in re.findall(r"--(paper|ink):\s*(#[0-9a-fA-F]{6})", dark):
        tokens.setdefault(name, value.lower())
    assert tokens == {"paper": DARK_PAPER.lower(), "ink": DARK_INK.lower()}


def test_plate_labels_are_ink_tagged(tmp_path) -> None:
    """These sit on the plate, not on a sticker, so they vanish on a dark page
    unless they flip with it."""
    notation = render_notation(_notation_moves()[0], tmp_path / "n").read_text()
    assert re.search(r'<text[^>]*class="ink"', notation), "move label not tagged"

    overview = render_overview(tmp_path / "o").read_text()
    # the pins' six letters all sit on the plate and flip with it
    assert len(re.findall(r'<text[^>]*class="ink"', overview)) == 6
    assert 'fill="#222"' not in overview and 'fill="#222"' not in notation


def test_pins_paint_nothing_unthemed_on_the_plate(tmp_path) -> None:
    """Every element the pins layout draws on the plate flips with the theme:
    the plate itself (`.bg`), the ribbons' paper fill and ink edges, the
    pins' plate runs, the dots and the letters. The only untagged ink is
    what sits on a sticker: the cube, its layer lines, and a visible face's
    pin from its centre to the face edge."""
    overview = render_overview(tmp_path / "o").read_text()
    untagged_ink_lines = []
    for elem in re.findall(r"<(?:path|polygon|line|circle|rect|text)\b[^>]*>", overview):
        if f'fill="{WHITE}"' in elem:
            assert 'class="bg"' in elem or 'class="paper"' in elem, elem
        if elem.startswith("<line") and f'stroke="{ARROW_COLOR}"' in elem and "class=" not in elem:
            untagged_ink_lines.append(elem)
    # the only untagged ink lines are the visible faces' on-face pin runs
    assert len(untagged_ink_lines) == len(_OV_ON_FACE), untagged_ink_lines
    assert all('stroke-width="2.0"' in e for e in untagged_ink_lines), untagged_ink_lines
    assert overview.count('class="paper"') >= 6 * 3, "band fills and head per ring"
    assert overview.count('class="ink-stroke"') > 6, "ribbon edges, caps and plate pins"


def test_card_diagrams_are_not_themed(tmp_path) -> None:
    """A printed card is ink on paper: no page behind it to show through."""
    assert CARD.themed is False and SCREEN.themed is True
    for content in (
        render(all_cases()[0], tmp_path / "r", style=CARD).read_text(),
        render_step(_step_cases()[0], tmp_path / "s", style=CARD).read_text(),
    ):
        assert "@media" not in content
        assert "<style" not in content, "a card carries no stylesheet at all"
        # The plate keeps its class — an inert hook with no rules to match it —
        # so `_bg` stays one code path, and its `fill=` is what actually prints.
        assert f'<rect class="bg" fill="{WHITE}"' in content


def test_overview_paints_nothing_white_but_the_plate(tmp_path) -> None:
    """The old ribbon rings carried ~30 opaque white occluders that punched
    holes through the cube in dark mode. The hub has one white fill: the
    plate, which the theme can turn off. (The pins' ribbons keep their paper
    fill on purpose; `test_pin_dots_sit_in_depth_order` gates their order.)"""
    overview = render_overview(tmp_path / "o", layout=OVERVIEW_HUB).read_text()
    assert overview.count(f'fill="{WHITE}"') == 1


def test_committed_diagrams_match_the_generator(tmp_path) -> None:
    """`make diagrams` is the only way these files change — a hand-edit fails
    here, the same contract test_logo.py holds over the favicon.

    Every group, not just this module's: `fullsets.py`'s 78 OLL/PLL and 41 F2L
    used to be gated only by the two trees agreeing with *each other*, which a
    hand-edit synced into both would have passed.
    """
    fresh = tmp_path / "gen"
    _render_everything(fresh)

    committed = {str(p.relative_to(_APP_SVG)) for p in _APP_SVG.rglob("*.svg")}
    generated = {str(p.relative_to(fresh)) for p in fresh.rglob("*.svg")}
    assert generated == committed, (
        f"tree membership differs — orphaned: {sorted(committed - generated)}, "
        f"missing: {sorted(generated - committed)}"
    )
    stale = [
        name
        for name in sorted(generated)
        if (_APP_SVG / name).read_bytes() != (fresh / name).read_bytes()
    ]
    assert not stale, f"committed SVGs differ from the generator: {stale}"


def test_the_guide_references_the_one_diagram_tree() -> None:
    """There is ONE committed tree, app/public/diagrams/, and the guide reaches
    up into it. This replaces a byte-identity check between two trees that
    existed only to prove scripts/sync-diagrams.sh had run; the duplication it
    guarded is gone, so what needs guarding instead is the wiring — that every
    figure the guide names resolves, and that nothing has quietly recreated the
    second tree or gone back to the old relative paths.

    `guide/defaults/pdf.yaml` must keep `--root ..` or typst refuses every one
    of these paths for escaping its project root; scripts/guide_stamp.py
    resolves the same references and would fail first if they broke.
    """
    guide_md = _REPO / "guide" / "cubepath.md"
    text = guide_md.read_text()

    refs = re.findall(r"\]\((\.\./app/public/diagrams/[^)\s]+)", text)
    assert refs, "the guide names no diagrams — did the figure paths change?"
    missing = sorted({r for r in refs if not (guide_md.parent / r).is_file()})
    assert not missing, f"guide references figures that do not exist: {missing}"

    assert "figures/generated" not in text, (
        "the guide still points at the deleted guide/figures/generated tree"
    )
    assert not (_REPO / "guide" / "figures").exists(), "the second diagram tree is back"
    assert not (_REPO / "scripts" / "sync-diagrams.sh").exists(), (
        "sync-diagrams.sh is back — there is only one tree to sync to now"
    )

    pdf_yaml = (_REPO / "guide" / "defaults" / "pdf.yaml").read_text()
    assert "--root" in pdf_yaml and '".."' in pdf_yaml, (
        "pdf.yaml lost `--root ..`; typst will reject every ../ figure path"
    )


def test_every_shipped_diagram_is_themed() -> None:
    """The regression the user actually reported, asserted over the real
    shipped tree rather than a fresh render."""
    svgs = sorted(_APP_SVG.rglob("*.svg"))
    assert len(svgs) == EXPECTED_DIAGRAMS, f"expected {EXPECTED_DIAGRAMS}, found {len(svgs)}"
    for svg in svgs:
        content = svg.read_text()
        assert "prefers-color-scheme" in content, f"{svg.name} has no colour-scheme rules"
        assert 'class="bg"' in content, f"{svg.name} has an unreachable plate"


needs_typst = pytest.mark.skipif(
    not all(shutil.which(t) for t in ("typst", "pdftoppm")),
    reason="needs typst + poppler",
)


@needs_typst
def test_the_pdf_never_sees_the_media_block(tmp_path) -> None:
    """The load-bearing claim behind one file serving both outputs: resvg
    applies the class rules but skips every @media, so the plate the guide
    needs survives while the web drops it. Rendered, not assumed — 13 figures
    sit inside a tinted `.algorithm` callout and would otherwise show it."""
    tint = "#e8f4fd"  # callouts.lua, `.algorithm` bg
    svg = render(all_cases()[0], tmp_path)
    # typst resolves paths against --root, so keep the figure beside the source
    shutil.copy(svg, tmp_path / "figure.svg")
    src = tmp_path / "proof.typ"
    src.write_text(
        f'#set page(width: 192pt, height: 192pt, margin: 0pt, fill: rgb("{tint}"))\n'
        '#image("figure.svg", width: 192pt, height: 192pt)\n'
    )
    subprocess.run(
        ["typst", "compile", "--root", str(tmp_path), str(src), str(tmp_path / "p.pdf")],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["pdftoppm", "-r", "36", str(tmp_path / "p.pdf"), str(tmp_path / "out")],
        check=True,
        capture_output=True,
    )
    header, dims, _, pixels = (tmp_path / "out-1.ppm").read_bytes().split(b"\n", 3)
    assert header == b"P6"
    w, h = (int(v) for v in dims.split())

    def px(x: int, y: int) -> tuple[int, int, int]:
        i = (y * w + x) * 3
        return tuple(pixels[i : i + 3])

    # Inside the plate: opaque white. Outside its corner radius: the page tint,
    # which is also what the whole figure would look like if @media had applied.
    assert px(6, 6) == (255, 255, 255), "the guide PDF lost its background plate"
    assert px(4, h // 2) == (255, 255, 255)
    assert px(0, 0) == (232, 244, 253), "sampled the wrong pixel — tint not visible"


# ── The three tiers ───────────────────────────────────────────────────
# Three meanings now share a diagram — full colour "this step solves it", dim
# "an earlier step did, keep it", and a grey "not reached yet" that is NOT the
# same grey as an OLL diagram's "not yellow yet". Every one of those has to be
# separable from the others by measurement, in both palettes, and — the part
# that matters — in the fills that actually reach the emitted SVG. A tier that
# is correct in `dim()` and absent from the file is the bug this work exists to
# fix, so the gates below open the files.
#
# Distances are CIE76 ΔE (`diagrams.delta_e`): ~2.3 is one just-noticeable
# difference. WCAG contrast is quoted alongside wherever the medium is a mono
# laser, which is the only place luminance alone is the right question.

_STICKER_FILL = re.compile(r'fill="(#[0-9A-Fa-f]{6})"')


def _fills(svg_text: str) -> set[str]:
    """Every literal fill colour in a rendered SVG, upper-cased."""
    return {m.upper() for m in _STICKER_FILL.findall(svg_text)}


def test_the_dim_tier_is_a_measurably_different_tone_in_both_palettes() -> None:
    """The tier's whole job. The mix this replaced managed 15.1 ΔE at worst —
    white, which has no chroma to spend — and 1.48:1 in greyscale, barely past
    the 1.36:1 in the player's palette that this pipeline exists to beat."""
    for name, faces in (("SCREEN", SCREEN_FACES), ("CARD", CARD_FACES)):
        for letter, full in faces.items():
            quiet = dim(full)
            assert delta_e(full, quiet) >= DIM_TARGET_DE - 0.5, (
                f"{name} {letter}: dim is only {delta_e(full, quiet):.1f} ΔE from its face"
            )
            # A card is printed, often on a mono laser, where ΔE means nothing.
            assert contrast(full, quiet) >= 1.5, (
                f"{name} {letter}: dim is {contrast(full, quiet):.2f}:1 in greyscale"
            )


def test_dim_white_clears_the_white_it_sits_beside() -> None:
    """The one case a single mix toward grey could not reach: white has no
    chroma, so the whole separation has to be lightness. `orient_corner` holds
    the cube white-up with the entire white face solved, so this is the tone the
    hero image of that lesson is drawn in."""
    assert delta_e(WHITE, dim(WHITE)) >= 29.0
    assert contrast(WHITE, dim(WHITE)) >= 2.2, "dim white would vanish against white"
    # And against the page it is drawn on, which is white in the guide PDF.
    assert contrast(dim(WHITE), "#FFFFFF") >= 2.2


def test_dim_keeps_a_third_of_the_chroma_so_it_still_names_its_face() -> None:
    """A learner reads the dim region to confirm the cross survived, so "some
    colour" is not enough — the tone has to stay recognisably ITS colour."""

    def chroma(hex_color: str) -> float:
        _, a, b = to_lab(hex_color)
        return math.hypot(a, b)

    for name, faces in (("SCREEN", SCREEN_FACES), ("CARD", CARD_FACES)):
        for letter, full in faces.items():
            if chroma(full) < 1:  # white has no hue to keep
                continue
            kept = chroma(dim(full)) / chroma(full)
            assert 0.28 <= kept <= 0.36, f"{name} {letter}: dim kept {kept:.0%} of its chroma"


def test_dim_is_separable_from_the_not_reached_tone_it_shares_a_picture_with() -> None:
    """Dim and not-reached appear side by side in every F2L and step diagram.
    The old ramp put dim yellow 7.2 ΔE from the grey — close enough to read as
    a second grey, which is the opposite of what the tier says."""
    for name, style in (("SCREEN", SCREEN), ("CARD", CARD)):
        for letter, full in style.faces.items():
            gap = delta_e(dim(full), style.unreached)
            assert gap >= 15.0, f"{name} {letter}: dim is {gap:.1f} ΔE from not-reached"


def test_a_full_face_is_separable_from_the_not_reached_tone_too() -> None:
    """The gate above covers the DIM tier; this covers the FULL one, and it is
    the binding constraint on how light "not reached" may be. `step_1_cross`
    puts full-colour WHITE stickers polygon-to-polygon with not-reached ones,
    and white is the only face with no hue to separate it: 15.0 ΔE on SCREEN
    where every other face is 60+. The whole argument in `diagrams.py` for the
    tone's lightness is an argument about THIS number — "going lighter spends
    white-face separation the picture does need" — so it is measured rather
    than reasoned about. The tier sits ON its floor; brightening it fails here
    before it fails anywhere else."""
    for name, style in (("SCREEN", SCREEN), ("CARD", CARD)):
        for letter, full in style.faces.items():
            gap = delta_e(full, style.unreached)
            assert gap >= 15.0, f"{name} {letter}: full is {gap:.1f} ΔE from not-reached"


def test_the_two_greys_are_different_tones() -> None:
    """ "Not yellow yet" and "not reached yet" are different claims and they meet
    on one page — `yellow-cross.mdx` prints step_4_ycross above the three OLL
    cross cases. One token cannot carry both.

    THE SCREEN THRESHOLD IS 8, NOT 12, AND THAT IS THE WEAKER OF TWO GATES ON
    PURPOSE. The two greys never share a FILE, and the gate that enforces that
    is `test_no_diagram_ever_carries_both_greys`, which is absolute. All this
    one has to buy is that they read as different tones when two pictures sit
    adjacent on a page, and 8 ΔE is ~3.5 just-noticeable differences with a hue
    change on top (the mask is neutral, the not-reached tier is warm). The
    threshold was 12 while the tier was `#C0D4E6`, and 12 is what forced that
    tone so light: a neutral can only buy ΔE from the mask with lightness, so
    every point of the gate pushed it further toward the page and toward the
    white face it also has to clear (which
    `test_a_full_face_is_separable_from_the_not_reached_tone_too` now measures).
    Lowering it to 8 is what let the tier come back down to `#D8D5CF`,
    which reads as a grey rather than as a seventh sticker colour and sits
    15.0 ΔE off white instead of 10.2. See diagrams.py for the full trade.

    THE CARD KEEPS 12, because none of that argument is about the card. Its
    palette did not move (`CARD.unreached` is still `#3F3F3F`, print inverts the
    tier), it sits at 13.7 ΔE, and a card is printed on a mono laser where hue
    is gone and only the luminance gap survives — so relaxing the card's floor
    alongside the screen's would have given away a gate for nothing."""
    for name, style, floor in (("SCREEN", SCREEN, 8.0), ("CARD", CARD, 12.0)):
        gap = delta_e(style.masked, style.unreached)
        assert gap >= floor, f"{name}: the two greys are {gap:.1f} ΔE apart"
    # And on the light page the guide prints on, the not-reached tier is the
    # quieter of the two — closer to the paper than the mask is, so "nothing
    # here yet" never outweighs a sticker that is really there. (On a dark app
    # background the order flips, which is inherent to a light neutral on a
    # dark ground and was already true of the single grey this replaced.)
    assert contrast(UNREACHED, "#FFFFFF") < contrast(UNORIENTED, "#FFFFFF")


def test_restyle_never_maps_two_tiers_onto_one_colour() -> None:
    """If a dim tone landed on a face colour — or two tiers on the same output —
    a card would silently say the wrong thing about what is solved."""
    for name, style in (("SCREEN", SCREEN), ("CARD", CARD)):
        remap = _restyle(style)
        assert len(remap) == 14, f"{name}: 6 faces + 6 dim + masked + not-reached"
        assert len(set(remap.values())) == len(remap), f"{name}: two tiers collide"


# ── What actually reaches the page ────────────────────────────────────
# Every assertion below reads a rendered file. The audit this work answers
# found a three-tier model that was correct, tested, and wired to nothing: the
# tests exercised the functions while the renderer called something else. So
# these do not ask `dim()` anything — they ask the SVG.

_TIERED_STEPS = {
    "step_2_corners",
    "step_3_edges",
    "step_4_ycross",
    "step_5_yedges",
    "step_6_ycorners_pos",
    "corner_right",
    "corner_front",
    "corner_up",
    "edge_right",
    "edge_left",
    "orient_corner",
    "orient_right",
    "orient_front",
    "corner_cycle",
    "align_adjacent",
    "align_diagonal",
    "step_oll_done",
    # The edge flip's picture: the centres are built (dim, and seven outer turns
    # cannot touch them) and the pair being turned over is the subject.
    "step_444_flip",
}
# Nothing earlier to preserve — see `_step_cases` for the first three, and
# `_web_steps` for the last three: a course-index card whose whole subject is
# "this is a 4x4" has no earlier step to dim.
_FLAT_STEPS = {
    "step_1_cross",
    "step_flip",
    "step_7_solved",
    "step_anatomy",
    "step_444_centres",
    "step_555_centres",
}


def test_every_shipped_step_diagram_draws_the_tier_its_lesson_needs() -> None:
    """The headline defect, asserted on the shipped tree. `step_2_corners` is
    the hero image of the white-corners lesson and drew the already-solved white
    cross at exactly the saturation of the corners being taught."""
    svgs = {p.stem: p for p in sorted((_APP_SVG / "steps").glob("*.svg"))}
    assert set(svgs) == _TIERED_STEPS | _FLAT_STEPS, sorted(svgs)
    dim_tones = {dim(c).upper() for c in SCREEN_FACES.values()}
    for stem, path in svgs.items():
        present = _fills(path.read_text()) & dim_tones
        if stem in _TIERED_STEPS:
            assert present, f"{stem}: no dim tier reached the file"
        else:
            assert not present, f"{stem}: has nothing earlier-solved but drew {present}"


def test_the_hero_image_separates_the_cross_from_the_corners() -> None:
    """`step_2_corners` names the exact pixels the complaint was about: the two
    cross edges' side stickers, against the four corner stickers beside them."""
    fills = _fills((_APP_SVG / "steps" / "step_2_corners.svg").read_text())
    for face in (RED, GREEN):
        assert face in fills, "the corners being taught are not in full colour"
        assert dim(face).upper() in fills, "the cross under them is not dimmed"
        assert delta_e(face, dim(face)) >= DIM_TARGET_DE - 0.5


def _dir_of(subdir: str, count: int) -> list[Path]:
    """Every SVG in one shipped group, with its size pinned — so a group that
    silently shrank fails here rather than passing an empty loop."""
    svgs = sorted((_APP_SVG / subdir).glob("*.svg"))
    assert len(svgs) == count, f"{subdir}: {len(svgs)} diagrams, expected {count}"
    return svgs


def test_no_diagram_ever_carries_both_greys() -> None:
    """The tonal split is only worth anything if the two never share a file —
    otherwise a reader has to tell two claims apart inside one picture."""
    both = [
        p.relative_to(_APP_SVG)
        for p in sorted(_APP_SVG.rglob("*.svg"))
        if {UNORIENTED, UNREACHED} <= _fills(p.read_text())
    ]
    assert not both, f"diagrams carrying both greys: {both}"


def test_the_oll_plan_views_are_untouched_two_tier_pictures() -> None:
    """Item 3 of the brief, pinned: an OLL diagram has no earlier-solved region
    in frame, so it must keep exactly yellow + the orientation mask and must not
    grow a dim tier."""
    # Directories, plus one FILE: `444-parity/` holds one OLL-style picture and
    # one PLL-style one, so it cannot be globbed as either.
    svgs = [
        *(p for subdir, count in (("oll", 12), ("oll-full", 57)) for p in _dir_of(subdir, count)),
        _APP_SVG / "444-parity" / "444_oll_parity.svg",
    ]
    for svg in svgs:
        assert _fills(svg.read_text()) <= {YELLOW, UNORIENTED, WHITE}, (
            f"{svg.name}: an OLL plan view grew a tier it does not need"
        )


def test_every_shipped_pll_plan_view_dims_the_oll_face() -> None:
    """PLL runs after OLL, so the U face is a finished result to preserve — the
    dim tier — while the side bands are what the step permutes. Before this,
    49 files carried zero dim and zero grey: every sticker full saturation."""
    quiet = dim(YELLOW).upper()
    groups: list[tuple[list[Path], int]] = [
        (_dir_of("pll", 6), 3),
        (_dir_of("pll-full", 21), 3),
        # One FILE, not a directory: the 4x4 parity pair splits across idioms.
        ([_APP_SVG / "444-parity" / "444_pll_pure_e.svg"], 4),
    ]
    for svgs, n in groups:
        for svg in svgs:
            text = svg.read_text()
            fills = _fills(text)
            assert quiet in fills, f"{svg.name}: the OLL-solved U face is not dimmed"
            assert YELLOW not in fills, f"{svg.name}: full yellow survived on a PLL diagram"
            assert text.count(f'fill="{dim(YELLOW)}"') == n * n, (
                f"{svg.name}: dim yellow is not exactly the {n}x{n} U face"
            )
            # The bands PLL actually permutes stay loud.
            assert fills & {RED, GREEN, ORANGE, BLUE}, f"{svg.name}: no full-colour side band"
            for band in fills & {RED, GREEN, ORANGE, BLUE}:
                assert delta_e(band, quiet) >= 30.0, f"{svg.name}: {band} too close to dim yellow"


def test_f2l_diagrams_are_themed_and_mark_the_slot(tmp_path) -> None:
    cases = f2l_cases()
    assert len(cases) == 41
    for case in cases[:3] + cases[-3:]:
        content = render_slot(case, tmp_path).read_text()
        assert "prefers-color-scheme" in content, f"{case.name}: no colour-scheme rules"
        assert content.count('class="bg"') == 1, f"{case.name}: expected exactly one plate"
        # Two slot outlines, one per visible face, drawn as unfilled polygons.
        outlines = re.findall(r'<polygon[^>]*fill="none"[^>]*/>', content)
        assert len(outlines) == 2, f"{case.name}: {len(outlines)} slot outlines, expected 2"
        for outline in outlines:
            assert f'stroke-width="{SLOT_STROKE_W}"' in outline


def test_every_shipped_f2l_diagram_marks_its_slot() -> None:
    """Asserted over the shipped tree, not a fresh render: a slot marker that
    silently stopped being drawn would leave 41 plausible-looking pictures with
    no indication of where the pair is going."""
    svgs = sorted((_APP_SVG / "f2l").glob("*.svg"))
    assert len(svgs) == 41, f"expected 41 F2L diagrams, found {len(svgs)}"
    for svg in svgs:
        assert svg.read_text().count('fill="none"') == 2, f"{svg.name}: slot marker missing"


# ── The icon filename contract ────────────────────────────────────────
# gen-cases.mjs synthesises every case's diagram path by string-building a
# filename that this generator has to have produced — two independent slug and
# zero-padding implementations that must agree, asserted nowhere until now. A
# divergence ships a broken image on every affected case with both halves' own
# gates green, which is exactly the failure this repo pins everywhere else.

_GENERATED_TS = _REPO / "app" / "src" / "data" / "fullsets.gen.ts"
# Curated cases declare their icon by hand. `444.oll-parity` is one: every case
# in JPerm's 4x4 OLL set has parity spliced into a last-layer algorithm, so the
# bare parity case is not in the extraction and cannot be a generated entry.
# A curated icon pointing at a file nobody wrote breaks exactly the same way a
# generated one does, so both files are searched wherever icons are checked.
_CURATED_TS = _REPO / "app" / "src" / "data" / "algs.ts"


def _declared_icons() -> str:
    return _GENERATED_TS.read_text() + _CURATED_TS.read_text()


def test_every_case_icon_resolves_to_a_shipped_diagram() -> None:
    icons = re.findall(r'"?icon"?:\s*"([^"]+)"', _declared_icons())
    assert icons, "no icon paths at all — did gen-cases.mjs stop emitting them?"
    missing = [i for i in icons if not (_APP_SVG.parent / i.lstrip("/")).is_file()]
    assert not missing, f"the app points at diagrams that do not exist: {missing}"


def test_the_f2l_set_is_fully_iconed() -> None:
    """The hole this work closed: /reference rendered all 41 F2L tiles as empty
    numbered boxes because no F2L case carried an icon."""
    text = _GENERATED_TS.read_text()
    f2l_icons = re.findall(r'"/diagrams/f2l/([a-z0-9_]+\.svg)"', text)
    assert sorted(f2l_icons) == [f"f2l_{n:02d}.svg" for n in range(1, 42)]
    for case in f2l_cases():
        assert f"/diagrams/f2l/{case.name}.svg" in text, f"{case.name} has no icon in the app"


# ── The 4x4 sets ──────────────────────────────────────────────────────
# 49 diagrams whose state Python cannot derive and must not learn to: cube.py
# is a gated 3x3 mirror, and the states come from the cubing.js kpuzzle through
# app/src/data/extracted/case-states.json. That makes these tests unusual —
# they cannot re-derive the answer, so instead they check the things a wrong
# picture could not survive: that the same renderer reproduces the 78 shipped
# 3x3 diagrams exactly, that every 4x4 picture is a physically possible cube,
# and that its arrows and its JPerm label agree with its own drawn colours.


def _444_parity_cases() -> list[CubeDiagram]:
    """The two 4x4 pictures `parity_cases()` produces — the third is the 5x5.
    Everything 4x4 that reaches the tree."""
    return [c for c in parity_cases() if c.n == 4]


# The 4x4 views the renderer is checked against. `big_oll_cases`/`big_pll_cases`
# write nothing (the course teaches reduction — see fullsets.TAUGHT_BIG_CUBE);
# only `444_parity_cases` reaches the tree, which is why it is the only entry
# with a directory beside it.
_BIG_SETS = (
    ("4x4 OLL (not shipped)", big_oll_cases, 27),
    ("4x4 PLL (not shipped)", big_pll_cases, 22),
    ("444-parity", _444_parity_cases, 2),
)


def test_the_four_by_four_sets_are_complete_and_four_wide() -> None:
    for subdir, builder, expected in _BIG_SETS:
        cases = builder()
        assert len(cases) == expected, f"{subdir}: {len(cases)} cases, expected {expected}"
        assert len({c.name for c in cases}) == expected, f"{subdir}: duplicate filenames"
        for case in cases:
            assert case.n == 4, f"{case.name}: drawn as a {case.n}x{case.n}"
            assert len(case.u_face) == 16, f"{case.name}: {len(case.u_face)} U facelets"
            for strip in (case.top_side, case.right_side, case.bottom_side, case.left_side):
                assert len(strip) == 4, f"{case.name}: {len(strip)}-cell side band"


def test_the_state_driven_renderer_reproduces_the_simulator_driven_one() -> None:
    """THE cross-language gate, at the level that matters here.

    The 4x4 diagrams are drawn from case-states.json by code that no Python
    cube model can check. So the same code is pointed at the 3x3 OLL and PLL
    sets, where cube.py derives the answer independently — and every drawn
    field must match: the U mask, all four side bands, and, for PLL, the arrows
    read off the piece permutation. 78 cases agreeing across two cube models
    is what makes the 49 that only one model can reach trustworthy.
    """
    drawn = ("u_face", "top_side", "right_side", "bottom_side", "left_side", "swaps", "cycles")
    for from_json, from_sim in (
        (plan_oll_cases("oll", "oll_full"), full_oll_cases()),
        (plan_pll_cases("pll", "pll_full"), full_pll_cases()),
    ):
        assert len(from_json) == len(from_sim) and from_json, "set sizes differ"
        for a, b in zip(from_json, from_sim, strict=True):
            for attr in drawn:
                assert getattr(a, attr) == getattr(b, attr), (
                    f"{b.name}: {attr} differs between the kpuzzle export and cube.py"
                )


def test_the_two_halves_agree_on_what_colour_each_face_is() -> None:
    """cubing.js ships its own palette (U white, F green); this repo uses
    another (U yellow, F red). The JSON therefore names FACES and carries the
    colour scheme separately, and that scheme is the single point where the two
    vocabularies meet — so it is checked, not assumed."""
    from cubepath.cube import COLORS

    named = case_states()["faceColors"]
    assert set(named) == set(COLORS), "the export and cube.py disagree on the six faces"
    for face, letter in COLORS.items():
        assert named[face].startswith(letter), f"{face}: {named[face]} vs cube.py {letter!r}"


def _u_layer_pieces(case) -> list[list[str]]:
    """Every last-layer piece of a plan-view diagram, as the list of colours it
    shows. Derived from the drawing's own geometry: a side band cell sits
    against the U cell the renderer draws it beside, so band i of `top` touches
    U row 0 column i, and a corner touches two bands."""
    n = case.n
    bands = {
        "top": [(0, i) for i in range(n)],
        "bottom": [(n - 1, i) for i in range(n)],
        "left": [(i, 0) for i in range(n)],
        "right": [(i, n - 1) for i in range(n)],
    }
    strips = {
        "top": case.top_side,
        "bottom": case.bottom_side,
        "left": case.left_side,
        "right": case.right_side,
    }
    touching: dict[tuple[int, int], list[str]] = {}
    for band, cells in bands.items():
        for i, cell in enumerate(cells):
            touching.setdefault(cell, []).append(strips[band][i])
    return [[case.u_face[r * n + c], *sides] for (r, c), sides in touching.items()]


def test_every_oll_picture_is_a_physically_possible_cube() -> None:
    """A last-layer piece has exactly one yellow sticker — it is either up or
    it is not. Checked on the 4x4 set, which nothing else can check, and on the
    3x3 set, which proves the check itself is right.

    This is also the only gate that would catch a side band drawn against the
    wrong edge of the U grid: mis-index one band and some piece ends up with
    two yellows or none.
    """
    for label, cases in (("3x3", full_oll_cases()), ("4x4", big_oll_cases())):
        assert cases
        for case in cases:
            for piece in _u_layer_pieces(case):
                yellow = piece.count(YELLOW)
                assert yellow == 1, f"{label} {case.name}: a piece shows {yellow} yellow stickers"


# Each corner's two side stickers, as (band, index into that band), in the
# ring order top -> right -> bottom -> left. Handedness is uniform around the
# ring, which is what makes the twist below comparable between corners.
_CORNER_BANDS = {
    "tl": ("left", "top"),
    "tr": ("top", "right"),
    "br": ("right", "bottom"),
    "bl": ("bottom", "left"),
}


def _corner_twists(case) -> list[int]:
    """Each corner's orientation: 0 yellow up, 1 yellow on the next face
    clockwise, 2 yellow on the one after."""
    n = case.n
    strips = {
        "top": case.top_side,
        "right": case.right_side,
        "bottom": case.bottom_side,
        "left": case.left_side,
    }
    cell = {"tl": (0, 0), "tr": (0, n - 1), "br": (n - 1, n - 1), "bl": (n - 1, 0)}
    end = {
        ("tl", "top"): 0,
        ("tl", "left"): 0,
        ("tr", "top"): -1,
        ("tr", "right"): 0,
        ("br", "right"): -1,
        ("br", "bottom"): -1,
        ("bl", "bottom"): 0,
        ("bl", "left"): -1,
    }
    twists = []
    for corner, (incoming, outgoing) in _CORNER_BANDS.items():
        r, c = cell[corner]
        if case.u_face[r * n + c] == YELLOW:
            twists.append(0)
        elif strips[outgoing][end[corner, outgoing]] == YELLOW:
            twists.append(1)
        else:
            assert strips[incoming][end[corner, incoming]] == YELLOW, (
                f"{case.name}: the {corner} corner has no yellow sticker at all"
            )
            twists.append(2)
    return twists


def test_every_oll_picture_obeys_the_corner_twist_law() -> None:
    """Corner orientations sum to zero mod 3 on any legal cube — you cannot
    twist one corner in place, at any size.

    This is the check that reaches furthest into the 4x4 states Python cannot
    model: it is a law about the physical puzzle, not about this repo's
    conventions, and a state export that mis-derived an orientation would break
    it. That it holds for all 57 3x3 pictures, which cube.py derives
    independently, is what shows the reading below is the right one.
    """
    for label, cases in (("3x3", full_oll_cases()), ("4x4", big_oll_cases())):
        for case in cases:
            twists = _corner_twists(case)
            assert sum(twists) % 3 == 0, f"{label} {case.name}: corner twists {twists}"


def _claimed_permutation(case) -> dict[str, str]:
    """The movement a diagram's arrows claim: anchor -> destination."""
    perm: dict[str, str] = {}
    for a, b in case.swaps:
        perm[a], perm[b] = b, a
    for cycle in case.cycles:
        for i, pos in enumerate(cycle):
            perm[pos] = cycle[(i + 1) % len(cycle)]
    return perm


def _drawn_permutation(case) -> dict[str, str]:
    """The movement the diagram's own side colours imply, re-read from the
    finished CubeDiagram rather than from the state it was built from."""
    letters = {v: k for k, v in SCREEN_FACES.items()}
    sides = {
        "top": [letters[c] for c in case.top_side],
        "right": [letters[c] for c in case.right_side],
        "bottom": [letters[c] for c in case.bottom_side],
        "left": [letters[c] for c in case.left_side],
    }
    return _plan_permutation(sides, case.n)


def test_four_by_four_pll_arrows_match_the_colours_beside_them() -> None:
    """Arrows are derived, so this is not a spelling check: it re-reads the
    permutation out of the finished picture and requires the arrows to agree
    with it, which is the property a reader actually relies on."""
    for case in big_pll_cases():
        real = _drawn_permutation(case)
        claimed = _claimed_permutation(case)
        for pos, dest in real.items():
            if pos == dest:
                assert pos not in claimed, f"{case.name}: arrow on a solved piece at {pos}"
            else:
                assert claimed.get(pos) == dest, (
                    f"{case.name}: the piece at {pos} belongs at {dest}, "
                    f"arrows say {claimed.get(pos)}"
                )


# ── Net whole-cube rotation ───────────────────────────────────────────
# Five of the 21 primary PLL algorithms end with the cube in a different
# orientation than they started: Aa and Ja open with `x`, Ab and E with `x'`,
# and V has a `y` in the middle. Deriving a case by inverting such an algorithm
# on a solved cube lands the last layer somewhere other than the top, and any
# mask or highlight computed in that frame disagrees with the frame the picture
# is drawn in — which is exactly how a 3-cycle ends up with one or two of its
# three pieces marked.
#
# `fullsets.case_state` handles it by searching the 24 whole-cube rotations for
# the one pre-rotation that brings every centre home, and composing it on the
# LEFT of the inverse. The two tests below are what makes that a guarantee
# rather than a comment: the first names the five algorithms so a data change
# cannot quietly drop one, and the second requires the arrow count in every
# shipped PLL picture to equal the number of pieces its permutation actually
# moves — the property a frame mismatch breaks first.
_NET_ROTATION_PLL = {"Aa", "Ab", "E", "Ja", "V"}


def test_the_pll_algorithms_that_rotate_the_whole_cube_are_known() -> None:
    from cubepath.cube import COLORS, invert_algorithm
    from cubepath.fullsets import _load, case_state

    rotating = set()
    for case in _load()["pll"]:
        cube = Cube.solved()
        cube.apply(invert_algorithm(case["algs"][0]))
        if not all(cube.faces[f][4] == COLORS[f] for f in COLORS):
            rotating.add(case["name"])
        # ... and the derived case is always brought back to yellow-up.
        home = case_state(case["algs"][0])
        assert all(home.faces[f][4] == COLORS[f] for f in COLORS), (
            f"{case['name']}: the case state kept a net rotation"
        )
    assert rotating == _NET_ROTATION_PLL, f"the rotating set changed: {sorted(rotating)}"


def _pll_diagrams_everywhere():
    """Every PLL picture this repo ships, at either cube size and in either
    palette's source data: 6 curated + 21 guide + 21 card + 22 4x4."""
    return (
        _pll_corner_cases()
        + _pll_edge_cases()
        + full_pll_cases()
        + card_pll_cases()
        + big_pll_cases()
    )


def test_every_pll_diagram_marks_exactly_the_pieces_its_permutation_moves() -> None:
    """The count gate. A picture whose arrows touch fewer anchors than the
    permutation moves is the visible symptom of a frame mismatch, and it is the
    one a reader cannot recover from: they learn the wrong case."""
    checked = 0
    for case in _pll_diagrams_everywhere():
        drawn = _drawn_permutation(case)
        moved = {a for a, dest in drawn.items() if a != dest}
        touched = {a for pair in case.swaps for a in pair}
        touched |= {a for pair in case.dashed_swaps for a in pair}
        touched |= {a for cycle in case.cycles for a in cycle}
        assert touched == moved, (
            f"{case.name}: arrows touch {sorted(touched)}, the permutation moves {sorted(moved)}"
        )
        counted = 2 * (len(case.swaps) + len(case.dashed_swaps))
        counted += sum(len(c) for c in case.cycles)
        assert counted == len(moved), (
            f"{case.name}: {counted} arrow endpoints for {len(moved)} moved pieces"
        )
        checked += 1
    assert checked == 6 + 21 + 21 + 22, checked


def test_the_arrows_that_reach_the_svg_are_the_ones_the_case_declares(tmp_path) -> None:
    """And the same count, read back out of the rendered file. `_draw_swap`
    gives a swap both markers and `_draw_cycle` gives each segment only an end
    marker, so the two marker counts recover the swap and cycle totals without
    the renderer being asked."""
    for case in _pll_corner_cases() + _pll_edge_cases() + full_pll_cases() + big_pll_cases():
        text = render(case, tmp_path).read_text()
        starts = text.count('marker-start="url(#arrowhead-rev)"')
        ends = text.count('marker-end="url(#arrowhead)"')
        swaps = len(case.swaps) + len(case.dashed_swaps)
        assert starts == swaps, f"{case.name}: {starts} swap arrows drawn, {swaps} declared"
        segments = sum(len(c) for c in case.cycles)
        assert ends - starts == segments, (
            f"{case.name}: {ends - starts} cycle segments drawn, {segments} declared"
        )
        drawn = _drawn_permutation(case)
        moved = len([a for a, dest in drawn.items() if a != dest])
        assert 2 * starts + segments == moved, (
            f"{case.name}: the file marks {2 * starts + segments} pieces, {moved} move"
        )


# A quarter turn of the top layer, on the eight anchors: F->L->B->R->F.
_AUF = {
    "bottom": "left",
    "left": "top",
    "top": "right",
    "right": "bottom",
    "bl": "tl",
    "tl": "tr",
    "tr": "br",
    "br": "bl",
}
_CORNER_ANCHORS = ("tl", "tr", "br", "bl")


def _corner_shape(perm: dict[str, str]) -> str:
    moved = [c for c in _CORNER_ANCHORS if perm[c] != c]
    if not moved:
        return "none"
    if len(moved) == 2:
        a, b = moved
        return "adjacent" if _AUF[a] == b or _AUF[b] == a else "diagonal"
    return f"{len(moved)}-moved"


def test_every_pll_picture_matches_its_jperm_group_up_to_auf() -> None:
    """JPerm groups PLL by what the corners do — "Edges Only", "Adjacent Corner
    Swap", "Diagonal Corner Swap" — and that description is true UP TO AUF: an
    adjacent swap composed with a U turn reads as a corner 3-cycle.

    The diagrams do not normalise the AUF away, deliberately: each picture is
    the state its own printed algorithm solves, so the algorithm beside it
    works on the state drawn. 7 of the 21 shipped 3x3 PLL diagrams already show
    such an offset (Z-perm among them), so this is the existing convention, not
    a new one. What must still hold is the label, up to a U turn — and it is
    checked on the 3x3 set too, which is what shows the check is honest rather
    than tuned to make the 4x4 set pass.
    """
    groups = {"Edges Only": "none", "Adjacent Corner Swap": "adjacent"}
    groups["Diagonal Corner Swap"] = "diagonal"
    for set_name, cases in (("pll", full_pll_cases()), ("4x4pll", big_pll_cases())):
        states = [c for c in case_states()["cases"] if c["set"] == set_name]
        assert len(states) == len(cases)
        for state, case in zip(states, cases, strict=True):
            want = groups[state["group"]]
            perm = _drawn_permutation(case)
            shapes = []
            for _ in range(4):
                shapes.append(_corner_shape(perm))
                # Undo one AUF: the piece in slot s came from the slot before it.
                perm = {_AUF[s]: perm[s] for s in perm}
            assert want in shapes, (
                f"{case.name}: JPerm calls it {state['group']!r}, but the corners read "
                f"{shapes} under the four AUFs"
            )


def test_every_four_by_four_picture_is_distinct() -> None:
    """Two cases that draw the same picture would be unlearnable — and would be
    the signature of a state export that collapsed a distinction."""
    for subdir, builder, _ in _BIG_SETS:
        seen: dict[tuple[object, ...], str] = {}
        for case in builder():
            key = (
                tuple(case.u_face),
                tuple(case.top_side),
                tuple(case.right_side),
                tuple(case.bottom_side),
                tuple(case.left_side),
                tuple(sorted(case.swaps)),
                tuple(sorted(map(tuple, case.cycles))),
            )
            assert key not in seen, f"{subdir}: {case.name} draws the same picture as {seen[key]}"
            seen[key] = case.name


def test_every_shipped_four_by_four_diagram_is_present_and_four_wide() -> None:
    """Asserted over the shipped tree: a 4x4 diagram that silently regressed to
    a 3x3 grid would still be a valid, themed, plausible SVG."""
    svgs = sorted((_APP_SVG / "444-parity").glob("*.svg"))
    assert {p.stem for p in svgs} == {c.name for c in _444_parity_cases()}
    for svg in svgs:
        content = svg.read_text()
        # 16 U cells + 4 bands of 4 + the plate.
        assert content.count("<rect") == 33, f"{svg.name}: not a 4x4 grid"
        assert 'viewBox="0 0 234 234"' in content, f"{svg.name}: wrong viewBox"


def test_the_unshipped_big_cube_sets_stay_unshipped() -> None:
    """The course teaches REDUCTION, so a big cube becomes a 3x3 and the 3x3
    sets finish it. The 27 4x4 OLL, 22 4x4 PLL and 13 5x5 L2E cases are
    one-look optimisations locked out of the UI, and 61 SVGs no page can reach
    are 61 SVGs that rot unnoticed. They were generated once; a call added back
    to `render_big_sets` would recreate the trees, so the trees are the gate."""
    for gone in ("444-oll", "444-pll", "555-l2e"):
        assert not (_APP_SVG / gone).exists(), f"{gone}/ is back — see fullsets.TAUGHT_BIG_CUBE"
    assert {c.name for c in parity_cases()} == {
        "444_oll_parity",
        "444_pll_pure_e",
        "555_l2e_6",
    }


def test_the_four_by_four_sets_are_fully_iconed() -> None:
    """The same filename contract the F2L set has: gen-cases.mjs builds each
    icon path by string surgery on the case id, and this generator builds the
    filename the same way. Nothing but a test makes the two agree."""
    text = _declared_icons()
    icons = re.findall(r'"/diagrams/444-parity/([a-z0-9_]+\.svg)"', text)
    assert sorted(icons) == sorted(f"{c.name}.svg" for c in _444_parity_cases())


def test_the_5x5_parity_picture_is_drawn_and_iconed() -> None:
    """The 5x5 had NO diagram at all — /reference rendered its one unlocked
    case as a text tile reading "6". One picture now, not thirteen: the course
    teaches reduction, so edge parity is the only 5x5 case it teaches."""
    cases = l2e_cases()
    assert len(cases) == 1
    icons = re.findall(r'"/diagrams/555-parity/([a-z0-9_]+\.svg)"', _declared_icons())
    assert sorted(icons) == sorted(f"{c.name}.svg" for c in cases)
    for case in cases:
        assert case.n == 5, f"{case.name}: drawn as a {case.n}x{case.n}"
        assert len(case.u_face) == 25
        for strip in (case.top_side, case.right_side, case.bottom_side, case.left_side):
            assert len(strip) == 5


def test_the_l2e_plan_view_is_three_tier_and_never_the_oll_mask() -> None:
    """L2E happens during reduction, before there is a last layer — the
    yellow/not-yellow mask would be answering a question the step does not ask,
    and dimming the U face flat (the PLL treatment) would delete the case,
    because a flipped pair shows the SIDE colour on top."""
    for svg in _dir_of("555-parity", 1):
        fills = _fills(svg.read_text())
        assert UNORIENTED not in fills, f"{svg.name}: an L2E view used the orientation mask"
        assert UNREACHED in fills, f"{svg.name}: the unreached corners are not greyed"
        # Full colour somewhere — the case — and dim somewhere: what pairing
        # already finished. A picture with only one of the two is not a step.
        assert fills & {YELLOW, RED, GREEN, ORANGE, BLUE}, f"{svg.name}: nothing in full colour"
        assert any(dim(c).upper() in fills for c in (YELLOW, RED, GREEN, ORANGE, BLUE)), (
            f"{svg.name}: nothing dimmed — the already-paired groups are shouting"
        )


def test_the_three_taught_big_cube_cases_are_the_same_three_everywhere() -> None:
    """One list, written in three languages, and nothing but this makes them
    agree: Python decides what is DRAWN, gen-cases.mjs decides what carries an
    ICON, and unlocks.ts decides what the UI SHOWS. A case that fell out of one
    of the three would ship as a row with a broken image, or a picture nobody
    can reach — both of which have happened here before."""
    from cubepath.fullsets import TAUGHT_BIG_CUBE

    # Python: the constant now SELECTS what parity_cases() renders (each entry
    # names the exported set its case is drawn from), so this compares the
    # declared list against the pictures actually produced rather than against
    # a second hand-written union of the same ids.
    assert {diagram_name(i) for i in TAUGHT_BIG_CUBE} == {c.name for c in parity_cases()}
    for case_id, (source, why) in TAUGHT_BIG_CUBE.items():
        assert case_id in {c["id"] for c in _states_of(source)}, f"{case_id} not in {source}"
        assert why.strip(), f"{case_id}: no description"

    # gen-cases.mjs: the ids its icon table carries.
    gen = (_REPO / "app" / "scripts" / "gen-cases.mjs").read_text()
    table = re.search(r"const TAUGHT_BIG_CUBE = \{(.*?)\};", gen, re.S)
    assert table, "gen-cases.mjs no longer declares TAUGHT_BIG_CUBE"
    icons = dict(re.findall(r'"([\w.-]+)":\s*"(/diagrams/[^"]+)"', table.group(1)))
    assert set(icons) == set(TAUGHT_BIG_CUBE)

    # ...and the VALUES have to be live too. `444.oll-parity` is the one id the
    # generator cannot build (it is curated in algs.ts, which carries its own
    # icon), so its path here is a second copy of that literal. Compare them, or
    # renaming the SVG in one file would leave the other silently wrong.
    curated = _CURATED_TS.read_text()
    compared = 0
    for case_id, icon in icons.items():
        block = re.search(rf'id:\s*"{re.escape(case_id)}",\s*\n\s*icon:\s*"([^"]+)"', curated)
        if not block:
            continue  # generated ids carry no curated literal to compare against
        compared += 1
        assert block.group(1) == icon, (
            f"{case_id}: algs.ts says {block.group(1)}, gen-cases.mjs says {icon}"
        )
    # ...and the skip above must never become the whole loop. Exactly one id is
    # curated (`444.oll-parity`); if a reformat of algs.ts moved `icon:` off the
    # line after `id:`, every match would fail and this cross-check would pass
    # by comparing nothing at all — which is the failure it exists to prevent.
    assert compared == 1, (
        f"{compared} curated icon literals matched in algs.ts, expected 1 — the "
        f"comparison is not running"
    )

    # unlocks.ts: the ids it keeps visible while the one-look sets are locked.
    unlocks = (_REPO / "app" / "src" / "lib" / "unlocks.ts").read_text()
    taught = set()
    for name in ("TAUGHT_444_CASES", "TAUGHT_555_CASES"):
        block = re.search(rf"{name}[^=]*=\s*new Set\(\[(.*?)\]\)", unlocks, re.S)
        assert block, f"unlocks.ts no longer declares {name} as a plain literal"
        taught |= set(re.findall(r'"([\w.-]+)"', block.group(1)))
    assert taught == set(TAUGHT_BIG_CUBE)


def test_the_diagram_filename_rule_is_a_pure_function_of_the_case_id() -> None:
    """Pinned because gen-cases.mjs re-implements it in JavaScript."""
    assert diagram_name("444.oll.u-f") == "444_oll_u_f"
    assert diagram_name("444.pll.o-minus") == "444_pll_o_minus"
    for case in big_oll_cases() + big_pll_cases():
        assert re.fullmatch(r"[a-z0-9_]+", case.name), case.name


def test_a_diagram_cannot_disagree_with_its_own_cube_order() -> None:
    """The failure this closes: hand a 4x4 renderer nine facelets and it draws
    a perfectly convincing picture of nothing."""
    from cubepath.diagrams import CubeDiagram

    with pytest.raises(ValueError, match="U facelets"):
        CubeDiagram(name="x", label="x", category="444_parity", u_face=[YELLOW] * 9, n=4)
    with pytest.raises(ValueError, match="has 3 cells"):
        CubeDiagram(
            name="x",
            label="x",
            category="444_parity",
            u_face=[YELLOW] * 16,
            top_side=[YELLOW] * 3,
            n=4,
        )
    # An unstated band still fills to the right width for the cube it is on.
    bare = CubeDiagram(name="x", label="x", category="444_parity", u_face=[YELLOW] * 16, n=4)
    assert bare.left_side


def test_an_unknown_category_cannot_be_written_to_the_tree_root() -> None:
    """It used to be: `_case_subdir` fell through to "", which put the file in
    the root of guide/figures/generated, where sync-diagrams.sh (which copies
    subdirectories) would never have shipped it."""
    from cubepath.diagrams import _case_subdir

    # Deliberately a category no cube has. This test used to name "555_l2e",
    # which stopped being unknown the moment the 5x5 set became drawable — a
    # negative test aimed at a real value passes for the wrong reason.
    with pytest.raises(ValueError, match="unknown diagram category"):
        _case_subdir("666_never")


def test_edge_anchors_sit_at_the_centre_of_the_edge_not_a_cell() -> None:
    """On a 4x4 an "edge" is a dedge — two wings — so its arrow must start
    between them. Anchoring it on a cell instead would point every 4x4 edge
    arrow half a sticker off, which is the kind of wrong that still looks
    right."""
    step = 42  # CELL + GAP
    for name in ("top", "bottom", "left", "right"):
        x4, y4 = _arrow_pos(name, 4)
        x3, y3 = _arrow_pos(name, 3)
        moving = x4 if name in ("top", "bottom") else y4
        wings = [_arrow_pos("tl", 4), _arrow_pos("br", 4)]
        # Midway between the two middle cell centres, i.e. half a step past one.
        assert moving in (
            wings[0][0] + 1.5 * step,
            wings[0][1] + 1.5 * step,
        ), f"{name}: anchored at a cell centre, not between the wings"
        # The 3x3 anchors are unchanged: one cell IS the whole edge there.
        assert (x3, y3) == _arrow_pos(name), f"{name}: the 3x3 anchor moved"
    for name in ("tl", "tr", "bl", "br"):
        x, y = _arrow_pos(name, 4)
        assert 34 <= x <= 200 and 34 <= y <= 200, f"{name}: {x},{y} outside the 4x4 grid"


def _u_face_cells(case) -> tuple[list[int], list[int]]:
    """(corner indices, edge-wing indices) into a plan view's U face."""
    n = case.n
    corners, wings = [], []
    for r in range(n):
        for c in range(n):
            on_r, on_c = r in (0, n - 1), c in (0, n - 1)
            if on_r and on_c:
                corners.append(r * n + c)
            elif on_r or on_c:
                wings.append(r * n + c)
    return corners, wings


def test_every_four_by_four_oll_picture_shows_exactly_one_flipped_dedge() -> None:
    """The parity signature — and the whole reason these 27 diagrams exist.

    Every case in JPerm's 4x4 OLL set carries OLL parity: exactly one dedge is
    flipped, which is impossible on a 3x3 and unrepresentable in a three-cell
    row. In the picture it must read as two ADJACENT wings grey on top with
    their yellow on the side. I checked the same count independently against
    the cubing.js kpuzzle orbits — 2 flipped EDGES wings in all 27 cases, with
    no facelet map involved — so this pins the picture to the puzzle, not to
    the export.
    """
    for case in big_oll_cases():
        _, wings = _u_face_cells(case)
        flipped = [i for i in wings if case.u_face[i] != YELLOW]
        assert len(flipped) == 2, f"{case.name}: {len(flipped)} wings grey, expected one dedge"
        a, b = ((i // case.n, i % case.n) for i in flipped)
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1, (
            f"{case.name}: the two flipped wings at {a} and {b} are not one dedge"
        )


def test_every_four_by_four_oll_picture_shows_the_corner_count_jperm_names() -> None:
    """JPerm groups this set by how many corners are already oriented — "4
    Corners", "2 Corners", "1 Corner", "0 Corners" — so the group name is an
    independent statement of what the picture must show, written by someone who
    never saw this renderer. Counted against the kpuzzle too: 0/2/3/4 corners
    twisted, matching 4/2/1/0 oriented, in all 27 cases.
    """
    states = {c["name"]: c for c in case_states()["cases"] if c["set"] == "4x4oll"}
    for case in big_oll_cases():
        name = case.label.split(" — ")[0]
        group = states[name]["group"]
        expected = int(group.split()[0])
        corners, _ = _u_face_cells(case)
        oriented = sum(1 for i in corners if case.u_face[i] == YELLOW)
        assert oriented == expected, (
            f"{case.name}: JPerm calls it {group!r}, the picture shows {oriented} oriented"
        )
