"""Diagram ↔ algorithm consistency tests.

These tests close the F4 blind spot: every published diagram is derived from
its algorithm's pre-state, arrows must match the actual piece permutation,
and the guide's tables must match the canonical algorithm data.
"""

import re
from pathlib import Path

from cubepath.algs import ALGORITHMS
from cubepath.cube import Cube, parse_algorithm, state_before
from cubepath.diagrams import (
    _SIM_COLOR,
    GREY,
    YELLOW,
    _align_edge_cases,
    _corner_case_steps,
    _corner_pos_case,
    _edge_case_steps,
    _oll_corner_cases,
    _oll_cross_cases,
    _orient_corner_case,
    _orient_corner_cases_15,
    _pll_corner_cases,
    _pll_edge_cases,
    _step_cases,
    _step_sticker_color,
    _u_layer_views,
)

GUIDE = Path(__file__).resolve().parents[3] / "guide" / "cubepath.md"

# ── Frame anchors ────────────────────────────────────────────────────
# Freeze the plan-view conventions (U row 0 = back; side strips as viewed
# from above, front at bottom) with two asymmetric hand-checked cases.


def _case(cases, name):
    return next(c for c in cases if c.name == name)


def test_sune_anchor():
    sune = _case(_oll_corner_cases(), "oll_sune")
    assert sune.u_face == [GREY, YELLOW, GREY, YELLOW, YELLOW, YELLOW, YELLOW, YELLOW, GREY]
    assert sune.top_side == [YELLOW, GREY, GREY]
    assert sune.right_side == [YELLOW, GREY, GREY]
    assert sune.bottom_side == [GREY, GREY, YELLOW]
    assert sune.left_side == [GREY, GREY, GREY]


def test_antisune_anchor():
    a = _case(_oll_corner_cases(), "oll_antisune")
    assert a.u_face == [GREY, YELLOW, YELLOW, YELLOW, YELLOW, YELLOW, GREY, YELLOW, GREY]
    assert a.top_side == [GREY, GREY, GREY]
    assert a.right_side == [GREY, GREY, YELLOW]
    assert a.bottom_side == [YELLOW, GREY, GREY]
    assert a.left_side == [YELLOW, GREY, GREY]


def test_hook_is_phase1_angle():
    """Hook diagram shows the L in back-left — the angle where F-sexy-F' → Line."""
    hook = _case(_oll_cross_cases(), "oll_hook")
    assert hook.u_face[1] == YELLOW and hook.u_face[3] == YELLOW  # back + left edges
    assert hook.u_face[5] == GREY and hook.u_face[7] == GREY


def test_phase1_cross_chain():
    """The Phase-1 flow Dot →(F-sexy-F')→ Hook →(F-sexy-F')→ Line → solved works
    when the learner holds Hook at back-left and Line horizontal, as pictured."""
    f_alg = ALGORITHMS["F-sexy-F'"]
    # Hook held with L in back-left → Line (horizontal)
    c = state_before(ALGORITHMS["f-sexy-f'"])
    c.apply("y2")
    c.apply(f_alg)
    u = c.faces["U"]
    assert u[3] == "Y" and u[5] == "Y" and u[1] != "Y" and u[7] != "Y"
    # Line horizontal → cross solved
    c2 = state_before(f_alg)
    c2.apply(f_alg)
    assert c2.u_cross_solved()


# ── OCLL coverage (F1 regression guard) ──────────────────────────────
# The seven corner-orientation algorithms must cover all seven OCLL twist
# classes exactly once — no gaps (like the old missing H), no duplicates.

_OCLL_ALGS = [
    "Sune",
    "Anti-Sune",
    "Pi",
    "Headlights",
    "Double Headlights",
    "Chameleon",
    "Bowtie",
]

# Per corner position (ring order tl→tr→br→bl, clockwise from above):
# the sticker locations of the two side faces, in (preceding, following)
# ring order. Encoded as (face, index) in the simulator's state.
_CORNER_SIDES = {
    "tl": (("L", 0), ("B", 2)),
    "tr": (("B", 0), ("R", 2)),
    "br": (("R", 0), ("F", 2)),
    "bl": (("F", 0), ("L", 2)),
}
_CORNER_UP = {"tl": 0, "tr": 2, "br": 8, "bl": 6}
_RING = ["tl", "tr", "br", "bl"]


def _ocll_class(cube: Cube) -> str:
    """Canonical corner-twist pattern, invariant under U-layer view rotation."""
    pattern = []
    for pos in _RING:
        if cube.faces["U"][_CORNER_UP[pos]] == "Y":
            pattern.append("U")
        else:
            (pf, pi), (ff, fi) = _CORNER_SIDES[pos]
            if cube.faces[pf][pi] == "Y":
                pattern.append("P")
            else:
                assert cube.faces[ff][fi] == "Y", f"corner {pos} has no yellow sticker"
                pattern.append("F")
    rotations = ["".join(pattern[i:] + pattern[:i]) for i in range(4)]
    return min(rotations)


def test_ocll_full_coverage():
    classes = {}
    for name in _OCLL_ALGS:
        cube = state_before(ALGORITHMS[name])
        cls = _ocll_class(cube)
        assert cls != "UUUU", f"{name} pre-state has all corners oriented"
        assert cls not in classes, f"{name} duplicates the case of {classes.get(cls)}"
        classes[cls] = name
    # There are exactly 7 non-solved OCLL classes; 7 distinct = full coverage.
    assert len(classes) == 7


# ── PLL arrows match the real piece permutation ──────────────────────

# Where each U-layer position's stickers live in the simulator state.
_EDGE_STICKER = {"top": ("B", 1), "right": ("R", 1), "bottom": ("F", 1), "left": ("L", 1)}
_EDGE_HOME = {"R": "bottom", "G": "right", "O": "top", "B": "left"}
_CORNER_HOME = {
    frozenset({"R", "G"}): "br",
    frozenset({"R", "B"}): "bl",
    frozenset({"O", "G"}): "tr",
    frozenset({"O", "B"}): "tl",
}


def _u_layer_permutation(cube: Cube) -> dict[str, str]:
    """Map each U-layer position to where its piece belongs (its destination)."""
    perm = {}
    for pos, (face, idx) in _EDGE_STICKER.items():
        perm[pos] = _EDGE_HOME[cube.faces[face][idx]]
    for pos, ((f1, i1), (f2, i2)) in _CORNER_SIDES.items():
        perm[pos] = _CORNER_HOME[frozenset({cube.faces[f1][i1], cube.faces[f2][i2]})]
    return perm


def _arrows_to_permutation(case) -> dict[str, str]:
    """The movement the diagram's arrows claim: position → destination."""
    perm = {}
    for a, b in list(case.swaps) + list(case.dashed_swaps):
        perm[a] = b
        perm[b] = a
    for cycle in case.cycles:
        for i, pos in enumerate(cycle):
            perm[pos] = cycle[(i + 1) % len(cycle)]
    return perm


def test_pll_arrows_match_permutation():
    for case in _pll_corner_cases() + _pll_edge_cases():
        cube = state_before(ALGORITHMS[case.label.removesuffix(" Perm")])
        real = _u_layer_permutation(cube)
        claimed = _arrows_to_permutation(case)
        for pos, dest in real.items():
            if pos == dest:
                assert pos not in claimed, f"{case.name}: arrow on solved piece {pos}"
            else:
                assert claimed.get(pos) == dest, (
                    f"{case.name}: piece at {pos} moves to {dest}, arrows say {claimed.get(pos)}"
                )


def test_pll_side_colors_match_prestate():
    """Every PLL diagram side sticker equals the algorithm's true pre-state color."""
    from cubepath.diagrams import _SIM_COLOR

    for case in _pll_corner_cases() + _pll_edge_cases():
        alg = ALGORITHMS[case.label.removesuffix(" Perm")]
        _, sides = _u_layer_views(state_before(alg))
        for side_name, attr in [
            ("top", case.top_side),
            ("right", case.right_side),
            ("bottom", case.bottom_side),
            ("left", case.left_side),
        ]:
            expected = [_SIM_COLOR[s] for s in sides[side_name]]
            assert attr == expected, f"{case.name} {side_name}: {attr} != {expected}"


# ── Step-diagram corner chirality ────────────────────────────────────
# A corner's three stickers wind around it with a fixed handedness — a
# diagram showing the mirror order depicts a physically impossible cube.
# The legal (U, F, R) triples are DERIVED from the simulator here, never
# hardcoded (hardcoding the set is exactly how the mirror bug shipped).

_HEX_TO_SIM = {v: k for k, v in _SIM_COLOR.items()}


def _ufr_triple(cube: Cube) -> tuple[str, str, str]:
    """The visible (U, F, R) stickers of the corner at up-front-right."""
    u, f, r = (cube.visible_sticker(face, 2, 2) for face in ("U", "F", "R"))
    return (u, f, r)


def _legal_ufr_triples() -> set[tuple[str, str, str]]:
    """All 24 legal (corner, twist) placements at UFR, read off whole-cube
    rotations of a solved cube — chirality-correct by construction."""
    triples = set()
    for r1 in ("", "x", "x2", "x'", "z", "z'"):
        for r2 in ("", "y", "y2", "y'"):
            c = Cube.solved()
            for r in (r1, r2):
                if r:
                    c.apply(r)
            triples.add(_ufr_triple(c))
    assert len(triples) == 24  # 8 corners × 3 twists, all distinct
    return triples


def _white_corner_triples_from_moves() -> set[tuple[str, str, str]]:
    """Every orientation the white-red-green corner reaches at UFR under face
    moves (breadth-first to depth 3) — the mechanical ground truth."""
    moves = [base + suffix for base in "RUFLBD" for suffix in ("", "'", "2")]
    found = set()
    frontier = [Cube.solved()]
    for _ in range(3):
        successors = []
        for cube in frontier:
            for m in moves:
                c2 = cube.copy()
                c2.apply_move(m)
                t = _ufr_triple(c2)
                if set(t) == {"W", "R", "G"}:
                    found.add(t)
                successors.append(c2)
        frontier = successors
    return found


def _all_step_diagrams():
    return (
        _step_cases()
        + _corner_case_steps()
        + _edge_case_steps()
        + [_orient_corner_case()]
        + _orient_corner_cases_15()
        + [_corner_pos_case()]
        + _align_edge_cases()
    )


def _step_ufr_triple(step) -> tuple[str, str, str] | None:
    """The diagram's (U, F, R) sticker triple at up-front-right, as simulator
    color letters — or None when the corner isn't fully colored."""
    colors = tuple(
        _step_sticker_color(face, 2, 2, step.solved, step.face_colors, step.overrides)
        for face in ("U", "F", "R")
    )
    if GREY in colors:
        return None
    u, f, r = (_HEX_TO_SIM[c] for c in colors)
    return (u, f, r)


def test_white_corner_has_exactly_three_orientations():
    """Mechanical derivation sanity: face moves reach the white-red-green
    corner at UFR in exactly the 3 legal twists, matching the rotation set."""
    derived = _white_corner_triples_from_moves()
    from_rotations = {t for t in _legal_ufr_triples() if set(t) == {"W", "R", "G"}}
    assert len(derived) == 3
    assert derived == from_rotations


def test_step_diagram_corners_are_physically_possible():
    """Every fully-colored UFR corner in a step diagram is a legal orientation
    of a real corner — mirror-image sticker orders cannot ship."""
    legal = _legal_ufr_triples()
    checked = 0
    for step in _all_step_diagrams():
        triple = _step_ufr_triple(step)
        if triple is None:
            continue
        assert triple in legal, f"{step.filename}: impossible corner {triple} at (U, F, R)"
        checked += 1
    # solved, 3 corner insertions, orient_corner, orient_right, orient_front
    assert checked >= 7


def test_corner_insertion_cases_match_captions():
    """White Right/Front/Up show white on the R/F/U face, with the other two
    stickers in the (simulator-derived) legal order for that twist."""
    white_at = {"corner_right": 2, "corner_front": 1, "corner_up": 0}
    wrg = _white_corner_triples_from_moves()
    by_filename = {s.filename: s for s in _corner_case_steps()}
    assert by_filename.keys() == white_at.keys()
    for filename, w_index in white_at.items():
        (expected,) = (t for t in wrg if t[w_index] == "W")
        assert _step_ufr_triple(by_filename[filename]) == expected, filename


# ── Guide ↔ data consistency ─────────────────────────────────────────


def _algs_from_cell(cell: str) -> str:
    """Extract the algorithm from a markdown cell.

    Unwraps `[...]{.trig-*}` highlight spans (used with and without backticks)
    and strips backticks, leaving plain move text.
    """
    cell = re.sub(r"\[([^\]]+)\]\{[^}]*\}", r"\1", cell)
    return cell.replace("`", " ").strip()


def test_guide_tables_match_canonical_algorithms():
    """Every named algorithm in the guide's tables matches algs.py exactly."""
    text = GUIDE.read_text()
    checked = set()
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        name_match = None
        alg_cell = None
        for cell in cells:
            m = re.match(r"\*\*(.+?)\*\*", cell)
            if m:
                name_match = m.group(1).split("—")[0].strip()
            elif re.search(r"`[^`]+`", cell) and "figures/" not in cell:
                alg_cell = cell
        # Reference-table rows: | phase | alg | Name | step |
        if name_match is None and len(cells) == 4 and cells[0] in {"1", "1.5", "2", "3"}:
            name_match = cells[2]
            alg_cell = cells[1]
        if not name_match or not alg_cell or name_match not in ALGORITHMS:
            continue
        extracted = _algs_from_cell(alg_cell)
        if not extracted or "×" in extracted or "Repeat" in alg_cell:
            continue
        expected = parse_algorithm(ALGORITHMS[name_match])
        actual = parse_algorithm(extracted)
        assert actual == expected, f"{name_match}: guide has {actual}, algs.py has {expected}"
        checked.add(name_match)
    # Each core algorithm must be checked at least once (present in the guide).
    for required in ALGORITHMS:
        assert required in checked, f"{required} not found (or not checkable) in the guide"
